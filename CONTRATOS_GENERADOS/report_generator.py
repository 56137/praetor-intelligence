import json
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def generate_report(report):

    filename = f"REPORT_{report['domain']}.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            f"PRAETOR Security Report - {report['domain']}",
            styles["Title"]
        )
    )

    elements.append(Spacer(1,20))

    elements.append(
        Paragraph(
            f"Risk Score: {report['risk_score']}",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            f"Risk Level: {report['risk_level']}",
            styles["Heading2"]
        )
    )

    elements.append(Spacer(1,20))

    elements.append(
        Paragraph(
            "Recommendations",
            styles["Heading1"]
        )
    )

    for rec in report.get("recommendations", []):
        elements.append(
            Paragraph(
                f"<b>{rec['title']}</b><br/>{rec['description']}",
                styles["BodyText"]
            )
        )

    doc.build(elements)

    return filename