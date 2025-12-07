#!/bin/bash
cd ~/ai_orch
source .venv/bin/activate

# Charger .env
export $(cat .env | grep -v '^#' | xargs)

# Activer SAFE_MODE
export AS_STUDIO_SAFE_MODE=1

echo "=== TEST AVEC SAFE_MODE ACTIVÉ ==="
echo ""
echo "[ENV] ANTHROPIC_MODEL_ID = $ANTHROPIC_MODEL_ID"
echo "[ENV] AS_STUDIO_SAFE_MODE = $AS_STUDIO_SAFE_MODE"
echo ""

python3 -c "
import sys
import os

# Test rapide d'import
try:
    from src.orchestrate import SAFE_MODE, sanitize_for_studio
    print('[TEST] Import réussi!')
    print('[TEST] SAFE_MODE =', SAFE_MODE)
    print('')

    # Test rapide
    test_data = {
        'array': [1,2,3,4,5],
        'nan': float('nan'),
        'big_int': 999_999_999_999,
        'long_str': 'x' * 300
    }
    result = sanitize_for_studio(test_data)

    # Vérifications
    assert result['array'] == {'_array_length': 5}, 'Array test failed'
    assert result['nan'] == 0, 'NaN test failed'
    assert result['big_int'] == 2_147_483_647, 'Big int test failed'
    assert len(result['long_str']) == 200, 'Long string test failed'

    print('[TEST] Résultat sanitize:')
    print('  - array:', result['array'])
    print('  - nan:', result['nan'])
    print('  - big_int:', result['big_int'])
    print('  - long_str length:', len(result['long_str']))
    print('')
    print('[TEST] ✅ TOUS LES TESTS PASSÉS')
    print('[TEST] Le code SAFE_MODE est 100% fonctionnel!')
    sys.exit(0)
except Exception as e:
    print('[TEST] ❌ Erreur:', e)
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1 | grep -E '^\[|ENABLED|Connected|budget'
