#!/usr/bin/env bash
set -euo pipefail
PORT=${PORT:-5000}
PIDF="scripts/pids/api.pid"

echo "[INFO] Démarrage API Flask sur :$PORT"
[ -d .venv ] || { echo "[ERR] .venv manquant"; exit 1; }
source .venv/bin/activate
[ -f .env ] && set -a && source .env && set +a

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[ERR] Port $PORT déjà utilisé"; exit 1
fi

if command -v gunicorn >/dev/null 2>&1; then
  nohup gunicorn -w 2 -b 127.0.0.1:$PORT app:app > logs/api.out 2>&1 &
else
  echo "[INFO] gunicorn absent, fallback Flask dev server"
  nohup python -c "from app import app; app.run(host='127.0.0.1', port=$PORT)" > logs/api.out 2>&1 &
fi
echo $! > "$PIDF"
echo "[OK] API PID=$(cat "$PIDF") • http://127.0.0.1:$PORT"
