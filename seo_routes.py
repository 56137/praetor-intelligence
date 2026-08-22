import os
from flask import Response, send_from_directory

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
    """Add canonical and hreflang links to the Spanish landing without editing its HTML."""
    if response.status_code == 200 and request_path_is_root(response):
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            body = response.get_data(as_text=True)
            marker = "</head>"
            if marker in body and "hreflang=\"en\"" not in body:
                tags = """\n<link rel=\"canonical\" href=\"https://praetor.lat/\">\n<link rel=\"alternate\" hreflang=\"es-MX\" href=\"https://praetor.lat/\">\n<link rel=\"alternate\" hreflang=\"en\" href=\"https://praetor.lat/en/\">\n<link rel=\"alternate\" hreflang=\"x-default\" href=\"https://praetor.lat/\">\n"""
                response.set_data(body.replace(marker, tags + marker, 1))
    return response


def request_path_is_root(response):
    # Avoid importing request at module load; response context is enough for the root marker.
    try:
        from flask import request
        return request.path == "/"
    except RuntimeError:
        return False
