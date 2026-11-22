"""Cevaptan önce bilinen geçmişi model girdilerine dönüştürür."""
from collections import defaultdict
from dataclasses import dataclass, field


CATEGORICAL_FEATURES = ['target_word', 'format']
NUMERIC_FEATURES = [
    'prior_target_count',
    'prior_accuracy_smoothed',
    'prior_word_count',
    'prior_word_accuracy_smoothed',
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


@dataclass
class LearnerHistory:
    target_count: int = 0
    correct_count: int = 0
    words: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    last_day: float = -1.0


def features_before_answer(history, word, exercise_format):
    """0 gözlemdeki 0.5, tarafsız başlangıç özelliğidir; model tahmini değildir."""
    word_count, word_correct = history.words.get(word, (0, 0))
    return {
        'target_word': word,
        'format': exercise_format,
        'prior_target_count': history.target_count,
        'prior_accuracy_smoothed': (history.correct_count + 1) / (history.target_count + 2),
        'prior_word_count': word_count,
        'prior_word_accuracy_smoothed': (word_correct + 1) / (word_count + 2),
    }


def exercise_rows(exercise, history):
    """Aynı cevaptaki bütün kelimeler, cevap öncesindeki aynı geçmişi görür."""
    assert exercise['source_format'] in ('reverse_translate', 'listen')
    assert exercise['days'] >= history.last_day
    rows = []
    labels = []
    metadata = []
    for token in exercise['tokens']:
        assert token['correct'] == 1 - token['source_error']
        assert token['correct'] in (0, 1)
        rows.append(features_before_answer(history, token['word_key'], exercise['source_format']))
        labels.append(token['correct'])
        metadata.append({
            'learner_id': exercise['learner_id'],
            'exercise_id': exercise['exercise_id'],
            'instance_id': token['instance_id'],
            'day': exercise['days'],
        })
    return rows, labels, metadata


def observe_completed_exercise(exercise, history):
    """Geçmiş, alıştırmanın tamamı cevaplandıktan sonra güncellenir."""
    for token in exercise['tokens']:
        history.target_count += 1
        history.correct_count += token['correct']
        word_state = history.words[token['word_key']]
        word_state[0] += 1
        word_state[1] += token['correct']
    history.last_day = exercise['days']
