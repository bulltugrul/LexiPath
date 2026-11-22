"""Basit yöntemlerin boş geçmiş ve kaynak sınırı kontrolleri."""
import unittest
from compare_dev_baselines import baseline_probabilities, read_exercises
from features import LearnerHistory, exercise_rows, observe_completed_exercise


class BaselineChecks(unittest.TestCase):
    def test_unseen_word_falls_back_without_creating_word_counts(self):
        words, modes = {}, {}
        row = {'target_word': 'cat', 'format': 'listen', 'prior_accuracy_smoothed': .8,
               'prior_word_count': 0, 'prior_word_accuracy_smoothed': .5}
        p = baseline_probabilities(row, .83, words, modes)
        self.assertEqual(p['learner_word_history'], .8)
        self.assertEqual(p['word_train'], .83)
        self.assertEqual(p['word_format_train'], .83)
        self.assertEqual((words, modes), ({}, {}))

    def test_laplace_formula_and_format_fallback(self):
        row = {'target_word': 'cat', 'format': 'listen', 'prior_accuracy_smoothed': .8,
               'prior_word_count': 2, 'prior_word_accuracy_smoothed': .25}
        p = baseline_probabilities(row, .83, {'cat': [8, 6]}, {('cat', 'listen'): [2, 0]})
        self.assertEqual(p['word_train'], .7)
        self.assertEqual(p['word_format_train'], .25)
        self.assertEqual(p['learner_word_history'], .25)
        self.assertEqual(baseline_probabilities(row, .83, {'cat': [8, 6]}, {})['word_format_train'], .7)

    def test_current_sister_token_does_not_enter_current_baseline(self):
        h = LearnerHistory()
        exercise = {'learner_id': 'a', 'exercise_id': 'x', 'days': .1, 'source_format': 'listen',
                    'tokens': [{'instance_id': str(i), 'word_key': 'cat', 'correct': c, 'source_error': 1-c}
                               for i, c in enumerate([1, 0])]}
        rows, _, _ = exercise_rows(exercise, h)
        probabilities = [baseline_probabilities(row, .83, {}, {}) for row in rows]
        self.assertEqual(probabilities[0], probabilities[1])
        self.assertEqual(probabilities[0]['learner_history'], .5)
        observe_completed_exercise(exercise, h)
        self.assertEqual(h.target_count, 2)
        self.assertEqual(h.words['cat'], [2, 1])

    def test_test_split_cannot_be_opened(self):
        with self.assertRaises(ValueError):
            next(read_exercises('test'))


if __name__ == '__main__':
    unittest.main()
