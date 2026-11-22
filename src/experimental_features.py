"""Deney özellikleri: mevcut uygulamanın altı özellikli sözleşmesini değiştirmez."""
from collections import defaultdict, deque
from dataclasses import dataclass, field

from features import LearnerHistory, exercise_rows, observe_completed_exercise, features_before_answer

RECENT_EXERCISES = 10
FORMAT_FEATURES = [
    'prior_format_target_count', 'prior_format_accuracy_smoothed',
    'prior_word_format_count', 'prior_word_format_accuracy_smoothed',
]
RECENT_FEATURES = ['prior_recent_target_count', 'prior_recent_accuracy_smoothed']


@dataclass
class ExperimentalHistory(LearnerHistory):
    formats: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    word_formats: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    # Her kayıt tamamlanmış bir alıştırmanın (hedef sayısı, doğru sayısı) çiftidir.
    recent_exercises: deque = field(default_factory=lambda: deque(maxlen=RECENT_EXERCISES))


def experimental_features_before_answer(history, word, mode):
    """Eğitim ve canlı tahmin için aynı 12 özellik; güncel cevap gerekmez."""
    row = features_before_answer(history, word, mode)
    format_n, format_s = history.formats.get(mode, (0, 0))
    recent_n = sum(n for n, _ in history.recent_exercises)
    recent_s = sum(s for _, s in history.recent_exercises)
    word_n, word_s = history.word_formats.get((word, mode), (0, 0))
    row.update({
            'prior_format_target_count': format_n,
            'prior_format_accuracy_smoothed': (format_s+1)/(format_n+2),
            'prior_word_format_count': word_n,
            'prior_word_format_accuracy_smoothed': (word_s+1)/(word_n+2),
            'prior_recent_target_count': recent_n,
            'prior_recent_accuracy_smoothed': (recent_s+1)/(recent_n+2),
    })
    return row


def experimental_rows(exercise, history):
    rows, labels, metadata = exercise_rows(exercise, history)
    rows = [experimental_features_before_answer(history, row['target_word'], exercise['source_format']) for row in rows]
    return rows, labels, metadata


def observe_experimental_exercise(exercise, history):
    """Yalnız bütün mevcut tahminler üretildikten sonra çağrılmalıdır."""
    observe_completed_exercise(exercise, history)
    mode = exercise['source_format']
    for token in exercise['tokens']:
        for pair in (history.formats[mode], history.word_formats[(token['word_key'], mode)]):
            pair[0] += 1
            pair[1] += token['correct']
    history.recent_exercises.append((len(exercise['tokens']), sum(t['correct'] for t in exercise['tokens'])))
