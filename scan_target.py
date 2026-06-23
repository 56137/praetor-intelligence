import argparse
import json
import re
import socket
import ssl
import sys
from datetime import datetime, timezone, timedelta

import dns.exception
import dns.resolver
import requests
import whois
import urllib3
from dateutil.parser import parse as parse_date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── crt.sh Certificate Transparency lookup ─────────────────────────────────

def enumerate_subdomains_ct(domain: str, timeout: float = 8.0) -> dict:
    """
    Queries crt.sh for subdomains registered via Certificate Transparency logs.
    Returns {"subdomains": [...], "error": None|str}
    Only reads public certificate records — never touches the target server.
    """
    result = {"subdomains": [], "error": None}
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "PRAETOR-Scanner/1.0"})
        resp.raise_for_status()
        entries = resp.json()
        seen = set()
        for entry in entries:
            name = entry.get("name_value", "")
            for sub in name.splitlines():
                sub = sub.strip().lower().lstrip("*.")
                if sub and sub != domain and sub.endswith(f".{domain}") and sub not in seen:
                    seen.add(sub)
        result["subdomains"] = sorted(seen)
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ── CVE lookup via NVD API ──────────────────────────────────────────────────

_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)*)")
_SKIP_BANNERS = {"cloudflare", "github.com", "fastly", "amazonaws"}

def _extract_version_from_banner(server_header: str | None, powered_header: str | None) -> dict | None:
    """Returns {"product": ..., "version": ...} or None if no actionable banner."""
    for header in [server_header, powered_header]:
        if not header:
            continue
        lower = header.lower()
        if any(skip in lower for skip in _SKIP_BANNERS):
            return None
        m = _VERSION_RE.search(header)
        if m:
            product = re.split(r"[/\s]", header)[0]
            return {"product": product, "version": m.group(1)}
    return None


def lookup_cves(server_header: str | None, powered_header: str | None,
                nvd_api_key: str | None = None, timeout: float = 8.0) -> dict:
    """
    Queries NVD for CVEs matching the detected server software version.
    Returns {"banner": ..., "cves": [...], "note": ..., "error": None|str}

    IMPORTANT: Banner-based CVE matching is indicative, not conclusive.
    A server may expose an old version string yet have backported patches.
    The caller MUST surface the "REQUIRES MANUAL VERIFICATION" disclaimer in reports.
    """
    result = {"banner": None, "cves": [], "note": None, "error": None}

    info = _extract_version_from_banner(server_header, powered_header)
    if not info:
        result["note"] = "Server does not expose a version string — CVE matching not possible."
        return result

    result["banner"] = f"{info['product']}/{info['version']}"
    keyword = f"{info['product']} {info['version']}"

    try:
        headers = {"User-Agent": "PRAETOR-Scanner/1.0"}
        if nvd_api_key:
            headers["apiKey"] = nvd_api_key
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {"keywordSearch": keyword, "resultsPerPage": 10}
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        cves = []
        for item in data.get("vulnerabilities", []):
            cve = item.get("cve", {})
            cve_id = cve.get("id", "")
            descriptions = cve.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
            metrics = cve.get("metrics", {})
            severity = "UNKNOWN"
            cvss_score = None
            for key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                metric_list = metrics.get(key, [])
                if metric_list:
                    cvss_data = metric_list[0].get("cvssData", {})
                    severity = cvss_data.get("baseSeverity", "UNKNOWN")
                    cvss_score = cvss_data.get("baseScore")
                    break
            cves.append({"id": cve_id, "severity": severity, "score": cvss_score, "description": desc[:200]})
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        cves.sort(key=lambda c: (severity_order.get(c["severity"], 4), -(c["score"] or 0)))
        result["cves"] = cves
        result["note"] = (
            "REQUIRES MANUAL VERIFICATION — version detected from HTTP banner. "
            "Backported patches may fix these CVEs even if the version string matches."
        )
    except Exception as exc:
        result["error"] = str(exc)

    return result

DEFAULT_SUBDOMAINS = [
    "www", "mail", "smtp", "api", "admin", "portal", "secure", "vpn",
    "webmail", "blog", "dev", "test", "beta", "m", "cdn", "ns1", "ns2",
    "ftp", "shop", "support", "docs", "status", "gateway", "services"
]

TECH_PATTERNS = [
    (r"wordpress|wp-content|wp-includes", "WordPress"),
    (r"shopify", "Shopify"),
    (r"woocommerce", "WooCommerce"),
    (r"drupal", "Drupal"),
    (r"joomla", "Joomla"),
    (r"wix.com|wixstatic.com", "Wix"),
    (r"squarespace", "Squarespace"),
    (r"cloudflare", "Cloudflare"),
    (r"google-analytics|gtag\(|ga\(", "Google Analytics"),
    (r"hubspot", "HubSpot"),
    (r"next\.js|nextjs|nextstatic", "Next.js"),
    (r"react", "React"),
    (r"angular", "Angular"),
    (r"vue\.js|vue", "Vue.js"),
    (r"django", "Django"),
    (r"flask", "Flask"),
    (r"express", "Express.js"),
    (r"asp\.net|microsoft-iis", "ASP.NET / IIS"),
    (r"nginx", "NGINX"),
    (r"apache", "Apache"),
    (r"php", "PHP"),
    (r"ruby on rails|rails", "Ruby on Rails"),
    (r"square\.site", "Square"),
    (r"geniuslink|tawk\.to|zendesk|intercom", "Third-party widget")
]

OBSOLETE_TECHS = {
    "WordPress",
    "Drupal",
    "Joomla",
    "ASP.NET / IIS",
    "PHP",
    "Apache"
}


def _is_valid_domain(domain: str) -> bool:
    if len(domain) > 253:
        return False
    pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,}$"
    return re.match(pattern, domain) is not None


def _normalize_whois_value(value):
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    if value is None:
        return None
    return str(value)


def query_whois(domain: str, timeout: float = 5.0) -> dict:
    result = {
        "domain_name": None,
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "name_servers": [],
        "emails": [],
        "status": None,
        "raw": None,
        "error": None
    }
    try:
        record = whois.whois(domain, timeout=timeout)
        result["domain_name"] = _normalize_whois_value(record.domain_name)
        result["registrar"] = _normalize_whois_value(record.registrar)
        result["creation_date"] = _normalize_whois_value(record.creation_date)
        result["expiration_date"] = _normalize_whois_value(record.expiration_date)
        result["name_servers"] = _normalize_whois_value(record.name_servers) or []
        result["emails"] = _normalize_whois_value(record.emails) or []
        result["status"] = _normalize_whois_value(record.status)
        result["raw"] = str(record.text)[:4000] if hasattr(record, "text") else None
    except Exception as exc:
        result["error"] = str(exc)
    return result


def query_ssl(domain: str, timeout: float = 5.0) -> dict:
    result = {
        "subject": None,
        "issuer": None,
        "not_before": None,
        "not_after": None,
        "subject_alt_names": [],
        "protocol": None,
        "cipher": None,
        "error": None
    }
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                result["protocol"] = ssock.version()
                result["cipher"] = ssock.cipher()[0]
                subject = cert.get("subject", [])
                issuer = cert.get("issuer", [])
                result["subject"] = ", ".join([item[0][1] for item in subject if item and item[0][0] == "commonName"])
                result["issuer"] = ", ".join([item[0][1] for item in issuer if item and item[0][0] == "commonName"])
                result["not_before"] = cert.get("notBefore")
                result["not_after"] = cert.get("notAfter")
                san = cert.get("subjectAltName", [])
                result["subject_alt_names"] = [value for _, value in san]
    except Exception as exc:
        result["error"] = str(exc)
    return result


def fetch_http_info(domain: str, timeout: float = 5.0) -> dict:
    info = {
        "url": None,
        "status_code": None,
        "headers": {},
        "server": None,
        "x_powered_by": None,
        "content_type": None,
        "title": None,
        "html": None,
        "error": None
    }
    headers = {"User-Agent": "PRAETOR-Scanner/1.0"}
    for scheme in ["https", "http"]:
        try:
            url = f"{scheme}://{domain}"
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
            info["url"] = response.url
            info["status_code"] = response.status_code
            info["headers"] = {k: v for k, v in response.headers.items()}
            info["server"] = response.headers.get("Server")
            info["x_powered_by"] = response.headers.get("X-Powered-By")
            info["content_type"] = response.headers.get("Content-Type")
            text = response.text
            info["html"] = text
            title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            if title_match:
                info["title"] = title_match.group(1).strip()
            return info
        except requests.RequestException:
            continue
    info["error"] = "Unable to retrieve HTTP page."
    return info


def detect_technologies(headers: dict, html: str) -> list:
    detected = set()
    text = (html or "").lower()
    for pattern, label in TECH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected.add(label)
    server_header = (headers.get("Server", "") or "").lower()
    powered_header = (headers.get("X-Powered-By", "") or "").lower()
    for pattern, label in TECH_PATTERNS:
        if re.search(pattern, server_header, re.IGNORECASE) or re.search(pattern, powered_header, re.IGNORECASE):
            detected.add(label)
    if not detected:
        detected.add("Unknown/Not detected")
    return sorted(detected)


def compute_risk_score(report: dict) -> dict:
    score = 0
    components = []

    if not report.get("spf"):
        score += 20
        components.append({"issue": "Missing SPF", "points": 20})

    if not report.get("dmarc"):
        score += 20
        components.append({"issue": "Missing DMARC", "points": 20})

    ssl_info = report.get("ssl", {}) or {}
    ssl_error = ssl_info.get("error")
    ssl_bad = False
    if ssl_error:
        ssl_bad = True
    else:
        not_after = ssl_info.get("not_after")
        if not_after:
            try:
                expiration = parse_date(not_after)
                if expiration < datetime.now(timezone.utc):
                    ssl_bad = True
                elif expiration - datetime.now(timezone.utc) < timedelta(days=30):
                    ssl_bad = True
            except Exception:
                ssl_bad = False
    if ssl_bad:
        score += 40
        components.append({"issue": "SSL expired or soon expiring", "points": 40})

    obsolete = [tech for tech in report.get("technologies", []) if tech in OBSOLETE_TECHS]
    if obsolete:
        score += 15
        components.append({"issue": "Obsolete technologies detected", "points": 15, "technologies": obsolete})

    if score >= 60:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    report["risk_score"] = score
    report["risk_level"] = level
    report["risk_components"] = components
    
    # Generate recommendations
    report["recommendations"] = generate_recommendations(report)
    
    return report


def generate_recommendations(report: dict) -> list:
    """Generate actionable recommendations based on scan findings."""
    recommendations = []
    
    if not report.get("spf"):
        recommendations.append({
            "type": "High",
            "title": "Configurar SPF",
            "description": "El registro SPF no está configurado. Esto permite que atacantes falsifiquen correos desde su dominio.",
            "action": "Agregue un registro SPF TXT en su DNS con la configuración de sus servidores de correo."
        })
    
    if not report.get("dmarc"):
        recommendations.append({
            "type": "High",
            "title": "Implementar DMARC",
            "description": "La política DMARC no está configurada. Mejora significativamente la protección contra phishing.",
            "action": "Implemente una política DMARC en _dmarc.sudominio.com especificando acciones para correos rechazados."
        })
    
    ssl_info = report.get("ssl", {}) or {}
    if ssl_info.get("error"):
        recommendations.append({
            "type": "High",
            "title": "Verificar Certificado SSL",
            "description": f"Error en certificado SSL: {ssl_info.get('error')}",
            "action": "Verifique que el certificado SSL esté instalado correctamente y sea válido."
        })
    else:
        not_after = ssl_info.get("not_after")
        if not_after:
            try:
                expiration = parse_date(not_after)
                days_until_exp = (expiration - datetime.now(timezone.utc)).days
                if days_until_exp < 0:
                    recommendations.append({
                        "type": "Critical",
                        "title": "Certificado SSL Expirado",
                        "description": f"El certificado SSL venció hace {abs(days_until_exp)} días.",
                        "action": "Renueve el certificado SSL inmediatamente."
                    })
                elif days_until_exp < 30:
                    recommendations.append({
                        "type": "High",
                        "title": "SSL Vencerá Pronto",
                        "description": f"El certificado SSL vencerá en {days_until_exp} días.",
                        "action": "Renueve el certificado SSL en los próximos días."
                    })
            except Exception:
                pass
    
    # Check for obsolete technologies
    obsolete = [tech for tech in report.get("technologies", []) if tech in OBSOLETE_TECHS]
    if obsolete:
        recommendations.append({
            "type": "Medium",
            "title": "Tecnologías Obsoletas Detectadas",
            "description": f"Se detectaron tecnologías obsoletas: {', '.join(obsolete)}",
            "action": "Considere actualizar a versiones modernas para mejorar seguridad."
        })
    
    # If no major issues, add positive recommendation
    if not recommendations:
        recommendations.append({
            "type": "Low",
            "title": "Configuración Adecuada",
            "description": "El dominio tiene una configuración de seguridad de correo adecuada.",
            "action": "Continúe monitoreando la seguridad regularmente."
        })
    
    return recommendations


def has_wildcard_dns(domain: str, resolver: dns.resolver.Resolver) -> bool:
    trial = f"{int(datetime.now(timezone.utc).timestamp())}.wildcard.{domain}"
    try:
        resolver.resolve(trial, "A")
        return True
    except dns.exception.DNSException:
        return False


def enumerate_subdomains(domain: str, resolver: dns.resolver.Resolver) -> list:
    found = []
    wildcard = has_wildcard_dns(domain, resolver)
    for label in DEFAULT_SUBDOMAINS:
        subdomain = f"{label}.{domain}"
        try:
            answers = resolver.resolve(subdomain, "A")
            for answer in answers:
                ip_address = answer.to_text()
                found.append({"subdomain": subdomain, "ip": ip_address})
        except dns.exception.DNSException:
            continue
    if wildcard and found:
        return [{"note": "Wildcard DNS detected; subdomain results may be unreliable."}] + found
    return found


def scan_target(domain: str, resolver_timeout: float = 3.0, fast_mode: bool = True,
                depth: str = "express", nvd_api_key: str | None = None) -> dict:
    """
    depth values:
      "express"   — base scan (SSL, headers, DNS/SPF/DMARC, tech detection)
      "pro"       — express + CT subdomain enumeration + CVE lookup
      "corporate" — pro + WHOIS + subdomain DNS brute-force
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = resolver_timeout
    resolver.lifetime = resolver_timeout * 2

    depth = depth.lower()

    report = {
        "domain": domain,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "depth": depth,
        "ip": None,
        "mx": [],
        "txt": [],
        "spf": None,
        "dmarc": None,
        "whois": {},
        "ssl": {},
        "http": {},
        "technologies": [],
        "subdomains": [],
        "ct_subdomains": [],
        "cves": {},
        "errors": []
    }

    try:
        ip = socket.gethostbyname(domain)
        report["ip"] = ip
    except socket.gaierror as e:
        report["errors"].append(f"DNS resolution error: {e}")
        return report

    try:
        mx_records = resolver.resolve(domain, "MX")
        for mx in mx_records:
            report["mx"].append({"exchange": str(mx.exchange).rstrip('.'), "preference": int(mx.preference)})
    except dns.exception.DNSException as e:
        report["errors"].append(f"MX lookup error: {e}")

    try:
        txt_records = resolver.resolve(domain, "TXT")
        for txt in txt_records:
            text = txt.to_text().strip('"')
            report["txt"].append(text)
            if "v=spf1" in text.lower() and report["spf"] is None:
                report["spf"] = text
        if report["spf"] is None:
            report["errors"].append("No SPF record found")
    except dns.exception.DNSException as e:
        report["errors"].append(f"TXT lookup error: {e}")

    try:
        dmarc_domain = f"_dmarc.{domain}"
        dmarc_records = resolver.resolve(dmarc_domain, "TXT")
        for txt in dmarc_records:
            text = txt.to_text().strip('"')
            report["dmarc"] = text
    except dns.exception.DNSException:
        report["errors"].append("No DMARC record found")

    # WHOIS: express skips it (slow), corporate always fetches it
    if depth == "corporate" or not fast_mode:
        report["whois"] = query_whois(domain, timeout=3.0)
        if report["whois"].get("error"):
            report["errors"].append(f"WHOIS lookup error: {report['whois']['error']}")

    report["ssl"] = query_ssl(domain, timeout=4.0)
    if report["ssl"].get("error"):
        report["errors"].append(f"SSL lookup error: {report['ssl']['error']}")

    report["http"] = fetch_http_info(domain, timeout=4.0)
    if report["http"].get("error"):
        report["errors"].append(report["http"]["error"])

    report["technologies"] = detect_technologies(
        report["http"].get("headers", {}), report["http"].get("html", "")
    )

    # DNS brute-force subdomains: pro and corporate
    if depth in ("pro", "corporate"):
        report["subdomains"] = enumerate_subdomains(domain, resolver)

    # Certificate Transparency subdomains: pro and corporate
    if depth in ("pro", "corporate"):
        ct = enumerate_subdomains_ct(domain)
        if ct.get("error"):
            report["errors"].append(f"CT lookup error: {ct['error']}")
        else:
            report["ct_subdomains"] = ct["subdomains"]

    # CVE lookup: pro and corporate
    if depth in ("pro", "corporate"):
        http_info = report.get("http", {})
        cve_result = lookup_cves(
            server_header=http_info.get("server"),
            powered_header=http_info.get("x_powered_by"),
            nvd_api_key=nvd_api_key,
        )
        if cve_result.get("error"):
            report["errors"].append(f"CVE lookup error: {cve_result['error']}")
        report["cves"] = cve_result

    report = compute_risk_score(report)

    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="PRAETOR — DNS, WHOIS y surface audit")
    parser.add_argument("--domain", "-d", required=False, help="Dominio objetivo (ej. empresa.com)")
    parser.add_argument("--output", "-o", help="Guardar reporte JSON en archivo")
    parser.add_argument("--timeout", "-t", type=float, default=3.0, help="Timeout DNS en segundos")

    args = parser.parse_args(argv)

    if not args.domain:
        try:
            args.domain = input("Ingresa el dominio objetivo (ej. empresa.com): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Cancelado.")
            sys.exit(1)

    domain = args.domain.lower().strip()
    if not _is_valid_domain(domain):
        print("Dominio no válido. Use un formato como: ejemplo.com")
        sys.exit(2)

    report = scan_target(domain, resolver_timeout=args.timeout)

    print(f"\n[+] REPORTE TÁCTICO - {domain}")
    print("=" * 50)
    print(f"IP: {report.get('ip')}")
    print(f"MX: {len(report.get('mx', []))} registros")
    print(f"SPF: {report.get('spf') or 'none'}")
    print(f"DMARC: {report.get('dmarc') or 'none'}")
    print(f"WHOIS registrar: {report['whois'].get('registrar')}")
    print(f"SSL issuer: {report['ssl'].get('issuer')}")
    print(f"HTTP server: {report['http'].get('server')}")
    print(f"Technologies: {', '.join(report.get('technologies', []))}")
    print(f"Subdomains: {len(report.get('subdomains', []))}")
    print(f"Risk score: {report.get('risk_score', 0)} ({report.get('risk_level', 'Unknown')})")
    if report.get("errors"):
        print("Errors:")
        for e in report["errors"]:
            print(f"  - {e}")
    print("=" * 50)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)
            print(f"Reporte guardado en: {args.output}")
        except Exception as e:
            print(f"Error guardando reporte: {e}")


if __name__ == "__main__":
    main()
