from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

# Google Tag Manager container used by PRAETOR marketing/analytics.
GTM_ID = 'GTM-T8ZJBWL8'
GTM_HEAD = f'''<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{GTM_ID}');</script>
<!-- End Google Tag Manager -->'''
GTM_BODY = f'''<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_ID}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->'''

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

    # Inject GTM once only. Head script is immediately after <head>; noscript
    # fallback is immediately after <body>, matching Google's placement guidance.
    if f'googletagmanager.com/gtm.js?id={GTM_ID}' not in text:
        text = re.sub(r'<head>\s*', '<head>\n' + GTM_HEAD + '\n', text, count=1, flags=re.IGNORECASE)
    if f'googletagmanager.com/ns.html?id={GTM_ID}' not in text:
        text = re.sub(r'<body>\s*', '<body>\n' + GTM_BODY + '\n', text, count=1, flags=re.IGNORECASE)

    # Normalize visible legacy prices without touching already-correct values.
    replacements = {
        '$99': '$2,999',
        '$1,900': '$2,999',
        '$6,900': '$6,999',
        '$24,900': '$10,999',
        '$3,900': '$3,999',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize checkout amounts only inside buyReport(...) calls.
    text = re.sub(
        r"buyReport\(\s*['\"]express['\"]\s*,\s*\d+\s*\)",
        "buyReport('express',299900)", text,
    )
    text = re.sub(
        r"buyReport\(\s*['\"]pro['\"]\s*,\s*\d+\s*\)",
        "buyReport('pro',699900)", text,
    )
    text = re.sub(
        r"buyReport\(\s*['\"]corporate['\"]\s*,\s*\d+\s*\)",
        "buyReport('corporate',1099900)", text,
    )
    text = re.sub(
        r"buyReport\(\s*['\"]monitoring['\"]\s*,\s*\d+\s*\)",
        "buyReport('monitoring',399900)", text,
    )

    # Keep the four visible cards authoritative even if an older runtime patch changed them.
    text = re.sub(
        r'(<h3>Express</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$2,999', text, count=1,
    )
    text = re.sub(
        r'(<h3>Pro</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$6,999', text, count=1,
    )
    text = re.sub(
        r'(<h3>Corporate</h3>\s*<div class="price">)(?:\$[\d,]+|A medida)',
        r'\1$10,999', text, count=1,
    )
    text = re.sub(
        r'(<h3>Vigilancia</h3>\s*<div class="price">)\$[\d,]+',
        r'\1$3,999', text, count=1,
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

    # Replace the old client-controlled pricing with authoritative server-side prices.
    text = re.sub(
        r"\s*price_amount\s*=\s*data\.get\('price',\s*100\)\s*\n\s*plan\s*=\s*data\.get\('plan',\s*'express'\)",
        "\n        plan = str(data.get('plan', 'express')).lower()\n"
        "        plan_prices = {'express': 299900, 'pro': 699900, 'corporate': 1099900, 'monitoring': 399900}\n"
        "        if plan not in plan_prices:\n"
        "            return jsonify({'error': 'Plan no válido'}), 400\n"
        "        price_amount = plan_prices[plan]",
        text, count=1,
    )

    # Monitoring is the only recurring product.
    text = re.sub(
        r"\s*'unit_amount':\s*price_amount,\s*\n\s*},",
        "                'unit_amount': price_amount,\n"
        "                **({'recurring': {'interval': 'month'}} if plan == 'monitoring' else {}),\n"
        "                },",
        text, count=1,
    )
    text = re.sub(
        r"\s*mode='payment',",
        "            mode=('subscription' if plan == 'monitoring' else 'payment'),",
        text, count=1,
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
