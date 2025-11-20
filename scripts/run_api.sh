#!/usr/bin/env bash
# scripts/run_api.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PORT=5000
echo "[INFO] Répertoire projet : $(pwd)"
if [ ! -d ".venv" ]; then
  echo "[ERR] Environnement virtuel .venv introuvable dans $(pwd)"
  exit 1
fi
echo "[INFO] Vérification du port $PORT..."
if lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n >/dev/null 2>&1; then
  echo "[ERR] Le port $PORT est déjà utilisé par :"
  lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n
  exit 1
fi
echo "[INFO] Activation de .venv..."
source ".venv/bin/activate"
echo "[INFO] Démarrage de l'API sur 127.0.0.1:$PORT..."
exec gunicorn -w 2 -b 127.0.0.1:"$PORT" app:app
