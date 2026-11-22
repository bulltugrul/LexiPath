"""Dört kelime, üç ayrı hedef ve gerçek saatle gecikmeli kontrol.

Seçenekli hedefleri SLAM'in dinleyerek-yazma göreviyle eşitlemez.
"""
import copy
import time
import uuid
from random import SystemRandom
from difflib import SequenceMatcher
from tutor_engine import TutorError, TEXT, LISTEN, normalized_answer, MODEL_VERSION
from learning_evidence import pilot_evidence,pattern_guidance

WORDS = ['cat', 'dog', 'apple', 'book']
SKILLS = ['writing', 'recognition', 'listening']
DELAY_SECONDS = 24*60*60


class Pilot:
    def __init__(self, engine, clock=time.time):
        self.engine, self.clock = engine, clock

    def new(self, name, include_listen_write=True):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
            raise TutorError('1–40 karakterli bir ad veya takma ad gir.')
        state = {'id':uuid.uuid4().hex,'name':name.strip(),'created_at':self.clock(),
                 'stage':'measurement','cycle':1,'attempts':[],'records':[],
                 'position':0,'order':WORDS.copy(),'teaching_words':[],
                 'assisted_index':0,'common_control_version':int(include_listen_write),
                 'due_at':None,'pending':None}
        self.prepare(state)
        return state

    @staticmethod
    def target_key(word, skill):
        return word+':'+skill

    def upgrade(self, state):
        """Eski kayıtları silmeden hedef başına geçerli kontrol sürümünü belirle."""
        # Başlamış eski ölçümleri geriye dönük uzatma; yeni pilotlar 16 soruyla başlar.
        state.setdefault('common_control_version',0)
        if 'target_epochs' in state:
            return
        state['target_epochs']={}
        state['target_due']={}
        for word in WORDS:
            for skill in SKILLS:
                key=self.target_key(word,skill)
                rows=[r for r in state['records'] if r.get('word')==word and
                      r.get('skill')==skill and r['stage'] in
                      ['teaching','assisted','independent','delayed']]
                epoch=max([r['cycle'] for r in rows] or [1])
                state['target_epochs'][key]=epoch
                independent=[r for r in rows if r['cycle']==epoch and r['stage']=='independent']
                if independent:
                    block=[r['at'] for r in state['records'] if r['cycle']==epoch and r['stage']=='independent']
                    state['target_due'][key]=max(block)+DELAY_SECONDS
        state['control_targets']=[{'word':w,'skill':k} for w in WORDS for k in SKILLS]
        # Eski sunucuda yeniden öğretim açılmış, henüz ilk kart kaydedilmemiş olabilir.
        # Bu durumda önceki kontrolü yeni öğretimin kanıtı olarak kullanma.
        if state['cycle']>1 and state['stage'] in ['teaching','assisted','assisted_feedback']:
            targets=[{'word':w,'skill':k} for w in state['teaching_words']
                     for k in self.needs(state,w) if not self.is_paused(state,w,k)]
            state['reteach_targets']=targets
            state['control_targets']=copy.deepcopy(targets)
            for t in targets:
                key=self.target_key(t['word'],t['skill'])
                state['target_epochs'][key]=state['cycle']
                state['target_due'].pop(key,None)

    def target_records(self, state, word, skill, records=None):
        epoch=state['target_epochs'][self.target_key(word,skill)]
        return [r for r in (state['records'] if records is None else records)
                if r.get('word')==word and r.get('skill')==skill and
                r['stage']!='measurement' and r.get('target_epoch',r['cycle'])==epoch]

    def decision(self, state, word, skill, records=None):
        rows=self.target_records(state,word,skill,records)
        by={r['stage']:r for r in rows}
        i,d,e=by.get('independent'),by.get('delayed'),by.get('extra_check')
        if self.is_paused(state,word,skill): return 'paused'
        if d:
            if not d['correct']: return 'reteach'
            if i and i['correct']: return 'retained'
            if e: return 'extra_confirmed' if e['correct'] else 'reteach'
            return 'extra_required'
        if i: return 'waiting' if i['correct'] else 'reteach'
        return 'pending'

    def pending_delayed(self, state):
        result=[]
        for word in WORDS:
            for skill in SKILLS:
                key=self.target_key(word,skill)
                rows=self.target_records(state,word,skill)
                if not self.is_paused(state,word,skill) and key in state['target_due'] and any(r['stage']=='independent' for r in rows) and not any(r['stage']=='delayed' for r in rows):
                    result.append({'word':word,'skill':skill})
        return result

    def finish_control(self, state):
        pending=self.pending_delayed(state)
        state.update(stage='waiting' if pending else 'complete',position=0,
                     due_at=min((state['target_due'][self.target_key(t['word'],t['skill'])] for t in pending),default=None))
        self.prepare(state)

    def prepare(self, state):
        self.upgrade(state)
        state.setdefault('control_batch',uuid.uuid4().hex)
        stage, position = state['stage'], state['position']
        if stage in ['waiting', 'complete', 'support_required']:
            state['pending'] = None
            return
        if stage == 'assisted_feedback':
            return
        if stage in ['teaching', 'assisted']:
            word = state['teaching_words'][position]
            skill = self.needs(state,word)[state.get('assisted_index',0)]
        else:
            plan_key=stage+'-'+str(state['cycle'])
            if state.get('plan_key') != plan_key:
                state['plan_key']=plan_key
                state['task_orders']={'writing':state['order'].copy(),
                                      'listen_write':SystemRandom().sample(WORDS,4),
                                      'recognition':SystemRandom().sample(WORDS,4),
                                      'listening':SystemRandom().sample(WORDS,4)}
            if state.get('assessment_key') != plan_key:
                state['assessment_key']=plan_key
                state['assessment_tasks']=[{'word':w,'skill':s} for s in SKILLS
                    for w in state['task_orders'][s] if not self.is_paused(state,w,s)
                    and (stage=='measurement' or {'word':w,'skill':s} in state['control_targets'])]
                if stage=='independent' and state['assessment_tasks']:
                    # Yazması duraklatılmış kelimenin başka açık hedefi aralıkta kullanılabilir.
                    remaining=state['assessment_tasks'].copy()
                    first=[]
                    for w in state['order']:
                        item=next((t for t in remaining if t['word']==w),None)
                        if item:
                            first.append(item);remaining.remove(item)
                        else:
                            # Kelimenin tüm hedefleri durakladıysa ona yeniden soru sorma.
                            first.append({'word':['water','banana','car','fish'][state['order'].index(w)],'skill':'spacing'})
                    state['assessment_tasks']=first+remaining
                if state.get('common_control_version') and stage in ['measurement','independent'] and state['cycle']==1 and state['assessment_tasks']:
                    common=[{'word':w,'skill':'listen_write'} for w in state['task_orders']['listen_write']
                            if not self.is_paused(state,w,'writing')]
                    if stage=='measurement':
                        state['assessment_tasks'][4:4]=common
                    else:
                        state['assessment_tasks'].extend(common)
            if not state['assessment_tasks']:
                if self.pending_delayed(state):
                    self.finish_control(state)
                else:
                    state.update(stage='support_required',pending=None,due_at=None)
                return
            item=state['assessment_tasks'][position]
            word,skill=item['word'],item['skill']
        pending = {'id':uuid.uuid4().hex,'word':word,'skill':skill,'stage':stage,
                   'batch_id':state['control_batch']}
        if skill in ['writing','listen_write'] and stage in ['measurement','independent','delayed','extra_check']:
            mode=LISTEN if skill=='listen_write' else TEXT
            score = self.engine.score(state, [self.engine.words[word]], mode)[word]
            pending['prediction'] = score
        # Seçenekler, hedef kelimeyi URL veya seçenek değerinde ifşa etmez.
        if skill in ['recognition','listening']:
            choices = [word]+[w for w in WORDS if w != word][:2]
            choices.sort(key=lambda _:uuid.uuid4().hex)
            pending['choices'] = choices
        state['pending'] = pending

    @staticmethod
    def is_paused(state,word,skill):
        return any(p['word']==word and p['skill']==skill
                   for p in state.get('paused_targets',[]))

    def support_explanation(self,word,skill,value,selected=None):
        meaning=self.engine.words[word]['turkish']
        if skill=='writing':
            changes=[]
            for operation,a,b,c,d in SequenceMatcher(None,normalized_answer(value),word,autojunk=False).get_opcodes():
                if operation=='insert': changes.append('Eksik harf: '+word[c:d])
                elif operation=='delete': changes.append('Fazladan harf: '+normalized_answer(value)[a:b])
                elif operation=='replace': changes.append('Düzelt: '+normalized_answer(value)[a:b]+' → '+word[c:d])
            return 'Beklenen yazılış: '+word+'. '+'. '.join(changes)+'. Harf sırasını görünür örnekle karşılaştır.'
        chosen=self.engine.words[selected]['turkish'] if selected else 'diğer resim'
        if skill=='recognition':
            return f'Yazılı {word} sözcüğünün anlamı {meaning}. Seçtiğin resim {chosen}. Doğru kelime–resim eşleşmesini karşılaştır.'
        return f'Kayıttaki sözcük {word}; anlamı {meaning}. Seçtiğin resim {chosen}. Sesi yeniden dinleyip doğru resimle eşleştir. Bu yanlış tek başına neden zorlandığını göstermez.'

    def continue_support(self,state,task_id):
        q=self.check_id(state,task_id)
        if state['stage']!='assisted_feedback':
            raise TutorError('Önce destekli denemenin geri bildirimini tamamla.')
        feedback=state['support_feedback']
        if feedback['decision']=='retry':
            state['stage']='assisted'
        else:
            state['assisted_index']=state.get('assisted_index',0)+1
            if state['assisted_index']<len(self.needs(state,q['word'])):
                state['stage']='teaching'
            else:
                state['assisted_index']=0
                state['position']+=1
                if state['position']<len(state['teaching_words']):
                    state['stage']='teaching'
                else:
                    self.begin_independent(state)
                    return
        self.prepare(state)

    def needs(self,state,word):
        if state.get('reteach_targets') is not None:
            return [s for s in SKILLS if {'word':word,'skill':s} in state['reteach_targets']]
        cycle=state['cycle']
        source=[r for r in state['records'] if r.get('word')==word and not r.get('correct',True)]
        source=[r for r in source if (cycle==1 and r['stage']=='measurement') or
                (cycle>1 and r['cycle']==cycle-1 and r['stage'] in ['independent','delayed'])]
        return [s for s in SKILLS if any(r['skill']==s for r in source)] or ['writing']

    def check_id(self, state, task_id):
        q = state['pending']
        if not q or q['id'] != task_id:
            raise TutorError('Bu adım değişti veya zaten kaydedildi. Güncel ekranı kullan.')
        return q

    def answer(self, state, task_id, value):
        q = self.check_id(state, task_id)
        stage, skill, word = q['stage'], q['skill'], q['word']
        if stage in ['teaching','assisted_feedback']:
            raise TutorError('Öğretim adımını devam düğmesiyle tamamla.')
        if not isinstance(value,str) or not value.strip() or len(value)>80:
            raise TutorError('Geçerli bir cevap gir veya resim seç.')
        if skill in ['writing','listen_write','spacing']:
            correct = int(normalized_answer(value) == word)
        else:
            selected = self.engine.audio_words.get(value)
            if selected not in q['choices']:
                raise TutorError('Gösterilen resimlerden birini seç.')
            correct = int(selected == word)
        now = self.clock()
        record = {'id':q['id'],'stage':'spacing' if skill=='spacing' else stage,'cycle':state['cycle'],'word':word,
                  'skill':skill,'correct':correct,'submitted':value,'at':now,
                  'assisted':stage == 'assisted' or skill=='spacing','native_history_used':False}
        record['batch_id']=q.get('batch_id',state.get('control_batch'))
        if skill in SKILLS:
            record['target_epoch']=state['target_epochs'][self.target_key(word,skill)]
        if skill=='listen_write':
            record['assessment_role']='common_control'
        if skill not in ['writing','listen_write','spacing']:
            record['selected_word']=selected
        if 'prediction' in q:
            before = copy.deepcopy(q['prediction'])
            # Ortak kontrol gerçekten dinleyerek yazmadır; ses-resim sonucu buraya girmez.
            mode=LISTEN if skill=='listen_write' else TEXT
            native = {'id':q['id'],'learner_id':state['id'],'word_id':word,
                      'topic_id':self.engine.words[word]['topic_id'],'format':mode,
                      'correct':correct,'day':max(0,(now-state['created_at'])/86400),
                      'timestamp':__import__('datetime').datetime.fromtimestamp(now,__import__('datetime').timezone.utc).isoformat(),
                      'kind':'pilot_'+stage,'pilot_skill':skill,'model_version':MODEL_VERSION,
                      'p_correct_before':before['p_correct'],'features_before':before['features']}
            state['attempts'].append(native)
            history,_ = self.engine.histories(state)
            record.update(native_history_used=True,model_version=MODEL_VERSION,
                          model_before=before,history_after=self.engine.history_snapshot(history,word,mode))
        state['records'].append(record)
        if stage == 'assisted':
            wrongs=sum(not r['correct'] for r in state['records'] if r['stage']=='assisted'
                       and r['cycle']==state['cycle'] and r['word']==word and r['skill']==skill)
            decision='supported_success' if correct else ('retry' if wrongs<2 else 'paused')
            record['support_decision']=decision
            if decision=='paused' and not self.is_paused(state,word,skill):
                state.setdefault('paused_targets',[]).append({'cycle':state['cycle'],'word':word,
                    'skill':skill,'at':now,'reason':'two_assisted_errors'})
            state['support_feedback']={'word':word,'skill':skill,'correct':correct,
                'wrong_count':wrongs,'decision':decision,
                'explanation':'Doğru cevap; bu yalnız destekli başarıdır.' if correct else self.support_explanation(word,skill,value,selected if skill!='writing' else None)}
            state['stage']='assisted_feedback'
            state['pending']={**q,'id':uuid.uuid4().hex,'stage':'assisted_feedback'}
            return
        else:
            state['position'] += 1
            if state['position'] == len(state.get('assessment_tasks',range(12))):
                if stage == 'measurement':
                    measured = [r for r in state['records'] if r['stage']=='measurement' and r['skill'] in SKILLS]
                    failed = {r['word'] for r in measured if not r['correct']}
                    writing_failed = {r['word'] for r in measured if r['skill']=='writing' and not r['correct']}
                    scores = self.engine.score(state,[self.engine.words[w] for w in writing_failed],TEXT) if writing_failed else {}
                    priority = sorted(writing_failed,key=lambda w:(scores[w]['p_correct'],w))
                    state['teaching_words'] = priority+[w for w in WORDS if w in failed and w not in writing_failed]
                    state['selection_note'] = 'Yazma hatası olan kelimeler LR metin tahminiyle sıralandı; yalnız tanıma/dinleme hataları gerçek sonuçlara dayalı kuralla eklendi.'
                    state['position'] = 0
                    if state['teaching_words']:
                        state['stage'] = 'teaching'
                    else:
                        self.begin_independent(state)
                        return
                elif stage == 'independent':
                    for t in state['control_targets']:
                        if not self.is_paused(state,t['word'],t['skill']):
                            state['target_due'][self.target_key(t['word'],t['skill'])]=now+DELAY_SECONDS
                    self.finish_control(state)
                    return
                else:
                    self.finish_control(state)
                    return
        self.prepare(state)

    def teach(self, state, task_id):
        q = self.check_id(state, task_id)
        if state['stage'] != 'teaching':
            raise TutorError('Bu adım bir öğretim kartı değil.')
        state['records'].append({'id':q['id'],'stage':'teaching','cycle':state['cycle'],
                                 'target_epoch':state['target_epochs'][self.target_key(q['word'],self.needs(state,q['word'])[state.get('assisted_index',0)])],
                                 'word':q['word'],'skill':self.needs(state,q['word'])[state.get('assisted_index',0)],'at':self.clock(),
                                 'native_history_used':False})
        state['stage'] = 'assisted'
        self.prepare(state)

    def begin_independent(self, state):
        # Öğretilen her hedefe dönmeden üç başka kelimenin cevaplanmasını sağlar.
        state['order'] = [w for w in WORDS if w not in state['teaching_words']]+state['teaching_words']
        state.update(stage='independent',position=0,control_batch=uuid.uuid4().hex)
        self.prepare(state)

    def delayed(self, state):
        self.upgrade(state)
        if state['stage'] != 'waiting' or self.clock() < state['due_at']:
            raise TutorError('Gecikmeli kontrol için gerçek 24 saat henüz dolmadı.')
        state['control_targets']=[t for t in self.pending_delayed(state)
            if state['target_due'][self.target_key(t['word'],t['skill'])]<=self.clock()]
        state.update(stage='delayed',position=0,order=WORDS.copy(),assessment_key=None,plan_key=None,
                     control_batch=uuid.uuid4().hex)
        self.prepare(state)

    def retry(self, state):
        self.upgrade(state)
        if state['stage'] not in ['waiting','complete']:
            raise TutorError('Önce mevcut kontrol bloğunu tamamla.')
        targets=[{'word':w,'skill':s} for w in WORDS for s in SKILLS
                 if self.decision(state,w,s)=='reteach']
        if not targets:
            raise TutorError('Yeniden öğretim gerektiren hedef yok.')
        writing_failed={t['word'] for t in targets if t['skill']=='writing'}
        failed={t['word'] for t in targets}
        scores=self.engine.score(state,[self.engine.words[w] for w in writing_failed],TEXT) if writing_failed else {}
        priority=sorted(writing_failed,key=lambda w:(scores[w]['p_correct'],w))
        state['cycle']+=1
        for t in targets:
            key=self.target_key(t['word'],t['skill'])
            state['target_epochs'][key]=state['cycle']
            state['target_due'].pop(key,None)
        state.update(stage='teaching',position=0,due_at=None,assisted_index=0,
                     reteach_targets=targets,control_targets=copy.deepcopy(targets),
                     assessment_key=None,plan_key=None,
                     teaching_words=priority+[w for w in WORDS if w in failed and w not in writing_failed])
        self.prepare(state)

    def extra_check(self, state):
        self.upgrade(state)
        if state['stage'] not in ['waiting','complete']:
            raise TutorError('Önce mevcut kontrol bloğunu tamamla.')
        targets=[{'word':w,'skill':s} for w in WORDS for s in SKILLS
                 if self.decision(state,w,s)=='extra_required']
        if not targets:
            raise TutorError('Ek bağımsız kontrol gerektiren hedef yok.')
        state.update(stage='extra_check',position=0,control_targets=targets,
                     assessment_key=None,plan_key=None,order=WORDS.copy(),control_batch=uuid.uuid4().hex)
        self.prepare(state)

    def payload(self, state):
        self.upgrade(state)
        q = state['pending']
        task = None
        if q:
            word = self.engine.words[q['word']]
            task = {'id':q['id'],'skill':q['skill']}
            if q['skill']=='writing':
                task['prompt'] = word['turkish']
            elif q['skill']=='spacing':
                task.update(prompt=word['turkish'],expected=q['word'])
            elif q['skill']=='recognition':
                task['prompt'] = q['word']
            elif q['skill'] in ['listening','listen_write']:
                task['audio'] = self.engine.audio_url(q['word'])
            if q['stage'] in ['teaching','assisted','assisted_feedback']:
                task.update(expected=q['word'],prompt=word['turkish'],example=word['example'],
                            image='/pilot-image/'+self.engine.audio_keys[q['word']]+'.svg',
                            audio=self.engine.audio_url(q['word']),
                            spelling=' + '.join(q['word']))
                task['needs'] = self.needs(state,q['word'])
                goal=q['skill'] if q['skill']!='exposure' else self.needs(state,q['word'])[state.get('assisted_index',0)]
                task['teaching_goal']=goal
                task['instruction']={'writing':'Harf sırasını incele. Yazımını görünür örnekle karşılaştır; sonraki kontrolde harf desteği kaldırılacak.',
                    'recognition':'İngilizce sözcüğü doğru nesne resmi ve Türkçe anlamıyla eşleştir.',
                    'listening':'Sesi yeniden dinle ve doğru resimle eşleştir. Sonraki dinleme kontrolünde yazılı kelime gösterilmeyecek.'}[goal]
            if q.get('choices'):
                task['options'] = [{'value':self.engine.audio_keys[w],
                                    'image':'/pilot-image/'+self.engine.audio_keys[w]+'.svg'} for w in q['choices']]
        # Tamamlanmamış ölçüm bloğunda hedef, doğru cevap veya kısmi sonuç açıklanmaz.
        def in_current_block(r):
            if state['stage'] not in ['measurement','independent','delayed','extra_check'] or r['stage']!=state['stage']:
                return False
            if r.get('batch_id'):
                return r['batch_id']==state.get('control_batch')
            # Eski, henüz tamamlanmamış bloklar için uyum: eski kayıtları yeniden yazma.
            return r['cycle']==state['cycle'] and {'word':r['word'],'skill':r['skill']} in state['control_targets']
        visible = [r for r in state['records'] if not in_current_block(r)]
        outcomes=[]
        for word in WORDS:
            for skill in SKILLS:
                records=self.target_records(state,word,skill,visible)
                by_stage={r['stage']:r for r in records}
                delayed=by_stage.get('delayed'); independent=by_stage.get('independent')
                extra=by_stage.get('extra_check'); assisted=by_stage.get('assisted')
                initial=next((r for r in visible if r['stage']=='measurement' and r['word']==word and r['skill']==skill),None)
                decision=self.decision(state,word,skill,visible)
                status={
                    'paused':'Ek destek gerekiyor; yalnız bu hedef duraklatıldı',
                    'retained':'Gecikmeli kontrolde hatırladı',
                    'extra_required':'Gecikmeli kontrolde doğru; ek bağımsız kontrol gerekiyor',
                    'extra_confirmed':'Ek bağımsız kontrolde doğruladı; kalıcı öğrenme garantisi değil',
                    'waiting':'Aynı oturumda bağımsız başardı; gecikmeli kontrol bekliyor',
                    'reteach':('Gecikmeli hatırlama başarısız; yeniden öğretim gerekiyor' if delayed and independent and independent['correct'] else 'Yeniden öğretim gerekiyor'),
                }.get(decision)
                if not status:
                    if assisted and assisted['correct']: status='Destekle başardı; bağımsız kontrol bekleniyor'
                    elif state['target_epochs'][self.target_key(word,skill)]>1: status='Yeniden öğretim süreci; yeni bağımsız kontrol bekleniyor'
                    elif initial: status='İlk ölçümde doğru; sonraki kontrol bekliyor' if initial['correct'] else 'Öğretim gerekiyor'
                    else: status='Henüz ölçülmedi'
                key=self.target_key(word,skill)
                outcomes.append({'word':word,'skill':skill,'status':status,'decision':decision,
                    'target_epoch':state['target_epochs'][key], 'due_at':state['target_due'].get(key),
                    'paused':decision=='paused',
                    'measurement':None if not initial else initial['correct'],
                    'assisted':None if not assisted else assisted['correct'],
                    'independent':None if not independent else independent['correct'],
                    'delayed':None if not delayed else delayed['correct'],
                    'extra_check':None if not extra else extra['correct']})
        profile=self.engine.progress(state)['profile']
        can_retry=state['stage'] in ['waiting','complete'] and any(o['decision']=='reteach' for o in outcomes)
        can_extra=state['stage'] in ['waiting','complete'] and any(o['decision']=='extra_required' for o in outcomes)
        common_results=[]
        for word in WORDS:
            rows={r['stage']:r for r in visible if r['word']==word and r['skill']=='listen_write'}
            common_results.append({'word':word,'measurement':rows.get('measurement',{}).get('correct'),
                                   'independent':rows.get('independent',{}).get('correct')})
        native_counts={mode:sum(a['format']==mode for a in state['attempts']) for mode in [TEXT,LISTEN]}
        return {'id':state['id'],'name':state['name'],'stage':state['stage'],'cycle':state['cycle'],'can_retry':can_retry,'can_extra':can_extra,
                'support_feedback':copy.deepcopy(state.get('support_feedback')) if state['stage']=='assisted_feedback' else None,
                'paused_targets':copy.deepcopy(state.get('paused_targets',[])),
                'task_total':len(state.get('assessment_tasks',range(12))),
                'position':state['position'],'task':task,'due_at':state['due_at'],
                'server_now':self.clock(),'delayed_ready':state['stage']=='waiting' and self.clock()>=state['due_at'],
                'selection_note':state.get('selection_note'), 'outcomes':[] if state['stage']=='measurement' else outcomes,
                'common_control_version':state['common_control_version'],
                'common_results':[] if state['stage']=='measurement' else common_results,
                'evidence':pilot_evidence(outcomes,visible,self.engine.words,self.engine.topics) if state['stage'] not in ['measurement','independent','delayed','extra_check'] else None,
                'guidance':pattern_guidance(profile),
                'records':visible,'record_counts':dict(__import__('collections').Counter(r['stage'] for r in state['records'])),
                'model_audit':{'lr_native_writing_records':native_counts[TEXT],
                    'lr_native_listen_write_records':native_counts[LISTEN], 'lr_native_records':len(state['attempts']),
                    'kmeans':profile,'note':'LR, yardımsız metin ve dinleyerek yazma cevaplarını tahmin eder; yazma tekrarlarını sıralamaya yardımcı olur. K-Means son 6 metin ve 6 dinleyerek yazma sonucundan geçici performans grubu çıkarır. Ses-resim, destekli cevap ve puansız aralık çalışmaları bu geçmişlere girmez. Grup öğretim kararını veya öğrenildi durumunu değiştirmez.'}}
