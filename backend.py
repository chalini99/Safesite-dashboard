from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import json
import os

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/run_ai', methods=['GET'])
def run_ai():
    try:
        subprocess.run(["python", "main.py"], check=True)
        if os.path.exists("data.json"):
            with open("data.json", "r") as f:
                data = json.load(f)
            return jsonify({"status": "success", "data": data})
        else:
            return jsonify({"status": "error", "message": "data.json not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_data', methods=['GET'])
def get_data():
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"error": "data.json not found"}), 404

if __name__ == "__main__":
    app.run(port=5001, debug=True)
