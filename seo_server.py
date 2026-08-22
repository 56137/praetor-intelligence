import os
from flask import Response, redirect, send_file
from app import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CANONICAL_HOST = "https://www.praetor.lat"


def seo_home():
    path = os.path.join(BASE_DIR, "landing.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    tags = f'''\n<link rel="canonical" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="es-MX" href="{CANONICAL_HOST}/">\n<link rel="alternate" hreflang="en" href="{CANONICAL_HOST}/en/">\n<link rel="alternate" hreflang="x-default" href="{CANONICAL_HOST}/en/">\n<meta property="og:locale" content="es_MX">\n<meta property="og:locale:alternate" content="en_US">\n'''
    html = html.replace("</head>", tags + "</head>", 1)
    return Response(html, status=200, mimetype="text/html")

# Replace the existing home handler while leaving the rest of PRAETOR unchanged.
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
