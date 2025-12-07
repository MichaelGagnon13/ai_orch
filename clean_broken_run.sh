#!/bin/bash
# Nettoie le run problématique du Studio

RUN_ID="5C4BAErUd7yWUeivkXQ4dZ"
STUDIO_URL="http://127.0.0.1:3000"

echo "🧹 Nettoyage du run problématique: $RUN_ID"

# Tenter de supprimer via l'API (si elle existe)
curl -X DELETE "$STUDIO_URL/api/runs/$RUN_ID" 2>&1 | head -10

# Redémarrer le Studio pour forcer un reload
echo ""
echo "🔄 Redémarrage du Studio..."
pkill -f "as_studio"
sleep 2

# Relancer avec SAFE_MODE activé par défaut
export AS_STUDIO_SAFE_MODE=1
as_studio --port 3000 &
STUDIO_PID=$!

echo "✅ Studio redémarré (PID: $STUDIO_PID) avec SAFE_MODE=1"
echo "🌐 Ouvrez: $STUDIO_URL/dashboard/projects/ai_orch"
echo ""
echo "Pour tuer le Studio: kill $STUDIO_PID"
