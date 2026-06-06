#!/usr/bin/env python3
"""Generate cold outreach templates for 20 prospects"""

import json
from datetime import datetime

# Load prospects
with open('prospectos_ensenada.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

prospects = data['prospectos']

# Templates
output = []
output.append("=" * 80)
output.append("PLANTILLAS DE PROSPECCIÓN - PRAETOR INTELLIGENCE")
output.append("=" * 80)
output.append(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
output.append("")

for i, prospect in enumerate(prospects, 1):
    output.append("\n" + "=" * 80)
    output.append(f"PROSPECTO #{i} - PRIORIDAD: {prospect['prioridad']}")
    output.append("=" * 80)
    output.append(f"Empresa: {prospect['empresa']}")
    output.append(f"Sector: {prospect['sector']}")
    output.append(f"Tipo: {prospect['tipo']}")
    output.append(f"Email: {prospect['contacto']}")
    output.append(f"Caso de Uso: {prospect['razon_contacto']}")
    output.append("")
    
    # EMAIL TEMPLATE
    output.append("📧 PLANTILLA EMAIL:")
    output.append("-" * 80)
    
    if prospect['prioridad'] == 'Crítica':
        asunto_prefix = "🔒 URGENTE: Auditoría de Seguridad"
    elif prospect['prioridad'] == 'Alta':
        asunto_prefix = "✓ Auditoría de Seguridad"
    else:
        asunto_prefix = "Auditoría de Seguridad"
    
    email_body = f"""Asunto: {asunto_prefix} para {prospect['empresa'].split()[0]}

Hola,

¿Sabes si tu dominio ({prospect['empresa'].split()[0].lower()}.mx) está protegido contra suplantación de identidad y phishing?

En {prospect['empresa']}, manejan información sensible de clientes. Sin SPF/DMARC configurado correctamente, un atacante puede enviar correos falsos desde tu dominio, causando:

✗ Pérdida de confianza con clientes
✗ Cumbre de regulaciones (GDPR, SAT, LGPD)
✗ Costo de breach: $100,000+

Ofrecemos auditoría de seguridad en 5 segundos:
✓ Score de riesgo (0-95)
✓ Validación SPF/DMARC/SSL
✓ Recomendaciones de remediación
✓ Reporte ejecutivo en PDF

💰 PRECIO ESPECIAL: {prospect['empresa'].split()[0]}, por ser cliente prioritario ofrecemos 50% off en primer escaneo.

¿Te interesa una auditoría rápida y gratuita? Respondé este email o contactame por WhatsApp.

Saludos,
PRAETOR Intelligence
Threat Intelligence & Seguridad
"""
    
    output.append(email_body)
    
    # WHATSAPP TEMPLATE
    output.append("\n📱 PLANTILLA WHATSAPP:")
    output.append("-" * 80)
    
    whatsapp_body = f"""Hola 👋

Vimos que {prospect['empresa']} opera en el sector {prospect['sector'].lower()}.

¿Sabés que sin SPF/DMARC correctamente configurado, tu dominio está expuesto a suplantación de identidad?

En 5 segundos podemos hacer una auditoría de seguridad de tu infraestructura email:
✓ Score de riesgo (0-95)
✓ Detecta vulnerabilidades SPF/DMARC/SSL
✓ Recomendaciones automáticas

50% off en primer escaneo para clientes prioritarios 🎁

¿Podemos agendar una llamada de 10 min? 📞

PRAETOR Intelligence
"""
    
    output.append(whatsapp_body)
    
    # NOTES
    output.append("\n📝 NOTAS DE SEGUIMIENTO:")
    output.append("-" * 80)
    output.append(f"• Razón contacto: {prospect['razon_contacto']}")
    output.append(f"• Caso de uso: {prospect['caso_uso']}")
    output.append(f"• Presión: {prospect['prioridad']}")
    output.append(f"• Próximo seguimiento: +3 días (si no responde)")
    output.append("")

# Save to file
output_file = "PLANTILLAS_PROSPECCIÓN.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f"✅ Plantillas generadas: {output_file}")
print(f"📄 Total: {len(prospects)} templates (email + WhatsApp)")

# Also create a quick reference CSV for tracking
import csv
csv_file = "prospectos_seguimiento.csv"
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['#', 'Empresa', 'Sector', 'Email', 'Teléfono', 'Prioridad', 'Caso Uso', 'Contactado', 'Respuesta', 'Cierre'])
    for i, p in enumerate(prospects, 1):
        writer.writerow([
            i,
            p['empresa'],
            p['sector'],
            p['contacto'],
            p['telefono'],
            p['prioridad'],
            p['caso_uso'],
            '',  # Contactado (fecha)
            '',  # Respuesta (sí/no)
            '',  # Cierre (nota)
        ])

print(f"📊 Tracker de seguimiento: {csv_file}")
print(f"\n🚀 PRÓXIMOS PASOS:")
print(f"   1. Copia PRAETOR_DEMO.pdf y envía por WhatsApp")
print(f"   2. Usa plantillas de PLANTILLAS_PROSPECCIÓN.txt")
print(f"   3. Registra seguimiento en {csv_file}")
print(f"   4. Meta: Primera conversación comercial esta semana")
