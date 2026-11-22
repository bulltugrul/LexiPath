"""TRAIN öğrenci profillerinde k=2,3,4 karşılaştırması; TEST'e bakılmaz."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import os
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from profiles import PROFILE_FEATURES

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/prepared/slam200'
OUTPUT = ROOT / 'outputs/kmeans_first_run'
CANDIDATES = (2, 3, 4)
MIN_CLUSTER_SIZE = 5
PARAMETERS = dict(init='k-means++', n_init=10, random_state=42, max_iter=300, tol=1e-4)


def save_json(name, value):
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe_groups(model, scaler, labels):
    centers = scaler.inverse_transform(model.cluster_centers_)
    # Grup numarası yalnız sunum içindir; düşük ortalamadan yükseğe sıralanır.
    order = sorted(range(model.n_clusters), key=lambda c: (float(centers[c].mean()), float(centers[c, 0]), c))
    display_map = {raw: number for number, raw in enumerate(order, 1)}
    groups = [{'display_group': display_map[raw], 'model_label': raw,
               'students': int((labels == raw).sum()),
               'center_original_scale': dict(zip(PROFILE_FEATURES, map(float, centers[raw])))}
              for raw in order]
    return groups, display_map


def plot_comparison(frame, outcomes, labels_by_k):
    cache = ROOT / 'tmp/matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    colors = ['#216d8a', '#c77c29', '#63834c', '#88629b']
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.4), constrained_layout=True)
    for ax, result in zip(axes, outcomes):
        k = result['k']
        if k not in labels_by_k:
            ax.set_title(f'k={k}: geçersiz aday')
            continue
        raw_labels = labels_by_k[k]
        data = frame.copy()
        data['model_label'] = raw_labels
        for group in result['groups']:
            raw = group['model_label']
            selected = data[data['model_label'] == raw]
            bubbles = selected.groupby(PROFILE_FEATURES).size().reset_index(name='students')
            color = colors[group['display_group']-1]
            ax.scatter(bubbles[PROFILE_FEATURES[0]], bubbles[PROFILE_FEATURES[1]],
                       s=35*bubbles['students'], color=color, alpha=0.7, edgecolors='white', linewidths=0.6,
                       label=f"Grup {group['display_group']} · {group['students']} öğrenci")
            center = group['center_original_scale']
            ax.scatter(center[PROFILE_FEATURES[0]], center[PROFILE_FEATURES[1]], marker='X', s=155,
                       color=color, edgecolors='black', linewidths=0.9, zorder=5)
        title = f"k={k} · silhouette {result['silhouette']:.3f}"
        if result.get('selected'):
            title += ' · seçildi'
        if not result['valid']:
            title += '\nGeçerlilik koşulu karşılanmadı'
        ax.set(title=title, xlabel='Son 6 metin hedefinde doğruluk', ylabel='Son 6 dinleme hedefinde doğruluk',
               xlim=(-0.07, 1.07), ylim=(-0.07, 1.07))
        ax.xaxis.set_major_formatter(PercentFormatter(1.0))
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.grid(alpha=0.2)
        ax.set_axisbelow(True)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), fontsize=8)
    fig.suptitle('200 TRAIN öğrencisi · balon alanı öğrenci sayısını, X grup merkezini gösterir', fontsize=12)
    fig.savefig(OUTPUT / 'kume_karsilastirmasi.png', dpi=160)
    plt.close(fig)


def plot_selected(result):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    groups = result['groups']
    x = np.arange(len(groups))
    text = [g['center_original_scale'][PROFILE_FEATURES[0]] for g in groups]
    listen = [g['center_original_scale'][PROFILE_FEATURES[1]] for g in groups]
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    bars1 = ax.bar(x-0.18, text, width=0.36, color='#216d8a', label='Metin')
    bars2 = ax.bar(x+0.18, listen, width=0.36, color='#c77c29', label='Dinleme')
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.015,
                    f'{100*bar.get_height():.1f}%', ha='center', fontsize=10)
    ax.set(xticks=x, xticklabels=[f"Grup {g['display_group']}\n{g['students']} öğrenci" for g in groups],
           ylim=(0, 1.12), ylabel='Grup merkezinin gözlenen doğruluğu',
           title=f"Seçilen k={result['k']}: son altı hedefin ortalama sonuçları")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)
    fig.savefig(OUTPUT / 'secili_kume_profilleri.png', dpi=160)
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / 'comparison.json').exists():
        raise RuntimeError('First run already exists; inspect its results before replacing it.')
    logistic_model = ROOT / 'outputs/logistic_first_run/logistic_model.joblib'
    logistic_test_metrics = ROOT / 'outputs/logistic_first_run/metrics.json'
    logistic_before = {str(p.relative_to(ROOT)): digest(p) for p in (logistic_model, logistic_test_metrics)}
    preparation = json.loads((DATA / 'profile_preparation_report.json').read_text(encoding='utf-8'))
    assert preparation['source_split'] == 'TRAIN only'
    snapshots = json.loads((DATA / 'train_profiles.json').read_text(encoding='utf-8'))
    eligible = [p for p in snapshots if p['status'] == 'provisional']
    assert len(eligible) == preparation['eligible_learners']
    assert all(p['observations_in_window'] == {'reverse_translate': 6, 'listen': 6} for p in eligible)
    frame = pd.DataFrame([p['features'] for p in eligible], columns=PROFILE_FEATURES)
    assert frame.notna().all().all()
    assert ((frame >= 0) & (frame <= 1)).all().all()
    assert np.allclose(frame.to_numpy()*6, np.rint(frame.to_numpy()*6))
    unique_count = len(np.unique(frame.to_numpy(), axis=0))
    scaler = StandardScaler().fit(frame)
    scaled = scaler.transform(frame)
    assert np.allclose(scaler.mean_, frame.mean().to_numpy())
    results, models, labels_by_k = [], {}, {}
    for k in CANDIDATES:
        if len(frame) <= k or unique_count <= k:
            results.append({'k': k, 'valid': False, 'reasons': ['Insufficient learners or distinct profiles'], 'silhouette': None, 'selected': False})
            continue
        model = KMeans(n_clusters=k, **PARAMETERS)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            labels = model.fit_predict(scaled)
        actual_clusters = len(set(labels))
        sizes = Counter(map(int, labels))
        reasons = []
        if actual_clusters != k:
            reasons.append('Fewer actual clusters than requested')
        if min(sizes.values()) < MIN_CLUSTER_SIZE:
            reasons.append('At least one cluster has fewer than five learners')
        score = float(silhouette_score(scaled, labels)) if 2 <= actual_clusters <= len(frame)-1 else None
        if score is None:
            reasons.append('Silhouette is undefined')
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            reasons.append('Convergence warning')
        groups, mapping = describe_groups(model, scaler, labels)
        result = {'k': k, 'valid': not reasons, 'reasons': reasons, 'selected': False,
                  'silhouette': score, 'inertia_scaled': float(model.inertia_),
                  'actual_clusters': actual_clusters, 'smallest_cluster': min(sizes.values()),
                  'iterations': int(model.n_iter_), 'groups': groups,
                  'fit_warnings': [str(w.message) for w in caught]}
        results.append(result)
        models[k] = model
        labels_by_k[k] = labels
        print(json.dumps(result, ensure_ascii=False), flush=True)
    valid = [r for r in results if r['valid']]
    selected = min(valid, key=lambda r: (-r['silhouette'], r['k'])) if valid else None
    if selected:
        selected['selected'] = True
        chosen_k = selected['k']
        chosen = models[chosen_k]
        pipeline = Pipeline([('scaler', scaler), ('kmeans', chosen)])
        predicted = pipeline.predict(frame)
        assert np.array_equal(predicted, labels_by_k[chosen_k])
        joblib.dump(pipeline, OUTPUT / 'kmeans_model.joblib')
        restored = joblib.load(OUTPUT / 'kmeans_model.joblib')
        assert np.array_equal(restored.predict(frame), predicted)
        _, mapping = describe_groups(chosen, scaler, predicted)
        assignments = [{
            'display_id': p['display_id'], 'learner_id': p['learner_id'], 'status': 'provisional',
            'features': p['features'], 'model_label': int(label), 'display_group': mapping[int(label)],
            'observations_per_format': 6,
        } for p, label in zip(eligible, predicted)]
        save_json('student_assignments.json', assignments)
        # Birbirinin aynı noktalarının tek bir gruba atandığını doğrula.
        label_by_point = defaultdict(set)
        for vector, label in zip(frame.to_numpy(), predicted):
            label_by_point[tuple(vector)].add(int(label))
        assert all(len(labels) == 1 for labels in label_by_point.values())
    assert {str(p.relative_to(ROOT)): digest(p) for p in (logistic_model, logistic_test_metrics)} == logistic_before
    comparison = {'source': 'Only TRAIN learner snapshots; no DEV or TEST files used',
                  'learners': len(frame), 'distinct_profiles': unique_count, 'features': PROFILE_FEATURES,
                  'parameters': PARAMETERS, 'minimum_cluster_size': MIN_CLUSTER_SIZE,
                  'selection_rule': 'Highest mean silhouette among valid k=2,3,4; smaller k on exact tie',
                  'selected_k': selected['k'] if selected else None, 'candidates': results}
    save_json('comparison.json', comparison)
    save_json('training_audit.json', {
        'passed': True, 'sklearn_version': sklearn.__version__, 'input_files': ['train_profiles.json', 'profile_preparation_report.json'],
        'profile_file_sha256': digest(DATA / 'train_profiles.json'),
        'profile_source': 'TRAIN only, as checked in profile_preparation_report.json',
        'duration_ids_preferences_not_model_features': True, 'provided_cluster_labels': False,
        'duplicate_rows_retained': True, 'scaler_fit_only_on_train_profiles': True,
        'scaler_mean': scaler.mean_.tolist(), 'scaler_scale': scaler.scale_.tolist(),
        'silhouette_coordinates': 'Same StandardScaler space as KMeans fit',
        'centers_reported_in_original_rate_scale': True, 'profiles_are_provisional': True,
        'logistic_model_and_results_unchanged': True, 'logistic_digests': logistic_before,
        'kmeans_model_reload_verified': bool(selected), 'test_evaluated_again': False,
    })
    plot_comparison(frame, results, labels_by_k)
    if selected:
        plot_selected(selected)
    print(json.dumps({'selected_k': comparison['selected_k'], 'completed': True}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
