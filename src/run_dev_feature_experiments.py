"""Üç sabit LR özellik deneyi; yalnız TRAIN fit, DEV karşılaştırması."""
from collections import defaultdict
from pathlib import Path
import csv
import json
import os
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from compare_dev_baselines import read_exercises, digest, evaluate, calibration_bins
from experimental_features import (
    FORMAT_FEATURES, RECENT_FEATURES, RECENT_EXERCISES, ExperimentalHistory,
    experimental_rows, observe_experimental_exercise,
)
from features import FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/dev_feature_experiments'
ORIGINAL = ROOT / 'outputs/logistic_first_run/logistic_model.joblib'
PARAMETERS = dict(C=1.0, solver='lbfgs', max_iter=1000, tol=1e-4, random_state=42)
VARIANTS = {
    'original': {'name': 'Mevcut model', 'extra': []},
    'format_history': {'name': '+ Biçime özel geçmiş', 'extra': FORMAT_FEATURES},
    'recent_history': {'name': '+ Yakın dönem', 'extra': RECENT_FEATURES},
    'format_and_recent': {'name': '+ İki grup birlikte', 'extra': FORMAT_FEATURES+RECENT_FEATURES},
}


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def build_split(split, histories):
    rows, labels, traces = [], [], []
    exercises = set()
    for exercise in read_exercises(split):
        assert exercise['exercise_id'] not in exercises
        exercises.add(exercise['exercise_id'])
        if split == 'dev':
            assert exercise['learner_id'] in histories
        history = histories[exercise['learner_id']]
        current_rows, current_y, current_traces = experimental_rows(exercise, history)
        rows.extend(current_rows)
        labels.extend(current_y)
        traces.extend(current_traces)
        # Mevcut alıştırmanın hiçbir etiketi mevcut özelliklere giremez.
        observe_experimental_exercise(exercise, history)
    frame = pd.DataFrame(rows, columns=FEATURES+FORMAT_FEATURES+RECENT_FEATURES)
    assert frame.notna().all().all()
    return frame, np.asarray(labels, dtype=np.int8), traces, exercises


def uncertainty(traces, y, predictions):
    learner_ids = np.asarray([trace['learner_id'] for trace in traces])
    learners, inverse = np.unique(learner_ids, return_inverse=True)
    counts = np.bincount(inverse)
    weights = np.random.default_rng(42).multinomial(len(learners), np.full(len(learners), 1/len(learners)), size=2000)
    denominator = weights @ counts
    losses = {key: -y*np.log(p)-(1-y)*np.log1p(-p) for key, p in predictions.items()}
    pairs = [('original', key) for key in VARIANTS if key != 'original']
    pairs += [('format_history', 'format_and_recent'), ('recent_history', 'format_and_recent')]
    results = {}
    for reference, candidate in pairs:
        diff = losses[reference]-losses[candidate]
        sample = (weights @ np.bincount(inverse, weights=diff))/denominator
        results[reference+'__minus__'+candidate] = {
            'reference': reference, 'candidate': candidate,
            'log_loss_improvement': float(diff.mean()),
            'percentile_95_interval': np.quantile(sample, [.025, .975]).tolist(),
        }
    return {'resampling_unit': 'learner with all DEV exercises and targets together',
            'learners': len(learners), 'draws': 2000, 'seed': 42,
            'exploratory_not_multiplicity_corrected_or_final_test': True, 'comparisons': results}


def plot(metrics, calibration):
    cache = ROOT / 'tmp/matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = [v['name'] for v in VARIANTS.values()]
    colors = ['#8295A8', '#087E86', '#BC813E', '#7352A1']
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    for ax, field, title in zip(axes, ['log_loss', 'roc_auc_correct_positive', 'error_recall_at_0_5'],
                               ['Olasılık kaybı — düşük daha iyi', 'AUC — yüksek daha iyi', 'Hata yakalama — eşik 0,50']):
        vals = [metrics[key][field] for key in VARIANTS]
        ax.barh(labels, vals, color=colors)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=11)
        ax.set_xlim(0, max(vals)*1.2 if field == 'log_loss' else 1)
        for i, value in enumerate(vals):
            ax.text(value+.005, i, f'{value:.4f}', va='center', fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Kontrollü özellik deneyleri — aynı DEV, aynı LR eğitim ayarları', fontsize=13)
    fig.savefig(OUT / 'ozellik_karsilastirmasi.png', dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    ax.plot([0, 1], [0, 1], '--', color='#8A96A2')
    for (key, variant), color in zip(VARIANTS.items(), colors):
        bins = calibration[key]
        ax.plot([b['mean_prediction'] for b in bins], [b['observed_correct'] for b in bins], 'o-', color=color, label=variant['name'])
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel='Tahmin edilen doğru olasılığı', ylabel='Gözlenen doğru oranı',
           title='DEV olasılık uyumu — düşük olasılıklarda kayıt sayıları az olabilir')
    ax.legend(fontsize=9)
    fig.savefig(OUT / 'olasilik_uyumu.png', dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'run_complete.json').exists():
        raise RuntimeError('Deney zaten tamamlandı; önce sonuçları incele.')
    frozen_hash = digest(ORIGINAL)
    # Sonuçları görmeden sabitlenen plan: pencere, üç özellik grubu ve ölçütler.
    plan = {
        'variants': {key: {'name': value['name'], 'raw_features': FEATURES+value['extra']} for key, value in VARIANTS.items()},
        'recent_window_completed_exercises': RECENT_EXERCISES,
        'recent_rate': '(correct targets in previous up-to-10 completed exercises + 1)/(targets in those exercises + 2)',
        'format_scope': 'Prior learner-format and learner-word-format target counts and Laplace rates',
        'empty_history': 'Count=0, smoothed rate=0.5 for every new feature group',
        'classifier_parameters': PARAMETERS, 'same_default_l2_as_original': True,
        'preprocessing': 'TRAIN-only OneHotEncoder for word/format, StandardScaler for all numeric features',
        'primary_metric': 'DEV log loss (lower is better)',
        'secondary_metrics': ['Brier', 'AUC', 'accuracy at 0.5', 'error recall and precision at 0.5', '10-bin calibration diagnostic'],
        'threshold_fixed': .5, 'no_hyperparameter_window_or_threshold_search': True,
        'fit_split': 'train', 'evaluation_split': 'dev', 'test_not_opened': True,
        'selection': 'Report minimum DEV log loss; inspect paired uncertainty and prefer simpler interpretation if added gain is unclear. No automatic production promotion.',
        'original_file_sha256': frozen_hash,
    }
    save_json('experiment_plan.json', plan)
    histories = defaultdict(ExperimentalHistory)
    train_x, train_y, train_traces, train_ids = build_split('train', histories)
    dev_x, dev_y, dev_traces, dev_ids = build_split('dev', histories)
    assert not train_ids & dev_ids
    # Altta yatan eski altı özellik, önceki doğrulanmış DEV tablosuyla aynı olmalı.
    previous = pd.read_csv(ROOT / 'outputs/dev_baseline_comparison/dev_predictions.csv')
    assert previous['instance_id'].tolist() == [t['instance_id'] for t in dev_traces]
    assert np.array_equal(dev_y, previous['actual_correct'].to_numpy())
    for field in FEATURES:
        if field in CATEGORICAL_FEATURES:
            assert dev_x[field].tolist() == previous[field].tolist()
        else:
            assert np.allclose(dev_x[field], previous[field], atol=1e-12, rtol=0)
    predictions, metrics, fits = {}, {}, {}
    for key, variant in VARIANTS.items():
        columns = FEATURES+variant['extra']
        numeric = NUMERIC_FEATURES+variant['extra']
        started = time.perf_counter()
        if key == 'original':
            model = joblib.load(ORIGINAL)
            fit_info = {'loaded_original_without_refit': True}
        else:
            preprocessing = ColumnTransformer([
                ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=True), CATEGORICAL_FEATURES),
                ('numeric', StandardScaler(), numeric),
            ], sparse_threshold=1.0)
            model = Pipeline([('preprocessing', preprocessing), ('classifier', LogisticRegression(**PARAMETERS))])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                model.fit(train_x[columns], train_y)
            errors = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
            if errors:
                raise RuntimeError('Yakınsama tamamlanmadı; bu adayın DEV sonucu hesaplanmadı: '+str(errors))
            scaler = model.named_steps['preprocessing'].named_transformers_['numeric']
            encoder = model.named_steps['preprocessing'].named_transformers_['categorical']
            assert np.allclose(scaler.mean_, train_x[numeric].mean().to_numpy(), rtol=0, atol=1e-10)
            assert set(encoder.categories_[0]) == set(train_x['target_word'])
            assert set(encoder.categories_[1]) == set(train_x['format'])
            joblib.dump(model, OUT / f'{key}_model.joblib')
            fit_info = {'fit_split': 'train', 'fit_targets': len(train_y),
                        'iterations': model.named_steps['classifier'].n_iter_.tolist(),
                        'fit_seconds': time.perf_counter()-started,
                        'convergence_warnings': errors, 'all_fit_warnings': [str(w.message) for w in caught],
                        'scaler_matches_train_only': True, 'vocabulary_matches_train_only': True,
                        'saved_model_sha256': digest(OUT / f'{key}_model.joblib')}
            # Bu katsayılar koşullu ilişkilerdir; nedensel öğrenme etkisi değildir.
            names = model.named_steps['preprocessing'].get_feature_names_out().tolist()
            coefficients = model.named_steps['classifier'].coef_[0]
            save_json(f'{key}_coefficients.json', {
                'numeric_coefficients_per_training_standard_deviation': {
                    name: float(coefficients[names.index('numeric__'+name)]) for name in numeric},
                'intercept': float(model.named_steps['classifier'].intercept_[0]),
                'interpretation': 'Conditional associations; correlated history features prevent simple causal interpretation.'})
        frozen_object = joblib.hash(model)
        assert model.named_steps['classifier'].classes_.tolist() == [0, 1]
        predictions[key] = model.predict_proba(dev_x[columns])[:, 1]
        assert joblib.hash(model) == frozen_object
        if key == 'original':
            assert np.allclose(predictions[key], previous['logistic'].to_numpy(), rtol=0, atol=1e-12)
        metrics[key] = evaluate(dev_y, predictions[key])
        fits[key] = {**fit_info, 'raw_feature_count': len(columns), 'raw_features': columns,
                     'model_unchanged_during_dev_prediction': True}
        print(json.dumps({'variant': key, 'fit': fit_info, 'dev_metrics': metrics[key]}, ensure_ascii=False), flush=True)
    masks = {
        'text': dev_x['format'].to_numpy() == 'reverse_translate',
        'listen': dev_x['format'].to_numpy() == 'listen',
        'learner_word_unseen': dev_x['prior_word_count'].to_numpy() == 0,
        'learner_word_seen_1_2': dev_x['prior_word_count'].between(1, 2).to_numpy(),
        'learner_word_seen_3_plus': dev_x['prior_word_count'].to_numpy() >= 3,
        'learner_word_format_unseen': dev_x['prior_word_format_count'].to_numpy() == 0,
    }
    segments = {name: {key: evaluate(dev_y[mask], p[mask]) for key, p in predictions.items()} for name, mask in masks.items()}
    calibration = {key: calibration_bins(dev_y, p) for key, p in predictions.items()}
    intervals = uncertainty(dev_traces, dev_y, predictions)
    best = min(metrics, key=lambda key: metrics[key]['log_loss'])
    save_json('comparison.json', {'variants': {key: v['name'] for key, v in VARIANTS.items()},
              'split': 'dev', 'train_targets': len(train_y), 'dev_targets': len(dev_y),
              'train_exercises': len(train_ids), 'dev_exercises': len(dev_ids),
              'train_learners': len(set(t['learner_id'] for t in train_traces)),
              'dev_learners': len(set(t['learner_id'] for t in dev_traces)),
              'metrics': metrics, 'segments': segments, 'minimum_dev_log_loss_variant': best,
              'production_model_changed': False})
    save_json('training_audit.json', {'passed': True, 'fits': fits, 'raw_splits_read': ['train', 'dev'],
              'train_dev_exercises_disjoint': True, 'original_features_and_predictions_reproduced': True,
              'current_labels_only_used_after_complete_exercise_features': True,
              'same_students_later_in_time_not_new_student_generalization': True,
              'original_model_file_unchanged': digest(ORIGINAL) == frozen_hash,
              'original_model_sha256': frozen_hash,
              'source_hashes': {split: digest(ROOT / f'data/prepared/slam200/{split}_exercises.jsonl') for split in ('train', 'dev')},
              'test_opened': False, 'test_predictions_computed': False,
              'feature_script_sha256': digest(ROOT / 'src/experimental_features.py'),
              'runner_sha256': digest(Path(__file__))})
    save_json('paired_uncertainty.json', intervals)
    save_json('calibration.json', calibration)
    # İlk 6 alıştırma özelliklerin nasıl oluştuğunu somut biçimde gösterir.
    first_ids = list(dict.fromkeys(t['exercise_id'] for t in dev_traces))[:6]
    examples = [{'trace': trace, 'features': dev_x.iloc[i].to_dict(), 'actual_correct': int(dev_y[i]),
                 'predictions': {key: float(p[i]) for key, p in predictions.items()}}
                for i, trace in enumerate(dev_traces) if trace['exercise_id'] in first_ids]
    save_json('first_exercise_examples.json', examples)
    with (OUT / 'dev_predictions.csv').open('w', encoding='utf-8', newline='') as handle:
        fields = list(dev_traces[0])+list(dev_x.columns)+['actual_correct']+list(VARIANTS)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, trace in enumerate(dev_traces):
            writer.writerow({**trace, **dev_x.iloc[i].to_dict(), 'actual_correct': int(dev_y[i]),
                             **{key: float(p[i]) for key, p in predictions.items()}})
    plot(metrics, calibration)
    save_json('run_complete.json', {'completed': True, 'new_candidate_models': 3,
              'minimum_dev_log_loss_variant': best, 'production_model_changed': False})
    print(json.dumps({'best_dev_log_loss': best, 'paired_intervals': intervals['comparisons']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
