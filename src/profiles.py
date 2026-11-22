"""Tamamlanmış alıştırmalardan iki boyutlu, geçici öğrenci profili hazırlar."""
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json


WINDOW = 6
PROFILE_FEATURES = ['text_target_accuracy', 'listen_target_accuracy']
FORMATS = ('reverse_translate', 'listen')


def select_target(tokens):
    """Sonuca bakmadan: ilk alfabetik isim; yoksa ilk alfabetik kelime."""
    alphabetic = [token for token in tokens if token['word_key'].isalpha()]
    nouns = [token for token in alphabetic if token['pos'] in ('NOUN', 'PROPN')]
    eligible = nouns or alphabetic
    return eligible[0] if eligible else None


@dataclass
class ProfileHistory:
    windows: dict = field(default_factory=lambda: {mode: deque(maxlen=WINDOW) for mode in FORMATS})
    available: dict = field(default_factory=lambda: {mode: 0 for mode in FORMATS})
    last_key: tuple = (-1.0, -1)


def observe_for_profile(exercise, history):
    """Bir alıştırma en fazla bir gözlem üretir; süreler kullanılmaz."""
    assert exercise['source_format'] in FORMATS
    chronology_key = (exercise['days'], exercise['source_order'])
    assert chronology_key >= history.last_key
    target = select_target(exercise['tokens'])
    history.last_key = chronology_key
    if target is None:
        return False
    correct = target['correct']
    assert correct in (0, 1)
    mode = exercise['source_format']
    history.windows[mode].append({
        'exercise_id': exercise['exercise_id'],
        'instance_id': target['instance_id'],
        'target_word': target['word_key'],
        'correct': correct,
        'day': exercise['days'],
    })
    history.available[mode] += 1
    return True


def profile_snapshot(learner_id, history):
    counts = {mode: len(history.windows[mode]) for mode in FORMATS}
    result = {
        'learner_id': learner_id,
        'status': 'provisional' if all(n == WINDOW for n in counts.values()) else 'insufficient_history',
        'observations_in_window': counts,
        'total_available_exercises': dict(history.available),
        'features': None,
        'windows': {mode: list(history.windows[mode]) for mode in FORMATS},
    }
    if result['status'] == 'provisional':
        result['features'] = {
            'text_target_accuracy': sum(t['correct'] for t in history.windows['reverse_translate']) / WINDOW,
            'listen_target_accuracy': sum(t['correct'] for t in history.windows['listen']) / WINDOW,
        }
    return result


def load_train_profiles(path):
    histories = defaultdict(ProfileHistory)
    seen_exercises = set()
    skipped = 0
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            exercise = json.loads(line)
            assert exercise['split'] == 'train'
            assert exercise['exercise_id'] not in seen_exercises
            seen_exercises.add(exercise['exercise_id'])
            if not observe_for_profile(exercise, histories[exercise['learner_id']]):
                skipped += 1
    snapshots = [profile_snapshot(learner, histories[learner]) for learner in sorted(histories)]
    return snapshots, {'exercises_read': len(seen_exercises), 'no_alphabetic_target': skipped}
