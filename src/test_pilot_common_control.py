"""Yeni 16 soruluk pilotta iki modelin gerçek cevap geçmişiyle bütünleşmesi."""
import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from pilot import Pilot,WORDS
from tutor_engine import TutorEngine,TEXT,LISTEN,ROOT,TutorError
from app_server import create_app


class CommonControlChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.engine=TutorEngine()
 def setup_run(self):
  self.now=[100000.0];self.p=Pilot(self.engine,lambda:self.now[0]);return self.p.new('Synthetic common control')
 def answer(self,s,correct=True):
  q=s['pending'];typed=q['skill'] in ['writing','listen_write','spacing']
  value=q['word'] if typed else self.engine.audio_keys[q['word']]
  if not correct:value='wrong' if typed else next(self.engine.audio_keys[w] for w in q['choices'] if w!=q['word'])
  self.p.answer(s,q['id'],value)
 def block(self,s,wrong_common=False):
  stage=s['stage'];n=0
  while s['stage']==stage:
   common=s['pending']['skill']=='listen_write'
   self.answer(s,not(common and wrong_common and n%2))
   if common:n+=1
 def teach(self,s):
  while s['stage'] in ['teaching','assisted','assisted_feedback']:
   if s['stage']=='teaching':self.p.teach(s,s['pending']['id'])
   elif s['stage']=='assisted_feedback':self.p.continue_support(s,s['pending']['id'])
   else:self.answer(s)

 def test_plan_and_real_listen_features_update_only_after_answer(self):
  s=self.setup_run()
  self.assertEqual([t['skill'] for t in s['assessment_tasks']],['writing']*4+['listen_write']*4+['recognition']*4+['listening']*4)
  for _ in range(4):self.answer(s)
  q=copy.deepcopy(s['pending']);public=self.p.payload(s)['task']
  self.assertEqual(q['prediction']['features']['format'],LISTEN)
  self.assertEqual(q['prediction']['features']['prior_format_target_count'],0)
  self.assertEqual(q['prediction']['features']['prior_target_count'],4)
  self.assertIn('audio',public)
  for key in ['prompt','image','options','expected','prediction','spelling']:self.assertNotIn(key,public)
  self.answer(s,False)
  record=s['records'][-1];native=s['attempts'][-1]
  self.assertEqual(record['assessment_role'],'common_control')
  self.assertEqual(native['format'],LISTEN);self.assertEqual(native['correct'],0)
  self.assertEqual(record['history_after']['format']['count'],1)
  self.assertEqual(record['history_after']['format']['correct'],0)
  self.assertEqual(record['model_before'],q['prediction'])
  with self.assertRaises(TutorError):self.p.answer(s,q['id'],'wrong')

 def test_full_flow_reaches_correct_group_without_changing_three_goal_outcomes(self):
  s=self.setup_run();self.block(s,wrong_common=True)
  self.assertEqual(s['stage'],'independent') # Ortak yanlış, dördüncü öğretim hedefi üretmez.
  audit=self.p.payload(s)['model_audit']
  self.assertEqual((audit['lr_native_writing_records'],audit['lr_native_listen_write_records']),(4,4))
  self.assertIsNone(audit['kmeans']['group'])
  self.block(s,wrong_common=True)
  self.assertEqual(s['stage'],'waiting')
  public=self.p.payload(s);audit=public['model_audit']
  self.assertEqual((audit['lr_native_writing_records'],audit['lr_native_listen_write_records']),(8,8))
  self.assertEqual(audit['kmeans']['features'],{'text_target_accuracy':1.0,'listen_target_accuracy':0.5})
  self.assertEqual(audit['kmeans']['group']['number'],3)
  self.assertEqual(len(public['outcomes']),12)
  self.assertTrue(all(o['decision']=='waiting' for o in public['outcomes']))
  self.assertEqual(len(s['target_due']),12)
  self.now[0]=s['due_at'];self.p.delayed(s)
  self.assertEqual(len(s['assessment_tasks']),12)
  self.assertTrue(all(t['skill']!='listen_write' for t in s['assessment_tasks']))

 def test_threshold_is_checked_on_actual_native_answers(self):
  s=self.setup_run();self.block(s)
  while s['pending']['skill']!='listen_write':self.answer(s)
  self.assertIsNone(self.p.payload(s)['model_audit']['kmeans']['group'])
  self.answer(s)
  self.assertEqual(self.p.payload(s)['model_audit']['kmeans']['counts'][LISTEN],5)
  self.assertIsNone(self.p.payload(s)['model_audit']['kmeans']['group'])
  self.answer(s)
  self.assertEqual(self.p.payload(s)['model_audit']['kmeans']['counts'],{TEXT:6,LISTEN:6})
  self.assertIsNotNone(self.p.payload(s)['model_audit']['kmeans']['group'])

 def test_paused_writing_is_not_reopened_by_common_control(self):
  s=self.setup_run()
  while s['stage']=='measurement':
   q=s['pending'];self.answer(s,not(q['word']=='cat' and q['skill']=='writing'))
  self.p.teach(s,s['pending']['id'])
  for _ in range(2):self.answer(s,False);self.p.continue_support(s,s['pending']['id'])
  self.assertEqual(s['stage'],'independent')
  self.assertNotIn({'word':'cat','skill':'listen_write'},s['assessment_tasks'])
  self.assertIn({'word':'cat','skill':'listening'},s['assessment_tasks'])

 def test_old_in_progress_pilot_plan_and_records_stay_unchanged(self):
  self.setup_run();s=self.p.new('Legacy',include_listen_write=False)
  s.pop('common_control_version');before=copy.deepcopy(s['assessment_tasks']);raw=copy.deepcopy(s['records'])
  self.p.upgrade(s)
  self.assertEqual(s['assessment_tasks'],before);self.assertEqual(s['records'],raw)
  self.assertEqual(s['common_control_version'],0)
  self.block(s);self.assertEqual(len(s['assessment_tasks']),12)

 def test_persisted_api_flow_native_routes_and_reload(self):
  with TemporaryDirectory(dir=ROOT/'tmp') as temp:
   db=Path(temp)/'isolated.sqlite3';app=create_app(db);client=app.test_client()
   public=client.post('/api/pilot',json={'name':'Synthetic API common'}).get_json();url='/api/pilot/'+public['id']
   self.assertEqual(public['task_total'],16)
   for _ in range(4):
    state=app.extensions['pilot_store'].get(public['id']);q=state['pending']
    public=client.post(url+'/answer',json={'task_id':q['id'],'answer':q['word']}).get_json()
   self.assertEqual(public['task']['skill'],'listen_write')
   restarted=create_app(db);client=restarted.test_client()
   reloaded=client.get(url).get_json()['task']
   self.assertEqual(reloaded['id'],public['task']['id'])
   self.assertEqual(reloaded['skill'],'listen_write')
   with client.get(reloaded['audio']) as response:self.assertEqual(response.status_code,200)
   self.assertEqual(client.get(url+'/export').status_code,400)
   state=restarted.extensions['pilot_store'].get(public['id']);q=state['pending']
   client.post(url+'/answer',json={'task_id':q['id'],'answer':'wrong'})
   saved=restarted.extensions['pilot_store'].get(public['id'])
   self.assertEqual(saved['attempts'][-1]['format'],LISTEN)
   self.assertEqual(saved['attempts'][-1]['correct'],0)
   self.assertEqual(len(saved['attempts']),5)

if __name__=='__main__':unittest.main()
