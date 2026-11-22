"""Prepare a reproducible learner-preserving subset; do not train models."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import random
import sys
import tarfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data/raw/slam/data_en_es.tar.gz'
OUT = ROOT / 'data/prepared/slam200'
OUT.mkdir(parents=True, exist_ok=True)
SEED = 42
FORMATS = {'reverse_translate', 'listen'}

def blocks(stream):
    block = []
    for line in stream:
        if line.strip():
            block.append(line)
        elif block:
            yield block
            block = []
    if block:
        yield block

def parse_exercise(block, order, wanted_users, split):
    header = next((line for line in block if line.startswith(b'# user:')), None)
    if header is None:
        raise ValueError('Missing exercise metadata')
    meta = dict(item.split(':', 1) for item in header.decode('utf-8').strip()[2:].split())
    if meta['user'] not in wanted_users or meta['format'] not in FORMATS:
        return None
    prompt = next((line.decode('utf-8').strip()[len('# prompt:'):] for line in block if line.startswith(b'# prompt:')), None)
    tokens = []
    for raw in block:
        if raw.startswith(b'#'):
            continue
        fields = raw.decode('utf-8').split()
        if len(fields) != (7 if split == 'train' else 6):
            raise ValueError(f'Unexpected token schema: {fields}')
        token = {'instance_id': fields[0], 'word': fields[1], 'word_key': fields[1].lower(), 'pos': fields[2]}
        if split == 'train':
            token['source_error'] = int(fields[-1])
            token['correct'] = 1 - token['source_error']
        tokens.append(token)
    assert tokens
    exercise_id = tokens[0]['instance_id'][:10]
    assert all(t['instance_id'][:10] == exercise_id for t in tokens)
    duration = None if meta['time'] == 'null' else float(meta['time'])
    if duration is not None and duration < 0:
        duration = None
    return {'split': split, 'source_order': order, 'learner_id': meta['user'], 'exercise_id': exercise_id, 'days': float(meta['days']), 'source_format': meta['format'], 'prompt_original': prompt, 'elapsed_seconds_LOG_ONLY': duration, 'tokens': tokens}

digest = hashlib.md5()
with ARCHIVE.open('rb') as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        digest.update(chunk)
assert digest.hexdigest() == '444e0d9e45bdc19822938cffb9fbcc7a'

all_exercises = {}
with tarfile.open(ARCHIVE, 'r:gz') as archive:
    members = {Path(member.name).name: member for member in archive.getmembers() if member.isfile() and not Path(member.name).name.startswith('._')}
    names = {split: next(name for name in members if name.endswith('.' + split)) for split in ('train', 'dev', 'test')}
    print(json.dumps({'official_members': [{'name': n, 'bytes': m.size} for n, m in members.items()]}), flush=True)
    learners = set()
    with archive.extractfile(members[names['train']]) as stream:
        for raw in stream:
            if raw.startswith(b'# user:'):
                learners.add(raw.split()[1].split(b':', 1)[1].decode('utf-8'))
    selected_users = sorted(random.Random(SEED).sample(sorted(learners), 200))
    selected_set = set(selected_users)
    (OUT / 'selected_learners.json').write_text(json.dumps({'seed': SEED, 'sampling_frame': 'All learner IDs present in official TRAIN, no performance-based filtering', 'total_train_learners': len(learners), 'selected': selected_users}, indent=2), encoding='utf-8')
    print(json.dumps({'train_learners': len(learners), 'selected_learners': len(selected_users)}), flush=True)
    for split in ('train', 'dev', 'test'):
        selected_exercises = []
        with archive.extractfile(members[names[split]]) as stream:
            for order, block in enumerate(blocks(stream)):
                exercise = parse_exercise(block, order, selected_set, split)
                if exercise:
                    selected_exercises.append(exercise)
        if split != 'train':
            wanted_ids = {t['instance_id'] for ex in selected_exercises for t in ex['tokens']}
            labels = {}
            with archive.extractfile(members[names[split] + '.key']) as stream:
                for raw in stream:
                    fields = raw.split()
                    if len(fields) == 2:
                        instance_id = fields[0].decode('utf-8')
                        if instance_id in wanted_ids:
                            assert instance_id not in labels
                            labels[instance_id] = int(fields[1])
            assert set(labels) == wanted_ids, f'Missing {split} labels'
            for ex in selected_exercises:
                for token in ex['tokens']:
                    token['source_error'] = labels[token['instance_id']]
                    token['correct'] = 1 - token['source_error']
        selected_exercises.sort(key=lambda ex: (ex['learner_id'], ex['days'], ex['source_order']))
        assert all(t['source_error'] in (0, 1) for ex in selected_exercises for t in ex['tokens'])
        with (OUT / f'{split}_exercises.jsonl').open('w', encoding='utf-8') as handle:
            for ex in selected_exercises:
                handle.write(json.dumps(ex, ensure_ascii=False, separators=(',', ':')) + '\n')
        all_exercises[split] = selected_exercises
        print(json.dumps({'split': split, 'exercises': len(selected_exercises), 'targets': sum(len(ex['tokens']) for ex in selected_exercises)}, ensure_ascii=False), flush=True)

summary = {}
exercise_ids = {}
for split, exercises in all_exercises.items():
    tokens = [t for ex in exercises for t in ex['tokens']]
    exercise_ids[split] = {ex['exercise_id'] for ex in exercises}
    assert len(exercise_ids[split]) == len(exercises)
    summary[split] = {'learners': len({ex['learner_id'] for ex in exercises}), 'exercises': len(exercises), 'targets': len(tokens), 'errors': sum(t['source_error'] for t in tokens), 'accuracy': sum(t['correct'] for t in tokens)/len(tokens), 'formats': dict(Counter(ex['source_format'] for ex in exercises))}
assert exercise_ids['train'].isdisjoint(exercise_ids['dev'])
assert exercise_ids['train'].isdisjoint(exercise_ids['test'])
assert exercise_ids['dev'].isdisjoint(exercise_ids['test'])
chronology_violations = []
for learner in selected_users:
    for earlier, later in [('train', 'dev'), ('dev', 'test')]:
        left = [ex['days'] for ex in all_exercises[earlier] if ex['learner_id'] == learner]
        right = [ex['days'] for ex in all_exercises[later] if ex['learner_id'] == learner]
        if left and right and max(left) > min(right):
            chronology_violations.append({'learner_id': learner, 'earlier': earlier, 'later': later})
assert not chronology_violations
report = {'source_doi': 'https://doi.org/10.7910/DVN/8SWHNO', 'archive_md5_verified': True, 'seed': SEED, 'selected_learners': 200, 'formats_kept': sorted(FORMATS), 'official_partitions_preserved': True, 'chronology_violations': chronology_violations, 'exercise_overlap_between_partitions': False, 'duration_is_log_only_not_a_model_feature': True, 'model_trained': False, 'summary': summary}
(OUT / 'preparation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
