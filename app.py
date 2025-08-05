from flask import Flask, request, jsonify
from scraper import run_tournament_analysis

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url")
    index = data.get("index")

    if not url or index is None:
        return jsonify({"error": "Missing URL or age group index"}), 400

    try:
        result = run_tournament_analysis(url, index)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "Tournament Analyzer is running!"
