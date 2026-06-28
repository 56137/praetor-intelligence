# ==========================================
# app.py - PRAETOR Intelligence
# Servidor Flask con Stripe, PDF y descarga
# Storage: PostgreSQL (leads + PDF bytes)
# ==========================================

import os
import re
import sys
import io
import json
import uuid
import stripe
import logging
import threading

# Windows consoles default to cp1252 and crash on emoji in print().
# Force UTF-8 so local `python app.py` runs the same as Render.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURACIÃ“N
# ==========================================

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
GMAIL_USER = os.getenv('GMAIL_USER', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')
DATABASE_URL = os.getenv('DATABASE_URL', '')
stripe.api_key = STRIPE_SECRET_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'pdf_reports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'TEMPLATES.html')

for folder in [PDF_DIR, LOG_DIR]:
    os.makedirs(folder, exist_ok=True)

# ==========================================
# CONFIGURACIÃ“N DE LOGGING
# ==========================================

try:
    from logger_config import payment_logger, email_logger, download_logger, webhook_logger, scan_logger
except ImportError:
    import logging
    payment_logger = logging.getLogger('payment')
    email_logger = logging.getLogger('email')
    download_logger = logging.getLogger('download')
    webhook_logger = logging.getLogger('webhook')
    scan_logger = logging.getLogger('scan')
    logging.basicConfig(level=logging.INFO)

# Logger general â€” stdout first so Render captures it; also write to file when possible
_log_handlers: list = [logging.StreamHandler()]
try:
    _log_handlers.append(logging.FileHandler(os.path.join(LOG_DIR, 'app.log')))
except Exception:
    pass
logging.root.setLevel(logging.INFO)
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=_log_handlers,
    )
logger = logging.getLogger(__name__)

# ==========================================
# DATABASE (PostgreSQL)
# ==========================================

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not available â€” falling back to leads.json")

def _get_conn():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def _use_db():
    """True if DATABASE_URL is set and psycopg2 is installed."""
    return bool(DATABASE_URL) and PSYCOPG2_AVAILABLE

def init_db():
    """Create leads table if it doesn't exist."""
    if not _use_db():
        return
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id           SERIAL PRIMARY KEY,
                email        TEXT,
                domain       TEXT NOT NULL,
                report_id    TEXT UNIQUE NOT NULL,
                plan         TEXT DEFAULT 'express',
                status       TEXT DEFAULT 'pending',
                created_at   TIMESTAMP DEFAULT NOW(),
                paid_date    TIMESTAMP,
                stripe_session TEXT,
                pdf_file     TEXT,
                pdf_data     BYTEA
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("âœ… PostgreSQL: tabla leads lista")
    except Exception as e:
        logger.error(f"âŒ init_db error: {e}")

# Initialize DB on startup
init_db()

# ---- DB helpers ----

def db_get_all_leads():
    """Return all leads as list of dicts (without pdf_data bytes)."""
    if not _use_db():
        return _file_load_leads()
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, email, domain, report_id, plan, status, created_at, paid_date, stripe_session, pdf_file FROM leads ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    # Serialize datetimes
    for r in rows:
        for k in ('created_at', 'paid_date'):
            if r.get(k) and hasattr(r[k], 'isoformat'):
                r[k] = r[k].isoformat()
    return rows

def db_get_lead_by_email(email):
    """Return (index_unused, lead_dict) or (None, None)."""
    if not _use_db():
        leads = _file_load_leads()
        for i, l in enumerate(leads):
            if l.get('email') == email:
                return i, l
        return None, None
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM leads WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        d = dict(row)
        d.pop('pdf_data', None)
        _serialize_dates(d)
        return 0, d
    return None, None

def db_get_lead_by_report_id(report_id):
    """Return (index_unused, lead_dict) or (None, None)."""
    if not _use_db():
        leads = _file_load_leads()
        for i, l in enumerate(leads):
            if l.get('report_id') == report_id or l.get('pdf_file') == f"REPORT_{report_id}.pdf":
                return i, l
        return None, None
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM leads WHERE report_id=%s OR pdf_file=%s LIMIT 1",
        (report_id, f"REPORT_{report_id}.pdf")
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        d = dict(row)
        d.pop('pdf_data', None)
        _serialize_dates(d)
        return 0, d
    return None, None

def db_upsert_lead(lead: dict):
    """Insert or update a lead. Uses report_id as the conflict key."""
    if not _use_db():
        return _file_upsert_lead(lead)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO leads (email, domain, report_id, plan, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (report_id) DO UPDATE SET
            email  = EXCLUDED.email,
            domain = EXCLUDED.domain,
            plan   = EXCLUDED.plan,
            status = EXCLUDED.status
    """, (
        lead.get('email'), lead.get('domain'), lead.get('report_id'),
        lead.get('plan', 'express'), lead.get('status', 'pending'),
        lead.get('created_at', datetime.now().isoformat())
    ))
    conn.commit(); cur.close(); conn.close()

def db_update_lead(report_id: str, **kwargs):
    """Update specific fields on a lead by report_id."""
    if not _use_db():
        return _file_update_lead(report_id, **kwargs)
    if not kwargs:
        return
    # pdf_data handled separately
    pdf_data = kwargs.pop('pdf_data', None)
    set_clauses = []
    values = []
    field_map = {
        'status': 'status', 'paid_date': 'paid_date',
        'stripe_session': 'stripe_session', 'pdf_file': 'pdf_file',
        'domain': 'domain', 'plan': 'plan'
    }
    for k, v in kwargs.items():
        col = field_map.get(k)
        if col:
            set_clauses.append(f"{col} = %s")
            values.append(v)
    conn = _get_conn()
    cur = conn.cursor()
    if set_clauses:
        values.append(report_id)
        cur.execute(f"UPDATE leads SET {', '.join(set_clauses)} WHERE report_id=%s", values)
    if pdf_data is not None:
        cur.execute("UPDATE leads SET pdf_data=%s WHERE report_id=%s",
                    (psycopg2.Binary(pdf_data), report_id))
    conn.commit(); cur.close(); conn.close()

def db_get_pdf_bytes(report_id: str):
    """Return PDF bytes from DB, or None."""
    if not _use_db():
        return None
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pdf_data FROM leads WHERE report_id=%s", (report_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and row[0]:
        return bytes(row[0])
    return None

def _serialize_dates(d: dict):
    for k in ('created_at', 'paid_date'):
        if d.get(k) and hasattr(d[k], 'isoformat'):
            d[k] = d[k].isoformat()

# ---- File-based fallback (used when DATABASE_URL is not set) ----

def _file_load_leads():
    try:
        with open(os.path.join(BASE_DIR, 'leads.json'), 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _file_save_leads(leads):
    with open(os.path.join(BASE_DIR, 'leads.json'), 'w') as f:
        json.dump(leads, f, indent=2)

def _file_upsert_lead(lead: dict):
    leads = _file_load_leads()
    existing = False
    for l in leads:
        if l.get('report_id') == lead.get('report_id'):
            l.update(lead)
            existing = True
            break
    if not existing:
        leads.append(lead)
    _file_save_leads(leads)

def _file_update_lead(report_id: str, **kwargs):
    leads = _file_load_leads()
    for l in leads:
        if l.get('report_id') == report_id:
            for k, v in kwargs.items():
                if k != 'pdf_data':
                    l[k] = v
            break
    _file_save_leads(leads)

# ==========================================
# FUNCIONES
# ==========================================

def generate_pdf_with_id(domain, report_id=None, depth="express"):
    """Scan domain and generate a real security report PDF."""
    if not report_id:
        report_id = str(uuid.uuid4())[:8]

    pdf_filename = f"REPORT_{report_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    try:
        from scan_target import scan_target
        from report_generator import generate_report

        scan_logger.info(f"Scanning {domain} (depth={depth}, report={report_id})")
        scan_result = scan_target(domain, depth=depth)
        generate_report(scan_result, output_path=pdf_path)
        scan_logger.info(f"PDF generated: {pdf_filename}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        scan_logger.error(f"PDF generation failed: {e}")
        # Minimal fallback so the download route still has a file
        try:
            from reportlab.pdfgen import canvas as _canvas
            c = _canvas.Canvas(pdf_path)
            c.drawString(72, 720, f"PRAETOR Intelligence â€” {domain}")
            c.drawString(72, 700, f"Report ID: {report_id}")
            c.drawString(72, 680, f"Generated: {datetime.now().isoformat()}")
            c.drawString(72, 640, f"Scan error: {str(e)[:200]}")
            c.save()
        except Exception:
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n")

    # Read bytes and store in DB for persistent access
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        db_update_lead(report_id, pdf_file=pdf_filename, pdf_data=pdf_bytes)
        logger.info(f"âœ… PDF stored in DB: {pdf_filename} ({len(pdf_bytes)} bytes)")
    except Exception as e:
        logger.error(f"âŒ Failed to store PDF in DB: {e}")

    return {
        'report_id': report_id,
        'pdf_path': pdf_path,
        'pdf_filename': pdf_filename
    }


def send_report_email(email, pdf_path, domain, report_id):
    """EnvÃ­a el reporte por email con logs detallados"""

    email_logger.info(f"ðŸ“§ EMAIL ENVIADO")
    email_logger.info(f"   - Destinatario: {email}")
    email_logger.info(f"   - Archivo adjunto: {pdf_path}")
    email_logger.info(f"   - Dominio: {domain}")
    email_logger.info(f"   - Report ID: {report_id}")

    try:
        from email_sender import enviar_reporte_por_email
        result = enviar_reporte_por_email(email, domain, pdf_path)
        email_logger.info(f"   - Resultado: {result}")
        email_logger.info(f"âœ… EMAIL COMPLETADO - {email}")
        return result
    except Exception as e:
        email_logger.error(f"âŒ Error enviando email: {str(e)}")
        return False

# ==========================================
# RUTAS DE API
# ==========================================

LANDING_FILE = os.path.join(BASE_DIR, 'landing.html')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')


@app.route('/')
def home():
    """Serve the landing page if present, else fall back to JSON status."""
    if os.path.exists(LANDING_FILE):
        with open(LANDING_FILE, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({
        'name': 'PRAETOR Intelligence',
        'version': '1.0.0',
        'status': 'online',
    })


@app.route('/api/health')
def api_health():
    return jsonify({'status': 'online', 'version': '1.0.0', 'db': 'postgres' if _use_db() else 'file'})

@app.route('/ping')
def ping():
    return jsonify({'ok': True, 'deploy': 'pg-migration'})


@app.route('/scan', methods=['POST'])
def scan_preview():
    """
    Free express preview scan. Returns a JSON summary â€” NOT the full report.
    The full PDF (with recommendations, subdomains, CVEs) is behind payment.
    """
    try:
        from scan_target import scan_target, _is_valid_domain
    except Exception as e:
        return jsonify({'error': f'Scanner unavailable: {e}'}), 500

    data = request.get_json(silent=True) or {}
    domain = (data.get('domain') or '').strip().lower()
    domain = re.sub(r'^https?://', '', domain).split('/')[0]

    if not _is_valid_domain(domain):
        return jsonify({'error': 'Dominio no vÃ¡lido. Usa un formato como: empresa.com'}), 400

    scan_logger.info(f"Free preview scan: {domain}")
    try:
        r = scan_target(domain, depth='express')
    except Exception as e:
        scan_logger.error(f"Preview scan failed for {domain}: {e}")
        return jsonify({'error': f'No se pudo escanear {domain}.'}), 502

    ssl_info = r.get('ssl') or {}
    findings = []
    if not r.get('spf'):
        findings.append('Sin registro SPF (riesgo de suplantaciÃ³n de correo)')
    if not r.get('dmarc'):
        findings.append('Sin polÃ­tica DMARC (protecciÃ³n anti-phishing dÃ©bil)')
    if ssl_info.get('error'):
        findings.append('Problema con el certificado SSL/TLS')

    return jsonify({
        'domain': r.get('domain'),
        'ip': r.get('ip'),
        'risk_score': r.get('risk_score'),
        'risk_level': r.get('risk_level'),
        'spf_configured': bool(r.get('spf')),
        'dmarc_configured': bool(r.get('dmarc')),
        'ssl_ok': not bool(ssl_info.get('error')),
        'ssl_issuer': ssl_info.get('issuer'),
        'technologies': r.get('technologies') or [],
        'key_findings': findings,
        'scanned_at': r.get('scanned_at'),
    })

@app.route('/status')
def status():
    leads = db_get_all_leads()
    paid_count = len([l for l in leads if l.get('status') == 'paid'])
    pdf_count = len([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]) if os.path.exists(PDF_DIR) else 0
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'pdf_count': pdf_count,
        'lead_count': len(leads),
        'paid_count': paid_count,
        'storage': 'postgres' if _use_db() else 'file'
    })


@app.route('/leads')
def list_leads():
    if ADMIN_TOKEN:
        auth = request.headers.get('Authorization', '')
        token = request.args.get('token', '')
        if auth != f'Bearer {ADMIN_TOKEN}' and token != ADMIN_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
    leads = db_get_all_leads()
    return jsonify(leads)


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crear sesiÃ³n de Stripe para pago"""
    try:
        data = request.json
        domain = data.get('domain', 'example.com')
        email = (data.get('email') or '').strip()
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            email = ''
        price_amount = data.get('price', 100)
        plan = data.get('plan', 'express')

        report_id = str(uuid.uuid4())[:8]

        # Upsert lead
        db_upsert_lead({
            'email': email,
            'domain': domain,
            'report_id': report_id,
            'plan': plan,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        })

        logger.info(f"ðŸ’° Lead guardado: {email} - {domain} - {report_id}")
        scan_logger.info(f"ðŸ“¡ SCAN INICIADO - Dominio: {domain}, Email: {email}, Report ID: {report_id}")

        session_params = dict(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': os.getenv('STRIPE_CURRENCY', 'mxn'),
                    'product_data': {
                        'name': f'PRAETOR Report - {domain}',
                        'description': f'Security analysis report for {domain}'
                    },
                    'unit_amount': price_amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            customer_creation='always',
            success_url=f'{BASE_URL}/success/{report_id}?domain={domain}&plan={plan}',
            cancel_url=f'{BASE_URL}',
            metadata={
                'report_id': report_id,
                'domain': domain,
                'email': email,
                'plan': plan,
            }
        )
        if email:
            session_params['customer_email'] = email
            session_params['payment_intent_data'] = {'receipt_email': email}
        session = stripe.checkout.Session.create(**session_params)

        logger.info(f"ðŸ’° SesiÃ³n de Stripe creada: {session.id} para {domain} - {email}")
        return jsonify({'session_id': session.id, 'url': session.url, 'report_id': report_id})

    except Exception as e:
        logger.error(f"âŒ Error creando sesiÃ³n de Stripe: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook de Stripe para confirmar pagos"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        webhook_logger.error(f"âŒ Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        webhook_logger.error(f"âŒ Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        sd = dict(session)
        customer_details = sd.get('customer_details') or {}
        if not isinstance(customer_details, dict):
            customer_details = dict(customer_details)
        customer_email = customer_details.get('email')
        metadata = sd.get('metadata') or {}
        if not isinstance(metadata, dict):
            metadata = dict(metadata)
        report_id    = metadata.get('report_id')
        domain       = metadata.get('domain')
        plan         = metadata.get('plan', 'express')
        session_id   = sd.get('id')

        webhook_logger.info(f"ðŸ’° WEBHOOK: {customer_email} | {domain} | {report_id}")

        # 1. Mark as paid immediately
        _, lead = db_get_lead_by_report_id(report_id)
        if not lead:
            _, lead = db_get_lead_by_email(customer_email)

        if lead:
            effective_domain = domain or lead.get('domain', 'unknown')
            effective_plan   = lead.get('plan', plan)
        else:
            effective_domain = domain or 'unknown'
            effective_plan   = plan
            db_upsert_lead({
                'email': customer_email, 'domain': effective_domain,
                'report_id': report_id, 'plan': effective_plan,
                'status': 'pending', 'created_at': datetime.now().isoformat()
            })

        db_update_lead(report_id,
            status='paid',
            paid_date=datetime.now().isoformat(),
            stripe_session=session_id,
            domain=effective_domain
        )
        webhook_logger.info(f"âœ… Lead marcado 'paid': {customer_email}")

        # 2. Generate PDF in background â€” return 200 to Stripe immediately
        def _background_work():
            try:
                result   = generate_pdf_with_id(effective_domain, report_id, depth=effective_plan)
                pdf_path = result['pdf_path']
                webhook_logger.info(f"ðŸ“„ PDF listo: {result['pdf_filename']}")
                if customer_email:
                    try:
                        send_report_email(customer_email, pdf_path, effective_domain, report_id)
                        webhook_logger.info(f"ðŸ“§ Email enviado a: {customer_email}")
                    except Exception as e:
                        webhook_logger.error(f"âŒ Error enviando email: {e}")
            except Exception as e:
                webhook_logger.error(f"âŒ Error en background_work: {e}")

        threading.Thread(target=_background_work, daemon=True).start()
        return jsonify({'status': 'queued', 'report_id': report_id}), 200

    return jsonify({'status': 'ok'}), 200


@app.route('/download/<report_id>')
def download_report(report_id):
    """Descargar PDF por ID â€” sirve desde DB (persistente) o filesystem (temporal)."""
    download_logger.info(f"ðŸ“¥ DESCARGA SOLICITADA - report_id: {report_id}")

    pdf_filename = f"REPORT_{report_id}.pdf"

    # 1. Try DB first (persistent across deploys)
    pdf_bytes = db_get_pdf_bytes(report_id)
    if pdf_bytes:
        download_logger.info(f"âœ… PDF servido desde DB: {pdf_filename} ({len(pdf_bytes)} bytes)")
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )

    # 2. Fallback to filesystem (exists right after generation in same process lifetime)
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        # Check leads for alternate filename
        _, lead = db_get_lead_by_report_id(report_id)
        if lead and lead.get('pdf_file'):
            pdf_path = os.path.join(PDF_DIR, lead['pdf_file'])
            pdf_filename = lead['pdf_file']

    if os.path.exists(pdf_path):
        download_logger.info(f"âœ… PDF servido desde filesystem: {pdf_filename}")
        # Also store in DB for future requests
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            db_update_lead(report_id, pdf_data=pdf_bytes)
        except Exception:
            pass
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )

    # 3. Report not ready yet (still generating) â€” regenerate on demand
    download_logger.warning(f"âš ï¸ PDF no encontrado, regenerando: {report_id}")
    _, lead = db_get_lead_by_report_id(report_id)
    if lead and lead.get('status') == 'paid':
        domain = lead.get('domain', 'unknown')
        plan   = lead.get('plan', 'express')
        try:
            result     = generate_pdf_with_id(domain, report_id, depth=plan)
            pdf_bytes  = db_get_pdf_bytes(report_id)
            if pdf_bytes:
                return send_file(
                    io.BytesIO(pdf_bytes),
                    as_attachment=True,
                    download_name=pdf_filename,
                    mimetype='application/pdf'
                )
        except Exception as e:
            logger.error(f"âŒ On-demand generation failed: {e}")

    download_logger.error(f"âŒ PDF no encontrado: {report_id}")
    return jsonify({'error': 'Report not found or still generating. Try again in a moment.'}), 404


@app.route('/success/<report_id>')
def success_page(report_id):
    """PÃ¡gina de Ã©xito con descarga automÃ¡tica"""
    _, lead = db_get_lead_by_report_id(report_id)
    pdf_file = lead.get('pdf_file') if lead else None

    # If PDF not ready yet, kick off generation in background
    if not pdf_file:
        domain = (lead.get('domain') if lead else None) or request.args.get('domain', 'unknown')
        plan   = (lead.get('plan') if lead else None) or request.args.get('plan', 'express')

        def _gen():
            try:
                generate_pdf_with_id(domain, report_id, depth=plan)
                logger.info(f"ðŸ“„ PDF generado en background: REPORT_{report_id}.pdf")
            except Exception as e:
                logger.error(f"âŒ Error generando PDF en background: {e}")

        threading.Thread(target=_gen, daemon=True).start()

    logger.info(f"ðŸ“„ Success page para: {report_id}")

    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
        html_content = html_content.replace('{{ report_id }}', report_id)
        html_content = html_content.replace('{{ pdf_file }}', pdf_file or '')
        return html_content, 200, {'Content-Type': 'text/html'}

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>PRAETOR - Descarga tu Reporte</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .box {{ text-align: center; background: #1a1a1a; padding: 40px; border-radius: 12px; border: 1px solid #00d4ff; max-width: 500px; }}
            h1 {{ color: #00d4ff; }}
            .btn {{ background: #00d4ff; color: #000; border: none; padding: 14px 35px; font-size: 18px; font-weight: bold; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; }}
            .btn:hover {{ background: #00e5ff; transform: scale(1.05); }}
            .info {{ color: #666; font-size: 14px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>âœ… Â¡PAGO CONFIRMADO!</h1>
            <p style="color:#888;">Tu reporte estÃ¡ listo para descargar</p>
            <a href="/download/{report_id}" class="btn">ðŸ“¥ DESCARGAR REPORTE</a>
            <p class="info">Guarda el PDF en tu dispositivo.</p>
        </div>
        <script>
            setTimeout(() => {{
                window.location.href = '/download/{report_id}';
            }}, 1500);
        </script>
    </body>
    </html>
    """


@app.route('/test-payment', methods=['GET'])
def test_payment():
    """Simula el flujo completo sin cobrar ni hacer scan de red."""
    domain    = request.args.get('domain', 'example.com')
    email     = request.args.get('email', 'test@praetor.lat')
    report_id = 'TEST_' + str(uuid.uuid4())[:6]
    results   = {}

    # PASO 1: Upsert lead en DB
    try:
        db_upsert_lead({
            'email': email, 'domain': domain,
            'report_id': report_id, 'plan': 'express',
            'status': 'pending', 'created_at': datetime.now().isoformat()
        })
        results['1_lead_db'] = f'PASS (storage={"postgres" if _use_db() else "file"})'
    except Exception as e:
        results['1_lead_db'] = f'FAIL: {e}'

    # PASO 2: GeneraciÃ³n de PDF
    pdf_filename = f'REPORT_{report_id}.pdf'
    pdf_path     = os.path.join(PDF_DIR, pdf_filename)
    try:
        from reportlab.pdfgen import canvas as _c
        c = _c.Canvas(pdf_path)
        c.setFont('Helvetica-Bold', 16)
        c.drawString(72, 750, 'PRAETOR Intelligence â€” Test Report')
        c.setFont('Helvetica', 12)
        c.drawString(72, 720, f'Domain : {domain}')
        c.drawString(72, 700, f'Report : {report_id}')
        c.drawString(72, 680, f'Date   : {datetime.now().isoformat()}')
        c.drawString(72, 640, 'Este es un reporte de prueba (sin scan real).')
        c.save()
        size = os.path.getsize(pdf_path)
        results['2_pdf_generado'] = f'PASS ({size} bytes)'
    except Exception as e:
        results['2_pdf_generado'] = f'FAIL: {e}'
        pdf_path = None

    # PASO 3: Guardar PDF en DB
    try:
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            db_update_lead(report_id, status='paid', paid_date=datetime.now().isoformat(),
                           pdf_file=pdf_filename, pdf_data=pdf_bytes)
            results['3_pdf_en_db'] = f'PASS ({len(pdf_bytes)} bytes en DB)'
        else:
            results['3_pdf_en_db'] = 'SKIP (no PDF)'
    except Exception as e:
        results['3_pdf_en_db'] = f'FAIL: {e}'

    # PASO 4: Verificar que /download lo encontrarÃ­a desde DB
    try:
        retrieved = db_get_pdf_bytes(report_id)
        if retrieved and len(retrieved) > 100:
            results['4_descarga_db'] = f'PASS â€” /download/{report_id} sirve desde DB'
        elif pdf_path and os.path.exists(pdf_path):
            results['4_descarga_db'] = f'PASS â€” /download/{report_id} sirve desde filesystem'
        else:
            results['4_descarga_db'] = 'FAIL: PDF no encontrado'
    except Exception as e:
        results['4_descarga_db'] = f'FAIL: {e}'

    # PASO 5: Email (opcional)
    if request.args.get('email_test') == '1':
        try:
            from email_sender import enviar_reporte_por_email
            ok = enviar_reporte_por_email(email, domain, pdf_path) if (pdf_path and os.path.exists(pdf_path)) else False
            results['5_email'] = 'PASS' if ok else 'FAIL: retornÃ³ False'
        except Exception as e:
            results['5_email'] = f'FAIL: {type(e).__name__}: {e}'
    else:
        results['5_email'] = 'SKIP (usa &email_test=1 para probar correo)'

    passed = sum(1 for v in results.values() if str(v).startswith('PASS'))
    results['_resumen']      = f'{passed} pasos PASS'
    results['_report_id']    = report_id
    results['_download_url'] = f'/download/{report_id}'

    return jsonify(results), 200


@app.route('/cron/monitor', methods=['POST', 'GET'])
def cron_monitor():
    """Called by Render Cron Job. Protected by CRON_SECRET."""
    secret = os.getenv('CRON_SECRET', '')
    if secret:
        incoming = request.headers.get('X-Cron-Secret') or request.args.get('secret', '')
        if incoming != secret:
            return jsonify({'error': 'Unauthorized'}), 403

    try:
        from monitor import run_monitor
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    leads   = db_get_all_leads()
    results = []
    for lead in leads:
        if lead.get('status') != 'paid':
            continue
        plan = lead.get('plan', 'express')
        if plan not in ('pro', 'corporate'):
            continue
        domain = lead.get('domain')
        if not domain:
            continue
        try:
            result = run_monitor(domain, depth=plan)
            diff   = result.get('diff') or {}
            results.append({
                'domain': domain,
                'is_first_scan': result['is_first_scan'],
                'summary': diff.get('summary'),
                'score_change': diff.get('score_change'),
            })
            logger.info(f"[cron] {domain}: {diff.get('summary', 'first scan')}")
        except Exception as e:
            logger.error(f"[cron] {domain} failed: {e}")
            results.append({'domain': domain, 'error': str(e)})

    return jsonify({'status': 'done', 'scanned': len(results), 'results': results})


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    import traceback
    tb = traceback.format_exc()
    logger.error(f"âŒ Error interno: {str(e)}\n{tb}")
    try:
        webhook_logger.error(f"âŒ Error interno (500):\n{tb}")
    except Exception:
        pass
    return jsonify({'error': 'Internal server error'}), 500

# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print(f"\n{'='*50}")
    print(f"ðŸš€ PRAETOR Intelligence")
    print(f"ðŸ“ http://localhost:{port}")
    print(f"ðŸ—„ï¸  Storage: {'PostgreSQL' if _use_db() else 'File (leads.json)'}")
    print(f"ðŸ“„ http://localhost:{port}/success/TEST123")
    print(f"ðŸ“Š http://localhost:{port}/status")
    print(f"ðŸ“‹ http://localhost:{port}/leads")
    print(f"{'='*50}\n")

    logger.info(f"ðŸš€ PRAETOR Intelligence iniciado en http://localhost:{port}")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

