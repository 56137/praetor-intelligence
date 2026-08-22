"""HTTP scan endpoint used by the PRAETOR landing page."""

import re
from flask import jsonify, request

from app import app
from scan_target import scan_target


def _valid_domain(domain: str) -> bool:
    if not domain or len(domain) > 253:
        return False
    return re.match(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$", domain) is not None


@app.route("/scan", methods=["POST"])
def landing_scan():
    """Run the free Express surface scan used by landing.html."""
    payload = request.get_json(silent=True) or {}
    raw_domain = str(payload.get("domain", "")).strip().lower()
    domain = re.sub(r"^https?://", "", raw_domain).split("/", 1)[0]

    if not _valid_domain(domain):
        return jsonify({"error": "Dominio no válido. Usa un formato como empresa.com"}), 400

    try:
        report = scan_target(domain, depth="express", fast_mode=True, resolver_timeout=3.0)
        report["ssl_ok"] = not bool((report.get("ssl") or {}).get("error"))
        report["spf_configured"] = bool(report.get("spf"))
        report["dmarc_configured"] = bool(report.get("dmarc"))
        report["key_findings"] = []

        for item in report.get("risk_components", []):
            issue = item.get("issue")
            if issue:
                report["key_findings"].append(issue)
        for error in report.get("errors", []):
            if error and error not in report["key_findings"]:
                report["key_findings"].append(error)

        return jsonify(report), 200
    except Exception as exc:
        return jsonify({"error": f"El escaneo falló: {exc}"}), 500
