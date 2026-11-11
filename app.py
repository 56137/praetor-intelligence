# ==========================================
# app.py - PRAETOR Intelligence
# Servidor Flask con Stripe, PDF y descarga
# Storage: PostgreSQL / Local JSON Fallback
# ==========================================

import os
import re
import sys
import json
import uuid
import stripe
import logging

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
CORS(app, origins=[origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,https://praetor.lat,https://www.praetor.lat').split(',') if origin.strip()])

# ==========================================
# CONFIGURACIÓN
# ==========================================

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
GMAIL_USER = os.getenv('GMAIL_USER', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '').strip()
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
DATABASE_URL = os.getenv('DATABASE_URL', '')
stripe.api_key = STRIPE_SECRET_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'pdf_reports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'TEMPLATES.html')
LANDING_FILE = os.path.join(BASE_DIR, 'landing.html')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')

for folder in [PDF_DIR, LOG_DIR]:
    os.makedirs(folder, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE LOGGING
# ==========================================

try:
    from logger_config import payment_logger, email_logger, download_logger, webhook_logger, scan_logger
except ImportError:
    payment_logger = logging.getLogger('payment')
    email_logger = logging.getLogger('email')
    download_logger = logging.getLogger('download')
    webhook_logger = logging.getLogger('webhook')
    scan_logger = logging.getLogger('scan')
    logging.basicConfig(level=logging.INFO)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# FUNCIONES AUXILIARES DE LEADS Y DB
# ==========================================

def _use_db():
    """Determina si se usa PostgreSQL o almacenamiento local en JSON."""
    return bool(DATABASE_URL)

def db_get_all_leads():
    """Obtiene todos los leads almacenados (soporte local para leads.json)."""
    leads_file = os.path.join(BASE_DIR, 'leads.json')
    if os.path.exists(leads_file):
        try:
            with open(leads_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def find_lead_by_email(email, leads):
    """Busca un lead por correo electrónico dentro de la lista."""
    if not email:
        return None, None
    for idx, lead in enumerate(leads):
        if lead.get('email', '').strip().lower() == email.strip().lower():
            return idx, lead
    return None, None

def find_lead_by_report_id(report_id, leads):
    """Busca un lead por su ID de reporte único."""
    if not report_id:
        return None, None
    for idx, lead in enumerate(leads):
        if lead.get('report_id') == report_id:
            return idx, lead
    return None, None

def get_pdf_for_report_id(report_id):
    """Recupera el nombre del archivo PDF asociado a un report_id."""
    leads = db_get_all_leads()
    for lead in leads:
        if lead.get('report_id') == report_id:
            return lead.get('pdf_file') or f"REPORT_{report_id}.pdf"
    return f"REPORT_{report_id}.pdf"

# ==========================================
# FUNCIONES DE NEGOCIO
# ==========================================

def generate_pdf_with_id(domain, report_id=None, depth="express"):
    """Scan domain and generate a real security report PDF."""
    if not report_id:
        report_id = uuid.uuid4().hex

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
        try:
            from reportlab.pdfgen import canvas as _canvas
            c = _canvas.Canvas(pdf_path)
            c.drawString(72, 720, f"PRAETOR Intelligence — {domain}")
            c.drawString(72, 700, f"Report ID: {report_id}")
            c.drawString(72, 680, f"Generated: {datetime.now().isoformat()}")
            c.drawString(72, 640, f"Scan error: {str(e)[:200]}")
            c.save()
        except Exception:
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n")

    return {
        'report_id': report_id,
        'pdf_path': pdf_path,
        'pdf_filename': pdf_filename
    }

def send_report_email(email, pdf_path, domain, report_id):
    """Envía el reporte por email con logs detallados"""
    email_logger.info(f"📧 EMAIL ENVIADO")
    email_logger.info(f"   - Destinatario: {email}")
    email_logger.info(f"   - Archivo adjunto: {pdf_path}")
    email_logger.info(f"   - Dominio: {domain}")
    email_logger.info(f"   - Report ID: {report_id}")

    try:
        from email_sender import enviar_reporte_por_email
        result = enviar_reporte_por_email(email, domain, pdf_path)
        email_logger.info(f"   - Resultado: {result}")
        email_logger.info(f"✅ EMAIL COMPLETADO - {email}")
        return True
    except Exception as e:
        email_logger.error(f"❌ Error enviando email: {str(e)}")
        return False

# ==========================================
# RUTAS DE API
# ==========================================

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
        'endpoints': {
            '/download/<report_id>': 'Descargar PDF',
            '/success/<report_id>': 'Página de éxito con descarga',
            '/webhook/stripe': 'Webhook de Stripe',
            '/create-checkout-session': 'Crear sesión de Stripe'
        }
    })

@app.route('/status')
def status():
    # Public health endpoint: expose operational state, never customer or revenue counts.
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/leads', methods=['GET'])
def list_leads():
    if not ADMIN_TOKEN:
        return jsonify({'error': 'Admin access is not configured'}), 503
    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {ADMIN_TOKEN}':
        return jsonify({'error': 'Unauthorized'}), 401
    leads = db_get_all_leads()
    return jsonify(leads)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crear sesión de Stripe para pago"""
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Payments are not configured'}), 503
    try:
        data = request.json or {}
        domain = data.get('domain', 'example.com')
        email = (data.get('email') or '').strip()
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            email = ''
        plan = str(data.get('plan', 'express')).lower()
        plan_prices = {'express': 299900, 'pro': 699900, 'corporate': 1099900, 'monitoring': 399900}
        if plan not in plan_prices:
            return jsonify({'error': 'Plan no válido'}), 400
        price_amount = plan_prices[plan]

        report_id = uuid.uuid4().hex
        
        # Guardar lead temporalmente
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        except Exception:
            leads = []
        
        existing = False
        for lead in leads:
            if lead.get('email') == email and lead.get('domain') == domain:
                existing = True
                lead['report_id'] = report_id
                lead['status'] = 'pending'
                break
        
        if not existing:
            leads.append({
                'email': email,
                'domain': domain,
                'report_id': report_id,
                'plan': plan,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            })
        
        with open(leads_file, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💰 Lead guardado: {email} - {domain} - {report_id}")
        scan_logger.info(f"📡 SCAN INICIADO - Dominio: {domain}, Email: {email}")
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': os.getenv('STRIPE_CURRENCY', 'mxn'),
                    'product_data': {
                        'name': f'PRAETOR Report - {domain}',
                        'description': f'Security analysis report for {domain}'
                    },
                    'unit_amount': price_amount,
                    **({'recurring': {'interval': 'month'}} if plan == 'monitoring' else {}),
                },
                'quantity': 1,
            }],
            mode=('subscription' if plan == 'monitoring' else 'payment'),
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
        
        logger.info(f"💰 Sesión de Stripe creada: {session.id} para {domain} - {email}")
        
        return jsonify({
            'session_id': session.id,
            'url': session.url,
            'report_id': report_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error creando sesión de Stripe: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook de Stripe para confirmar pagos"""
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({'error': 'Webhook is not configured'}), 503
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        webhook_logger.error(f"❌ Error en webhook (payload inválido): {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        webhook_logger.error(f"❌ Error en webhook (firma inválida): {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')
        report_id = session.get('metadata', {}).get('report_id')
        domain = session.get('metadata', {}).get('domain')
        plan = session.get('metadata', {}).get('plan', 'express')
        session_id = session.get('id')
        
        webhook_logger.info(f"💰 WEBHOOK RECIBIDO - email: {customer_email}, report_id: {report_id}")
        
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        except Exception:
            leads = []
        
        if session.get('payment_status') not in ('paid', 'no_payment_required'):
            webhook_logger.warning("Ignoring completed checkout with unpaid status")
            return jsonify({'error': 'Payment not completed'}), 400
        if not report_id or not session_id:
            return jsonify({'error': 'Missing checkout metadata'}), 400

        idx, lead = find_lead_by_report_id(report_id, leads)
        if lead and lead.get('stripe_session') == session_id:
            return jsonify({'status': 'already_processed'}), 200
        
        if lead:
            lead['status'] = 'paid'
            lead['paid_date'] = datetime.now().isoformat()
            lead['stripe_session'] = session_id
            
            # Generar PDF real si no existe
            pdf_result = generate_pdf_with_id(domain or lead.get('domain', 'unknown'), report_id, depth=plan)
            lead['pdf_file'] = pdf_result['pdf_filename']
            
            with open(leads_file, 'w', encoding='utf-8') as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
                
            pdf_path = os.path.join(PDF_DIR, lead['pdf_file'])
            send_report_email(customer_email, pdf_path, domain, report_id)
        else:
            webhook_logger.warning(f"⚠️ LEAD NO ENCONTRADO - {customer_email}")
            pdf_result = generate_pdf_with_id(domain or 'unknown', report_id, depth=plan)
            pdf_file = pdf_result['pdf_filename']
            
            new_lead = {
                'email': customer_email,
                'domain': domain or 'unknown',
                'report_id': report_id,
                'pdf_file': pdf_file,
                'status': 'paid',
                'paid_date': datetime.now().isoformat(),
                'stripe_session': session_id
            }
            leads.append(new_lead)
            
            with open(leads_file, 'w', encoding='utf-8') as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
            
            pdf_path = os.path.join(PDF_DIR, pdf_file)
            send_report_email(customer_email, pdf_path, domain, report_id)
    
    return jsonify({'status': 'ok'}), 200

@app.route('/download/<report_id>')
def download_report(report_id):
    """Download a report only after a verified payment has been recorded."""
    if not re.fullmatch(r'[a-fA-F0-9-]{8,36}', report_id or ''):
        return jsonify({'error': 'Report not found'}), 404

    leads = db_get_all_leads()
    lead = next((item for item in leads if item.get('report_id') == report_id), None)
    if not lead or lead.get('status') != 'paid':
        return jsonify({'error': 'Report not found'}), 404

    pdf_filename = os.path.basename(lead.get('pdf_file') or f'REPORT_{report_id}.pdf')
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.isfile(pdf_path):
        logger.warning("Paid report PDF missing for report_id=%s", report_id)
        return jsonify({'error': 'Report not found'}), 404

    download_logger.info("Paid report download completed for report_id=%s", report_id)
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_filename,
        mimetype='application/pdf'
    )

@app.route('/success/<report_id>')
def success_page(report_id):
    """Show the success page only for a report with a recorded paid status."""
    if not re.fullmatch(r'[a-fA-F0-9-]{8,36}', report_id or ''):
        return jsonify({'error': 'Report not found'}), 404
    leads = db_get_all_leads()
    lead = next((item for item in leads if item.get('report_id') == report_id), None)
    if not lead or lead.get('status') != 'paid':
        return jsonify({'error': 'Report not found'}), 404
    pdf_file = os.path.basename(lead.get('pdf_file') or f'REPORT_{report_id}.pdf')
    
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
            body {{ font-family: Arial, sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .box {{ text-align: center; background: #1e293b; padding: 40px; border-radius: 12px; border: 1px solid #0284c7; max-width: 500px; }}
            h1 {{ color: #0284c7; }}
            .btn {{ background: #0284c7; color: #fff; border: none; padding: 14px 35px; font-size: 18px; font-weight: bold; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; }}
            .btn:hover {{ background: #0369a1; }}
            .info {{ color: #94a3b8; font-size: 14px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>✅ ¡PAGO CONFIRMADO!</h1>
            <p style="color:#94a3b8;">Tu reporte está listo para descargar</p>
            <a href="/download/{report_id}" class="btn">📥 DESCARGAR REPORTE</a>
            <p class="info">También recibirás una copia por correo electrónico</p>
        </div>
        <script>
            setTimeout(() => {{
                window.location.href = '/download/{report_id}';
            }}, 1500);
        </script>
    </body>
    </html>
    """

@app.route('/cron/monitor', methods=['POST'])
def cron_monitor():
    """Called by Render Cron Job. Protected by CRON_SECRET."""
    secret = os.getenv('CRON_SECRET', '').strip()
    if not secret:
        return jsonify({'error': 'Cron access is not configured'}), 503
    incoming = request.headers.get('X-Cron-Secret', '')
    if incoming != secret:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from monitor import run_monitor
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    leads = db_get_all_leads()
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
            diff = result.get('diff') or {}
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
    logger.error(f"❌ Error interno: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n{'='*50}")
    print(f"🚀 PRAETOR Intelligence")
    print(f"📍 http://localhost:{port}")
    print(f"📄 http://localhost:{port}/success/TEST123")
    print(f"📊 http://localhost:{port}/status")
    print(f"📋 http://localhost:{port}/leads")
    print(f"{'='*50}\n")
    
    logger.info(f"🚀 PRAETOR Intelligence iniciado en http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
