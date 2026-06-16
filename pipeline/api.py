"""
NOTA API — принимает запросы на анализ ниш от фронтенда.
Запускается через gunicorn: gunicorn -w 1 -b 127.0.0.1:5000 pipeline.api:app
"""

import os
import sys
import uuid
import json
import subprocess
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.supabase_client import supabase

app = Flask(__name__)
CORS(app, origins=["*"])


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Принимает нишу от фронтенда, создаёт pending-запись,
    запускает pipeline в фоне.
    Body: {"niche": "Сырки"}
    Returns: {"id": "uuid", "status": "pending"}
    """
    body = request.get_json(force=True, silent=True) or {}
    niche = (body.get("niche") or "").strip()

    if not niche:
        return jsonify({"error": "niche is required"}), 400

    if len(niche) > 200:
        return jsonify({"error": "niche too long"}), 400

    idea_id = str(uuid.uuid4())

    # Создаём pending-запись в Supabase
    record = {
        "id": idea_id,
        "title": niche,
        "status": "pending",
        "category": "Анализируется",
        "summary": "",
        "score": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        supabase.table("launch_ideas").insert(record).execute()
    except Exception as e:
        return jsonify({"error": f"db error: {e}"}), 500

    # Запускаем worker в фоне
    worker_path = os.path.join(os.path.dirname(__file__), "worker.py")
    venv_python = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "venv", "bin", "python"
    )
    python_bin = venv_python if os.path.exists(venv_python) else sys.executable

    subprocess.Popen(
        [python_bin, worker_path, idea_id, niche],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

    return jsonify({"id": idea_id, "status": "pending"})


@app.route("/api/idea/<idea_id>", methods=["GET"])
def get_idea(idea_id):
    """Возвращает статус и данные идеи по ID."""
    try:
        result = supabase.table("launch_ideas").select(
            "id,title,status,score,summary,category,created_at"
        ).eq("id", idea_id).single().execute()
        return jsonify(result.data or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
