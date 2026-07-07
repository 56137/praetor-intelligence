# scripts/check_dns_batch.py (robusto)
import dns.resolver
import pandas as pd
import sys, os
from datetime import datetime

def has_dmarc(domain):
    try:
        answers = dns.resolver.resolve('_dmarc.'+domain, 'TXT', lifetime=5)
        for r in answers:
            txt = ''.join([s.decode() if isinstance(s, bytes) else str(s) for s in getattr(r,'strings',[r])])
            if 'v=DMARC1' in txt.upper():
                return True, txt
    except Exception:
        return False, ''
    return False, ''

def has_mx(domain):
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=5)
        return len(answers) > 0
    except Exception:
        return False

def get_spf(domain):
    try:
        answers = dns.resolver.resolve(domain, 'TXT', lifetime=5)
        for r in answers:
            txt = ''.join([s.decode() if isinstance(s, bytes) else str(s) for s in getattr(r,'strings',[r])])
            if txt.strip().lower().startswith('v=spf1'):
                return True, txt
    except Exception:
        return False, ''
    return False, ''

def process(input_csv, output_csv):
    if not os.path.exists(input_csv):
        print(f"[!] Input CSV not found: {input_csv}. Creating empty output CSV.")
        pd.DataFrame([], columns=['dominio','DMARC','MX','SPF','checked_at']).to_csv(output_csv, index=False)
        return
    df = pd.read_csv(input_csv)
    rows = []
    for _, r in df.iterrows():
        if 'dominio' in r:
            domain = r.get('dominio')
        elif 'domain' in r:
            domain = r.get('domain')
        else:
            domain = r.iloc[0]
        domain = str(domain).strip()
        dmarc, _ = has_dmarc(domain)
        mx = has_mx(domain)
        spf, _ = get_spf(domain)
        r['DMARC'] = 'SI' if dmarc else 'NO'
        r['MX'] = 'SI' if mx else 'NO'
        r['SPF'] = 'SI' if spf else 'NO'
        r['checked_at'] = datetime.utcnow().isoformat()
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(output_csv, index=False)
    print("Saved:", output_csv)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/check_dns_batch.py input.csv output.csv")
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])
