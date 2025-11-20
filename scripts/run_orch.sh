#!/usr/bin/env bash
# scripts/run_orch.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
echo "[INFO] Répertoire projet : $(pwd)"
if [ ! -d ".venv" ]; then
  echo "[ERR] Environnement virtuel .venv introuvable dans $(pwd)"
  exit 1
fi
if [ ! -f ".env" ]; then
  echo "[ERR] Fichier .env introuvable dans $(pwd)"
  exit 1
fi
echo "[INFO] Activation de .venv..."
source ".venv/bin/activate"
echo "[INFO] Chargement des variables depuis .env..."
export $(grep -v '^#' .env | xargs)
echo "[INFO] Lancement de l'orchestrateur (python -m src.orchestrate)..."
exec python -m src.orchestrate
