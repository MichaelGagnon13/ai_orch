#!/bin/bash
# setup_taskbot.sh - Installation rapide de TaskBot

set -e

echo "🤖 Installation de TaskBot pour ai_orch"
echo "========================================"
echo ""

# Vérifie Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

echo "✅ Python $(python3 --version) détecté"
echo ""

# Vérifie pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ pip n'est pas installé"
    exit 1
fi

echo "📦 Installation des dépendances..."
pip install anthropic openai typer --quiet

echo "✅ Dépendances installées"
echo ""

# Copie .env.example si .env n'existe pas
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Fichier .env créé depuis .env.example"
        echo ""
        echo "⚠️  IMPORTANT: Édite .env et ajoute tes vraies API keys:"
        echo "   - ANTHROPIC_API_KEY (https://console.anthropic.com/)"
        echo "   - OPENAI_API_KEY (https://platform.openai.com/api-keys)"
        echo ""
    else
        echo "⚠️  .env.example non trouvé. Crée .env manuellement."
        echo ""
    fi
else
    echo "✅ Fichier .env existe déjà"
    echo ""
fi

# Rend taskbot.py exécutable
if [ -f taskbot.py ]; then
    chmod +x taskbot.py
    echo "✅ taskbot.py est exécutable"
    echo ""
fi

# Test rapide
echo "🧪 Test de configuration..."
python3 taskbot.py status

echo ""
echo "✨ Installation terminée !"
echo ""
echo "📖 Prochaines étapes:"
echo "   1. Édite .env avec tes API keys"
echo "   2. Source .env: source .env"
echo "   3. Lance: python taskbot.py 'ta première tâche'"
echo ""
echo "   Ou consulte: cat exemple_usage.sh"
echo ""
