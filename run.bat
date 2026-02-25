@echo off
REM Career Assistant AI - Sunucuyu baslat (py kullanir, python PATH'te olmasa da calisir)
cd /d "%~dp0"
if not exist "venv" (
    echo Sanal ortam yok. Olusturuluyor: py -3 -m venv venv
    py -3 -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -q 2>nul
echo Sunucu baslatiliyor: http://localhost:8000
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
