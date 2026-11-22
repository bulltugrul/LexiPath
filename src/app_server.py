"""Yerel prototip: .venv/Scripts/python.exe src/app_server.py"""
from pathlib import Path
import argparse
import json
import os

from flask import Flask, jsonify, request, send_from_directory

from tutor_engine import ROOT, TutorEngine, TutorError, MODEL_VERSION, ACTIVE_FEATURES, VISUAL_WORDS
from tutor_store import LocalStore
from pilot import Pilot


def create_app(db_path=None):
    app = Flask(__name__, static_folder=str(ROOT / 'web/static'), static_url_path='/static')
    app.json.ensure_ascii = False
    app.config['MAX_CONTENT_LENGTH'] = 100_000
    engine = TutorEngine()
    store = LocalStore(db_path or os.environ.get('TUTOR_DB', ROOT / 'data/prototype/PROTOTYPE_students.sqlite3'), upgrade=engine.upgrade_state)
    app.extensions['tutor_engine'] = engine
    app.extensions['tutor_store'] = store
    pilot = Pilot(engine)
    pilot_store = LocalStore(store.path.with_name(store.path.stem + '_pilot.sqlite3'),upgrade=pilot.upgrade)
    app.extensions['pilot'] = pilot
    app.extensions['pilot_store'] = pilot_store

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise TutorError('Geçerli bir istek gönderilemedi.')
        return value

    @app.get('/')
    def index():
        return send_from_directory(ROOT / 'web', 'index.html')

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ready', 'local_only': True, 'models': ['logistic_regression', 'kmeans'],
                        'words': len(engine.words), 'logistic_version': MODEL_VERSION, 'raw_features': len(ACTIVE_FEATURES),
                        'pilot':True,'pilot_common_control_version':1})

    @app.get('/pilot')
    def pilot_page():
        return send_from_directory(ROOT/'web','pilot.html')

    @app.get('/pilot-image/<key>.svg')
    def pilot_image(key):
        word=engine.audio_words.get(key)
        if word not in VISUAL_WORDS:
            return jsonify({'error':'Görsel bulunamadı.'}),404
        return send_from_directory(ROOT/'web/static/visual',word+'.svg')

    @app.post('/api/pilot')
    def pilot_create():
        state=pilot.new(body().get('name','Pilot öğrenci'))
        pilot_store.create(state)
        return jsonify(pilot.payload(state)),201

    @app.get('/api/pilot/<pilot_id>')
    def pilot_get(pilot_id):
        return jsonify(pilot.payload(pilot_store.get(pilot_id)))

    @app.post('/api/pilot/<pilot_id>/<action>')
    def pilot_action(pilot_id,action):
        data=body()
        actions={'answer':lambda s:pilot.answer(s,data.get('task_id'),data.get('answer')),
                 'teach':lambda s:pilot.teach(s,data.get('task_id')),
                 'delayed':pilot.delayed,'retry':pilot.retry,'extra-check':pilot.extra_check,
                 'support-next':lambda s:pilot.continue_support(s,data.get('task_id'))}
        if action not in actions:
            raise TutorError('Geçersiz pilot işlemi.')
        return jsonify(pilot.payload(pilot_store.change(pilot_id,actions[action])))

    @app.get('/api/pilot/<pilot_id>/export')
    def pilot_export(pilot_id):
        # Kontrol bloğu tamamlanmadan dışa aktarım üzerinden cevaplara erişilmez.
        state=pilot_store.get(pilot_id)
        if state['stage'] not in ['waiting','complete','support_required']:
            raise TutorError('Kayıt çıktısı kontrol bloğu tamamlandıktan sonra açılır.')
        response=app.response_class(json.dumps(state,ensure_ascii=False,indent=2),mimetype='application/json')
        response.headers['Content-Disposition']='attachment; filename=pilot_kayitlari.json'
        return response

    @app.get('/api/catalog')
    def catalog():
        return jsonify({'topics': engine.catalog['topics'], 'word_count': len(engine.words)})

    @app.get('/audio/<asset_key>.wav')
    def audio(asset_key):
        word_id = engine.audio_words.get(asset_key)
        if not word_id:
            return jsonify({'error': 'Ses kaydı bulunamadı.'}), 404
        return send_from_directory(ROOT / 'web/static/audio', word_id + '.wav')

    @app.get('/api/learners')
    def learners():
        return jsonify(store.listing())

    @app.post('/api/learners')
    def create_learner():
        data = body()
        if not isinstance(data.get('topics'), list) or not all(isinstance(t, str) for t in data['topics']):
            raise TutorError('İlgi alanlarını seçmelisin.')
        if not isinstance(data.get('name', ''), str):
            raise TutorError('Ad alanı metin olmalı.')
        state = engine.new_learner(data.get('name'), data['topics'])
        store.create(state)
        return jsonify(engine.payload(state)), 201

    @app.get('/api/learners/<learner_id>')
    def learner(learner_id):
        return jsonify(engine.payload(store.get(learner_id)))

    @app.post('/api/learners/<learner_id>/answer')
    def answer(learner_id):
        data = body()
        state = store.change(learner_id, lambda s: engine.answer(s, data.get('question_id'), data.get('answer')))
        return jsonify(engine.payload(state))

    @app.post('/api/learners/<learner_id>/next')
    def next_question(learner_id):
        return jsonify(engine.payload(store.change(learner_id, engine.next_step)))

    @app.post('/api/learners/<learner_id>/round')
    def new_round(learner_id):
        state = store.change(learner_id, lambda s: engine.start_session(s, diagnostic=False))
        return jsonify(engine.payload(state))

    @app.get('/api/learners/<learner_id>/export')
    def export(learner_id):
        state = store.get(learner_id)
        response = app.response_class(json.dumps({'prototype': True, 'learner': state}, ensure_ascii=False, indent=2), mimetype='application/json')
        response.headers['Content-Disposition'] = 'attachment; filename=ogrenci_kaydi.json'
        return response

    @app.post('/api/learners/<learner_id>/visual')
    def visual(learner_id):
        state = store.change(learner_id, engine.prepare_visual)
        return jsonify(engine.payload(state))

    @app.post('/api/learners/<learner_id>/visual-answer')
    def visual_answer(learner_id):
        data = body()
        state = store.change(learner_id, lambda s:engine.answer_visual(s,data.get('task_id'),data.get('choice')))
        return jsonify(engine.payload(state))

    @app.get('/api/system')
    def system():
        return jsonify({'decisions': json.loads((ROOT / 'project_decisions.json').read_text(encoding='utf-8')),
                        'diagram': '/diagrams/ml_blok_diyagrami.svg', 'flow': '/diagrams/ogrenci_akisi.svg',
                        'input_fields': ACTIVE_FEATURES, 'logistic_version': MODEL_VERSION})

    @app.get('/diagrams/<path:filename>')
    def diagrams(filename):
        allowed = {'ml_blok_diyagrami.svg', 'ml_blok_diyagrami.png', 'ogrenci_akisi.svg', 'ogrenci_akisi.png', 'DIYAGRAM_ACIKLAMASI.txt'}
        if filename not in allowed:
            return jsonify({'error': 'Dosya bulunamadı.'}), 404
        return send_from_directory(ROOT / 'outputs/diagrams', filename)

    @app.errorhandler(TutorError)
    def tutor_error(error):
        return jsonify({'error': str(error)}), 400

    @app.errorhandler(KeyError)
    def missing(error):
        return jsonify({'error': str(error).strip("'")}), 404

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    create_app().run(host='127.0.0.1', port=args.port, debug=False)
