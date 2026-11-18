#!/usr/bin/env bash
set -e

echo "============================================================================"
echo "  Atelier Documentaire RAG — Assistant Technique Projets Étudiants"
echo "  Extraction Datasheets/Datasets, Vectorisation Sémantique & Qwen2.5-7B"
echo "============================================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] python3 n'est pas installé sur votre machine."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/3] Création de l'environnement virtuel Python (.venv)..."
    python3 -m venv .venv
fi

echo "[2/3] Installation des dépendances..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "[3/3] Démarrage de l'application sur http://localhost:8000 ..."
if command -v xdg-open &> /dev/null; then
    (sleep 2 && xdg-open "http://localhost:8000") &
elif command -v open &> /dev/null; then
    (sleep 2 && open "http://localhost:8000") &
fi

.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
