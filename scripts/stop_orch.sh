#!/usr/bin/env bash
set -euo pipefail
PIDF="scripts/pids/orch.pid"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "[INFO] Arrêt Orchestrateur PID=$(cat "$PIDF")"; kill "$(cat "$PIDF")" || true; rm -f "$PIDF"; echo "[OK] Orchestrateur arrêté"
else
  echo "[ERR] PID Orchestrateur introuvable ou déjà stoppé"; exit 1
fi
