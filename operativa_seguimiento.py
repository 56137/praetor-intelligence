import smtplib
import ssl
import json
import csv
import time
from datetime import datetime, timedelta

# --- CREDENCIALES VALIDADAS ---
SENDER = "tjlovetjgang@gmail.com"
PASSWORD = "tacj cwts bmma ckbz"
REPORTE_DESTINO = "maxesquerra@gmail.com"

def registrar_logistica(email, contrato):
    """Mantiene la persistencia para el seguimiento."""
    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_sig = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    registro = {
        "prospecto": email,
        "ultimo_impacto": fecha_hoy,
        "contrato": contrato,
        "proximo_seguimiento": fecha_sig,
        "estado": "ENVIADO"
    }
    try:
        with open('logistica_seguimiento.json', 'r') as f:
            datos = json.load(f)
    except: datos = []
    datos.append(registro)
    with open('logistica_seguimiento.json', 'w') as f:
        json.dump(datos, f, indent=4)

def operacion_maestra_praetor():
    print("--- PRAETOR INTELLIGENCE: INICIANDO OPERACION AUTONOMA ---")
    contexto = ssl.create_default_context()
    objetivos_logrados = 0
    
    try:
        # 1. EJECUCIÓN MASIVA DESDE PROSPECTOS.CSV
        with open('prospectos.csv', mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as server:
                server.login(SENDER, PASSWORD)
                
                for fila in lector:
                    email_objetivo = fila['email']
                    asunto = f"Subject: ESTRATEGIA PRAETOR - {fila['nombre']}\n\n"
                    cuerpo = f"Operativo iniciado para la industria {fila['industria']}. Sistema listo."
                    
                    server.sendmail(SENDER, email_objetivo, asunto + cuerpo)
                    registrar_logistica(email_objetivo, "Propuesta_Base_15K")
                    objetivos_logrados += 1
                    print(f"[✓] IMPACTO: {email_objetivo}")
                    time.sleep(2) # Seguridad antispam

        # 2. ENVÍO DE REPORTE FINAL A MAX ESQUERRA
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as server:
            server.login(SENDER, PASSWORD)
            asunto_reporte = "Subject: PRAETOR: REPORTE DE OPERACION COMPLETADA\n\n"
            cuerpo_reporte = f"General, la operacion ha finalizado con exito.\nObjetivos impactados: {objetivos_logrados}\nLogistica registrada para seguimiento."
            server.sendmail(SENDER, REPORTE_DESTINO, asunto_reporte + cuerpo_reporte)
            
        print(f"\n[!] OPERACION FINALIZADA. Reporte enviado a {REPORTE_DESTINO}")

    except Exception as e:
        print(f"[!] FALLO EN EL SISTEMA: {e}")

if __name__ == "__main__":
    operacion_maestra_praetor()
    