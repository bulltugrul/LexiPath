"""Prototipi tek çift tıklamayla, görünür komut penceresi açmadan başlatır."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8765'


def ready():
    try:
        with urlopen(URL + '/api/health', timeout=0.6) as response:
            data = json.load(response)
        return data.get('status') == 'ready' and data.get('raw_features') == 12
    except Exception:
        return False


def main():
    if not ready():
        log_path = ROOT / 'data/prototype/prototype_server.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open('a', encoding='utf-8') as log:
            subprocess.Popen([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'src/app_server.py'), '--port', '8765'],
                             cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for _ in range(30):
            if ready():
                break
            time.sleep(0.25)
        else:
            if os.name == 'nt':
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, 'Uygulama başlatılamadı. data/prototype/prototype_server.log dosyasını kontrol edin.', 'LexiPath', 0)
            return
    if '--no-browser' not in sys.argv:
        webbrowser.open(URL)


if __name__ == '__main__':
    main()
