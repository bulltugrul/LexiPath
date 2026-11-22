import copy
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from pilot import Pilot, WORDS, DELAY_SECONDS
from tutor_engine import TutorEngine, TutorError, ROOT
from app_server import create_app


class PilotChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.engine=TutorEngine()
 def setup_run(self):
  self.clock=[100000.0]
  self.pilot=Pilot(self.engine,lambda:self.clock[0])
  return self.pilot.new('Synthetic pilot',include_listen_write=False)
 def answer(self,state,correct=True):
  q=state['pending'];value=q['word'] if q['skill'] in ['writing','spacing'] else self.engine.audio_keys[q['word']]
  if not correct:value='wrong' if q['skill'] in ['writing','spacing'] else next(self.engine.audio_keys[w] for w in q['choices'] if w!=q['word'])
  self.pilot.answer(state,q['id'],value)
 def measured(self,state,wrong=True):
  for _ in range(12):
   q=state['pending'];self.answer(state,not(wrong and q['word']=='cat' and q['skill'] in ['writing','listening']))
 def taught(self,state):
  while state['stage'] in ['teaching','assisted','assisted_feedback']:
   if state['stage']=='teaching':self.pilot.teach(state,state['pending']['id'])
   elif state['stage']=='assisted_feedback':self.pilot.continue_support(state,state['pending']['id'])
   else:self.answer(state)
 def test_full_flow_separates_records_and_enforces_real_delay(self):
  state=self.setup_run()
  for _ in range(11):
   self.answer(state)
   public=self.pilot.payload(state)
   self.assertEqual(public['records'],[])
   self.assertEqual(public['outcomes'],[])
   self.assertNotIn('prediction',public['task'])
   self.assertNotIn('expected',public['task'])
  # Dernier test yanlış: kitap dinleme -> öğretim kuralıyla eklenir.
  self.answer(state,False)
  self.assertEqual(state['stage'],'teaching')
  self.assertEqual(len(state['attempts']),4)
  self.taught(state)
  self.assertEqual(len(state['attempts']),4)
  self.assertEqual(state['order'][-1],state['teaching_words'][-1])
  for _ in range(12):self.answer(state)
  self.assertEqual(state['stage'],'waiting')
  self.assertEqual(len(state['attempts']),8)
  self.assertEqual(self.pilot.payload(state)['model_audit']['kmeans']['group'],None)
  frozen=copy.deepcopy(state)
  with self.assertRaises(TutorError):self.pilot.delayed(state)
  self.assertEqual(state,frozen)
  self.clock[0]=state['due_at']-1
  with self.assertRaises(TutorError):self.pilot.delayed(state)
  self.clock[0]+=1
  self.pilot.delayed(state)
  for _ in range(12):self.answer(state)
  self.assertEqual(state['stage'],'complete')
  self.assertEqual(len(state['attempts']),12)
  self.assertTrue(all(o['status']=='Gecikmeli kontrolde hatırladı' for o in self.pilot.payload(state)['outcomes']))
 def test_teaching_gap_has_three_other_words_and_duplicate_is_rejected(self):
  state=self.setup_run();self.measured(state);self.taught(state)
  self.assertEqual(state['order'],['dog','apple','book','cat'])
  q=copy.deepcopy(state['pending']);self.answer(state)
  n=len(state['records'])
  with self.assertRaises(TutorError):self.pilot.answer(state,q['id'],'dog')
  self.assertEqual(len(state['records']),n)
 def test_failed_control_retry_keeps_previous_evidence_and_resets_due(self):
  state=self.setup_run();self.measured(state);self.taught(state)
  for i in range(12):self.answer(state,correct=i!=3)
  self.assertTrue(self.pilot.payload(state)['can_retry'])
  previous=copy.deepcopy(state['records'])
  self.pilot.retry(state)
  self.assertEqual(state['cycle'],2)
  self.assertIsNone(state['due_at'])
  self.assertEqual(state['records'],previous)
  self.assertEqual(state['stage'],'teaching')
 def test_all_correct_measurement_skips_teaching_but_not_retention_control(self):
  state=self.setup_run();self.measured(state,wrong=False)
  self.assertEqual(state['stage'],'independent')
  self.assertTrue(all('Öğretim' not in o['status'] for o in self.pilot.payload(state)['outcomes']))
 def test_api_persistence_export_guard_and_clock_cannot_be_supplied(self):
  with TemporaryDirectory(dir=ROOT/'tmp') as temp:
   db=Path(temp)/'isolated.sqlite3';app=create_app(db);client=app.test_client()
   public=client.post('/api/pilot',json={'name':'Synthetic API'}).get_json();url='/api/pilot/'+public['id']
   self.assertEqual(client.get(url).get_json()['task'],public['task'])
   self.assertEqual(client.get(url+'/export').status_code,400)
   self.assertEqual(client.post(url+'/delayed',json={'now':9999999999999}).status_code,400)
   self.assertEqual(app.extensions['tutor_store'].listing(),[])
   app2=create_app(db);reloaded=app2.test_client().get(url).get_json()
   self.assertEqual(reloaded['id'],public['id'])
   self.assertEqual(reloaded['task']['id'],public['task']['id'])
   # Yeni sunucu aynı görevi yeni yerel ses/görsel anahtarlarıyla sürdürür.
   response=app2.test_client().post(url+'/answer',json={'task_id':public['task']['id'],'answer':'cat'})
   self.assertEqual(response.status_code,200)

 def test_first_error_retries_same_target_second_pauses_only_that_target(self):
  state=self.setup_run();self.measured(state)
  self.pilot.teach(state,state['pending']['id'])
  self.assertEqual((state['pending']['word'],state['pending']['skill']),('cat','writing'))
  native=copy.deepcopy(state['attempts'])
  old=state['pending']['id']
  self.pilot.answer(state,old,'ca')
  self.assertEqual(state['stage'],'assisted_feedback')
  self.assertEqual(state['support_feedback']['decision'],'retry')
  self.assertIn('Eksik harf: t',state['support_feedback']['explanation'])
  self.assertEqual(state['assisted_index'],0)
  self.assertEqual(state['position'],0)
  with self.assertRaises(TutorError):self.pilot.answer(state,old,'ca')
  self.pilot.continue_support(state,state['pending']['id'])
  self.assertEqual((state['pending']['word'],state['pending']['skill']),('cat','writing'))
  self.answer(state,False)
  self.assertEqual(state['support_feedback']['decision'],'paused')
  self.assertEqual(state['support_feedback']['wrong_count'],2)
  self.assertEqual(state['attempts'],native)
  self.pilot.continue_support(state,state['pending']['id'])
  self.assertEqual((state['stage'],state['pending']['word'],state['pending']['skill']),('teaching','cat','listening'))
  self.taught(state)
  tasks=state['assessment_tasks']
  self.assertNotIn({'word':'cat','skill':'writing'},tasks)
  self.assertIn({'word':'cat','skill':'listening'},tasks)
  self.assertIn({'word':'cat','skill':'recognition'},tasks)
  paused=next(o for o in self.pilot.payload(state)['outcomes'] if o['word']=='cat' and o['skill']=='writing')
  self.assertTrue(paused['paused']);self.assertIsNone(paused['independent'])
  for _ in range(len(tasks)):self.answer(state)
  self.clock[0]=state['due_at'];self.pilot.delayed(state)
  self.assertNotIn({'word':'cat','skill':'writing'},state['assessment_tasks'])

 def test_supported_success_is_only_recorded_as_supported_after_retry(self):
  state=self.setup_run();self.measured(state);self.pilot.teach(state,state['pending']['id'])
  self.answer(state,False);self.pilot.continue_support(state,state['pending']['id'])
  self.answer(state,True)
  self.assertEqual(state['support_feedback']['decision'],'supported_success')
  self.assertEqual(state['support_feedback']['wrong_count'],1)
  self.assertFalse(state.get('paused_targets'))
  outcome=next(o for o in self.pilot.payload(state)['outcomes'] if o['word']=='cat' and o['skill']=='writing')
  self.assertEqual(outcome['assisted'],1);self.assertIsNone(outcome['independent'])
  self.assertIn('Destekle',outcome['status'])
  self.assertEqual(len(state['attempts']),4)

 def test_invalid_answer_does_not_consume_support_attempt(self):
  state=self.setup_run();self.measured(state);self.pilot.teach(state,state['pending']['id'])
  frozen=copy.deepcopy(state)
  with self.assertRaises(TutorError):self.pilot.answer(state,state['pending']['id'],' ')
  self.assertEqual(state,frozen)

 def test_all_paused_no_false_independent_completion_or_delayed_timer(self):
  state=self.setup_run()
  for _ in range(12):self.answer(state,False)
  while state['stage'] in ['teaching','assisted','assisted_feedback']:
   if state['stage']=='teaching':self.pilot.teach(state,state['pending']['id'])
   elif state['stage']=='assisted_feedback':self.pilot.continue_support(state,state['pending']['id'])
   else:self.answer(state,False)
  self.assertEqual(state['stage'],'support_required')
  self.assertIsNone(state['due_at'])
  self.assertEqual(len(state['paused_targets']),12)
  self.assertEqual(len(state['attempts']),4)
  self.assertTrue(all(o['paused'] and o['independent'] is None for o in self.pilot.payload(state)['outcomes']))

 def test_paused_whole_word_uses_ungraded_gap_without_reopening_it(self):
  state=self.setup_run()
  for _ in range(12):self.answer(state,state['pending']['word']!='cat')
  while state['stage'] in ['teaching','assisted','assisted_feedback']:
   if state['stage']=='teaching':self.pilot.teach(state,state['pending']['id'])
   elif state['stage']=='assisted_feedback':self.pilot.continue_support(state,state['pending']['id'])
   else:self.answer(state,False)
  self.assertEqual(state['stage'],'independent')
  self.assertTrue(any(t['skill']=='spacing' for t in state['assessment_tasks']))
  self.assertFalse(any(t['word']=='cat' for t in state['assessment_tasks']))
  for _ in range(len(state['assessment_tasks'])):self.answer(state)
  self.assertEqual(state['stage'],'waiting')
  self.assertEqual(len(state['attempts']),7)
  self.assertTrue(all(not r['native_history_used'] for r in state['records'] if r['stage']=='spacing'))

 def test_pause_persists_when_another_target_is_retaught(self):
  state=self.setup_run();self.measured(state);self.pilot.teach(state,state['pending']['id'])
  for _ in range(2):
   self.answer(state,False);self.pilot.continue_support(state,state['pending']['id'])
  self.taught(state)
  for _ in range(len(state['assessment_tasks'])):
   q=state['pending'];self.answer(state,not(q['word']=='cat' and q['skill']=='listening'))
  self.pilot.retry(state)
  self.assertEqual(state['cycle'],2)
  self.assertTrue(self.pilot.is_paused(state,'cat','writing'))
  self.assertEqual(state['pending']['skill'],'listening')
  self.taught(state)
  self.assertNotIn({'word':'cat','skill':'writing'},state['assessment_tasks'])
  self.assertTrue(next(o for o in self.pilot.payload(state)['outcomes'] if o['word']=='cat' and o['skill']=='writing')['paused'])

 def test_support_wrong_counter_survives_api_restart_and_stale_submit(self):
  state=self.setup_run();self.measured(state);self.pilot.teach(state,state['pending']['id'])
  with TemporaryDirectory(dir=ROOT/'tmp') as temp:
   db=Path(temp)/'isolated.sqlite3';app=create_app(db)
   app.extensions['pilot_store'].create(state);client=app.test_client();url='/api/pilot/'+state['id']
   q=state['pending']['id']
   first=client.post(url+'/answer',json={'task_id':q,'answer':'ca'}).get_json()
   self.assertEqual(first['support_feedback']['wrong_count'],1)
   self.assertEqual(client.post(url+'/answer',json={'task_id':q,'answer':'ca'}).status_code,400)
   restarted=create_app(db);client=restarted.test_client()
   current=client.get(url).get_json()
   next_state=client.post(url+'/support-next',json={'task_id':current['task']['id']}).get_json()
   second=client.post(url+'/answer',json={'task_id':next_state['task']['id'],'answer':'ca'}).get_json()
   self.assertEqual(second['support_feedback']['wrong_count'],2)
   self.assertEqual(second['support_feedback']['decision'],'paused')
   self.assertEqual(len(second['paused_targets']),1)

if __name__=='__main__':unittest.main()
