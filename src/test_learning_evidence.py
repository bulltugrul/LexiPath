import unittest
from learning_evidence import pattern_guidance,attempt_summary,pilot_evidence

class EvidenceSummaryChecks(unittest.TestCase):
 def test_guidance_uses_own_pattern_and_does_not_invent_a_difference(self):
  center={'text_target_accuracy':.9,'listen_target_accuracy':.5}
  p={'group':{'reference_center':center},'features':{'text_target_accuracy':.5,'listen_target_accuracy':.5}}
  self.assertIn('aynı',pattern_guidance(p)['text'])
  p['features']['text_target_accuracy']=1
  self.assertIn('dinleyerek yazma daha düşük',pattern_guidance(p)['text'])
 def test_topic_phase_and_rounds_are_kept_separate(self):
  rows=[{'word_id':'cat','topic_id':'animals','format':'listen','correct':v,'kind':kind,'session_id':session,'timestamp':str(i)}
        for i,(v,kind,session) in enumerate([(1,'diagnostic','s1'),(0,'practice','s2'),(0,'practice','s3'),(1,'practice','s3')])]
  result=attempt_summary(rows,{}, {'animals':{'title':'Hayvanlar'}})
  self.assertEqual(len(result['areas']),2)
  practice=next(a for a in result['areas'] if a['phase']=='alıştırma')
  self.assertEqual((practice['correct'],practice['count'],practice['words'],practice['rounds']),(1,3,1,2))
  self.assertEqual(result['repeated_words'][0]['last_three'],[0,0,1])
 def test_pilot_missing_delayed_is_not_zero_or_retained(self):
  o={'word':'cat','skill':'writing','measurement':0,'independent':1,'delayed':None,'extra_check':None,'decision':'waiting','paused':False}
  e=pilot_evidence([o],[],{'cat':{'topic_id':'animals'}},{'animals':{'title':'Hayvanlar'}})
  self.assertIsNone(e['areas'][0]['delayed']['rate']);self.assertEqual(e['remembered'],[])
