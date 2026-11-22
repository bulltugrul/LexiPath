"""Profilleri göster; bu adımda henüz K-Means eğitme."""
from pathlib import Path
import json
import sys

from profiles import PROFILE_FEATURES, load_train_profiles

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]


def main():
    snapshots, audit = load_train_profiles(ROOT / 'data/prepared/slam200/train_exercises.jsonl')
    eligible = [p for p in snapshots if p['status'] == 'provisional']
    for number, snapshot in enumerate(snapshots, 1):
        snapshot['display_id'] = f'S{number:03d}'
    vectors = [tuple(p['features'][name] for name in PROFILE_FEATURES) for p in eligible]
    report = {
        **audit,
        'source_split': 'TRAIN only',
        'total_learners': len(snapshots),
        'eligible_learners': len(eligible),
        'insufficient_learners': len(snapshots)-len(eligible),
        'distinct_profiles': len(set(vectors)),
        'features': PROFILE_FEATURES,
        'observations_per_eligible_learner': {'text': 6, 'listen': 6},
        'max_distinct_profiles_with_six_binary_observations_per_format': 49,
        'duplicate_learner_rows_retained': True,
        'model_fitted': False,
    }
    selected_examples = []
    predicates = [
        lambda f: f['text_target_accuracy'] >= 5/6 and f['listen_target_accuracy'] >= 5/6,
        lambda f: f['text_target_accuracy'] - f['listen_target_accuracy'] >= 2/6-1e-9,
        lambda f: f['listen_target_accuracy'] - f['text_target_accuracy'] >= 2/6-1e-9,
        lambda f: f['text_target_accuracy'] <= 3/6 and f['listen_target_accuracy'] <= 3/6,
    ]
    for condition in predicates:
        chosen = next((p for p in eligible if condition(p['features']) and p not in selected_examples), None)
        if chosen:
            selected_examples.append(chosen)
    out = ROOT / 'data/prepared/slam200'
    for name, value in [('train_profiles.json', snapshots), ('profile_preparation_report.json', report), ('profile_examples.json', selected_examples)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for p in selected_examples:
        print(json.dumps({'student': p['display_id'], 'features': p['features'], 'text_results': [t['correct'] for t in p['windows']['reverse_translate']], 'listen_results': [t['correct'] for t in p['windows']['listen']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
