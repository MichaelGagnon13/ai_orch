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

@app.route('/version', methods=['GET'])
def version():
    return jsonify({'version': '0.1.0'}), 200

@app.route('/mean', methods=['POST'])
def mean_endpoint():
    data = request.get_json(silent=True) or {}
    nums = data.get('numbers', [])
    if not isinstance(nums, list) or not nums or not all(isinstance(x, (int, float)) for x in nums):
        return jsonify({'error': 'numbers must be a non-empty list of numbers'}), 400
    return jsonify({'result': sum(nums)/len(nums)}), 200


@app.route('/median', methods=['POST'])
def median_endpoint():
    data = request.get_json() or {}
    nums = data.get('numbers')
    if not isinstance(nums, list):
        return jsonify({'error': 'numbers must be a list'}), 400
    try:
        arr = sorted(float(x) for x in nums)
    except Exception:
        return jsonify({'error': 'invalid numbers'}), 400
    n = len(arr)
    if n == 0:
        return jsonify({'error': 'numbers empty'}), 400
    mid = n // 2
    if n % 2:
        result = arr[mid]
    else:
        result = (arr[mid-1] + arr[mid]) / 2
    return jsonify({'result': result}), 200
