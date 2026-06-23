import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def enviar_reporte_por_email(email_cliente, dominio, pdf_filename):
    """
    Envía el PDF del reporte por email al cliente
    
    Args:
        email_cliente (str): Email del cliente
        dominio (str): Dominio escaneado
        pdf_filename (str): Nombre del archivo PDF
    
    Returns:
        bool: True si se envió correctamente, False si hubo error
    """
    
    print(f"📧 Intentando enviar email a {email_cliente}")
    
    # Configuración del email
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("GMAIL_USER", os.getenv("SMTP_USER", ""))
    SMTP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
    
    print(f"📧 SMTP_USER: {SMTP_USER[:5]}... (oculto)")
    print(f"📧 SMTP_PASSWORD: {'*' * 8 if SMTP_PASSWORD else 'NO_CONFIGURADO'}")
    
    # Si no hay credenciales, modo desarrollo
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"⚠️ [MODO DESARROLLO] Credenciales no configuradas")
        print(f"📧 Email simulado para {email_cliente}")
        print(f"   Asunto: Reporte PRAETOR - {dominio}")
        print(f"   Adjunto: {pdf_filename}")
        return True
    
    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email_cliente
        msg['Subject'] = f"🔒 Reporte de Seguridad PRAETOR - {dominio}"
        
        # Cuerpo del email (HTML)
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">🛡️ PRAETOR Intelligence</h1>
                <p style="margin: 5px 0 0; opacity: 0.8;">Auditoría de Seguridad</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #1a1a2e;">¡Tu reporte está listo!</h2>
                
                <p>Hemos completado el análisis de seguridad para:</p>
                <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #e74c3c;">
                    <strong style="font-size: 20px;">{dominio}</strong>
                </div>
                
                <p style="margin-top: 20px;">
                    El reporte incluye:
                </p>
                <ul style="background: white; padding: 20px; border-radius: 8px;">
                    <li>✅ Análisis de configuración de seguridad</li>
                    <li>✅ Evaluación de riesgos</li>
                    <li>✅ Recomendaciones específicas</li>
                    <li>✅ Plan de acción priorizado</li>
                </ul>
                
                <p>
                    <strong>📎 El PDF está adjunto a este email.</strong>
                </p>
                
                <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    ⏰ Este reporte es válido por 30 días.
                    <br>
                    <small>Si tienes preguntas, responde a este email.</small>
                </div>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                © 2026 PRAETOR Intelligence - Auditoría de Ciberseguridad
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))
        
        # Adjuntar PDF
        pdf_path = os.path.join(os.getcwd(), pdf_filename)
        print(f"📎 Buscando PDF en: {pdf_path}")
        
        if os.path.exists(pdf_path):
            print(f"📎 PDF encontrado: {pdf_path}")
            with open(pdf_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename=Reporte_PRAETOR_{dominio.replace(".", "_")}.pdf'
                )
                msg.attach(part)
            print(f"📎 PDF adjuntado: {pdf_filename}")
        else:
            print(f"❌ PDF no encontrado: {pdf_path}")
            return False
        
        # Enviar email
        print(f"📧 Conectando a SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            print(f"📧 Login con {SMTP_USER}")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print(f"📧 Enviando email...")
            server.send_message(msg)
        
        print(f"✅ Email enviado a {email_cliente}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False