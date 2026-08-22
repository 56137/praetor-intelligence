from flask import request, jsonify
import os

from app import app
from openai_service_v2 import analyze_security_report


@app.route("/ai/analyze", methods=["POST"])
def ai_analyze():
    try:
        data = request.get_json(silent=True) or {}
        report_text = data.get("report_text", "")
        if not isinstance(report_text, str) or not report_text.strip():
            return jsonify({"error": "report_text is required"}), 400
        analysis = analyze_security_report(report_text)
        return jsonify({
            "status": "success",
            "model": os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            "analysis": analysis,
        }), 200
    except Exception as exc:
        app.logger.exception("OpenAI analysis failed")
        return jsonify({"error": str(exc)}), 500
