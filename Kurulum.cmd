@echo off
cd /d "%~dp0"
py -3.13 -m venv .venv
if errorlevel 1 python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto fail
echo Kurulum tamamlandi. Baslat.cmd ile acabilirsiniz.
pause
exit /b 0
:fail
echo Kurulum tamamlanamadi. Python 3.13 ve internet baglantisini kontrol edin.
pause
exit /b 1
