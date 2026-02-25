@echo off
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (call venv\Scripts\activate.bat) else (echo Once run.bat ile venv olusturun.)
py -m pytest tests/test_cases.py -v 2>nul || py tests/run_test_cases.py
