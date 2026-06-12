import os
import json
import stripe
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, send_file

from scan_target import scan_target
from report_generator import generate_report

app = Flask(__name__)


@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


# ── Stripe (una sola vez) ──────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

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
    return send_from_directory(
        os.getcwd(),
        'ip_protection.html'
    )


@app.route('/scan', methods=['POST'])
def scan():

    payload = request.get_json()

    if not payload:
        return jsonify({"error": "JSON requerido"}), 400

    domain = payload.get('domain', '').strip()
    email = payload.get('email', '').strip()

    if not domain:
        return jsonify({"error": "Domain requerido"}), 400

    try:

        report = scan_target(domain)

        pdf_file = generate_report(report)

        report["pdf_file"] = pdf_file

        save_lead(
            domain,
            email,
            score=report.get("risk_score"),
            scanned_at=report.get("scanned_at")
        )

        return jsonify(report), 200

    except Exception as exc:

        scanned_at = datetime.now(timezone.utc).isoformat()

        save_lead(
            domain,
            email,
            score=None,
            scanned_at=scanned_at
        )

        return jsonify({
            "domain": domain,
            "scanned_at": scanned_at,
            "risk_score": None,
            "errors": [str(exc)],
            "error": "El escaneo falló. Lead guardado."
        }), 500


@app.route('/success')
def success():
    pdf_link = "/download/REPORT_google_com.pdf"

    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'r') as f:
            leads = json.load(f)
        paid = [l for l in leads if l.get('status') == 'paid' and l.get('pdf_file')]
        if paid:
            pdf_link = f"/download/{paid[-1]['pdf_file']}"

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:60px;">
        <h1>✅ Pago recibido correctamente</h1>
        <p>Gracias por adquirir una auditoría PRAETOR.</p>
        <p>Tu pago fue confirmado por Stripe.</p>
        <p>El reporte premium está disponible para descarga.</p>
        <a href="{pdf_link}">
            <button style="padding:15px 25px;font-size:18px;">Descargar Reporte</button>
        </a>
        <br><br>
        <a href="/">
            <button>Volver al sistema</button>
        </a>
    </body>
    </html>
    """


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return jsonify({"error": "Payload inválido"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Firma inválida"}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        customer_details = session.get('customer_details') or {}
        customer_email = customer_details.get('email') or session.get('customer_email')

        if customer_email and os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r') as f:
                leads = json.load(f)

            matching = [l for l in leads if l.get('email') == customer_email]
            if matching:
                last_lead = matching[-1]
                domain = last_lead['domain']
                safe_name = domain.replace('.', '_').replace('/', '_')
                pdf_filename = f'REPORT_{safe_name}.pdf'

                last_lead['status'] = 'paid'
                last_lead['pdf_file'] = pdf_filename
                with open(LEADS_FILE, 'w') as f:
                    json.dump(leads, f, indent=2)

    return jsonify({"status": "ok"}), 200


@app.route("/download/<filename>")
def download_report(filename):
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    return {"error": "Archivo no encontrado"}, 404


if __name__ == '__main__':
    try:
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()