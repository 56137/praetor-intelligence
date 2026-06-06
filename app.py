import os
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from scan_target import scan_target

app = Flask(__name__)
LEADS_FILE = "leads.json"


def save_lead(domain, email, score=None, scanned_at=None):
    leads = []
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, 'r') as f:
                leads = json.load(f)
        except Exception:
            leads = []

    fecha = scanned_at.split('T', 1)[0] if scanned_at else datetime.now(timezone.utc).date().isoformat()
    leads.append({
        "domain": domain,
        "email": email,
        "score": score,
        "fecha": fecha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "new"
    })

    with open(LEADS_FILE, 'w') as f:
        json.dump(leads, f, indent=2)


@app.route('/')
def index():
    return send_from_directory(os.getcwd(), 'ip_protection.html')


@app.route('/scan', methods=['POST'])
def scan():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'Request JSON inválido.'}), 400

    domain = payload.get('domain', '').strip()
    email = payload.get('contact', '').strip()
    
    if not domain:
        return jsonify({'error': 'Dominio requerido.'}), 400

    try:
        report = scan_target(domain)
    except Exception as exc:
        scanned_at = datetime.now(timezone.utc).isoformat()
        save_lead(domain, email, score=None, scanned_at=scanned_at)
        return jsonify({
            'domain': domain,
            'scanned_at': scanned_at,
            'risk_score': None,
            'errors': [str(exc)],
            'error': 'El escaneo falló. Lead guardado.'
        }), 500

    save_lead(domain, email, score=report.get('risk_score'), scanned_at=report.get('scanned_at'))
    return jsonify(report)


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
