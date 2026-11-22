"""Etiket sızıntısı ve öğrenci geçmişlerinin ayrılığı için küçük kontroller."""
import copy
import unittest

from features import LearnerHistory, exercise_rows, observe_completed_exercise


def example(labels, day=0.1):
    return {
        'learner_id': 'learner-a', 'exercise_id': 'exercise-a',
        'days': day, 'source_format': 'listen',
        'tokens': [{'instance_id': str(i), 'word_key': 'apple',
                    'source_error': 1-value, 'correct': value}
                   for i, value in enumerate(labels)],
    }


class CausalityChecks(unittest.TestCase):
    def test_changing_current_labels_cannot_change_current_features(self):
        original = example([1, 0])
        changed = example([0, 0])
        h1, h2 = LearnerHistory(), LearnerHistory()
        before1, _, _ = exercise_rows(original, h1)
        before2, _, _ = exercise_rows(changed, h2)
        self.assertEqual(before1, before2)
        self.assertEqual(before1[0], before1[1])
        observe_completed_exercise(original, h1)
        observe_completed_exercise(changed, h2)
        next1, _, _ = exercise_rows(example([1], 0.2), h1)
        next2, _, _ = exercise_rows(example([1], 0.2), h2)
        self.assertEqual(next1[0]['prior_word_count'], 2)
        self.assertNotEqual(next1, next2)

    def test_other_learner_has_no_access_to_first_learners_history(self):
        first, second = LearnerHistory(), LearnerHistory()
        observe_completed_exercise(example([1]), first)
        second_rows, _, _ = exercise_rows(example([0]), second)
        self.assertEqual(second_rows[0]['prior_target_count'], 0)
        self.assertEqual(second_rows[0]['prior_accuracy_smoothed'], 0.5)

    def test_time_ids_and_labels_are_not_model_features(self):
        exercise = copy.deepcopy(example([1]))
        exercise['elapsed_seconds_LOG_ONLY'] = 999
        rows, _, _ = exercise_rows(exercise, LearnerHistory())
        self.assertEqual(set(rows[0]), {
            'target_word', 'format', 'prior_target_count',
            'prior_accuracy_smoothed', 'prior_word_count',
            'prior_word_accuracy_smoothed',
        })


if __name__ == '__main__':
    unittest.main()
