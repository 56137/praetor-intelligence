import os
from flask import Response, send_from_directory, request

from app import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EN_DIR = os.path.join(BASE_DIR, "en")


@app.route("/en/")
@app.route("/en")
def english_landing():
    """English-language landing page for international organic search."""
    return send_from_directory(EN_DIR, "index.html")


@app.route("/sitemap.xml")
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://praetor.lat/</loc>
    <xhtml:link rel="alternate" hreflang="es-MX" href="https://praetor.lat/" />
    <xhtml:link rel="alternate" hreflang="en" href="https://praetor.lat/en/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="https://praetor.lat/" />
  </url>
  <url>
    <loc>https://praetor.lat/en/</loc>
    <xhtml:link rel="alternate" hreflang="es-MX" href="https://praetor.lat/" />
    <xhtml:link rel="alternate" hreflang="en" href="https://praetor.lat/en/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="https://praetor.lat/" />
  </url>
</urlset>
"""
    return Response(xml, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = """User-agent: *
Allow: /

Sitemap: https://praetor.lat/sitemap.xml
"""
    return Response(body, mimetype="text/plain")


@app.after_request
def add_language_seo_headers(response):
    """Add canonical, hreflang and a visible language switcher to the two landing pages."""
    if response.status_code != 200:
        return response

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return response

    path = request.path
    if path not in {"/", "/en", "/en/"}:
        return response

    body = response.get_data(as_text=True)

    if path == "/":
        if "hreflang=\"en\"" not in body:
            tags = """\n<link rel=\"canonical\" href=\"https://praetor.lat/\">\n<link rel=\"alternate\" hreflang=\"es-MX\" href=\"https://praetor.lat/\">\n<link rel=\"alternate\" hreflang=\"en\" href=\"https://praetor.lat/en/\">\n<link rel=\"alternate\" hreflang=\"x-default\" href=\"https://praetor.lat/\">\n<meta property=\"og:locale\" content=\"es_MX\">\n<meta property=\"og:locale:alternate\" content=\"en_US\">\n"""
            body = body.replace("</head>", tags + "</head>", 1)
        switcher = """<nav aria-label=\"Language\" style=\"position:fixed;top:14px;right:14px;z-index:9999;display:flex;gap:6px;font:600 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;background:rgba(10,10,10,.88);border:1px solid #222a30;border-radius:999px;padding:7px 9px;backdrop-filter:blur(8px)\"><a href=\"/\" aria-current=\"page\" style=\"color:#e8eef2;text-decoration:none\">ES</a><span style=\"color:#8a949c\">|</span><a href=\"/en/\" style=\"color:#00d4ff;text-decoration:none\">EN</a></nav>"""
    else:
        tags = """\n<link rel=\"canonical\" href=\"https://praetor.lat/en/\">\n<link rel=\"alternate\" hreflang=\"en\" href=\"https://praetor.lat/en/\">\n<link rel=\"alternate\" hreflang=\"es-MX\" href=\"https://praetor.lat/\">\n<link rel=\"alternate\" hreflang=\"x-default\" href=\"https://praetor.lat/\">\n<meta property=\"og:locale\" content=\"en_US\">\n<meta property=\"og:locale:alternate\" content=\"es_MX\">\n"""
        if "<link rel=\"canonical\"" not in body:
            body = body.replace("</head>", tags + "</head>", 1)
        switcher = """<nav aria-label=\"Language\" style=\"position:fixed;top:14px;right:14px;z-index:9999;display:flex;gap:6px;font:600 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;background:rgba(7,9,11,.9);border:1px solid #253038;border-radius:999px;padding:7px 9px;backdrop-filter:blur(8px)\"><a href=\"/\" style=\"color:#98a5ad;text-decoration:none\">ES</a><span style=\"color:#98a5ad\">|</span><a href=\"/en/\" aria-current=\"page\" style=\"color:#00d4ff;text-decoration:none\">EN</a></nav>"""

    if "aria-label=\"Language\"" not in body:
        body = body.replace("<body>", "<body>\n" + switcher, 1)

    response.set_data(body)
    response.headers["Content-Language"] = "es-MX" if path == "/" else "en"
    return response
