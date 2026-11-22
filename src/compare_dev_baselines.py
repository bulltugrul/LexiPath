"""Sabit ilk LR modelini yalnız DEV'de nedensel geçmiş yöntemleriyle karşılaştırır.

Yeni model eğitmez, TEST açmaz, uygulamanın modelini değiştirmez.
Karşılaştırma kuralları aşağıda sabittir; DEV ile ağırlık/eşik aranmaz.
"""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, log_loss, roc_auc_score

from features import FEATURES, LearnerHistory, exercise_rows, observe_completed_exercise

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/prepared/slam200'
OUT = ROOT / 'outputs/dev_baseline_comparison'
MODEL_PATH = ROOT / 'outputs/logistic_first_run/logistic_model.joblib'
NAMES = {
    'constant_train': 'Sabit TRAIN oranı',
    'learner_history': 'Öğrencinin genel geçmişi',
    'word_train': 'Kelimenin TRAIN geçmişi',
    'word_format_train': 'Kelime + biçim TRAIN geçmişi',
    'learner_word_history': 'Öğrenci + kelime geçmişi',
    'logistic': 'Mevcut lojistik regresyon',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_exercises(split):
    if split not in ('train', 'dev'):
        raise ValueError('Bu karşılaştırma yalnız TRAIN ve DEV okuyabilir.')
    with (DATA / f'{split}_exercises.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            yield json.loads(line)


def baseline_probabilities(features, train_rate, word_counts, word_format_counts):
    """Sayaçlar [gözlem, doğru]; kelime havuzları yalnız TRAIN'den gelir."""
    word, mode = features['target_word'], features['format']
    n_word, s_word = word_counts.get(word, (0, 0))
    p_word = (s_word+1)/(n_word+2) if n_word else train_rate
    n_mode, s_mode = word_format_counts.get((word, mode), (0, 0))
    p_word_mode = (s_mode+1)/(n_mode+2) if n_mode else p_word
    learner = features['prior_accuracy_smoothed']
    return {
        'constant_train': train_rate,
        'learner_history': learner,
        'word_train': p_word,
        'word_format_train': p_word_mode,
        'learner_word_history': features['prior_word_accuracy_smoothed'] if features['prior_word_count'] else learner,
    }


def calibration_bins(y, p):
    """10 sabit eşit genişlikli aralık; tanısaldır, kalibrasyon eğitimi değildir."""
    bins = []
    assigned = np.minimum((p*10).astype(int), 9)
    for i in range(10):
        mask = assigned == i
        if not mask.any():
            continue
        bins.append({'lower': i/10, 'upper': (i+1)/10, 'records': int(mask.sum()),
                     'mean_prediction': float(p[mask].mean()), 'observed_correct': float(y[mask].mean())})
    return bins


def evaluate(y, p):
    if not len(y):
        return {'records': 0}
    assert np.isfinite(p).all() and ((p > 0) & (p < 1)).all()
    # Önceki deneydeki aynı sabit karar: p_correct >= 0.50 -> doğru.
    pred = (p >= .5).astype(np.int8)
    matrix = confusion_matrix(y, pred, labels=[0, 1])
    errors, warnings = int(matrix[0].sum()), int(matrix[:, 0].sum())
    bins = calibration_bins(y, p)
    return {
        'records': len(y), 'observed_correct': float(y.mean()), 'mean_prediction': float(p.mean()),
        'accuracy_at_0_5': float(accuracy_score(y, pred)),
        'roc_auc_correct_positive': float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
        'log_loss': float(log_loss(y, p, labels=[0, 1])),
        'brier_score': float(brier_score_loss(y, p)),
        'error_recall_at_0_5': float(matrix[0, 0]/errors) if errors else None,
        'error_precision_at_0_5': float(matrix[0, 0]/warnings) if warnings else 0.0,
        'actual_errors': errors, 'caught_errors': int(matrix[0, 0]),
        'missed_errors': int(matrix[0, 1]), 'correct_answers_flagged_as_errors': int(matrix[1, 0]),
        'confusion_rows_actual_cols_predicted_error_correct': matrix.tolist(),
        'calibration_gap_equal_width_10': sum(b['records']*abs(b['mean_prediction']-b['observed_correct']) for b in bins)/len(y),
    }


def paired_bootstrap(frame, y, predictions):
    """Öğrenciyi bütün olarak yeniden örnekle: aynı kişideki hedefler bağımsız sayılmaz."""
    learners, learner_index = np.unique(frame['learner_id'].to_numpy(), return_inverse=True)
    counts = np.bincount(learner_index)
    rng = np.random.default_rng(42)
    weights = rng.multinomial(len(learners), np.full(len(learners), 1/len(learners)), size=2000)
    denominator = weights @ counts
    model_loss = -(y*np.log(predictions['logistic'])+(1-y)*np.log1p(-predictions['logistic']))
    result = {}
    for key, p in predictions.items():
        if key == 'logistic':
            continue
        baseline_loss = -(y*np.log(p)+(1-y)*np.log1p(-p))
        # Pozitif fark, LR'nin daha düşük kayıp ürettiği anlamına gelir.
        per_learner = np.bincount(learner_index, weights=baseline_loss-model_loss)
        differences = (weights @ per_learner)/denominator
        result[key] = {'baseline_minus_lr_log_loss': float((baseline_loss-model_loss).mean()),
                       'percentile_95_interval': np.quantile(differences, [.025, .975]).tolist()}
    return {'resampling_unit': 'learner (all exercises/tokens retained together)', 'learners': len(learners),
            'draws': 2000, 'seed': 42, 'exploratory_dev_interval_not_final_test': True, 'comparisons': result}


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def charts(metrics, calibration):
    cache = ROOT / 'tmp/matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = ['Sabit', 'Öğrenci', 'Kelime', 'Kelime + biçim', 'Öğrenci + kelime', 'Lojistik regresyon']
    colors = ['#A5B3C1']*5+['#087E86']
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), constrained_layout=True)
    for ax, metric, title in zip(axes, ['log_loss', 'roc_auc_correct_positive', 'error_recall_at_0_5'],
                                 ['Olasılık kaybı — düşük daha iyi', 'AUC — yüksek daha iyi', 'Hata yakalama — eşik 0,50']):
        values = [metrics[k][metric] for k in NAMES]
        ax.barh(labels, values, color=colors)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=11)
        ax.set_xlim(0, 1 if metric != 'log_loss' else max(values)*1.22)
        for i, value in enumerate(values):
            ax.text(value+.008, i, f'{value:.3f}', va='center', fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Yalnız DEV: aynı 23.583 hedefte, cevap öncesi geçmişle karşılaştırma', fontsize=14)
    fig.savefig(OUT / 'dev_karsilastirma.png', dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    ax.plot([0, 1], [0, 1], '--', color='#8A96A2', label='Tahmin = gözlenen oran')
    for key in ('learner_history', 'word_format_train', 'learner_word_history', 'logistic'):
        bins = calibration[key]
        ax.plot([b['mean_prediction'] for b in bins], [b['observed_correct'] for b in bins],
                'o-', label=NAMES[key], linewidth=2 if key == 'logistic' else 1)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel='Tahmin edilen doğru cevap olasılığı',
           ylabel='O aralıkta gözlenen doğru cevap oranı', title='DEV olasılık uyumu — 10 sabit aralık')
    ax.legend(fontsize=9)
    fig.savefig(OUT / 'dev_olasilik_uyumu.png', dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'run_complete.json').exists():
        raise RuntimeError('Karşılaştırma zaten tamamlandı; önce mevcut sonuçları incele.')
    frozen_file_hash = digest(MODEL_PATH)
    model = joblib.load(MODEL_PATH)
    frozen_object_hash = joblib.hash(model)
    original = json.loads((ROOT / 'outputs/logistic_first_run/metrics.json').read_text(encoding='utf-8'))
    histories = defaultdict(LearnerHistory)
    words, word_formats = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    train_count = train_correct = train_exercises = 0
    train_ids = set()
    for exercise in read_exercises('train'):
        assert exercise['exercise_id'] not in train_ids
        train_ids.add(exercise['exercise_id'])
        for token in exercise['tokens']:
            n = token['correct']
            assert n == 1-token['source_error']
            for key, store in [(token['word_key'], words), ((token['word_key'], exercise['source_format']), word_formats)]:
                store[key][0] += 1
                store[key][1] += n
            train_count += 1
            train_correct += n
        observe_completed_exercise(exercise, histories[exercise['learner_id']])
        train_exercises += 1
    train_rate = train_correct/train_count
    train_counters_hash = joblib.hash((dict(words), dict(word_formats)))
    rows, labels, traces, exercise_ids = [], [], [], set()
    predicted = {key: [] for key in NAMES if key != 'logistic'}
    for exercise in read_exercises('dev'):
        assert exercise['exercise_id'] not in train_ids and exercise['exercise_id'] not in exercise_ids
        exercise_ids.add(exercise['exercise_id'])
        assert exercise['learner_id'] in histories
        history = histories[exercise['learner_id']]
        current_rows, current_labels, current_traces = exercise_rows(exercise, history)
        # Bütün mevcut alıştırma tahminleri tamamlanmadan hiçbir etiketi geçmişe ekleme.
        for row in current_rows:
            for key, value in baseline_probabilities(row, train_rate, words, word_formats).items():
                predicted[key].append(value)
        rows.extend(current_rows)
        labels.extend(current_labels)
        traces.extend(current_traces)
        observe_completed_exercise(exercise, history)
    frame = pd.DataFrame(rows, columns=FEATURES)
    trace_frame = pd.DataFrame(traces)
    y = np.asarray(labels, dtype=np.int8)
    predictions = {key: np.asarray(p, dtype=float) for key, p in predicted.items()}
    predictions['logistic'] = model.predict_proba(frame)[:, 1]
    metrics = {key: evaluate(y, predictions[key]) for key in NAMES}
    # Eski DEV sonucu birebir yeniden üretilebilmeli; yeni deney TEST'e dokunmaz.
    for key in ('accuracy_at_0_5', 'roc_auc_correct_positive', 'log_loss', 'brier_score', 'error_recall_at_0_5'):
        assert np.isclose(metrics['logistic'][key], original['metrics']['dev']['logistic'][key], rtol=0, atol=1e-12)
    assert joblib.hash(model) == frozen_object_hash
    assert digest(MODEL_PATH) == frozen_file_hash
    assert joblib.hash((dict(words), dict(word_formats))) == train_counters_hash
    masks = {
        'text': frame['format'].to_numpy() == 'reverse_translate',
        'listen': frame['format'].to_numpy() == 'listen',
        'learner_word_unseen': frame['prior_word_count'].to_numpy() == 0,
        'learner_word_seen_1_2': frame['prior_word_count'].between(1, 2).to_numpy(),
        'learner_word_seen_3_plus': frame['prior_word_count'].to_numpy() >= 3,
    }
    segments = {name: {key: evaluate(y[mask], p[mask]) for key, p in predictions.items()} for name, mask in masks.items()}
    calibration = {key: calibration_bins(y, p) for key, p in predictions.items()}
    bootstrap = paired_bootstrap(trace_frame, y, predictions)
    strongest = min((key for key in NAMES if key != 'logistic'), key=lambda key: metrics[key]['log_loss'])
    # Açıklama örnekleri: en güçlü basit yöntem ve LR olasılıklarının ayrıldığı
    # kayıtları inceleriz; başarı ölçümü bu seçilmiş örnekler üzerinden yapılmaz.
    examples = []
    p_lr, p_simple = predictions['logistic'], predictions[strongest]
    for actual in (0, 1):
        for favorable in ('lr_higher', 'simple_higher'):
            direction = p_lr-p_simple if favorable == 'lr_higher' else p_simple-p_lr
            candidates = np.flatnonzero((y == actual) & (direction > .05))
            if len(candidates):
                ordered = candidates[np.argsort(direction[candidates], kind='stable')]
                index = int(ordered[len(ordered)//2])
                examples.append({'selection': 'Illustrative middle probability disagreement >0.05; not a representative performance sample',
                                 'direction': favorable, 'trace': traces[index], 'features': rows[index],
                                 'actual_correct': int(y[index]), 'strongest_simple_method': strongest,
                                 'predictions': {key: float(p[index]) for key, p in predictions.items()}})
    save_json('comparison.json', {'split': 'dev', 'names': NAMES, 'train_targets': train_count,
              'dev_exercises': len(exercise_ids), 'dev_learners': trace_frame['learner_id'].nunique(),
              'baseline_rules': {
                  'constant_train': 'Unsmoothed overall TRAIN correctness, fixed.',
                  'learner_history': '(prior learner correct + 1)/(prior learner targets + 2).',
                  'word_train': 'Laplace TRAIN pooled word rate; unseen word -> overall TRAIN rate. Frozen during DEV.',
                  'word_format_train': 'Laplace TRAIN pooled word-format rate; absent pair -> word_train. Frozen during DEV.',
                  'learner_word_history': 'Laplace prior learner-word rate; no prior word observations -> learner_history.',
                  'logistic': 'Original six-feature saved pipeline; predict only, no refit or recalibration.'},
              'metrics': metrics, 'segments': segments, 'strongest_simple_by_dev_log_loss': strongest})
    save_json('calibration.json', calibration)
    save_json('paired_uncertainty.json', bootstrap)
    save_json('prediction_examples.json', examples)
    save_json('audit.json', {'passed': True, 'raw_splits_read': ['train', 'dev'], 'test_predictions_not_computed': True,
              'model_refit': False, 'model_file_sha256': frozen_file_hash, 'model_object_unchanged': True,
              'train_word_counters_frozen_during_dev': True, 'original_dev_metrics_reproduced': True,
              'threshold_fixed': .5, 'smoothing_fixed': 'add-one / Laplace; no tuning',
              'current_exercise_labels_observed_only_after_all_feature_rows_and_baseline_predictions': True,
              'protocol': 'Same learners later in time. DEV starts with TRAIN histories and receives feedback only after each completed exercise. Pooled word baselines remain TRAIN-only.',
              'source_hashes': {split: digest(DATA / f'{split}_exercises.jsonl') for split in ('train', 'dev')},
              'script_sha256': digest(Path(__file__)), 'train_exercises': train_exercises,
              'limits': ['DEV exploratory comparison; no new learner generalization evaluation.',
                         'No custom app data or teaching-effect evaluation.',
                         'Calibration gap depends on fixed bins; it is not a fitted calibration method.',
                         'Baseline selection on DEV is exploratory; no final TEST claim is made.']})
    with (OUT / 'dev_predictions.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(traces[0])+FEATURES+['actual_correct']+list(NAMES))
        writer.writeheader()
        for i, trace in enumerate(traces):
            writer.writerow({**trace, **rows[i], 'actual_correct': int(y[i]), **{key: float(p[i]) for key, p in predictions.items()}})
    charts(metrics, calibration)
    save_json('run_complete.json', {'completed': True, 'split': 'dev', 'new_model_trained': False})
    print(json.dumps({'strongest_simple': strongest, 'metrics': metrics, 'paired_log_loss': bootstrap['comparisons']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
