import json
import os

from flask import jsonify, request

from app import app
from openai_service_v2 import analyze_security_report


@app.route('/ai/analyze', methods=['POST'])
def ai_analyze():
    """Convert PRAETOR scan data into an executive security analysis."""
    data = request.get_json(silent=True) or {}
    domain = str(data.get('domain', '')).strip()
    report = data.get('scan_result', data.get('report_text', ''))

    if not report:
        return jsonify({'error': 'scan_result or report_text is required'}), 400

    if isinstance(report, (dict, list)):
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        report_text = str(report)

    if len(report_text) > 120000:
        return jsonify({'error': 'scan_result is too large'}), 413

    try:
        analysis = analyze_security_report(report_text)
        return jsonify({
            'status': 'success',
            'domain': domain,
            'model': os.getenv('OPENAI_MODEL', 'gpt-5.6-luna'),
            'analysis': analysis,
        }), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        app.logger.exception('OpenAI analysis failed')
        return jsonify({'error': 'OpenAI analysis failed', 'detail': str(exc)}), 502
