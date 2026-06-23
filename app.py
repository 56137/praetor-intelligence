# ==========================================
# app.py - PRAETOR Intelligence
# Servidor Flask con Stripe, PDF y descarga
# ==========================================

import os
import re
import sys
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
# CONFIGURACIÓN
# ==========================================

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
GMAIL_USER = os.getenv('GMAIL_USER', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')
stripe.api_key = STRIPE_SECRET_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'pdf_reports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'TEMPLATES.html')

for folder in [PDF_DIR, LOG_DIR]:
    os.makedirs(folder, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE LOGGING
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

# Logger general
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def find_lead_by_email(email, leads):
    """Busca un lead por email"""
    for i, lead in enumerate(leads):
        if lead.get('email') == email:
            return i, lead
    return None, None

def find_lead_by_report_id(report_id, leads):
    """Busca un lead por report_id"""
    for i, lead in enumerate(leads):
        if lead.get('report_id') == report_id:
            return i, lead
        if lead.get('pdf_file') == f"REPORT_{report_id}.pdf":
            return i, lead
    return None, None

def get_pdf_for_report_id(report_id):
    """Obtiene el PDF asociado a un report_id"""
    
    # 1. Buscar en leads.json
    leads_file = os.path.join(BASE_DIR, 'leads.json')
    try:
        with open(leads_file, 'r') as f:
            leads = json.load(f)
    except:
        leads = []
    
    # Buscar por report_id
    idx, lead = find_lead_by_report_id(report_id, leads)
    if lead:
        pdf_file = lead.get('pdf_file')
        if pdf_file and os.path.exists(os.path.join(PDF_DIR, pdf_file)):
            logger.info(f"✅ PDF encontrado en leads.json: {pdf_file}")
            return pdf_file
    
    # 2. Buscar en pdf_reports
    pdf_path = os.path.join(PDF_DIR, f"REPORT_{report_id}.pdf")
    if os.path.exists(pdf_path):
        logger.info(f"✅ PDF encontrado en pdf_reports: REPORT_{report_id}.pdf")
        return f"REPORT_{report_id}.pdf"
    
    return None

def send_report_email(email, pdf_path, domain, report_id):
    """Envía el reporte por email con logs detallados"""
    
    email_logger.info(f"📧 EMAIL ENVIADO")
    email_logger.info(f"   - Destinatario: {email}")
    email_logger.info(f"   - Archivo adjunto: {pdf_path}")
    email_logger.info(f"   - Dominio: {domain}")
    email_logger.info(f"   - Report ID: {report_id}")
    
    # Aquí va tu lógica de envío de email existente
    # Si tienes email_sender.py, importarlo y usarlo
    
    try:
        from email_sender import enviar_reporte_por_email
        # enviar_reporte_por_email(email, dominio, pdf_filename) — accepts a full path
        result = enviar_reporte_por_email(email, domain, pdf_path)
        email_logger.info(f"   - Resultado: {result}")
        email_logger.info(f"✅ EMAIL COMPLETADO - {email}")
        return result
    except Exception as e:
        email_logger.error(f"❌ Error enviando email: {str(e)}")
        return False

# ==========================================
# RUTAS DE API
# ==========================================

LANDING_FILE = os.path.join(BASE_DIR, 'landing.html')


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
    return jsonify({'status': 'online', 'version': '1.0.0'})

@app.route('/ping')
def ping():
    return jsonify({'ok': True, 'deploy': 'e432c97'})


@app.route('/scan', methods=['POST'])
def scan_preview():
    """
    Free express preview scan. Returns a JSON summary — NOT the full report.
    The full PDF (with recommendations, subdomains, CVEs) is behind payment.
    """
    try:
        from scan_target import scan_target, _is_valid_domain
    except Exception as e:
        return jsonify({'error': f'Scanner unavailable: {e}'}), 500

    data = request.get_json(silent=True) or {}
    domain = (data.get('domain') or '').strip().lower()
    # strip scheme/path if the user pasted a URL
    domain = re.sub(r'^https?://', '', domain).split('/')[0]

    if not _is_valid_domain(domain):
        return jsonify({'error': 'Dominio no válido. Usa un formato como: empresa.com'}), 400

    scan_logger.info(f"Free preview scan: {domain}")
    try:
        r = scan_target(domain, depth='express')
    except Exception as e:
        scan_logger.error(f"Preview scan failed for {domain}: {e}")
        return jsonify({'error': f'No se pudo escanear {domain}.'}), 502

    ssl_info = r.get('ssl') or {}
    findings = []
    if not r.get('spf'):
        findings.append('Sin registro SPF (riesgo de suplantación de correo)')
    if not r.get('dmarc'):
        findings.append('Sin política DMARC (protección anti-phishing débil)')
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
    try:
        with open(os.path.join(BASE_DIR, 'leads.json'), 'r') as f:
            leads = json.load(f)
        lead_count = len(leads)
        paid_count = len([l for l in leads if l.get('status') == 'paid'])
    except:
        lead_count = 0
        paid_count = 0
    
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'pdf_count': len([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]),
        'lead_count': lead_count,
        'paid_count': paid_count
    })

@app.route('/leads')
def list_leads():
    try:
        with open(os.path.join(BASE_DIR, 'leads.json'), 'r') as f:
            leads = json.load(f)
        return jsonify(leads)
    except:
        return jsonify([])

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crear sesión de Stripe para pago"""
    
    try:
        data = request.json
        domain = data.get('domain', 'example.com')
        email = (data.get('email') or '').strip()
        # Solo aceptar correo con formato válido; si no, Stripe lo pedirá en su página
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            email = ''
        price_amount = data.get('price', 100)  # cents USD
        plan = data.get('plan', 'express')  # express | pro | corporate

        report_id = str(uuid.uuid4())[:8]
        
        # Guardar lead temporalmente
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r') as f:
                leads = json.load(f)
        except:
            leads = []
        
        # Verificar si ya existe
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
        
        with open(leads_file, 'w') as f:
            json.dump(leads, f, indent=2)
        
        logger.info(f"💰 Lead guardado: {email} - {domain} - {report_id}")
        scan_logger.info(f"📡 SCAN INICIADO - Dominio: {domain}, Email: {email}")
        scan_logger.info(f"   - Dominio recibido: {domain}")
        scan_logger.info(f"   - Email recibido: {email}")
        scan_logger.info(f"   - Report ID: {report_id}")
        
        # Crear sesión de Stripe
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
        # Solo fijar el correo si es válido; si no, Stripe lo pedirá en su página
        if email:
            session_params['customer_email'] = email
            session_params['receipt_email'] = email
        session = stripe.checkout.Session.create(**session_params)
        
        logger.info(f"💰 Sesión de Stripe creada: {session.id} para {domain} - {email}")
        scan_logger.info(f"💰 Sesión Stripe creada: {session.id}")
        
        return jsonify({
            'session_id': session.id,
            'url': session.url,
            'report_id': report_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error creando sesión de Stripe: {str(e)}")
        scan_logger.error(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook de Stripe para confirmar pagos"""
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        logger.error(f"❌ Error en webhook (payload inválido): {str(e)}")
        webhook_logger.error(f"❌ Error en webhook (payload inválido): {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Error en webhook (firma inválida): {str(e)}")
        webhook_logger.error(f"❌ Error en webhook (firma inválida): {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Procesar evento
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
        report_id = metadata.get('report_id')
        domain    = metadata.get('domain')
        plan      = metadata.get('plan', 'express')
        session_id = sd.get('id')

        webhook_logger.info(f"💰 WEBHOOK: {customer_email} | {domain} | {report_id}")

        # 1. Guardar status=paid en leads.json INMEDIATAMENTE
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r') as f:
                leads = json.load(f)
        except Exception:
            leads = []

        idx, lead = find_lead_by_email(customer_email, leads)
        if idx is None:
            idx, lead = find_lead_by_report_id(report_id, leads)

        if lead:
            leads[idx]['status']         = 'paid'
            leads[idx]['paid_date']      = datetime.now().isoformat()
            leads[idx]['stripe_session'] = session_id
            leads[idx]['domain']         = domain or lead.get('domain')
            effective_domain = leads[idx]['domain']
            effective_plan   = leads[idx].get('plan', plan)
        else:
            effective_domain = domain or 'unknown'
            effective_plan   = plan
            leads.append({
                'email': customer_email, 'domain': effective_domain,
                'report_id': report_id, 'plan': effective_plan,
                'status': 'paid', 'paid_date': datetime.now().isoformat(),
                'stripe_session': session_id
            })
            idx = len(leads) - 1

        with open(leads_file, 'w') as f:
            json.dump(leads, f, indent=2)

        webhook_logger.info(f"✅ leads.json actualizado a 'paid' para {customer_email}")

        # 2. Generar PDF en background — Stripe recibe 200 ya.
        def _background_work():
            try:
                result   = generate_pdf_with_id(effective_domain, report_id, depth=effective_plan)
                pdf_file = result['pdf_filename']
                pdf_path = result['pdf_path']
                # actualizar leads con pdf_file
                try:
                    with open(leads_file, 'r') as f:
                        ls = json.load(f)
                    for l in ls:
                        if l.get('report_id') == report_id:
                            l['pdf_file'] = pdf_file
                            break
                    with open(leads_file, 'w') as f:
                        json.dump(ls, f, indent=2)
                except Exception:
                    pass
                webhook_logger.info(f"📄 PDF listo: {pdf_file}")
                # Enviar email con el reporte adjunto
                if customer_email:
                    try:
                        send_report_email(customer_email, pdf_path, effective_domain, report_id)
                        webhook_logger.info(f"📧 Email enviado a: {customer_email}")
                    except Exception as e:
                        webhook_logger.error(f"❌ Error enviando email: {e}")
            except Exception as e:
                webhook_logger.error(f"❌ Error en background_work: {e}")

        threading.Thread(target=_background_work, daemon=True).start()

        return jsonify({'status': 'queued', 'report_id': report_id}), 200

    return jsonify({'status': 'ok'}), 200

@app.route('/download/<report_id>')
def download_report(report_id):
    """Descargar PDF por ID"""
    
    # ==========================================
    # LOGGING DE DESCARGA
    # ==========================================
    download_logger.info(f"📥 DESCARGA SOLICITADA - report_id: {report_id}")
    
    pdf_filename = f"REPORT_{report_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    download_logger.info(f"   - Buscando: {pdf_filename}")
    download_logger.info(f"   - Ruta: {os.path.abspath(pdf_path)}")
    
    # Si no existe con ese nombre, buscar en leads.json
    if not os.path.exists(pdf_path):
        download_logger.info(f"   - No encontrado en pdf_reports, buscando en leads.json...")
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r') as f:
                leads = json.load(f)
            
            for lead in leads:
                if lead.get('report_id') == report_id:
                    pdf_file = lead.get('pdf_file')
                    if pdf_file:
                        pdf_path = os.path.join(PDF_DIR, pdf_file)
                        if os.path.exists(pdf_path):
                            pdf_filename = pdf_file
                            download_logger.info(f"   - Encontrado en leads.json: {pdf_file}")
                            break
        except:
            pass
    
    if os.path.exists(pdf_path):
        download_logger.info(f"   - ARCHIVO EXISTE - {pdf_filename}")
        download_logger.info(f"   - Tamaño: {os.path.getsize(pdf_path)} bytes")
        download_logger.info(f"✅ DESCARGA COMPLETADA - {pdf_filename}")
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    
    download_logger.warning(f"   - ARCHIVO NO ENCONTRADO - {pdf_filename}")
    logger.warning(f"❌ PDF no encontrado: {report_id}")
    return jsonify({'error': 'Report not found'}), 404

@app.route('/success/<report_id>')
def success_page(report_id):
    """Página de éxito con descarga automática"""

    # Obtener el PDF correcto
    pdf_file = get_pdf_for_report_id(report_id)

    # Si no existe aún, lanzar generación en background y responder inmediatamente
    if not pdf_file:
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        try:
            with open(leads_file, 'r') as f:
                leads = json.load(f)
        except Exception:
            leads = []
        _, lead = find_lead_by_report_id(report_id, leads)

        domain = (lead.get('domain') if lead else None) or request.args.get('domain', 'unknown')
        plan = (lead.get('plan') if lead else None) or request.args.get('plan', 'express')

        def _gen():
            try:
                generate_pdf_with_id(domain, report_id, depth=plan)
                logger.info(f"📄 PDF generado en background: REPORT_{report_id}.pdf")
            except Exception as e:
                logger.error(f"❌ Error generando PDF en background: {e}")

        threading.Thread(target=_gen, daemon=True).start()

    logger.info(f"📄 PDF SELECCIONADO: {pdf_file}")
    download_logger.info(f"📄 PDF para success: {pdf_file}")
    
    # Si TEMPLATES.html existe, usarlo
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Reemplazar variables
        html_content = html_content.replace('{{ report_id }}', report_id)
        html_content = html_content.replace('{{ pdf_file }}', pdf_file or '')
        
        return html_content, 200, {'Content-Type': 'text/html'}
    
    # Fallback si TEMPLATES.html no existe
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
            .pdf-name {{ color: #00d4ff; font-size: 12px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>✅ ¡PAGO CONFIRMADO!</h1>
            <p style="color:#888;">Tu reporte está listo para descargar</p>
            <a href="/download/{report_id}" class="btn">📥 DESCARGAR REPORTE</a>
            <p class="pdf-name">📄 {pdf_file or 'REPORT_' + report_id + '.pdf'}</p>
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
    """
    Simula el flujo completo sin cobrar ni hacer scan de red.
    Responde en <5 segundos. Uso: /test-payment?email=tu@email.com
    """
    domain    = request.args.get('domain', 'example.com')
    email     = request.args.get('email', 'test@praetor.lat')
    report_id = 'TEST_' + str(uuid.uuid4())[:6]
    results   = {}
    leads_file = os.path.join(BASE_DIR, 'leads.json')

    # PASO 1: Escritura en leads.json
    try:
        try:
            with open(leads_file, 'r') as f:
                leads = json.load(f)
        except Exception:
            leads = []
        leads.append({
            'email': email, 'domain': domain,
            'report_id': report_id, 'plan': 'express',
            'status': 'pending', 'created_at': datetime.now().isoformat()
        })
        with open(leads_file, 'w') as f:
            json.dump(leads, f, indent=2)
        results['1_lead_json'] = 'PASS'
    except Exception as e:
        results['1_lead_json'] = f'FAIL: {e}'

    # PASO 2: Generación de PDF (sin scan — usa reportlab directo)
    pdf_filename = f'REPORT_{report_id}.pdf'
    pdf_path     = os.path.join(PDF_DIR, pdf_filename)
    try:
        from reportlab.pdfgen import canvas as _c
        c = _c.Canvas(pdf_path)
        c.setFont('Helvetica-Bold', 16)
        c.drawString(72, 750, 'PRAETOR Intelligence — Test Report')
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

    # PASO 3: Verificar que /download lo encontraría
    try:
        exists = pdf_path and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100
        results['3_descarga'] = f'PASS — descargable en /download/{report_id}' if exists else 'FAIL: archivo no encontrado'
    except Exception as e:
        results['3_descarga'] = f'FAIL: {e}'

    # PASO 4: Simular webhook (marcar pagado en leads.json)
    try:
        with open(leads_file, 'r') as f:
            leads = json.load(f)
        for lead in leads:
            if lead.get('report_id') == report_id:
                lead['status'] = 'paid'
                lead['paid_date'] = datetime.now().isoformat()
                lead['pdf_file'] = pdf_filename
                break
        with open(leads_file, 'w') as f:
            json.dump(leads, f, indent=2)
        results['4_webhook_sim'] = 'PASS'
    except Exception as e:
        results['4_webhook_sim'] = f'FAIL: {e}'

    # PASO 5: Email — solo si ?email_test=1 (llama directo para ver el error real)
    if request.args.get('email_test') == '1':
        try:
            from email_sender import enviar_reporte_por_email
            ok = enviar_reporte_por_email(email, domain, pdf_path) if (pdf_path and os.path.exists(pdf_path)) else False
            results['5_email'] = 'PASS' if ok else 'FAIL: retornó False'
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
    """
    Called by Render Cron Job daily.
    Re-scans all paid Corporate leads and stores diffs.
    Render Cron Job URL: POST https://praetor-intelligence.onrender.com/cron/monitor
    Protected by CRON_SECRET env var.
    """
    secret = os.getenv('CRON_SECRET', '')
    if secret:
        incoming = request.headers.get('X-Cron-Secret') or request.args.get('secret', '')
        if incoming != secret:
            return jsonify({'error': 'Unauthorized'}), 403

    try:
        from monitor import run_monitor
        leads_file = os.path.join(BASE_DIR, 'leads.json')
        with open(leads_file, 'r') as f:
            leads = json.load(f)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    import traceback
    tb = traceback.format_exc()
    logger.error(f"❌ Error interno: {str(e)}\n{tb}")
    try:
        webhook_logger.error(f"❌ Error interno (500):\n{tb}")
    except Exception:
        pass
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
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
