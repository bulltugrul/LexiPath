import unittest, wave, copy
from tempfile import TemporaryDirectory
from pathlib import Path
from tutor_engine import TutorEngine, ROOT, VISUAL_WORDS
from app_server import create_app

class CatalogVisualChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.engine=TutorEngine()
 def test_catalog_audio_support(self):
  self.assertEqual(len(self.engine.words),48)
  for word in self.engine.words:
   with wave.open(str(ROOT/f'web/static/audio/{word}.wav')) as audio:
    self.assertGreater(audio.getnframes(),0)
 def test_all_visual_bank_images_are_served_through_opaque_http_payload_urls(self):
  with TemporaryDirectory(dir=ROOT/'tmp') as folder:
   app=create_app(Path(folder)/'isolated.sqlite3');e=app.extensions['tutor_engine'];client=app.test_client()
   state=e.new_learner('Synthetic image route',['animals','food','daily'])
   for word in VISUAL_WORDS:
    with self.subTest(word=word):
     state['visual_task']={'id':'synthetic-'+word,'word_id':word,'options':VISUAL_WORDS[:3]}
     path=e.payload(state)['visual']['image']
     self.assertNotIn(word,path)
     with client.get(path) as response:
      self.assertEqual(response.status_code,200)
      self.assertEqual(response.mimetype,'image/svg+xml')
      self.assertIn(b'<svg',response.data)
   self.assertEqual(client.get('/pilot-image/unknown.svg').status_code,404)
   self.assertEqual(client.get('/pilot-image/'+e.audio_keys['water']+'.svg').status_code,404)
 def test_measurement_hidden_visual_separate_followup_updates_models(self):
  e=self.engine;s=e.new_learner('Synthetic',['animals'])
  for i in range(12):
   self.assertIsNone(e.payload(s)['question']['prediction'])
   q=s['session']['pending'];w=q['word_id']
   e.answer(s,q['id'],'wrong' if w=='cat' else w)
   self.assertIsNone(e.payload(s)['feedback']['p_correct_before'])
   e.next_step(s)
  before=copy.deepcopy(s['attempts']);profile=e.progress(s)['profile']
  e.prepare_visual(s)
  self.assertEqual(s['visual_task']['word_id'],'cat')
  task=s['visual_task'];e.answer_visual(s,task['id'],'cat')
  self.assertEqual(s['attempts'],before)
  self.assertEqual(e.progress(s)['profile'],profile)
  self.assertEqual(len(s['visual_attempts']),1)
  e.start_session(s)
  self.assertEqual(s['session']['pending']['word_id'],'cat')
  self.assertIsNotNone(e.payload(s)['question']['prediction'])
  q=s['session']['pending'];e.answer(s,q['id'],'cat')
  self.assertEqual(len(s['attempts']),13)
  self.assertTrue(s['attempts'][-1]['after_visual_review'])

if __name__=='__main__':unittest.main()
