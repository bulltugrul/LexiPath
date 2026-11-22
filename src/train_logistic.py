"""İlk deneme: yalnız TRAIN ile öğren; DEV ve TEST'te sıralı geri bildirim kullan."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import os
import platform
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, brier_score_loss, confusion_matrix, log_loss,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from features import (
    CATEGORICAL_FEATURES, NUMERIC_FEATURES, FEATURES,
    LearnerHistory, exercise_rows, observe_completed_exercise,
)

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/prepared/slam200'
OUTPUT = ROOT / 'outputs/logistic_first_run'
PARAMETERS = dict(C=1.0, solver='lbfgs', max_iter=1000, tol=1e-4, random_state=42)


def save_json(name, value):
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load_split(split, histories):
    """DEV/TEST'in yalnız önceki tamamlanmış cevapları sonraki girdiye girebilir."""
    rows, labels, metadata = [], [], []
    with (DATA / f'{split}_exercises.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            exercise = json.loads(line)
            history = histories[exercise['learner_id']]
            current_rows, current_labels, current_metadata = exercise_rows(exercise, history)
            rows.extend(current_rows)
            labels.extend(current_labels)
            metadata.extend(current_metadata)
            # Özellikler kaydedilmeden bu satır çalışmamalı.
            observe_completed_exercise(exercise, history)
    frame = pd.DataFrame(rows, columns=FEATURES)
    assert frame.notna().all().all()
    return frame, np.asarray(labels, dtype=np.int8), metadata


def evaluate(labels, probabilities):
    predicted = (probabilities >= 0.5).astype(np.int8)
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    return {
        'records': int(len(labels)),
        'accuracy_at_0_5': float(accuracy_score(labels, predicted)),
        'roc_auc_correct_positive': float(roc_auc_score(labels, probabilities)),
        'log_loss': float(log_loss(labels, probabilities, labels=[0, 1])),
        'brier_score': float(brier_score_loss(labels, probabilities)),
        'error_recall_at_0_5': float(recall_score(labels, predicted, pos_label=0, zero_division=0)),
        'error_precision_at_0_5': float(precision_score(labels, predicted, pos_label=0, zero_division=0)),
        'confusion_rows_actual_cols_predicted_order_error_correct': matrix.tolist(),
        'actual_errors': int(matrix[0].sum()),
        'caught_errors': int(matrix[0, 0]),
        'missed_errors': int(matrix[0, 1]),
        'correct_answers_flagged_as_errors': int(matrix[1, 0]),
    }


def plot_results(y, model_p, baseline_p, results):
    cache_dir = ROOT / 'tmp/matplotlib'
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache_dir))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import roc_curve

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    fpr, tpr, _ = roc_curve(y, model_p)
    auc = results['logistic']['roc_auc_correct_positive']
    axes[0].plot(fpr, tpr, color='#146b73', lw=2, label=f'Lojistik regresyon: AUC {auc:.3f}')
    axes[0].plot([0, 1], [0, 1], '--', color='#777777', label='Sabit olasılık: AUC 0.500')
    axes[0].set(xlabel='Yanlış pozitif oranı', ylabel='Doğru pozitif oranı', title='Sıralama gücü (pozitif: doğru cevap)')
    axes[0].legend(loc='lower right', fontsize=8)

    observed, estimated = calibration_curve(y, model_p, n_bins=10, strategy='quantile')
    axes[1].plot([0, 1], [0, 1], '--', color='#777777')
    axes[1].plot(estimated, observed, 'o-', color='#146b73', label='Model, eşit sayılı 10 grup')
    axes[1].scatter([baseline_p[0]], [y.mean()], marker='s', color='#bd7733', label='Sabit olasılık')
    axes[1].set(xlim=(0, 1), ylim=(0, 1), xlabel='Tahmin edilen doğru olasılığı', ylabel='Gözlenen doğru oranı', title='Olasılıkların gözlemlerle uyumu')
    axes[1].legend(loc='lower right', fontsize=8)

    matrix = np.asarray(results['logistic']['confusion_rows_actual_cols_predicted_order_error_correct'])
    axes[2].imshow(matrix, cmap='Blues')
    for i in range(2):
        for j in range(2):
            axes[2].text(j, i, f'{matrix[i,j]:,}', ha='center', va='center', fontsize=13,
                         color='white' if matrix[i,j] > matrix.max()/2 else 'black')
    axes[2].set(xticks=[0, 1], yticks=[0, 1], xticklabels=['Yanlış', 'Doğru'], yticklabels=['Yanlış', 'Doğru'],
                xlabel='Modelin sınıf tahmini', ylabel='Gerçek cevap', title='Sınıf tahminleri (eşik 0.50)')
    fig.suptitle('İlk lojistik regresyon deneyi — 200 öğrencinin sonraki TEST cevapları', fontsize=13)
    fig.savefig(OUTPUT / 'sonuc_grafikleri.png', dpi=160)
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Aynı çıktının üzerine tekrar eğitim yapıp TEST'i sessizce yeniden ölçmeyelim.
    if (OUTPUT / 'metrics.json').exists():
        raise RuntimeError('This run already exists. Review its results instead of silently rerunning TEST.')
    histories = defaultdict(LearnerHistory)
    started = time.perf_counter()
    train_x, train_y, train_meta = load_split('train', histories)
    print(f'TRAIN: {len(train_y):,} hedef; 6 ham özellik.', flush=True)

    preprocessing = ColumnTransformer([
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=True), CATEGORICAL_FEATURES),
        ('numeric', StandardScaler(), NUMERIC_FEATURES),
    ], sparse_threshold=1.0)
    model = Pipeline([('preprocessing', preprocessing), ('classifier', LogisticRegression(**PARAMETERS))])
    fit_started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(train_x, train_y)
    convergence_warnings = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    if convergence_warnings:
        raise RuntimeError('Convergence did not pass; TEST has not been evaluated: ' + '; '.join(convergence_warnings))
    assert model.named_steps['classifier'].classes_.tolist() == [0, 1]
    numeric_scaler = model.named_steps['preprocessing'].named_transformers_['numeric']
    assert np.allclose(numeric_scaler.mean_, train_x[NUMERIC_FEATURES].mean().to_numpy())
    encoder = model.named_steps['preprocessing'].named_transformers_['categorical']
    assert set(encoder.categories_[0]) == set(train_x['target_word'])
    frozen_coefficients = model.named_steps['classifier'].coef_.copy()
    frozen_intercept = model.named_steps['classifier'].intercept_.copy()
    frozen_mean = numeric_scaler.mean_.copy()
    frozen_categories = [values.copy() for values in encoder.categories_]
    fit_seconds = time.perf_counter() - fit_started
    joblib.dump(model, OUTPUT / 'logistic_model.joblib')
    frozen_hash = hashlib.sha256((OUTPUT / 'logistic_model.joblib').read_bytes()).hexdigest()
    baseline_probability = float(train_y.mean())
    print(f'Eğitim tamamlandı: {fit_seconds:.2f} saniye; optimizer iterations={model.named_steps["classifier"].n_iter_.tolist()}', flush=True)

    metrics = {}
    split_data = {}
    for split in ('train', 'dev', 'test'):
        if split == 'train':
            frame, labels, metadata = train_x, train_y, train_meta
        else:
            frame, labels, metadata = load_split(split, histories)
        # Model dönüşümleri ve ağırlıkları bu noktadan itibaren hiç fit edilmez.
        p_correct = model.predict_proba(frame)[:, 1]
        baseline = np.full(len(labels), baseline_probability)
        metrics[split] = {'constant_baseline': evaluate(labels, baseline), 'logistic': evaluate(labels, p_correct)}
        known_words = set(encoder.categories_[0])
        metrics[split]['unseen_word_records'] = int((~frame['target_word'].isin(known_words)).sum())
        metrics[split]['by_format'] = {}
        for mode in ('reverse_translate', 'listen'):
            mask = frame['format'].to_numpy() == mode
            metrics[split]['by_format'][mode] = {'constant_baseline': evaluate(labels[mask], baseline[mask]), 'logistic': evaluate(labels[mask], p_correct[mask])}
        split_data[split] = (frame, labels, metadata, p_correct, baseline)
        print(json.dumps({'split': split, 'baseline': metrics[split]['constant_baseline'], 'logistic': metrics[split]['logistic']}, ensure_ascii=False), flush=True)

    assert hashlib.sha256((OUTPUT / 'logistic_model.joblib').read_bytes()).hexdigest() == frozen_hash
    assert np.array_equal(model.named_steps['classifier'].coef_, frozen_coefficients)
    assert np.array_equal(model.named_steps['classifier'].intercept_, frozen_intercept)
    assert np.array_equal(numeric_scaler.mean_, frozen_mean)
    assert all(np.array_equal(now, before) for now, before in zip(encoder.categories_, frozen_categories))
    feature_names = model.named_steps['preprocessing'].get_feature_names_out().tolist()
    coefficients = model.named_steps['classifier'].coef_[0]
    save_json('coefficients.json', {'intercept': float(model.named_steps['classifier'].intercept_[0]), 'numeric_coefficients_per_one_training_standard_deviation': {name: float(coefficients[feature_names.index('numeric__'+name)]) for name in NUMERIC_FEATURES}, 'all_coefficients': dict(zip(feature_names, map(float, coefficients))), 'note': 'Associations conditional on the model, not causal learning effects.'})

    # DEV örnekleri açıklama içindir; en iyi görünen örneklerle başarı ölçülmez.
    frame, labels, metadata, probabilities, _ = split_data['dev']
    examples = []
    for actual, predicted_class in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        candidates = np.flatnonzero((labels == actual) & ((probabilities >= 0.5) == predicted_class))
        if not len(candidates):
            continue
        index = int(candidates[len(candidates)//2])
        example = {'split': 'dev', 'selection': 'One illustrative record from each available actual/predicted class combination', **metadata[index], 'features': frame.iloc[index].to_dict(), 'p_correct': float(probabilities[index]), 'p_error': float(1-probabilities[index]), 'actual_correct': int(labels[index]), 'predicted_correct_at_0_5': int(predicted_class)}
        encoded_row = model.named_steps['preprocessing'].transform(frame.iloc[[index]])
        score = float(np.asarray(encoded_row @ coefficients).ravel()[0] + model.named_steps['classifier'].intercept_[0])
        sigmoid = float(1/(1+np.exp(-score)))
        assert np.isclose(sigmoid, probabilities[index])
        example['linear_score'] = score
        example['sigmoid_reproduces_probability'] = True
        examples.append(example)
    save_json('prediction_examples.json', examples)
    versions = {'python': platform.python_version(), 'scikit_learn': sklearn.__version__, 'numpy': np.__version__, 'pandas': pd.__version__}
    audit = {'passed': True, 'raw_features': FEATURES, 'forbidden_inputs_absent': ['learner_id', 'instance_id', 'exercise_id', 'day', 'elapsed_seconds', 'current_correct'], 'scaler_fit_matches_train_only': True, 'encoder_vocabulary_matches_train_only': True, 'in_memory_model_scaler_and_vocabulary_unchanged_on_heldout': True, 'current_exercise_labels_used_only_after_all_features_saved': True, 'heldout_protocol': 'Fixed model; predict each exercise from prior completed exercises; after submission reveal its labels for subsequent history. DEV starts from TRAIN history; TEST starts from TRAIN+DEV history. This is sequential-feedback evaluation, not a reproduction of the original blind shared-task leaderboard.', 'model_parameters_fixed_before_dev_test': PARAMETERS, 'class_weight': None, 'classification_threshold_fixed': 0.5, 'baseline_probability_fit_on_train_only': baseline_probability, 'convergence_warnings': convergence_warnings, 'other_fit_warnings': [str(w.message) for w in caught], 'iterations': model.named_steps['classifier'].n_iter_.tolist(), 'fit_seconds': fit_seconds, 'encoded_features': len(feature_names), 'model_file_sha256': frozen_hash, 'versions': versions, 'kmeans_trained': False}
    save_json('training_audit.json', audit)
    result = {'baseline_description': 'The observed TRAIN correctness rate assigned to every future token', 'positive_label': 'correct=1', 'evaluation_scope': 'Later records of the same 200 learners, two retained formats only', 'model_selection': 'One fixed C=1 L2 logistic model, no tuning, no class reweighting, TEST evaluated once', 'metrics': metrics}
    save_json('metrics.json', result)
    test_frame, test_y, test_meta, test_p, test_baseline = split_data['test']
    with (OUTPUT / 'test_predictions.jsonl').open('w', encoding='utf-8') as handle:
        for trace, y, p in zip(test_meta, test_y, test_p):
            handle.write(json.dumps({**trace, 'actual_correct': int(y), 'p_correct': float(p)}, ensure_ascii=False) + '\n')
    plot_results(test_y, test_p, test_baseline, metrics['test'])
    save_json('run_complete.json', {'completed': True, 'elapsed_seconds': time.perf_counter()-started, 'trained_model': 'logistic_regression_only'})


if __name__ == '__main__':
    main()
