"""İki sabit modeli öğrenci oturumuna bağlayan açık ve yerel kurallar."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import copy
import json
import time
import uuid

import joblib
import pandas as pd

from features import FEATURES
from experimental_features import (
    FORMAT_FEATURES, RECENT_FEATURES, ExperimentalHistory,
    experimental_features_before_answer, observe_experimental_exercise,
)
from profiles import PROFILE_FEATURES, ProfileHistory, observe_for_profile, profile_snapshot
from learning_evidence import attempt_summary,pattern_guidance

ROOT = Path(__file__).resolve().parents[1]
TEXT = 'reverse_translate'
LISTEN = 'listen'
ACTIVE_FEATURES = FEATURES + FORMAT_FEATURES + RECENT_FEATURES
MODEL_VERSION = 'lr12-format-recent10-v1'
LEGACY_MODEL_VERSION = 'lr6-v1'
MODEL_PATH = ROOT / 'outputs/dev_feature_experiments/format_and_recent_model.joblib'
VISUAL_WORDS = ['cat','dog','bird','fish','apple','banana','book','car']


class TutorError(ValueError):
    pass


def normalized_answer(value):
    return value.strip().strip('.,!?;:\"\' ').lower()


def exercise_from_attempt(attempt, index):
    """Uygulamada zaten tek hedef var; eğitimdeki aynı geçmiş işlevleri kullanılır."""
    return {
        'learner_id': attempt['learner_id'], 'exercise_id': attempt['id'],
        'source_order': index, 'days': attempt['day'], 'source_format': attempt['format'],
        'tokens': [{'instance_id': attempt['id'] + '-word', 'word_key': attempt['word_id'],
                    'pos': 'NOUN', 'correct': attempt['correct'], 'source_error': 1-attempt['correct']}],
    }


class TutorEngine:
    def __init__(self):
        self.catalog = json.loads((ROOT / 'data/prototype/catalog.json').read_text(encoding='utf-8'))
        self.words = {word['id']: word for word in self.catalog['words']}
        self.audio_keys = {word_id: uuid.uuid4().hex for word_id in self.words}
        self.audio_words = {key: word_id for word_id, key in self.audio_keys.items()}
        self.topics = {topic['id']: topic for topic in self.catalog['topics']}
        self.logistic = joblib.load(MODEL_PATH)
        self.kmeans = joblib.load(ROOT / 'outputs/kmeans_first_run/kmeans_model.joblib')
        comparison = json.loads((ROOT / 'outputs/kmeans_first_run/comparison.json').read_text(encoding='utf-8'))
        chosen = next(candidate for candidate in comparison['candidates'] if candidate['selected'])
        self.groups = {group['model_label']: group for group in chosen['groups']}
        assert self.logistic.named_steps['classifier'].classes_.tolist() == [0, 1]
        assert self.logistic.feature_names_in_.tolist() == ACTIVE_FEATURES
        assert len(self.words) >= 24

    def new_learner(self, name, topics):
        selected = list(dict.fromkeys(topics))
        if not selected or any(topic not in self.topics for topic in selected):
            raise TutorError('En az bir konu seçmelisin.')
        name = (name or 'Öğrenci').strip()
        if not name or len(name) > 40:
            raise TutorError('Adın veya takma adın 1–40 karakter olmalı.')
        state = {'id': uuid.uuid4().hex, 'name': name, 'topics': selected, 'created_at': time.time(),
                 'active_model_version': MODEL_VERSION,
                 'diagnostic_complete': False, 'practice_rounds': 0, 'attempts': [],
                 'session': None, 'feedback': None, 'stage': 'question'}
        self.start_session(state, diagnostic=True)
        return state

    def audio_url(self, word_id):
        return '/audio/' + self.audio_keys[word_id] + '.wav'

    def histories(self, state):
        learning, profile = ExperimentalHistory(), ProfileHistory()
        for index, attempt in enumerate(state['attempts']):
            exercise = exercise_from_attempt(attempt, index)
            observe_experimental_exercise(exercise, learning)
            observe_for_profile(exercise, profile)
        return learning, profile

    def score(self, state, words, mode):
        history, _ = self.histories(state)
        rows = [experimental_features_before_answer(history, word['id'], mode) for word in words]
        frame = pd.DataFrame(rows, columns=ACTIVE_FEATURES)
        probabilities = self.logistic.predict_proba(frame)[:, 1]
        return {word['id']: {'p_correct': float(prob), 'features': row,
                            'history': self.history_snapshot(history, word['id'], mode)}
                for word, prob, row in zip(words, probabilities, rows)}

    @staticmethod
    def history_snapshot(history, word, mode):
        def pair(n, s):
            return {'count': n, 'correct': s, 'smoothed_rate': (s+1)/(n+2)}
        snapshot = {
            'general': pair(history.target_count, history.correct_count),
            'word': pair(*history.words.get(word, (0, 0))),
            'format': pair(*history.formats.get(mode, (0, 0))),
            'word_format': pair(*history.word_formats.get((word, mode), (0, 0))),
            'recent': pair(sum(n for n, _ in history.recent_exercises), sum(s for _, s in history.recent_exercises)),
        }
        snapshot['recent']['exercises'] = len(history.recent_exercises)
        return snapshot

    def upgrade_state(self, state):
        """Eski cevapları koru; yalnız henüz cevaplanmamış sorunun tahminini yenile."""
        pending = (state.get('session') or {}).get('pending')
        if pending and pending.get('model_version') != MODEL_VERSION:
            word = self.words[pending['word_id']]
            score = self.score(state, [word], pending['format'])[word['id']]
            pending.update({'id': uuid.uuid4().hex, 'model_version': MODEL_VERSION,
                            'features_before': score['features'], 'p_correct_before': score['p_correct'],
                            'history_before': score['history'],
                            'reason': 'Devam eden soru önceki sürümde seçilmişti. Tahmini güncel modelle, yalnız tamamlanmış geçmişinden yeniden hesaplandı.'})
            state['model_update_notice'] = 'Devam eden sorunun tahmini güncellendi. Önceki cevapların korundu.'
        state['active_model_version'] = MODEL_VERSION

    def diagnostic_plan(self):
        by_topic = {topic: [w for w in self.catalog['words'] if w['topic_id'] == topic] for topic in self.topics}
        plan = []
        for position in range(4):
            for topic in self.topics:
                plan.append({'word_id': by_topic[topic][position]['id'],
                             'format': TEXT if len(plan) % 2 == 0 else LISTEN})
        return plan

    def start_session(self, state, diagnostic=False):
        old = state.get('session')
        if old and not old['completed']:
            raise TutorError('Önce devam eden çalışmanı tamamla.')
        if old and not diagnostic and state['stage'] != 'summary':
            raise TutorError('Yeni tura geçmeden önce mevcut çalışmanın sonuçlarını gör.')
        if not diagnostic and not state['diagnostic_complete']:
            raise TutorError('Önce başlangıç değerlendirmesini tamamla.')
        if not diagnostic:
            state['practice_rounds'] += 1
        state['session'] = {
            'id': uuid.uuid4().hex, 'kind': 'diagnostic' if diagnostic else 'practice',
            'round_number': state['practice_rounds'], 'position': 0,
            'total': 12 if diagnostic else 6, 'completed': False, 'pending': None,
            'word_counts': {}, 'wrong_counts': {}, 'answers': [],
            'plan': self.diagnostic_plan() if diagnostic else None,
        }
        state['feedback'] = None
        state['stage'] = 'question'
        self.prepare_question(state)

    def prepare_question(self, state):
        state.pop('visual_task', None)
        session = state['session']
        position = session['position']
        if session['kind'] == 'diagnostic':
            item = session['plan'][position]
            word = self.words[item['word_id']]
            mode = item['format']
            category = 'diagnostic'
            reason = 'Başlangıç planı sabit: üç konudan dengeli metin ve dinleme soruları.'
            score = self.score(state, [word], mode)[word['id']]
        else:
            mode = TEXT if position % 2 == 0 else LISTEN
            requested = ['review', 'review', 'new', 'review', 'review', 'new'][position]
            seen = {attempt['word_id'] for attempt in state['attempts']}
            recent = {attempt['word_id'] for attempt in state['attempts'][-2:]}
            candidates = [w for w in self.catalog['words']
                          if w['topic_id'] in state['topics'] and w['id'] not in recent
                          and session['word_counts'].get(w['id'], 0) < 2
                          and session['wrong_counts'].get(w['id'], 0) < 2]
            scores = self.score(state, candidates, mode) if candidates else {}
            category = requested
            pool = [w for w in candidates if (w['id'] in seen) == (category == 'review')]
            if category == 'review':
                due = [w for w in pool if w['id'] in state.get('visual_review_queue', [])]
                if due:
                    pool = due
            fallback = False
            if not pool:
                category = 'new' if requested == 'review' else 'review'
                pool = [w for w in candidates if (w['id'] in seen) == (category == 'review')]
                fallback = True
            if not pool:
                raise TutorError('Bu tur için uygun kelime kalmadı. Yeni bir çalışma turu gerekli.')
            pool.sort(key=lambda w: ((scores[w['id']]['p_correct'] if category == 'review' else -scores[w['id']]['p_correct']), w['id']))
            word = pool[0]
            score = scores[word['id']]
            reason = ('İlgi alanındaki tekrar kelimeleri arasında tahmini doğruluğu daha düşük olanlara öncelik verildi.'
                      if category == 'review' else
                      'İlgi alanındaki yeni kelimeler arasında tahmini doğruluğu daha yüksek olanla başlandı.')
            if fallback:
                reason = ('Bu adımda planlanan kelime havuzu uygun değildi; diğer havuz kullanıldı. ' + reason)
            if word['id'] in state.get('visual_review_queue', []):
                reason = 'Görsel çalışmadan sonraki metin/dinleme kontrolü; tekrar aralığı ve tur sınırları korunarak seçildi. ' + reason
        session['pending'] = {
            'id': uuid.uuid4().hex, 'word_id': word['id'], 'format': mode,
            'category': category, 'reason': reason, 'p_correct_before': score['p_correct'],
            'features_before': score['features'], 'started_at': time.time(),
            'history_before': score['history'], 'model_version': MODEL_VERSION,
        }
        state['model_update_notice'] = None

    def answer(self, state, question_id, answer):
        session = state['session']
        question = session['pending'] if session else None
        if question and question.get('model_version') != MODEL_VERSION:
            raise TutorError('Sorunun tahmini güncellendi. Cevaplamadan önce sayfayı yenile.')
        if state['stage'] != 'question' or not question or question['id'] != question_id:
            raise TutorError('Bu soru zaten cevaplandı veya güncellendi. Güncel ekranı kullan.')
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 80:
            raise TutorError('Cevap alanına kısa bir İngilizce kelime yaz.')
        word = self.words[question['word_id']]
        correct = int(normalized_answer(answer) == word['target_word'])
        now = time.time()
        prior_day = state['attempts'][-1]['day'] if state['attempts'] else 0.0
        attempt = {
            'id': question['id'], 'learner_id': state['id'], 'session_id': session['id'],
            'kind': session['kind'], 'word_id': word['id'], 'topic_id': word['topic_id'],
            'format': question['format'], 'category': question['category'],
            'submitted': answer.strip(), 'correct': correct,
            'day': max(prior_day, (now-state['created_at'])/86400),
            'timestamp': datetime.fromtimestamp(now, timezone.utc).isoformat(),
            'elapsed_seconds_LOG_ONLY': max(0, now-question['started_at']),
            'p_correct_before': question['p_correct_before'], 'features_before': question['features_before'],
            'selection_reason': question['reason'],
            'model_version': question['model_version'], 'history_before': copy.deepcopy(question['history_before']),
        }
        # Cevap kaydedildikten sonra iki model için geçmiş yeniden hesaplanabilir.
        state['attempts'].append(attempt)
        if word['id'] in state.get('visual_review_queue', []):
            state['visual_review_queue'].remove(word['id'])
            attempt['after_visual_review'] = True
        updated_history, _ = self.histories(state)
        history_after = self.history_snapshot(updated_history, word['id'], question['format'])
        attempt['history_after'] = history_after
        session['answers'].append(attempt['id'])
        session['word_counts'][word['id']] = session['word_counts'].get(word['id'], 0)+1
        if not correct:
            session['wrong_counts'][word['id']] = session['wrong_counts'].get(word['id'], 0)+1
        session['position'] += 1
        session['pending'] = None
        state['feedback'] = {
            'correct': correct, 'submitted': answer.strip(), 'expected': word['target_word'],
            'turkish': word['turkish'], 'example': word['example'], 'audio': word['audio'],
            'category': question['category'], 'p_correct_before': question['p_correct_before'],
            'features_before': question['features_before'], 'reason': question['reason'],
            'deferred': session['wrong_counts'].get(word['id'], 0) >= 2,
            'last_question': session['position'] == session['total'],
            'model_version': question['model_version'],
            'history_update': {'before': copy.deepcopy(question['history_before']), 'after': history_after},
        }
        state['stage'] = 'feedback'
        if session['position'] == session['total']:
            session['completed'] = True
            if session['kind'] == 'diagnostic':
                state['diagnostic_complete'] = True

    def next_step(self, state):
        if state['stage'] != 'feedback':
            raise TutorError('Devam etmeden önce mevcut soruyu cevapla.')
        state['feedback'] = None
        if state['session']['completed']:
            state['stage'] = 'summary'
        else:
            state['stage'] = 'question'
            self.prepare_question(state)

    def prepare_visual(self, state):
        if not state['diagnostic_complete'] or state['stage'] == 'question':
            raise TutorError('Görsel çalışma için önce mevcut çalışmanın cevabını tamamla.')
        if state.get('visual_task'):
            return
        errors = {a['word_id'] for a in state['attempts'] if not a['correct']}
        candidates = [self.words[w] for w in VISUAL_WORDS if w in errors and self.words[w]['topic_id'] in state['topics']]
        if not candidates:
            raise TutorError('Görsel bankasındaki seçili konu kelimelerinde henüz yanlış kaydın yok.')
        scores = self.score(state, candidates, TEXT)
        word = min(candidates,key=lambda w:(scores[w['id']]['p_correct'],w['id']))
        others = [w for w in VISUAL_WORDS if w != word['id']][:2]
        options = [word['id']]+others
        options.sort(key=lambda w: uuid.uuid4().hex)
        state['visual_task'] = {'id':uuid.uuid4().hex,'word_id':word['id'],'options':options,
                                'selection_model_version':MODEL_VERSION,'selection_text_p':scores[word['id']]['p_correct']}

    def answer_visual(self, state, task_id, choice):
        task = state.get('visual_task')
        if not task or task['id'] != task_id or choice not in task['options'] or task.get('answered'):
            raise TutorError('Güncel görsel çalışmayı kullan.')
        task.update(answered=True,correct=int(choice==task['word_id']))
        state.setdefault('visual_attempts',[]).append({**task,'choice':choice})
        queue = state.setdefault('visual_review_queue',[])
        if task['word_id'] not in queue:
            queue.append(task['word_id'])

    def progress(self, state):
        attempts = state['attempts']
        modes = {}
        for key, mode in [('text', TEXT), ('listen', LISTEN)]:
            records = [a for a in attempts if a['format'] == mode]
            modes[key] = {'count': len(records), 'correct': sum(a['correct'] for a in records),
                          'rate': sum(a['correct'] for a in records)/len(records) if records else None}
        _, profile_history = self.histories(state)
        snapshot = profile_snapshot(state['id'], profile_history)
        profile = {'status': snapshot['status'], 'counts': snapshot['observations_in_window'],
                   'features': snapshot['features'], 'group': None}
        if snapshot['features']:
            frame = pd.DataFrame([snapshot['features']], columns=PROFILE_FEATURES)
            raw = int(self.kmeans.predict(frame)[0])
            reference = self.groups[raw]
            profile['group'] = {'number': reference['display_group'],
                                'reference_students': reference['students'],
                                'reference_center': reference['center_original_scale']}
        chart, correct_so_far = [], 0
        for index, attempt in enumerate(attempts, 1):
            correct_so_far += attempt['correct']
            chart.append({'index': index, 'rate': correct_so_far/index, 'timestamp': attempt['timestamp']})
        return {'total': len(attempts), 'correct': correct_so_far,
                'evidence':attempt_summary(attempts,self.words,self.topics),
                'guidance':pattern_guidance(profile),
                'rate': correct_so_far/len(attempts) if attempts else None,
                'modes': modes, 'profile': profile, 'chart': chart,
                'recent': [{'word': self.words[a['word_id']]['target_word'],
                            'format': a['format'], 'correct': a['correct'], 'timestamp': a['timestamp']}
                           for a in attempts[-8:][::-1]]}

    def payload(self, state):
        session = state['session']
        public_session = {key: session[key] for key in ('id', 'kind', 'round_number', 'position', 'total', 'completed')}
        results = [a for a in state['attempts'] if a['session_id'] == session['id']]
        public_session['correct'] = sum(a['correct'] for a in results)
        public_session['categories'] = dict(Counter(a['category'] for a in results))
        public_session['wrong_words'] = list(dict.fromkeys(self.words[a['word_id']]['target_word'] for a in results if not a['correct']))
        question = None
        if session['pending']:
            q = session['pending']
            word = self.words[q['word_id']]
            question = {'id': q['id'], 'mode': q['format'], 'category': q['category'],
                        'topic': self.topics[word['topic_id']]['title'],
                        'prompt': word['turkish'] if q['format'] == TEXT else None,
                        'audio': self.audio_url(word['id']) if q['format'] == LISTEN else None,
                        'prediction': {'p_correct': q['p_correct_before'], 'model_version': q['model_version'],
                                       'history': copy.deepcopy(q['history_before'])}}
            question['letter_hint'] = {'first': word['target_word'][0], 'length': len(word['target_word'])} if q['format'] == TEXT else None
            if session['kind'] == 'diagnostic':
                question['prediction'] = None
        feedback = copy.deepcopy(state['feedback'])
        if feedback:
            feedback['audio'] = self.audio_url(feedback['expected'])
            feedback.setdefault('model_version', LEGACY_MODEL_VERSION)
            if session['kind'] == 'diagnostic':
                feedback['p_correct_before'] = None
        visual = None
        task = state.get('visual_task')
        if task:
            visual = {'id':task['id'],'image':'/pilot-image/'+self.audio_keys[task['word_id']]+'.svg',
                      'options':task['options'],'answered':task.get('answered',False),
                      'reason':'Yanlış kaydı olan uygun kelimeler, metin tekrarı için model tahminine göre sıralandı. Görsel soru için olasılık hesaplanmaz.'}
            if task.get('answered'):
                visual.update(correct=task['correct'],expected=task['word_id'],example=self.words[task['word_id']]['example'])
        return {'learner': {'id': state['id'], 'name': state['name'], 'topics': state['topics']},
                'visual':visual,
                'model': {'version': MODEL_VERSION, 'raw_features': len(ACTIVE_FEATURES)},
                'notice': state.get('model_update_notice'),
                'stage': state['stage'], 'diagnostic_complete': state['diagnostic_complete'],
                'session': public_session, 'question': question,
                'feedback': feedback, 'progress': self.progress(state)}
