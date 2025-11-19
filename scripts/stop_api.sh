#!/usr/bin/env bash
set -euo pipefail
PIDF="scripts/pids/api.pid"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "[INFO] Arrêt API PID=$(cat "$PIDF")"; kill "$(cat "$PIDF")" || true; rm -f "$PIDF"; echo "[OK] API arrêtée"
else
  echo "[ERR] PID API introuvable ou déjà stoppée"; exit 1
fi
