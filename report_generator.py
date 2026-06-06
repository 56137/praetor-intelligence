from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
import os


def generate_report(report: dict) -> str:
    domain = report.get('domain', 'unknown')
    safe_name = domain.replace('.', '_').replace('/', '_')
    filename = f'REPORT_{safe_name}.pdf'
    filepath = os.path.join(os.getcwd(), filename)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, pagesize=letter,
        topMargin=0.5*inch, bottomMargin=0.5*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch)
    elements = []
    h1 = ParagraphStyle('T', parent=styles['Heading1'], fontSize=24,
        textColor=colors.HexColor('#003366'), alignment=TA_CENTER, spaceAfter=12)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13,
        textColor=colors.HexColor('#003366'), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, leading=14)
    elements.append(Paragraph('PRAETOR Intelligence', h1))
    elements.append(Paragraph('Reporte de Auditoria de Seguridad', styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    info = [
        ['Dominio', report.get('domain', '')],
        ['Fecha', report.get('scanned_at', '')[:19].replace('T', ' ') + ' UTC'],
        ['IP', report.get('ip', 'N/A')],
        ['Risk Score', str(report.get('risk_score', 0)) + ' / 95'],
        ['Risk Level', report.get('risk_level', 'Unknown')],
    ]
    t = Table(info, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 6),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph('Hallazgos', h2))
    spf = report.get('spf')
    dmarc = report.get('dmarc')
    ssl = report.get('ssl') or {}
    findings = [
        ['Verificacion', 'Estado', 'Detalle'],
        ['SPF', 'OK' if spf else 'FALTANTE', spf or 'No encontrado'],
        ['DMARC', 'OK' if dmarc else 'FALTANTE', dmarc or 'No encontrado'],
        ['SSL', 'ERROR' if ssl.get('error') else 'OK',
         ssl.get('error') or ssl.get('not_after', 'N/A')],
    ]
    ft = Table(findings, colWidths=[1.5*inch, 1*inch, 4*inch])
    ft.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 6),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(ft)
    recs = report.get('recommendations', [])
    if recs:
        elements.append(Paragraph('Recomendaciones', h2))
        for rec in recs:
            elements.append(Paragraph(
                f"[{rec.get('type','')}] {rec.get('title','')}", h2))
            elements.append(Paragraph(rec.get('description', ''), body))
            elements.append(Paragraph(f"Accion: {rec.get('action','')}", body))
            elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    return filename