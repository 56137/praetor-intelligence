from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

# Authoritative public pricing. Amounts are MXN cents.
PRICES = {
    'express': 299900,      # MXN 2,999 one-time
    'pro': 699900,          # MXN 6,999 one-time
    'corporate': 1099900,   # MXN 10,999 one-time
    'monitoring': 399900,   # MXN 3,999/month
}


def patch_landing(path: Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8', errors='ignore')
    original = text

    # Normalize visible prices from any of the older versions.
    for old, new in {
        '$99': '$2,999',
        '$1,900': '$2,999',
        '$2,999': '$2,999',
        '$399': '$6,999',
        '$6,900': '$6,999',
        '$6,999': '$6,999',
        '$24,900': '$10,999',
        '$10,999': '$10,999',
        '$3,900': '$3,999',
        '$3,999': '$3,999',
    }.items():
        text = text.replace(old, new)

    # Normalize checkout amounts in the existing landing JS.
    for old, new in {
        '9900)': '299900)',
        '190000)': '299900)',
        '299900)': '299900)',
        '39900)': '699900)',
        '690000)': '699900)',
        '699900)': '699900)',
        '24900)': '1099900)',
        '2490000)': '1099900)',
        '1099900)': '1099900)',
        '3900)': '399900)',
        '390000)': '399900)',
        '399900)': '399900)',
    }.items():
        text = text.replace(old, new)

    # Keep explicit plan cards aligned even if a prior patch changed wording.
    text = re.sub(
        r'(<h3>Express</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$2,999', text, count=1
    )
    text = re.sub(
        r'(<h3>Pro</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$6,999', text, count=1
    )
    text = re.sub(
        r'(<h3>Corporate</h3>\s*<div class="price">)\$[\d,]+|(<h3>Corporate</h3>\s*<div class="price">)A medida',
        lambda m: (m.group(1) or m.group(2)) + '$10,999', text, count=1
    )
    text = re.sub(
        r'(<h3>Vigilancia</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$3,999', text, count=1
    )

    text = re.sub(r'buyReport\([\'\"]express[\'\"],\s*\d+\)', "buyReport('express',299900)", text)
    text = re.sub(r'buyReport\([\'\"]pro[\'\"],\s*\d+\)', "buyReport('pro',699900)", text)
    text = re.sub(r'buyReport\([\'\"]corporate[\'\"],\s*\d+\)', "buyReport('corporate',1099900)", text)
    text = re.sub(r'buyReport\([\'\"]monitoring[\'\"],\s*\d+\)', "buyReport('monitoring',399900)", text)

    if 'startMonitoring()' not in text:
        text = text.replace(
            '<button class="btn btn-ghost" onclick="startMonitoring()">Activar monitoreo</button>',
            '<button class="btn btn-ghost" onclick="startMonitoring()">Activar monitoreo</button>'
        )

    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def patch_backend(path: Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8-sig', errors='ignore')
    original = text

    old = "        price_amount = data.get('price', 100)\n        plan = data.get('plan', 'express')"
    new = (
        "        plan = str(data.get('plan', 'express')).lower()\n"
        "        plan_prices = {'express': 299900, 'pro': 699900, 'corporate': 1099900, 'monitoring': 399900}\n"
        "        if plan not in plan_prices:\n"
        "            return jsonify({'error': 'Plan no válido'}), 400\n"
        "        price_amount = plan_prices[plan]"
    )
    if old in text:
        text = text.replace(old, new, 1)

    text = text.replace(
        "                'unit_amount': price_amount,\n                },",
        "                'unit_amount': price_amount,\n                **({'recurring': {'interval': 'month'}} if plan == 'monitoring' else {}),\n                },",
        1,
    )
    text = text.replace("            mode='payment',", "            mode=('subscription' if plan == 'monitoring' else 'payment'),", 1)

    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


changed = False
for rel in ('landing.html', 'en/index.html'):
    changed |= patch_landing(ROOT / rel)
changed |= patch_backend(ROOT / 'app.py')
print('PRAETOR pricing patch:', 'CHANGED' if changed else 'already synchronized')
