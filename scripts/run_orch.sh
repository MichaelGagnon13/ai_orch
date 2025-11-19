#!/usr/bin/env bash
set -euo pipefail
PIDF="scripts/pids/orch.pid"

echo "[INFO] Démarrage orchestrateur"
[ -d .venv ] || { echo "[ERR] .venv manquant"; exit 1; }
source .venv/bin/activate
[ -f .env ] && set -a && source .env && set +a

export AS_STUDIO_URL=${AS_STUDIO_URL:-http://127.0.0.1:3000}
export AS_STUDIO_SAFE_MODE=${AS_STUDIO_SAFE_MODE:-1}

nohup python -m src.orchestrate > logs/orch.out 2>&1 &
echo $! > "$PIDF"
echo "[OK] Orchestrateur PID=$(cat "$PIDF") • Studio=$AS_STUDIO_URL SAFE_MODE=$AS_STUDIO_SAFE_MODE"
