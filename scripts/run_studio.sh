#!/usr/bin/env bash
# scripts/run_studio.sh
set -euo pipefail
PORT=3000
echo "[INFO] Vérification du port $PORT..."
if lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n >/dev/null 2>&1; then
  echo "[ERR] Le port $PORT est déjà utilisé par :"
  lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n
  exit 1
fi
echo "[INFO] Démarrage d'AgentScope Studio sur le port $PORT..."
exec as_studio --port "$PORT"
