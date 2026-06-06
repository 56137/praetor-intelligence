import json
import os

def generar_propuesta_tecnica(cliente, prioridad, potencial):
    # La arquitectura de la propuesta cambia según el potencial financiero
    tarifa_auditoria = potencial * 0.15 # 15% del presupuesto estimado
    
    propuesta = f"""
==========================================================
   PRAETOR INTELLIGENCE: PROPUESTA DE DESPLIEGUE TÁCTICO
==========================================================
OBJETIVO: {cliente}
NIVEL DE PRIORIDAD: {prioridad}
VALOR ESTRATÉGICO ESTIMADO: ${potencial:,} USD

1. AUDITORÍA VULNERABILIDAD AGENTE AI
   - Escaneo de infraestructura técnica para detección de fugas.
   - Optimización de scripts Python para automatización de marketing.

2. CONTENT FLOW AI (SISTEMA AUTÓNOMO)
   - Despliegue de red de agentes para generación de autoridad.
   - Reducción de carga manual operativa en un 40%.

3. CONDICIONES DE OPERACIÓN
   - TARIFA DE ACTIVACIÓN: ${tarifa_auditoria:,.2f} USD
   - TIEMPO DE DESPLIEGUE: 72 horas tras confirmación.

----------------------------------------------------------
ESTADO: PENDIENTE DE FIRMA DIGITAL
==========================================================
"""
    return propuesta

def ejecutar_operacion_c():
    print("--- PRAETOR: GENERANDO BORRADORES DE CIERRE ---")
    
    try:
        with open('campaña_final_praetor.json', 'r', encoding='utf-8') as f:
            leads = json.load(f)
    except:
        print("[!] Error: No se detecta el arsenal de mensajes.")
        return

    # Crear carpeta para contratos si no existe
    if not os.path.exists('CONTRATOS_GENERADOS'):
        os.makedirs('CONTRATOS_GENERADOS')

    for lead in leads:
        # Asignamos un valor de presupuesto según prioridad para la simulación
        presupuesto = 100000 if "ALTA" in lead['prioridad'] else 45000
        
        cuerpo = generar_propuesta_tecnica(lead['nombre'], lead['prioridad'], presupuesto)
        
        nombre_archivo = f"CONTRATOS_GENERADOS/Contrato_{lead['nombre']}.txt"
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(cuerpo)
        
        print(f"[✓] Propuesta de ${presupuesto * 0.15:,.0f} generada para: {lead['nombre']}")

    print(f"\n[!] OPERACIÓN COMPLETADA. Revisa la carpeta 'CONTRATOS_GENERADOS'.")

if __name__ == "__main__":
    ejecutar_operacion_c()
    