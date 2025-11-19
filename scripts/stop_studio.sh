#!/usr/bin/env bash
set -euo pipefail
PIDF="scripts/pids/studio.pid"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "[INFO] Arrêt Studio PID=$(cat "$PIDF")"; kill "$(cat "$PIDF")" || true; rm -f "$PIDF"; echo "[OK] Studio arrêté"
else
  echo "[ERR] PID Studio introuvable ou déjà stoppé"; exit 1
fi
