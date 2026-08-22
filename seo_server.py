import os
import re

from pathlib import Path

# Production entrypoint: register all runtime patches and routes here.
from pricing_patch import patch_landing, patch_backend

BASE_DIR = Path(__file__).resolve().parent
patch_landing(BASE_DIR / "landing.html")
patch_landing(BASE_DIR / "en" / "index.html")
patch_backend(BASE_DIR / "app.py")

from flask import Response, redirect, send_file, jsonify, request
from app import app
from scan_target import scan_target

CANONICAL_HOST = "https://www.praetor.lat"
RUNTIME_VERSION = "2026-08-22-scan-v4"


def seo_home():
    path = BASE_DIR / "landing.html"
    with path.open("r", encoding="utf-8") as f:
        html = f.read()
    tags = f'''\n<link rel="canonical" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="es-MX" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="en" href="{CANONICAL_HOST}/en/">\n<link rel="alternate" hreflang="x-default" href="{CANONICAL_HOST}/">\n<meta property="og:locale" content="es_MX">\n<meta property="og:locale:alternate" content="en_US">\n<meta name="praetor-runtime" content="{RUNTIME_VERSION}">\n'''
    html = html.replace("</head>", tags + "</head>", 1)
    return Response(html, status=200, mimetype="text/html")


if "home" in app.view_functions:
    app.view_functions["home"] = seo_home


def _valid_domain(domain: str) -> bool:
    if not domain or len(domain) > 253:
        return False
    return re.match(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$", domain) is not None


@app.route("/scan", methods=["POST"])
def landing_scan():
    payload = request.get_json(silent=True) or {}
    raw_domain = str(payload.get("domain", "")).strip().lower()
    domain = re.sub(r"^https?://", "", raw_domain).split("/", 1)[0]

    if not _valid_domain(domain):
        return jsonify({"error": "Dominio no válido. Usa un formato como empresa.com"}), 400

    try:
        report = scan_target(
            domain,
            resolver_timeout=3.0,
            fast_mode=True,
            depth="express",
        )
        report["ssl_ok"] = not bool((report.get("ssl") or {}).get("error"))
        report["spf_configured"] = bool(report.get("spf"))
        report["dmarc_configured"] = bool(report.get("dmarc"))
        findings = []
        for item in report.get("risk_components", []):
            issue = item.get("issue")
            if issue:
                findings.append(issue)
        for error in report.get("errors", []):
            if error and error not in findings:
                findings.append(error)
        report["key_findings"] = findings
        report["runtime_version"] = RUNTIME_VERSION
        return jsonify(report), 200
    except Exception as exc:
        app.logger.exception("Landing scan failed for %s", domain)
        return jsonify({"error": f"El escaneo falló: {exc}", "runtime_version": RUNTIME_VERSION}), 500


@app.route("/runtime-check", methods=["GET"])
def runtime_check():
    return jsonify({
        "status": "online",
        "runtime_version": RUNTIME_VERSION,
        "scan_endpoint": "/scan",
    }), 200


@app.route("/en")
def english_redirect():
    return redirect("/en/", code=308)


@app.route("/en/")
def english_home():
    return send_file(str(BASE_DIR / "en" / "index.html"), mimetype="text/html")


@app.route("/robots.txt")
def robots():
    return send_file(str(BASE_DIR / "robots.txt"), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    return send_file(str(BASE_DIR / "sitemap.xml"), mimetype="application/xml")
