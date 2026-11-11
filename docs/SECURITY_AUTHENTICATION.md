# PRAETOR Authentication and Credential Handling

## Scope

PRAETOR is currently a Flask application served through Gunicorn. It does **not** implement customer accounts, browser sessions, OAuth, or JWT-based user authentication. Access control is route-specific and relies on server-side environment variables, Stripe webhook signature verification, and high-entropy report identifiers.

## Components

| Component | Purpose | Credential boundary |
|---|---|---|
| Flask application (`app.py`) | HTTP routes and business logic | Reads secrets from environment variables |
| Gunicorn | Production WSGI process | No application-user authentication |
| `ADMIN_TOKEN` | Protects `GET /leads` | Bearer token in the Authorization header |
| Stripe Checkout | Collects customer payments | Secret API key stays on the server |
| Stripe webhook | Confirms asynchronous payment events | Validates `Stripe-Signature` using webhook signing secret |
| `CRON_SECRET` | Protects monitoring job | `X-Cron-Secret` request header |
| `report_id` | Identifies a paid report | Random UUID-derived capability identifier |
| CORS allowlist | Restricts browser origins | `CORS_ORIGINS` environment variable |

## Request flows

### 1. Administrative lead access

1. An operator sends `GET /leads`.
2. The server checks that `ADMIN_TOKEN` is configured.
3. The caller must provide `Authorization: Bearer <ADMIN_TOKEN>`.
4. Missing configuration fails closed with HTTP 503; an absent or incorrect token returns HTTP 401.
5. Only then does the route return lead records.

Do not put the admin token in a URL, query string, browser code, issue, or log.

### 2. Checkout and payment confirmation

1. A client submits `POST /create-checkout-session` with a plan and customer information.
2. The server validates the plan and derives the amount from its server-side price table. Client-supplied prices are not authoritative.
3. The server creates a Stripe Checkout Session using `STRIPE_SECRET_KEY` and stores a pending lead with a report identifier.
4. Stripe sends an event to `POST /webhook/stripe`.
5. The application validates the Stripe signature using `STRIPE_WEBHOOK_SECRET`.
6. For a completed Checkout Session, it checks the payment status and report metadata, records the Stripe session against the lead, marks the lead paid, generates the PDF, and sends the report email.
7. Repeated delivery of the same event/session is treated as already processed when the stored Stripe session identifier matches.

The webhook signing secret is not an API key. It is used only to verify that incoming webhook payloads were signed by Stripe.

### 3. Paid report retrieval

1. The customer reaches `/success/<report_id>` after Checkout.
2. The route checks that the report exists in the lead store and has `status = paid`.
3. `/download/<report_id>` repeats the same paid-status check before serving a PDF.
4. The report identifier is generated using a full UUID hex value rather than a short truncated UUID.
5. The PDF filename is reduced to its basename before joining it to the report directory.

The report identifier acts as a capability URL, not as a customer login. Treat it as sensitive and do not publish it.

### 4. Scheduled monitoring

1. Render invokes `POST /cron/monitor`.
2. The request must include `X-Cron-Secret`.
3. If `CRON_SECRET` is missing, the endpoint fails closed with HTTP 503.
4. Incorrect credentials return HTTP 403.

The secret is never accepted through a query parameter.

### 5. Public health and scan routes

- `GET /status` exposes only basic service health and a timestamp.
- `POST /scan` and `GET /runtime-check` are public product routes.
- These public routes do not authenticate a user. The scan endpoint should be protected by rate limiting, request quotas, and abuse monitoring before broad production use.

## Credential handling

Required or optional server-side environment variables include:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `ADMIN_TOKEN`
- `CRON_SECRET`
- `DATABASE_URL`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `OPENAI_API_KEY`
- `CORS_ORIGINS`
- `BASE_URL`

Credentials must be configured in Render's environment-variable settings or a local untracked `.env` file. The repository's `.gitignore` excludes `.env*`, key files, generated reports, logs, and customer/prospect artifacts. Never paste production values into GitHub, documentation, screenshots, or chat.

Rotate any credential that has ever been committed to a public or otherwise untrusted repository. Removing a file from the current tree does not remove it from Git history.

## Known limitations and follow-up work

1. There is no customer identity system or per-user authorization. Paid report IDs are bearer capabilities.
2. The current lead helper reads `leads.json`; `DATABASE_URL` detection alone does not establish that PostgreSQL persistence is implemented. Storage must be consolidated before relying on horizontal scaling.
3. Public scan routes need rate limiting and abuse controls.
4. Webhook processing should ultimately use a durable event-idempotency store and transactional persistence.
5. Operational logs must avoid customer email addresses, report contents, tokens, and payment credentials.
6. The public health endpoint intentionally does not disclose lead counts or revenue counts.

## Production deployment boundary

Render's `praetor-backend` service currently tracks `main`. The `alignerr-audit-readiness` branch is for review and automated checks only. Do not deploy it to production or merge it without reviewing the pull request and passing the test suite.
