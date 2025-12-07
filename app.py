from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.api_errors import bad_request, rate_limit_exceeded
from src.budgets import load_budgets

app = Flask(__name__)
# CORS - localhost uniquement
CORS(
    app,
    origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
)

# Rate limiting - 10 req/min
limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["10 per minute"], storage_uri="memory://"
)


@app.errorhandler(429)
def ratelimit_handler(e):
    return rate_limit_exceeded(f"Rate limit exceeded: {e.description}")


@app.route("/sum", methods=["POST"])
def sum_endpoint():
    data = request.get_json(silent=True) or {}
    if "numbers" not in data:
        return bad_request("numbers is required")
    numbers = data.get("numbers")
    if not isinstance(numbers, list) or not all(isinstance(x, (int, float)) for x in numbers):
        return bad_request("numbers must be a list of numbers")
    return jsonify({"result": sum(numbers)}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/budget", methods=["GET"])
def budget():
    try:
        b = load_budgets()
        return jsonify({"profile": b["meta"]["active_profile"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/version", methods=["GET"])
def version():
    return jsonify({"version": "0.1.0"}), 200


@app.route("/mean", methods=["POST"])
def mean_endpoint():
    data = request.get_json(silent=True) or {}
    nums = data.get("numbers", [])
    if not isinstance(nums, list) or not nums or not all(isinstance(x, (int, float)) for x in nums):
        return bad_request("numbers must be a non-empty list of numbers")
    return jsonify({"result": sum(nums) / len(nums)}), 200


@app.route("/median", methods=["POST"])
def median_endpoint():
    data = request.get_json() or {}
    nums = data.get("numbers")
    if not isinstance(nums, list):
        return bad_request("numbers must be a list")
    try:
        arr = sorted(float(x) for x in nums)
    except Exception:
        return bad_request("invalid numbers")
    n = len(arr)
    if n == 0:
        return bad_request("numbers empty")
    mid = n // 2
    if n % 2:
        result = arr[mid]
    else:
        result = (arr[mid - 1] + arr[mid]) / 2
    return jsonify({"result": result}), 200


import pathlib
import time


@app.route("/stats", methods=["GET"])
def stats():
    logs = pathlib.Path("rag/logs/tasks.jsonl")
    n = 0
    if logs.exists():
        with logs.open() as f:
            for _ in f:
                n += 1
    return jsonify({"ts": int(time.time()), "tasks_logged": n}), 200
