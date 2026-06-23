from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from datetime import datetime
import os


_TEAL = colors.HexColor('#00838f')
_RED = colors.HexColor('#cc0000')
_ORANGE = colors.HexColor('#ff6600')
_GREEN = colors.HexColor('#007700')
_GREY = colors.HexColor('#666666')
_LIGHT_GREY = colors.HexColor('#888888')


def _severity_color(severity: str):
    s = (severity or "").upper()
    if s == "CRITICAL":
        return _RED
    if s == "HIGH":
        return _ORANGE
    if s in ("MEDIUM", "LOW"):
        return _GREEN
    return _LIGHT_GREY


def generate_report(report: dict, output_path: str | None = None) -> str:
    """
    Generate a PDF from a scan_target() result dict.
    Returns the path to the generated PDF.

    report keys consumed:
      domain, scanned_at, depth, risk_score, risk_level, risk_components,
      ssl, spf, dmarc, mx, technologies, subdomains, ct_subdomains, cves,
      recommendations, errors, whois, http
    """
    domain = report.get("domain", "unknown")
    depth = (report.get("depth") or "express").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_path is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"REPORT_{domain}_{timestamp}.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("title", parent=styles["Heading1"], fontSize=22,
        textColor=_TEAL, spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold")
    subtitle_s = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=11,
        textColor=_GREY, spaceAfter=12, alignment=TA_CENTER)
    h2_s = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
        textColor=_TEAL, spaceAfter=6, spaceBefore=12, fontName="Helvetica-Bold")
    body_s = ParagraphStyle("body", parent=styles["Normal"], fontSize=9,
        textColor=colors.black, spaceAfter=4, leading=13)
    mono_s = ParagraphStyle("mono", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#333333"), spaceAfter=3, fontName="Courier", leading=11)
    warn_s = ParagraphStyle("warn", parent=styles["Normal"], fontSize=8,
        textColor=_ORANGE, spaceAfter=4, leading=11)
    footer_s = ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
        textColor=_GREY, alignment=TA_CENTER)

    def h2(text):
        return [HRFlowable(width="100%", thickness=0.5, color=_TEAL, spaceAfter=2),
                Paragraph(text, h2_s)]

    def row(label, value, style=body_s):
        return Paragraph(f"<b>{label}:</b> {value or '—'}", style)

    elements = []

    # ── Header ──────────────────────────────────────────────────────────────
    elements.append(Paragraph("PRAETOR INTELLIGENCE", title_s))
    elements.append(Paragraph(f"Security Report — {domain}", subtitle_s))
    elements.append(Paragraph(
        f"Scanned: {report.get('scanned_at', 'N/A')} &nbsp;|&nbsp; Depth: {depth.upper()}",
        subtitle_s))

    # ── Risk score ──────────────────────────────────────────────────────────
    score = report.get("risk_score")
    level = report.get("risk_level", "Unknown")
    if isinstance(score, (int, float)):
        if score < 30:
            sc, sc_color = f"{score}/100", _GREEN
        elif score < 60:
            sc, sc_color = f"{score}/100", _ORANGE
        else:
            sc, sc_color = f"{score}/100", _RED
    else:
        sc, sc_color = "N/A", _LIGHT_GREY

    score_s = ParagraphStyle("score", parent=styles["Normal"], fontSize=18,
        textColor=sc_color, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4)
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(f"Risk Score: {sc} — {level}", score_s))

    components = report.get("risk_components") or []
    for comp in components:
        elements.append(Paragraph(
            f"  ▸ {comp['issue']} (+{comp['points']} pts)", warn_s))

    # ── DNS & Email security ─────────────────────────────────────────────────
    elements += h2("DNS &amp; Email Security")
    elements.append(row("IP", report.get("ip")))
    mx_list = report.get("mx") or []
    mx_str = ", ".join(r.get("exchange", "") for r in mx_list) if mx_list else "none"
    elements.append(row("MX records", mx_str))
    elements.append(row("SPF", report.get("spf") or "<b style='color:red'>NOT CONFIGURED</b>"))
    elements.append(row("DMARC", report.get("dmarc") or "<b style='color:red'>NOT CONFIGURED</b>"))

    # ── SSL certificate ──────────────────────────────────────────────────────
    elements += h2("SSL / TLS Certificate")
    ssl_info = report.get("ssl") or {}
    if ssl_info.get("error"):
        elements.append(Paragraph(f"Error: {ssl_info['error']}", warn_s))
    else:
        elements.append(row("Issuer", ssl_info.get("issuer")))
        elements.append(row("Valid until", ssl_info.get("not_after")))
        elements.append(row("Protocol", ssl_info.get("protocol")))
        elements.append(row("Cipher", ssl_info.get("cipher")))

    # ── HTTP & Technologies ──────────────────────────────────────────────────
    elements += h2("HTTP &amp; Technologies")
    http_info = report.get("http") or {}
    elements.append(row("Server", http_info.get("server")))
    elements.append(row("X-Powered-By", http_info.get("x_powered_by")))
    elements.append(row("Page title", http_info.get("title")))
    techs = report.get("technologies") or []
    elements.append(row("Detected stack", ", ".join(techs) if techs else "Not detected"))

    # ── Subdomains (Pro / Corporate) ─────────────────────────────────────────
    if depth in ("pro", "corporate"):
        elements += h2("Subdomains")

        ct_subs = report.get("ct_subdomains") or []
        if ct_subs:
            elements.append(Paragraph(
                f"<b>Certificate Transparency logs ({len(ct_subs)} found):</b>", body_s))
            for sub in ct_subs[:30]:
                elements.append(Paragraph(f"  • {sub}", mono_s))
            if len(ct_subs) > 30:
                elements.append(Paragraph(f"  … and {len(ct_subs) - 30} more", body_s))
        else:
            elements.append(Paragraph("No subdomains found in CT logs.", body_s))

        dns_subs = report.get("subdomains") or []
        dns_subs = [s for s in dns_subs if isinstance(s, dict) and "subdomain" in s]
        if dns_subs:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(
                f"<b>DNS resolution ({len(dns_subs)} resolved):</b>", body_s))
            for s in dns_subs[:20]:
                elements.append(Paragraph(f"  • {s['subdomain']} → {s['ip']}", mono_s))

    # ── CVEs (Pro / Corporate) ───────────────────────────────────────────────
    if depth in ("pro", "corporate"):
        cve_data = report.get("cves") or {}
        elements += h2("CVE Candidates")
        if cve_data.get("note"):
            elements.append(Paragraph(cve_data["note"], warn_s))
        cve_list = cve_data.get("cves") or []
        if cve_list:
            for cve in cve_list:
                sev_color = _severity_color(cve.get("severity", ""))
                sev_s = ParagraphStyle(f"sev_{cve['id']}", parent=body_s,
                    textColor=sev_color)
                score_str = f" (CVSS {cve['score']})" if cve.get("score") else ""
                elements.append(Paragraph(
                    f"<b>{cve['id']}</b> — {cve.get('severity','?')}{score_str}", sev_s))
                if cve.get("description"):
                    elements.append(Paragraph(cve["description"], mono_s))
        else:
            elements.append(Paragraph("No CVEs matched for detected banner.", body_s))

    # ── Recommendations ──────────────────────────────────────────────────────
    elements += h2("Recommendations")
    recs = report.get("recommendations") or []
    for rec in recs:
        if isinstance(rec, dict):
            rtype = rec.get("type", "Info")
            rc = _severity_color(rtype) if rtype in ("Critical", "High") else _TEAL
            rs = ParagraphStyle(f"rec_{rtype}", parent=body_s, textColor=rc)
            elements.append(Paragraph(f"<b>[{rtype}] {rec.get('title','')}</b>", rs))
            if rec.get("description"):
                elements.append(Paragraph(rec["description"], body_s))
            if rec.get("action"):
                elements.append(Paragraph(f"Action: {rec['action']}", mono_s))
        else:
            elements.append(Paragraph(f"• {rec}", body_s))

    # ── Errors ───────────────────────────────────────────────────────────────
    errs = report.get("errors") or []
    if errs:
        elements += h2("Scan Notes")
        for err in errs:
            elements.append(Paragraph(f"• {err}", warn_s))

    # ── Footer ───────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.4 * inch))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=_GREY))
    elements.append(Paragraph(
        "This report is confidential. CVE findings require manual verification before remediation.",
        footer_s))
    elements.append(Paragraph("PRAETOR Intelligence — praetor.lat", footer_s))

    doc.build(elements)
    return output_path
