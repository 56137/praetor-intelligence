#!/usr/bin/env python3
"""Generate PRAETOR_DEMO.pdf - Commercial presentation for WhatsApp sharing"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from datetime import datetime

# Output path
pdf_path = "PRAETOR_DEMO.pdf"

# Create PDF
doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                       topMargin=0.5*inch,
                       bottomMargin=0.5*inch,
                       leftMargin=0.75*inch,
                       rightMargin=0.75*inch)

# Container for PDF elements
elements = []

# Styles
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=32,
    textColor=colors.HexColor('#00f3ff'),
    spaceAfter=12,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=16,
    textColor=colors.HexColor('#00f3ff'),
    spaceAfter=10,
    spaceBefore=10,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['Normal'],
    fontSize=11,
    textColor=colors.black,
    spaceAfter=8,
    alignment=TA_LEFT,
    leading=14
)

subtitle_style = ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontSize=13,
    textColor=colors.HexColor('#666666'),
    spaceAfter=6,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

# PAGE 1: TITLE
elements.append(Spacer(1, 0.5*inch))
elements.append(Paragraph("🛡️ PRAETOR INTEL", title_style))
elements.append(Paragraph("Auditoría de Seguridad de Dominios", subtitle_style))
elements.append(Spacer(1, 0.3*inch))
elements.append(Paragraph(
    "Protección de Activos Digitales e IP | En Menos de 5 Segundos",
    ParagraphStyle('SubtitleSmall', parent=styles['Normal'], fontSize=11, 
                   textColor=colors.HexColor('#999999'), alignment=TA_CENTER)
))
elements.append(Spacer(1, 0.8*inch))

# Company stamp
elements.append(Paragraph(
    "<b>PRAETOR Intelligence</b><br/>Threat Intelligence Platform<br/>© 2026",
    ParagraphStyle('Stamp', parent=styles['Normal'], fontSize=10, 
                   textColor=colors.HexColor('#cccccc'), alignment=TA_CENTER)
))

elements.append(PageBreak())

# PAGE 2: PROBLEMA
elements.append(Paragraph("🎯 El Problema", heading_style))
elements.append(Spacer(1, 0.2*inch))

problems = [
    ("Suplantación de Identidad", "Atacantes envían correos falsificados desde su dominio, engañando a clientes y empleados."),
    ("Phishing y Spam", "Sin SPF/DMARC configurado, sus correos legítimos van a spam y se abren puertas para fraudes."),
    ("Pérdida de Reputación", "Un email falso puede destruir años de confianza con clientes y socios comerciales."),
    ("Incumplimiento Normativo", "GDPR, ISO 27001 y regulaciones bancarias EXIGEN validación de infraestructura de correo."),
]

for title, desc in problems:
    elements.append(Paragraph(f"<b>✗ {title}</b>", body_style))
    elements.append(Paragraph(desc, body_style))
    elements.append(Spacer(1, 0.15*inch))

elements.append(Spacer(1, 0.3*inch))
elements.append(Paragraph(
    "<b>La mayoría de empresas NO SABE cuán expuesto está su correo corporativo.</b>",
    ParagraphStyle('Alert', parent=styles['Normal'], fontSize=12, 
                   textColor=colors.HexColor('#ff6600'), fontName='Helvetica-Bold')
))

elements.append(PageBreak())

# PAGE 3: SOLUCIÓN
elements.append(Paragraph("💡 La Solución: PRAETOR", heading_style))
elements.append(Spacer(1, 0.2*inch))

elements.append(Paragraph(
    "Un análisis forense de la superficie de seguridad que identifica vulnerabilidades en 5 segundos:",
    body_style
))
elements.append(Spacer(1, 0.15*inch))

features = [
    ("✓ Configuración SPF", "Validar Sender Policy Framework"),
    ("✓ Política DMARC", "Domain-based Message Authentication & Compliance"),
    ("✓ Certificado SSL/TLS", "Validez, vigencia y protocolo de encriptación"),
    ("✓ Tecnologías Detectadas", "Stack tecnológico y dependencias conocidas"),
    ("✓ Vulnerabilidades", "Exploits documentados en infraestructura"),
    ("✓ Recomendaciones", "Acciones inmediatas de remediación"),
]

for feature, desc in features:
    elements.append(Paragraph(f"<b>{feature}</b><br/><font size=9>{desc}</font>", body_style))
    elements.append(Spacer(1, 0.1*inch))

elements.append(Spacer(1, 0.3*inch))
elements.append(Paragraph(
    "🚀 <b>Resultado: Un Score de Riesgo (0-95) + Recomendaciones de remediación en 1 reporte ejecutivo.</b>",
    ParagraphStyle('Success', parent=styles['Normal'], fontSize=11, 
                   textColor=colors.HexColor('#00aa00'), fontName='Helvetica-Bold')
))

elements.append(PageBreak())

# PAGE 4: PRECIOS
elements.append(Paragraph("💰 Planes Disponibles", heading_style))
elements.append(Spacer(1, 0.2*inch))

# Pricing table
pricing_data = [
    ['Plan', 'Precio USD', 'Precio MXN', 'Incluye'],
    ['EXPRESS', '$29', '$500', 'Escaneo automatizado\nScore de riesgo\nReporte PDF\nRecomendaciones básicas'],
    ['PROFESIONAL', '$99', '$1,500', 'Todo EXPRESS +\nAnálisis WHOIS\nDNS Deep Dive\nDetección de subdominios\nPlan de remediación\n3 consultas email\n30 días panel web'],
    ['CORPORATIVO', '$499+', '$5,000+', 'Todo PROFESIONAL +\nEscaneo multi-dominio\nPentest básico\nConsulta telefónica 1h\nReporte ejecutivo\nSoporte prioritario 30 días'],
]

pricing_table = Table(pricing_data, colWidths=[1.2*inch, 1*inch, 1*inch, 2.3*inch])
pricing_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00f3ff')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f9f9')),
    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
    ('VALIGN', (0, 1), (-1, -1), 'TOP'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
]))

elements.append(pricing_table)
elements.append(Spacer(1, 0.3*inch))

elements.append(Paragraph(
    "<b>🎁 BONUS: 50% off en primer escaneo para los primeros 100 clientes</b>",
    ParagraphStyle('Bonus', parent=styles['Normal'], fontSize=10, 
                   textColor=colors.HexColor('#ff6600'), fontName='Helvetica-Bold')
))

elements.append(PageBreak())

# PAGE 5: VENTAJAS COMPETITIVAS
elements.append(Paragraph("⚡ ¿Por qué PRAETOR?", heading_style))
elements.append(Spacer(1, 0.2*inch))

advantages = [
    ("Velocidad", "3-5 segundos vs 5-15 minutos con herramientas manuales"),
    ("Facilidad", "100% automatizado vs análisis manual complicado"),
    ("Costo", "Accesible ($29-$499) vs honorarios de $1,000+ por auditoría"),
    ("Recomendaciones", "Automáticas y accionables en cada reporte"),
    ("Disponibilidad", "24/7 acceso web, sin horario comercial"),
    ("ROI", "Costo $29 vs costo típico de breach $100,000+"),
]

for adv, detail in advantages:
    elements.append(Paragraph(f"<b>✓ {adv}</b><br/><font size=9>{detail}</font>", body_style))
    elements.append(Spacer(1, 0.12*inch))

elements.append(PageBreak())

# PAGE 6: CONTACTO Y CTA
elements.append(Spacer(1, 1*inch))
elements.append(Paragraph("📞 Contacto", heading_style))
elements.append(Spacer(1, 0.3*inch))

contact_data = [
    ("Email", "ventas@praetor.com"),
    ("WhatsApp", "+52 667 XXX XXXX"),
    ("Web", "www.praetor.com"),
    ("Consultora", "Threat Intelligence & Seguridad Ofensiva"),
]

for label, value in contact_data:
    elements.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
    elements.append(Spacer(1, 0.1*inch))

elements.append(Spacer(1, 0.5*inch))
elements.append(Paragraph(
    "Solicita tu auditoría HOY y empieza a proteger tu dominio.",
    ParagraphStyle('CTA', parent=styles['Normal'], fontSize=12, 
                   textColor=colors.HexColor('#00aa00'), fontName='Helvetica-Bold', alignment=TA_CENTER)
))

# Build PDF
doc.build(elements)

print(f"✅ PDF creado: {pdf_path}")
print(f"📊 Tamaño: {__import__('os').path.getsize(pdf_path) / 1024:.1f} KB")
print(f"📱 Listo para WhatsApp (< 30 segundos)")
