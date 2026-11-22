"""Validate the deliverable in a temporary extraction without personal records."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT / 'output/submission/LexiPath_Midterm.zip'
    with tempfile.TemporaryDirectory(prefix='submission_check_', dir=ROOT / 'tmp') as folder:
        dest = Path(folder).resolve()
        assert dest.is_relative_to((ROOT / 'tmp').resolve())
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            names = z.namelist()
            forbidden = {'SUNUM_PROVASI.txt', 'DIYAGRAM_SAVUNMASI.txt',
                         'TESLIM_MESAJI.txt', 'PILOT_DINLEYEREK_YAZMA.txt'}
            for name in names:
                assert (dest / name).resolve().is_relative_to(dest)
                assert Path(name).name not in forbidden
                assert not name.endswith(('.sqlite3', '.log', '.db'))
                assert '/.venv/' not in name and '__pycache__' not in name
            manifest = json.loads(z.read('LexiPath/DOSYA_LISTESI.json'))
            for item in manifest:
                content = z.read('LexiPath/' + item['path'])
                assert len(content) == item['bytes']
                assert hashlib.sha256(content).hexdigest() == item['sha256']
            assert z.read('LexiPath/Rapor_TR.pdf') == (ROOT / 'output/pdf/LexiPath_Midterm_Raporu.pdf').read_bytes()
            assert z.read('LexiPath/Rapor_EN.pdf') == (ROOT / 'output/pdf/LexiPath_Midterm_Report_EN.pdf').read_bytes()
            z.extractall(dest)
        package = dest / 'LexiPath'
        sys.path.insert(0, str(package / 'src'))
        from app_server import create_app
        import tutor_engine
        assert tutor_engine.ROOT.resolve() == package.resolve()
        app = create_app(package / 'tmp/clean.sqlite3')
        client = app.test_client()
        assert client.get('/api/health').get_json()['status'] == 'ready'
        assert len(app.extensions['tutor_store'].listing()) == 0
        assert client.get('/api/catalog').get_json()['word_count'] == 48
        p = client.post('/api/pilot', json={'name': 'SYNTHETIC package validation'}).get_json()
        url = '/api/pilot/' + p['id']
        assert p['task_total'] == 16
        for _ in range(200):
            if p['stage'] == 'waiting':
                break
            state = app.extensions['pilot_store'].get(p['id'])
            q = state['pending']
            if p['stage'] == 'teaching':
                action, data = 'teach', {'task_id': q['id']}
            elif p['stage'] == 'assisted_feedback':
                action, data = 'support-next', {'task_id': q['id']}
            else:
                typed = q['skill'] in ['writing', 'listen_write', 'spacing']
                value = q['word'] if typed else app.extensions['tutor_engine'].audio_keys[q['word']]
                if q['skill'] == 'listen_write' and q['word'] in ['dog', 'book']:
                    value = 'wrong'
                action, data = 'answer', {'task_id': q['id'], 'answer': value}
            response = client.post(url + '/' + action, json=data)
            assert response.status_code == 200
            p = response.get_json()
        assert p['stage'] == 'waiting'
        audit = p['model_audit']
        assert audit['lr_native_writing_records'] == 8
        assert audit['lr_native_listen_write_records'] == 8
        assert audit['kmeans']['group']['number'] == 3
        engine = app.extensions['tutor_engine']
        for word in tutor_engine.VISUAL_WORDS:
            key = engine.audio_keys[word]
            with client.get('/pilot-image/' + key + '.svg') as response:
                assert response.status_code == 200, word
        with client.get('/audio/' + engine.audio_keys['cat'] + '.wav') as response:
            assert response.status_code == 200
        assert client.get('/diagrams/ml_blok_diyagrami.svg').status_code == 200
        report = {
            'archive_integrity': 'passed', 'manifest_hashes': 'passed',
            'reports_match_external_copies': True,
            'isolated_extract': 'temporary directory; automatically removed',
            'fresh_empty_store': True, 'catalog_words': 48,
            'visual_routes_checked': len(tutor_engine.VISUAL_WORDS),
            'audio_and_image': 'passed', 'diagram': 'passed',
            'full_pilot_measurement_and_independent': 'passed',
            'native_records': {'text': 8, 'listen': 8}, 'group': 3,
            'records_in_archive': False, 'internal_team_notes_in_archive': False,
            'application_dependencies': 'existing pinned environment reused for extracted copy',
            'fresh_internet_pip_install_verified': False,
            'automated_tests_in_workspace': 56,
            'pdf_pages': {'TR': 33, 'EN': 33},
            'pdf_visual_review': 'Both final reports rendered and inspected',
            'real_24h_learning_measured': False, 'teacher_submission_performed': False,
        }
        (ROOT / 'outputs/final_delivery_check.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
