#!/usr/bin/env python3
import os
import csv
import re
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración de rutas
DOMAINS_FILE = "results/checked_domains.csv"
STATUS_FILE = "results/screenshots_status.csv"
OUTPUT_DIR = "captures"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("results", exist_ok=True)

DOMAIN_REGEX = re.compile(
    r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.'
    r'([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])+$'
)

def validate_domain(domain):
    domain = (domain or "").strip().lower()
    if not domain or "@" in domain or "/" in domain:
        return None
    domain = re.sub(r'^https?://', '', domain)
    if DOMAIN_REGEX.match(domain):
        return domain
    return None

def main():
    # Leer dominios
    domains = []
    if os.path.exists(DOMAINS_FILE):
        with open(DOMAINS_FILE, mode="r", encoding="utf-8") as f:
            sample = f.read(1024)
            f.seek(0)
            if "," in sample:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        domains.append(row[0].strip())
            else:
                domains = [line.strip() for line in f if line.strip()]
    else:
        print(f"[-] No se encontró {DOMAINS_FILE}. Creando lista de prueba.")
        domains = ["google.com", "github.com"]

    # Inicializar CSV de estado
    with open(STATUS_FILE, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dominio", "status", "reason", "screenshot_path", "checked_at"])

    print(f"[+] Iniciando capturas para {len(domains)} dominios...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-gpu"])
        context = browser.new_context(viewport={"width": 1280, "height": 720}, ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(25000)

        for raw_domain in domains:
            domain = validate_domain(raw_domain)
            checked_at = datetime.utcnow().isoformat() + "Z"

            if not domain:
                print(f"[-] Dominio inválido: {raw_domain}")
                with open(STATUS_FILE, mode="a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([raw_domain, "SKIPPED", "Invalid domain", "", checked_at])
                continue

            filename = f"screenshot_{domain}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)
            url = f"http://{domain}"

            success = False
            error_reason = ""

            for attempt in range(1, 3):
                try:
                    print(f"[+] [{attempt}/2] Capturando {url}...")
                    page.goto(url, wait_until="load")
                    page.wait_for_timeout(1000)
                    page.screenshot(path=filepath, full_page=False)
                    success = True
                    break
                except PlaywrightTimeoutError:
                    error_reason = "TimeoutError"
                except Exception as e:
                    error_reason = type(e).__name__
                    url = f"https://{domain}"

            if success:
                print(f"[+] Completado: {domain}")
                status, reason, path = "SUCCESS", "OK", filepath
            else:
                print(f"[-] Falló: {domain} ({error_reason})")
                status, reason, path = "FAILED", error_reason, ""

            with open(STATUS_FILE, mode="a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([domain, status, reason, path, checked_at])

        try:
            context.close()
            browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()