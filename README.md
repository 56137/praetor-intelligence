# PRAETOR Intelligence

## Authoritative pricing

| Plan | Price | Billing |
|---|---:|---|
| Express | MXN $2,999 | One-time |
| Pro | MXN $6,999 | One-time |
| Corporate | MXN $10,999 | One-time |
| Vigilancia / Monitoring | MXN $3,999 | Monthly subscription |

Checkout amounts are defined server-side in `app.py`; client-submitted prices are not authoritative.


## Security and authentication

See [docs/SECURITY_AUTHENTICATION.md](docs/SECURITY_AUTHENTICATION.md) for the authentication components, request flows, credential handling, and current security boundaries.

## Development checks

Run the test suite locally:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
python -m compileall -q app.py seo_server.py scan_target.py
```

The `alignerr-audit-readiness` branch runs these checks through GitHub Actions. Production remains connected to `main`.
