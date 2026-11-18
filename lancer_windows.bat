@echo off
chcp 65001 >nul
title Atelier Documentaire RAG - Assistant Projets Etudiants (Qwen2.5-7B)

echo ============================================================================
echo   Atelier Documentaire RAG - Assistant Technique Projets Etudiants
echo   Extraction Datasheets/Datasets, Vectorisation Semantique ^& Qwen2.5-7B
echo ============================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH Windows.
    echo Telechargez Python 3.10+ depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Creation de l'environnement virtuel Python (.venv)...
    python -m venv .venv
)

echo [2/3] Verification et installation des dependances...
call .venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo [3/3] Demarrage du serveur FastAPI sur http://localhost:8000 ...
echo Ouverture automatique de votre navigateur dans 3 secondes...
start "" cmd /c "timeout /t 3 >nul && start http://localhost:8000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
