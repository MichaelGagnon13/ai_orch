#!/usr/bin/env bash
# scripts/stop_all.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[INFO] Arrêt d'AgentScope Studio (port 3000)..."
"$SCRIPT_DIR/stop_studio.sh" || true
echo "[INFO] Arrêt de l'API (port 5000)..."
"$SCRIPT_DIR/stop_api.sh" || true
echo "[OK] Tous les services demandés ont été arrêtés."
