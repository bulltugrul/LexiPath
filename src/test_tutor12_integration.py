"""12 özellikli sabit modelin yanıt öncesi/sonrası ve kayıt geçişi kontrolleri."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app_server import create_app
from features import FEATURES
from tutor_engine import TutorEngine, ACTIVE_FEATURES, MODEL_VERSION, TutorError, ROOT
from tutor_store import LocalStore


class IntegrationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = TutorEngine()

    def learner(self):
        return self.engine.new_learner('Test', ['animals'])

    def answer(self, state, correct=True):
        pending = state['session']['pending']
        word = self.engine.words[pending['word_id']]['target_word']
        self.engine.answer(state, pending['id'], word if correct else 'wrong')

    def test_active_model_contract_and_public_prediction_before_answer(self):
        state = self.learner()
        original = copy.deepcopy(state)
        public = self.engine.payload(state)
        self.assertIsNone(public['question']['prediction'])
        pending = state['session']['pending']
        pred = {'p_correct':pending['p_correct_before'],'model_version':pending['model_version'],'history':pending['history_before']}
        self.assertEqual(public['model']['raw_features'], 12)
        self.assertEqual(pred['model_version'], MODEL_VERSION)
        self.assertEqual(list(state['session']['pending']['features_before']), ACTIVE_FEATURES)
        self.assertEqual(pred['history']['general']['count'], 0)
        self.assertEqual(pred['history']['general']['smoothed_rate'], .5)
        self.assertGreater(pred['p_correct'], 0)
        self.assertLess(pred['p_correct'], 1)
        self.assertEqual(set(pred), {'p_correct', 'model_version', 'history'})
        self.assertEqual(state, original)

    def test_feedback_freezes_previous_probability_and_records_exactly_once(self):
        state = self.learner()
        q = copy.deepcopy(state['session']['pending'])
        self.answer(state, True)
        f = state['feedback']
        self.assertEqual(f['p_correct_before'], q['p_correct_before'])
        self.assertEqual(f['history_update']['before']['general'], {'count':0,'correct':0,'smoothed_rate':.5})
        for key in ['general', 'word', 'format', 'word_format', 'recent']:
            self.assertEqual(f['history_update']['after'][key]['count'], 1)
            self.assertEqual(f['history_update']['after'][key]['correct'], 1)
            self.assertEqual(f['history_update']['after'][key]['smoothed_rate'], 2/3)
        with self.assertRaises(TutorError):
            self.engine.answer(state, q['id'], 'cat')
        self.assertEqual(len(state['attempts']), 1)
        self.engine.next_step(state)
        pending = state['session']['pending']
        next_p = {'history':pending['history_before']}
        self.assertEqual(next_p['history']['general']['count'], 1)
        self.assertEqual(next_p['history']['format']['count'], 0)

    def test_wrong_answer_updates_denominator_and_recent_window_evicts_oldest(self):
        state = self.learner()
        for i in range(11):
            self.answer(state, correct=i != 0)
            if i == 0:
                f = state['feedback']['history_update']['after']['general']
                self.assertEqual(f, {'count':1,'correct':0,'smoothed_rate':1/3})
            if i != 10:
                self.engine.next_step(state)
        update = state['feedback']['history_update']
        self.assertEqual(update['before']['recent']['count'], 10)
        self.assertEqual(update['before']['recent']['correct'], 9)
        self.assertEqual(update['after']['recent']['count'], 10)
        self.assertEqual(update['after']['recent']['correct'], 10)
        self.assertEqual(update['after']['recent']['smoothed_rate'], 11/12)
        self.assertEqual(update['after']['general']['count'], 11)

    def test_legacy_pending_migration_preserves_attempts_and_invalidates_stale_id(self):
        state = self.learner()
        self.answer(state, False)
        self.engine.next_step(state)
        for attempt in state['attempts']:
            for key in ['model_version','history_before','history_after']:
                attempt.pop(key, None)
            attempt['features_before'] = {key:attempt['features_before'][key] for key in FEATURES}
        pending = state['session']['pending']
        pending.pop('model_version')
        pending.pop('history_before')
        pending['features_before'] = {key:pending['features_before'][key] for key in FEATURES}
        pending['p_correct_before'] = .123
        stale_id, old_word = pending['id'], pending['word_id']
        saved_attempts = copy.deepcopy(state['attempts'])
        with TemporaryDirectory(dir=ROOT/'tmp') as folder:
            db = Path(folder)/'migration.sqlite3'
            LocalStore(db).create(state)
            app = create_app(db)
            client = app.test_client()
            url = '/api/learners/'+state['id']
            response = client.get(url).get_json()
            reloaded = app.extensions['tutor_store'].get(state['id'])
            self.assertEqual(reloaded['attempts'], saved_attempts)
            self.assertEqual(reloaded['session']['pending']['word_id'], old_word)
            self.assertNotEqual(response['question']['id'], stale_id)
            self.assertIsNone(response['question']['prediction'])
            self.assertEqual(reloaded['session']['pending']['model_version'], MODEL_VERSION)
            self.assertNotEqual(reloaded['session']['pending']['p_correct_before'], .123)
            self.assertEqual(reloaded['session']['pending']['history_before']['general']['count'], 1)
            self.assertEqual(client.get(url).get_json(), response)
            self.assertEqual(client.post(url+'/answer', json={'question_id':stale_id,'answer':'apple'}).status_code,400)
            self.assertEqual(app.extensions['tutor_store'].get(state['id'])['attempts'], saved_attempts)

    def test_legacy_feedback_prediction_is_not_rewritten(self):
        state = self.learner()
        self.answer(state)
        state['feedback'].pop('history_update')
        state['feedback'].pop('model_version')
        state['feedback']['p_correct_before'] = .123
        self.engine.upgrade_state(state)
        f = self.engine.payload(state)['feedback']
        self.assertIsNone(f['p_correct_before'])
        self.assertEqual(state['feedback']['p_correct_before'], .123)
        self.assertEqual(f['model_version'], 'lr6-v1')
        self.assertNotIn('history_update', f)
        self.engine.next_step(state)
        self.assertEqual(state['session']['pending']['model_version'], MODEL_VERSION)


if __name__ == '__main__':
    unittest.main()
