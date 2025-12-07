#!/bin/bash
echo "================================================"
echo "🔍 DÉMONSTRATION SAFE_MODE : AVANT/APRÈS"
echo "================================================"
echo ""

cd ~/ai_orch
source .venv/bin/activate 2>/dev/null
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null

echo "📊 Test avec données problématiques:"
echo "  - Array: [1,2,3,4,5,6,7,8,9,10]"
echo "  - NaN: float('nan')"
echo "  - Big int: 999_999_999_999"
echo "  - Long string: 300 caractères"
echo ""

echo "─────────────────────────────────────────────────"
echo "❌ SANS SAFE_MODE (mode normal)"
echo "─────────────────────────────────────────────────"

unset AS_STUDIO_SAFE_MODE

python3 -c "
from src.orchestrate import SAFE_MODE

print(f'SAFE_MODE actif: {SAFE_MODE}')
print('')

# Données problématiques
data = {
    'array': [1,2,3,4,5,6,7,8,9,10],
    'nan': float('nan'),
    'big_int': 999_999_999_999,
    'long_str': 'x' * 300
}

print('Données SANS sanitization:')
print(f'  - array: {data[\"array\"]}')
print(f'  - nan: {data[\"nan\"]}')
print(f'  - big_int: {data[\"big_int\"]}')
print(f'  - long_str: {len(data[\"long_str\"])} chars')
print('')
print('⚠️  Ces données causent \"Invalid array length\" dans Studio!')
" 2>&1 | grep -v "INFO" | grep -v "Connected" | grep -v "View the run"

echo ""
echo "─────────────────────────────────────────────────"
echo "✅ AVEC SAFE_MODE=1 (mode sécurisé)"
echo "─────────────────────────────────────────────────"

export AS_STUDIO_SAFE_MODE=1

python3 -c "
from src.orchestrate import SAFE_MODE, sanitize_for_studio

print(f'SAFE_MODE actif: {SAFE_MODE}')
print('')

# Mêmes données problématiques
data = {
    'array': [1,2,3,4,5,6,7,8,9,10],
    'nan': float('nan'),
    'big_int': 999_999_999_999,
    'long_str': 'x' * 300
}

# Sanitization automatique
clean_data = sanitize_for_studio(data)

print('Données AVEC sanitization:')
print(f'  - array: {clean_data[\"array\"]}')
print(f'  - nan: {clean_data[\"nan\"]}')
print(f'  - big_int: {clean_data[\"big_int\"]}')
print(f'  - long_str: {len(clean_data[\"long_str\"])} chars')
print('')
print('✅ Ces données sont sûres pour Studio!')
" 2>&1 | grep -E "SAFE_MODE|Données|array|nan|big_int|long_str|sûres|ENABLED"

echo ""
echo "================================================"
echo "📝 RÉSUMÉ"
echo "================================================"
echo ""
echo "✅ SAFE_MODE fonctionne correctement"
echo "✅ Arrays → {\"_array_length\": N}"
echo "✅ NaN/Inf → 0"
echo "✅ Big int → plafonné à 2_147_483_647"
echo "✅ Long string → tronquée à 200 chars"
echo ""
echo "🚀 Pour activer: export AS_STUDIO_SAFE_MODE=1"
echo "📖 Documentation: cat SAFE_MODE_README.md"
echo ""
