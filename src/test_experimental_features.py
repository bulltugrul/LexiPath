"""Deneylerde nedensellik, pencere sınırı ve biçim ayrılığı."""
import copy
import unittest

from experimental_features import ExperimentalHistory, experimental_rows, observe_experimental_exercise
from features import FEATURES, LearnerHistory, exercise_rows, observe_completed_exercise


def example(labels, mode='listen', day=.1, words=None):
    words = words or ['cat']*len(labels)
    return {'learner_id': 'a', 'exercise_id': f'x-{day}', 'source_format': mode, 'days': day,
            'tokens': [{'word_key': w, 'instance_id': f'{day}-{i}', 'correct': c, 'source_error': 1-c}
                       for i, (w, c) in enumerate(zip(words, labels))]}


class ExperimentalChecks(unittest.TestCase):
    def test_current_labels_do_not_change_any_current_feature(self):
        first, second = example([1, 0]), example([0, 0])
        h1, h2 = ExperimentalHistory(), ExperimentalHistory()
        rows1, _, _ = experimental_rows(first, h1)
        rows2, _, _ = experimental_rows(second, h2)
        self.assertEqual(rows1, rows2)
        self.assertEqual(rows1[0], rows1[1])
        self.assertEqual(rows1[0]['prior_recent_target_count'], 0)
        observe_experimental_exercise(first, h1)
        next_rows, _, _ = experimental_rows(example([1], day=.2), h1)
        self.assertEqual(next_rows[0]['prior_recent_target_count'], 2)
        self.assertEqual(next_rows[0]['prior_word_format_count'], 2)
        self.assertEqual(next_rows[0]['prior_word_format_accuracy_smoothed'], .5)

    def test_format_and_word_format_histories_are_separate(self):
        h = ExperimentalHistory()
        observe_experimental_exercise(example([1, 1], mode='listen'), h)
        text, _, _ = experimental_rows(example([0], mode='reverse_translate', day=.2), h)
        listen, _, _ = experimental_rows(example([0], day=.2), h)
        self.assertEqual(text[0]['prior_format_target_count'], 0)
        self.assertEqual(text[0]['prior_word_format_count'], 0)
        self.assertEqual(listen[0]['prior_format_target_count'], 2)
        self.assertEqual(listen[0]['prior_word_format_count'], 2)
        self.assertEqual(listen[0]['prior_format_accuracy_smoothed'], .75)
        self.assertEqual(text[0]['prior_word_count'], 2)

    def test_recent_window_is_ten_completed_exercises_not_ten_tokens(self):
        h = ExperimentalHistory()
        observe_experimental_exercise(example([0]*4), h)
        for i in range(1, 11):
            observe_experimental_exercise(example([1, 1], day=i), h)
        rows, _, _ = experimental_rows(example([0], day=11), h)
        self.assertEqual(len(h.recent_exercises), 10)
        self.assertEqual(rows[0]['prior_target_count'], 24)
        self.assertEqual(rows[0]['prior_recent_target_count'], 20)
        self.assertEqual(rows[0]['prior_recent_accuracy_smoothed'], 21/22)

    def test_original_six_features_match_old_implementation(self):
        old, new = LearnerHistory(), ExperimentalHistory()
        for ex in (example([1, 0]), example([1], mode='reverse_translate', day=.2), example([0, 0], day=.3)):
            old_rows, old_y, _ = exercise_rows(ex, old)
            new_rows, new_y, _ = experimental_rows(ex, new)
            self.assertEqual(old_y, new_y)
            self.assertEqual(old_rows, [{key: row[key] for key in FEATURES} for row in new_rows])
            observe_completed_exercise(ex, old)
            observe_experimental_exercise(ex, new)

    def test_reading_features_does_not_create_counts_or_mix_learners(self):
        h, other = ExperimentalHistory(), ExperimentalHistory()
        observe_experimental_exercise(example([1]), h)
        empty_before = copy.deepcopy(other)
        rows, _, _ = experimental_rows(example([0], day=.2), other)
        self.assertEqual(other, empty_before)
        self.assertEqual(rows[0]['prior_format_target_count'], 0)
        self.assertEqual(rows[0]['prior_recent_accuracy_smoothed'], .5)

    def test_elapsed_time_and_ids_are_not_feature_fields(self):
        ex = example([1])
        ex['elapsed_seconds_LOG_ONLY'] = 999
        rows, _, _ = experimental_rows(ex, ExperimentalHistory())
        self.assertFalse({'learner_id', 'exercise_id', 'instance_id', 'days', 'elapsed_seconds_LOG_ONLY', 'correct'} & set(rows[0]))


if __name__ == '__main__':
    unittest.main()
