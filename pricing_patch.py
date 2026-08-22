from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

# Authoritative public pricing, matching the active Stripe prices shown in the dashboard.
PRICES = {
    'express': 190000,      # MXN 1,900 one-time
    'pro': 690000,          # MXN 6,900 one-time
    'corporate': 2490000,   # MXN 24,900 one-time
    'monitoring': 390000,   # MXN 3,900/month
}


def patch_landing(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8', errors='ignore')
    original = text

    replacements = {
        '$99': '$1,900',
        '$1,900': '$1,900',
        '$2,999': '$1,900',
        '$399': '$6,900',
        '$6,900': '$6,900',
        '$6,999': '$6,900',
        '$24,900': '$24,900',
        '$10,999': '$24,900',
        '$3,900': '$3,900',
        '$3,999': '$3,900',
        '9900)': '190000)',
        '299900)': '190000)',
        '39900)': '690000)',
        '699900)': '690000)',
        '24900)': '2490000)',
        '1099900)': '2490000)',
        '3900)': '390000)',
        '399900)': '390000)',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Corporate is a paid tier at the active Stripe price.
    text = re.sub(
        r'(<h3>Corporate</h3>\s*<div class="price">)(?:A medida|\$24,900|\$10,999)(?:\s*<small>[^<]*</small>)?',
        r'\1$24,900 <small>MXN / reporte</small>',
        text,
        count=1,
    )
    text = text.replace(
        '<button class="btn btn-ghost" onclick="contactSales()">Solicitar info</button>',
        '<button class="btn btn-ghost" onclick="buyReport(\'corporate\',2490000)">Comprar Corporate</button>',
        1,
    )

    # Ensure a recurring monitoring tier exists in the source used at runtime.
    if 'startMonitoring()' not in text:
        marker = '      <div class="tier">\n        <div class="tag">PRÓXIMAMENTE</div>'
        if marker in text:
            monitoring = '''      <div class="tier">\n        <div class="tag">RECURRENTE</div>\n        <h3>Vigilancia</h3>\n        <div class="price">$3,900 <small>MXN / mes</small></div>\n        <ul>\n          <li>Reescaneo mensual automático</li>\n          <li>Alerta ante cambios de configuración</li>\n          <li>Nuevos subdominios y CVEs detectados</li>\n          <li>Informe comparativo mes a mes</li>\n          <li>Prioridad en soporte</li>\n        </ul>\n        <button class="btn btn-ghost" onclick="startMonitoring()">Activar monitoreo</button>\n      </div>\n'''
            text = text.replace(marker, monitoring + marker, 1)

    if 'function startMonitoring()' not in text:
        handler = '''\nfunction startMonitoring(){\n  if(!lastDomain){ alert('Primero escanea un dominio.'); return; }\n  if(!lastEmail || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(lastEmail)){\n    const e=(prompt('Escribe un correo válido para el monitoreo:')||'').trim();\n    if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(e)){ alert('Correo inválido.'); return; }\n    lastEmail=e;\n  }\n  buyReport('monitoring',390000);\n}\n'''
        text = text.replace('</script>', handler + '</script>', 1)

    text = text.replace('DESCARGAR REPORTE COMPLETO — $99 MXN', 'DESCARGAR REPORTE COMPLETO — $1,900 MXN')
    text = text.replace('DESCARGAR REPORTE COMPLETO — $2,999 MXN', 'DESCARGAR REPORTE COMPLETO — $1,900 MXN')
    text = text.replace("buyReport()", "buyReport('express',190000)", 1)

    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def patch_backend(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8-sig', errors='ignore')
    original = text

    old = "        price_amount = data.get('price', 100)\n        plan = data.get('plan', 'express')"
    new = "        plan = str(data.get('plan', 'express')).lower()\n        plan_prices = {'express': 190000, 'pro': 690000, 'corporate': 2490000, 'monitoring': 390000}\n        if plan not in plan_prices:\n            return jsonify({'error': 'Plan no válido'}), 400\n        price_amount = plan_prices[plan]"
    text = text.replace(old, new, 1)

    # Recurring price_data for monitoring.
    text = text.replace(
        "                'unit_amount': price_amount,\n                },",
        "                'unit_amount': price_amount,\n                    **({'recurring': {'interval': 'month'}} if plan == 'monitoring' else {}),\n                },",
        1,
    )
    text = text.replace("            mode='payment',", "            mode=('subscription' if plan == 'monitoring' else 'payment'),", 1)

    marker = "        plan = session.get('metadata', {}).get('plan', 'express')\n        session_id = session.get('id')"
    if marker in text and "Monitoring subscription checkout completed" not in text:
        text = text.replace(
            marker,
            marker + "\n        if plan == 'monitoring':\n            logger.info(f'✅ Monitoring subscription checkout completed: {session_id}')\n            return jsonify({'status': 'success', 'plan': plan}), 200",
            1,
        )

    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


changed = False
for rel in ('landing.html', 'en/index.html'):
    changed |= patch_landing(ROOT / rel)
changed |= patch_backend(ROOT / 'app.py')
print('PRAETOR pricing patch:', 'CHANGED' if changed else 'already synchronized')
