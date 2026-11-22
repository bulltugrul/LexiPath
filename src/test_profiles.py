import copy
import unittest

from profiles import ProfileHistory, observe_for_profile, profile_snapshot, select_target


def exercise(index, mode='listen', result=1):
    return {'source_order': index, 'days': float(index), 'exercise_id': f'ex-{index}',
            'source_format': mode, 'tokens': [
                {'word_key': 'a', 'pos': 'DET', 'correct': 1-result, 'instance_id': f'{index}-a'},
                {'word_key': 'cat', 'pos': 'NOUN', 'correct': result, 'instance_id': f'{index}-cat'},
                {'word_key': 'dog', 'pos': 'NOUN', 'correct': 1-result, 'instance_id': f'{index}-dog'}]}


class ProfileChecks(unittest.TestCase):
    def test_target_selection_does_not_depend_on_answers(self):
        first = exercise(0)
        flipped = copy.deepcopy(first)
        for token in flipped['tokens']:
            token['correct'] = 1-token['correct']
        self.assertEqual(select_target(first['tokens'])['instance_id'], '0-cat')
        self.assertEqual(select_target(first['tokens'])['instance_id'], select_target(flipped['tokens'])['instance_id'])
        self.assertEqual(select_target([{'word_key': '-', 'pos': 'PUNCT'}, {'word_key': 'hello', 'pos': 'INTJ'}])['word_key'], 'hello')

    def test_one_exercise_is_one_observation_and_only_last_six_remain(self):
        state = ProfileHistory()
        for i in range(8):
            observe_for_profile(exercise(i, 'listen', int(i >= 2)), state)
        self.assertEqual(state.available['listen'], 8)
        self.assertEqual(len(state.windows['listen']), 6)
        self.assertEqual([r['exercise_id'] for r in state.windows['listen']], [f'ex-{i}' for i in range(2, 8)])
        for i in range(8, 14):
            observe_for_profile(exercise(i, 'reverse_translate', int(i >= 11)), state)
        snapshot = profile_snapshot('learner', state)
        self.assertEqual(snapshot['status'], 'provisional')
        self.assertEqual(snapshot['features'], {'text_target_accuracy': 0.5, 'listen_target_accuracy': 1.0})

    def test_missing_format_is_not_zero_performance(self):
        state = ProfileHistory()
        for i in range(6):
            observe_for_profile(exercise(i), state)
        snapshot = profile_snapshot('learner', state)
        self.assertEqual(snapshot['status'], 'insufficient_history')
        self.assertIsNone(snapshot['features'])


if __name__ == '__main__':
    unittest.main()
