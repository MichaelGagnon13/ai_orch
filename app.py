from flask import Flask, request, jsonify
from src.budgets import load_budgets

app = Flask(__name__)

@app.route('/sum', methods=['POST'])
def sum_endpoint():
    data = request.get_json(silent=True) or {}
    numbers = data.get('numbers', [])
    if not isinstance(numbers, list) or not all(isinstance(x, (int, float)) for x in numbers):
        return jsonify({'error': 'numbers must be a list of numbers'}), 400
    return jsonify({'result': sum(numbers)}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/budget', methods=['GET'])
def budget():
    try:
        b = load_budgets()
        return jsonify({'profile': b['meta']['active_profile']}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
