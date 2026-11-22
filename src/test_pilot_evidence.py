"""Hedefe özgü sürüm, zaman, dört karar ve ek kontrolün uçtan uca denetimi."""
import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from pilot import Pilot, WORDS, SKILLS, DELAY_SECONDS
from tutor_engine import TutorEngine, TutorError, ROOT
from app_server import create_app


class EvidenceChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.engine=TutorEngine()
 def setup_run(self):
  self.now=[100000.0];self.p=Pilot(self.engine,lambda:self.now[0]);return self.p.new('Synthetic evidence',include_listen_write=False)
 def answer(self,s,correct=True):
  q=s['pending'];word=q['word']
  value=word if q['skill'] in ['writing','spacing'] else self.engine.audio_keys[word]
  if not correct:value='wrong' if q['skill'] in ['writing','spacing'] else next(self.engine.audio_keys[w] for w in q['choices'] if w!=word)
  self.p.answer(s,q['id'],value)
 def block(self,s,fail=()):
  stage=s['stage']
  while s['stage']==stage:
   q=s['pending'];self.answer(s,(q['word'],q['skill']) not in fail)
 def teach(self,s):
  while s['stage'] in ['teaching','assisted','assisted_feedback']:
   if s['stage']=='teaching':self.p.teach(s,s['pending']['id'])
   elif s['stage']=='assisted_feedback':self.p.continue_support(s,s['pending']['id'])
   else:self.answer(s)
 def outcome(self,s,w,k='writing'):
  return next(o for o in self.p.payload(s)['outcomes'] if o['word']==w and o['skill']==k)
 def matrix(self):
  s=self.setup_run();self.block(s)
  self.block(s,{('apple','writing'),('book','writing')})
  self.now[0]=s['due_at'];self.p.delayed(s)
  self.block(s,{('dog','writing'),('book','writing')})
  return s

 def test_four_outcomes_and_missing_delayed_is_waiting(self):
  s=self.setup_run();self.block(s);self.block(s)
  self.assertTrue(all(o['decision']=='waiting' and o['delayed'] is None for o in self.p.payload(s)['outcomes']))
  s=self.matrix()
  self.assertEqual([self.outcome(s,w)['decision'] for w in WORDS],['retained','reteach','extra_required','reteach'])
  self.assertIn('Gecikmeli hatırlama başarısız',self.outcome(s,'dog')['status'])
  self.assertTrue(self.p.payload(s)['can_extra']);self.assertTrue(self.p.payload(s)['can_retry'])

 def test_retry_only_selected_targets_preserves_other_visible_evidence(self):
  s=self.matrix();before=copy.deepcopy(s['records'])
  cat=self.outcome(s,'cat');dog_listen=self.outcome(s,'dog','listening');apple=self.outcome(s,'apple')
  self.p.retry(s)
  self.assertEqual(s['records'],before)
  self.assertEqual(s['reteach_targets'],[{'word':'dog','skill':'writing'},{'word':'book','skill':'writing'}])
  self.assertEqual(self.outcome(s,'cat'),cat)
  self.assertEqual(self.outcome(s,'dog','listening'),dog_listen)
  self.assertEqual(self.outcome(s,'apple'),apple)
  reset=self.outcome(s,'dog')
  self.assertEqual(reset['target_epoch'],2);self.assertIsNone(reset['delayed']);self.assertIsNone(reset['independent'])
  self.assertEqual(self.p.needs(s,'dog'),['writing'])
  self.teach(s)
  actual=[t for t in s['assessment_tasks'] if t['skill']!='spacing']
  self.assertCountEqual(actual,s['reteach_targets'])
  # Devam eden yeni blok da diğer hedeflerin görünür sonuçlarını gizlemez.
  self.answer(s);self.assertEqual(self.outcome(s,'cat'),cat)
  while s['stage']=='independent':self.answer(s)
  self.now[0]=s['due_at'];self.p.delayed(s);self.block(s)
  self.assertEqual(self.outcome(s,'dog')['decision'],'retained')
  self.assertEqual(self.outcome(s,'apple'),apple)
  self.assertEqual(self.outcome(s,'cat'),cat)

 def test_extra_control_has_no_teaching_resets_or_answers_exposed(self):
  s=self.matrix();before=copy.deepcopy(s['records']);epoch=s['target_epochs'].copy()
  self.p.extra_check(s)
  self.assertEqual(s['stage'],'extra_check');self.assertEqual(s['records'],before)
  public=self.p.payload(s)
  self.assertEqual(public['task']['skill'],'writing');self.assertNotIn('expected',public['task']);self.assertNotIn('prediction',public['task'])
  old=s['pending']['id'];self.answer(s)
  self.assertEqual(s['stage'],'complete');self.assertEqual(s['target_epochs'],epoch)
  self.assertEqual(self.outcome(s,'apple')['decision'],'extra_confirmed')
  self.assertEqual(self.outcome(s,'apple')['independent'],0)
  self.assertEqual(self.outcome(s,'apple')['delayed'],1)
  self.assertEqual(self.outcome(s,'apple')['extra_check'],1)
  self.assertTrue(s['records'][-1]['native_history_used'])
  with self.assertRaises(TutorError):self.p.answer(s,old,'apple')
  with self.assertRaises(TutorError):self.p.extra_check(s)

 def test_failed_extra_control_reteaches_only_its_target_and_hides_old_pair(self):
  s=self.matrix();self.p.extra_check(s);self.answer(s,False)
  self.assertEqual(self.outcome(s,'apple')['decision'],'reteach')
  self.p.retry(s)
  self.assertIn({'word':'apple','skill':'writing'},s['reteach_targets'])
  self.assertNotIn({'word':'apple','skill':'recognition'},s['reteach_targets'])
  self.assertIsNone(self.outcome(s,'apple')['extra_check'])
  self.assertIsNone(self.outcome(s,'apple')['delayed'])

 def test_target_timers_preserved_and_delayed_batches_obey_own_deadlines(self):
  s=self.setup_run();self.block(s);self.block(s,{('cat','writing')})
  due=s['due_at'];dog=self.outcome(s,'dog')
  self.p.retry(s);self.now[0]+=3600;self.teach(s);self.block(s)
  self.assertEqual(s['due_at'],due)
  self.assertEqual(self.outcome(s,'dog'),dog)
  new_due=self.outcome(s,'cat')['due_at'];self.assertEqual(new_due,due+3600)
  self.now[0]=due;self.p.delayed(s)
  self.assertNotIn({'word':'cat','skill':'writing'},s['assessment_tasks'])
  self.block(s);self.assertEqual(s['stage'],'waiting');self.assertEqual(s['due_at'],new_due)
  frozen=copy.deepcopy(s)
  with self.assertRaises(TutorError):self.p.delayed(s)
  self.assertEqual(s,frozen)
  self.now[0]=new_due;self.p.delayed(s)
  self.assertEqual(s['assessment_tasks'],[{'word':'cat','skill':'writing'}])
  self.block(s);self.assertEqual(s['stage'],'complete')

 def test_sparse_retry_keeps_three_other_word_gap_without_retesting_good_targets(self):
  s=self.setup_run();self.block(s);self.block(s,{('cat','writing')});self.p.retry(s);self.teach(s)
  tasks=s['assessment_tasks'];self.assertEqual(tasks[-1],{'word':'cat','skill':'writing'})
  self.assertEqual(len({t['word'] for t in tasks[:-1]}),3)
  self.assertTrue(all(t['skill']=='spacing' for t in tasks[:-1]))
  native=len(s['attempts']);self.block(s)
  self.assertEqual(len(s['attempts']),native+1)
  self.assertTrue(all(not r['native_history_used'] for r in s['records'] if r['stage']=='spacing'))

 def test_extra_api_persists_evidence_and_guards_export_during_control(self):
  s=self.matrix()
  with TemporaryDirectory(dir=ROOT/'tmp') as temp:
   db=Path(temp)/'isolated.sqlite3';app=create_app(db);app.extensions['pilot_store'].create(s)
   client=app.test_client();url='/api/pilot/'+s['id']
   public=client.post(url+'/extra-check',json={}).get_json()
   self.assertEqual(public['stage'],'extra_check');self.assertEqual(client.get(url+'/export').status_code,400)
   restarted=create_app(db);client=restarted.test_client()
   self.assertEqual(client.get(url).get_json()['task'],public['task'])
   final=client.post(url+'/answer',json={'task_id':public['task']['id'],'answer':'apple'}).get_json()
   self.assertEqual(next(o for o in final['outcomes'] if o['word']=='apple' and o['skill']=='writing')['decision'],'extra_confirmed')
   self.assertEqual(client.get(url+'/export').status_code,200)

 def test_picture_target_retry_and_extra_do_not_enter_model_history(self):
  s=self.setup_run();self.block(s);self.block(s,{('cat','recognition'),('dog','listening')})
  self.now[0]=s['due_at'];self.p.delayed(s);self.block(s,{('dog','listening')})
  self.assertEqual(self.outcome(s,'cat','recognition')['decision'],'extra_required')
  native=len(s['attempts']);self.p.extra_check(s);self.answer(s)
  self.assertEqual(len(s['attempts']),native)
  good=self.outcome(s,'dog','writing');self.p.retry(s)
  self.assertEqual(s['reteach_targets'],[{'word':'dog','skill':'listening'}])
  self.teach(s);self.block(s)
  self.assertEqual(len(s['attempts']),native)
  self.assertEqual(self.outcome(s,'dog','writing'),good)

 def test_paused_reteach_target_does_not_cancel_other_targets_pending_delay(self):
  s=self.setup_run();self.block(s);self.block(s,{('cat','writing')})
  due=s['due_at'];self.p.retry(s)
  self.p.teach(s,s['pending']['id'])
  for _ in range(2):
   self.answer(s,False);self.p.continue_support(s,s['pending']['id'])
  self.assertEqual(s['stage'],'waiting');self.assertEqual(s['due_at'],due)
  self.assertTrue(self.outcome(s,'cat')['paused'])

 def test_legacy_completed_evidence_is_read_without_rewriting_raw_records(self):
  s=self.matrix()
  for key in ['target_epochs','target_due','control_targets','control_batch']:s.pop(key,None)
  for r in s['records']:
   r.pop('target_epoch',None);r.pop('batch_id',None)
  before=copy.deepcopy(s['records']);self.p.upgrade(s)
  self.assertEqual(s['records'],before)
  self.assertEqual([self.outcome(s,w)['decision'] for w in WORDS],['retained','reteach','extra_required','reteach'])

 def test_legacy_active_reteaching_does_not_reuse_old_control_evidence(self):
  s=self.matrix();self.p.retry(s)
  for key in ['target_epochs','target_due','control_targets','reteach_targets','control_batch']:s.pop(key,None)
  for r in s['records']:
   r.pop('target_epoch',None);r.pop('batch_id',None)
  before=copy.deepcopy(s['records']);self.p.upgrade(s)
  self.assertEqual(s['records'],before)
  self.assertIsNone(self.outcome(s,'dog')['delayed'])
  self.assertEqual(self.outcome(s,'dog')['target_epoch'],2)
  self.assertEqual(self.outcome(s,'dog','listening')['decision'],'retained')

if __name__=='__main__':unittest.main()
