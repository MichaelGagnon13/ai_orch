#!/usr/bin/env bash
set -euo pipefail
PORT=${PORT:-3000}
PIDF="scripts/pids/studio.pid"

echo "[INFO] Démarrage AgentScope Studio sur :$PORT"
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[ERR] Port $PORT déjà utilisé"; exit 1
fi

if command -v as_studio >/dev/null 2>&1; then
  nohup as_studio --host 0.0.0.0 --port "$PORT" > logs/studio.out 2>&1 &
  echo $! > "$PIDF"
  echo "[OK] Studio PID=$(cat "$PIDF") • http://127.0.0.1:$PORT"
else
  echo "[ERR] binaire 'as_studio' introuvable. Installez AgentScope."; exit 1
fi
