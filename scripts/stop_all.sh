#!/usr/bin/env bash
set -euo pipefail
scripts/stop_orch.sh 2>/dev/null || true
scripts/stop_api.sh 2>/dev/null || true
scripts/stop_studio.sh 2>/dev/null || true
echo "[OK] Tous les services stoppés"
