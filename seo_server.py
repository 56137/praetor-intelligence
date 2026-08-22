import os

# The production Procfile runs `seo_server:app`, so runtime patches and routes
# must be registered here before exposing the Flask app.
from pricing_patch import patch_landing, patch_backend

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
patch_landing(os.path.join(BASE_DIR, "landing.html"))
patch_landing(os.path.join(BASE_DIR, "en", "index.html"))
patch_backend(os.path.join(BASE_DIR, "app.py"))

from flask import Response, redirect, send_file
from app import app

# Register the landing scanner endpoint on the production app.
import scan_routes  # noqa: F401,E402

CANONICAL_HOST = "https://www.praetor.lat"


def seo_home():
    path = os.path.join(BASE_DIR, "landing.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    tags = f'''\n<link rel="canonical" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="es-MX" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="en" href="{CANONICAL_HOST}/en/">\n<link rel="alternate" hreflang="x-default" href="{CANONICAL_HOST}/">\n<meta property="og:locale" content="es_MX">\n<meta property="og:locale:alternate" content="en_US">\n'''
    html = html.replace("</head>", tags + "</head>", 1)
    return Response(html, status=200, mimetype="text/html")


if "home" in app.view_functions:
    app.view_functions["home"] = seo_home


@app.route("/en")
def english_redirect():
    return redirect("/en/", code=308)


@app.route("/en/")
def english_home():
    return send_file(os.path.join(BASE_DIR, "en", "index.html"), mimetype="text/html")


@app.route("/robots.txt")
def robots():
    return send_file(os.path.join(BASE_DIR, "robots.txt"), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    return send_file(os.path.join(BASE_DIR, "sitemap.xml"), mimetype="application/xml")
