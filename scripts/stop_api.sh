#!/usr/bin/env bash
# scripts/stop_api.sh
set -euo pipefail
PORT=5000
echo "[INFO] Recherche de processus sur le port $PORT..."
PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN -P -n 2>/dev/null || true)"
if [ -z "${PIDS:-}" ]; then
  echo "[INFO] Aucun processus à arrêter sur le port $PORT."
  exit 0
fi
echo "[INFO] PID(s) trouvés sur le port $PORT : $PIDS"
for pid in $PIDS; do
  if kill "$pid" 2>/dev/null; then
    echo "[OK] SIGTERM envoyé au PID $pid (port $PORT)."
  else
    echo "[ERR] Impossible de tuer le PID $pid (port $PORT)."
  fi
done
