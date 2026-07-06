import sys
import os
from playwright.sync_api import sync_playwright

def capture_site(domain):
    if not domain.startswith('http'):
        url = f"https://{domain}"
    else:
        url = domain
        domain = domain.replace('https://', '').replace('http://', '').split('/')[0]

    output_dir = "captures"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{domain}.png")

    print(f"[+] Iniciando captura para: {url}")
    with sync_playwright() as p:
        # Lanzamiento del navegador en modo headless
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.set_viewport_size({"width": 1280, "height": 800})
            # Espera hasta 30 segundos a que la red esté inactiva
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=output_path, full_page=True)
            print(f"[✔] Captura guardada con éxito en: {output_path}")
        except Exception as e:
            print(f"[✘] Error al capturar {url}: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python praetor_screenshot.py <dominio.com>")
        sys.exit(1)
    capture_site(sys.argv[1])
