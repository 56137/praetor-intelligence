# scripts/praetor_screenshot.py (robusto: retries + ignore_https_errors)
import sys, os, time
from playwright.sync_api import sync_playwright

def capture_site(domain, retries=2, timeout=45000):
    if not domain.startswith('http'):
        url = f"https://{domain}"
    else:
        url = domain
        domain = domain.replace('https://','').replace('http://','').split('/')[0]

    output_dir = "captures"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{domain}.png")

    print(f"[+] Iniciando captura para: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        attempt = 0
        while attempt <= retries:
            try:
                page.set_viewport_size({"width":1280,"height":800})
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                page.screenshot(path=output_path, full_page=True)
                print(f"[✔] Captura guardada con éxito en: {output_path}")
                break
            except Exception as e:
                attempt += 1
                print(f"[✘] Error al capturar {url} (intento {attempt}/{retries}): {e}")
                if attempt > retries:
                    print(f"[✘] Saltando {url} tras {retries} reintentos.")
                else:
                    time.sleep(2)
        try:
            context.close()
            browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python praetor_screenshot.py <dominio.com>")
        sys.exit(1)
    capture_site(sys.argv[1])
