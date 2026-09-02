"""Interactive Stripe TEST checkout harness for PRAETOR.

This file is intentionally test-only. It never writes Stripe secrets to disk.
Run locally with: python tests/stripe_checkout_test_2026_09.py
"""

import getpass
import sys
import uuid

import stripe

from stripe_test_config_2026_09 import STRIPE_TEST_PRICES


def main():
    print("PRAETOR — Stripe TEST checkout")
    print("Plans: express / pro / corporate / monitoring")
    plan = input("Plan: ").strip().lower()
    if plan not in STRIPE_TEST_PRICES:
        raise SystemExit(f"Plan inválido: {plan}")

    secret = getpass.getpass("Stripe TEST secret key (no se mostrará): ").strip()
    if not secret.startswith("sk_test_"):
        raise SystemExit("La clave debe ser una Secret Key de TEST (sk_test_...).")

    stripe.api_key = secret
    cfg = STRIPE_TEST_PRICES[plan]
    domain = input("Dominio de prueba [example.com]: ").strip() or "example.com"
    email = input("Email de prueba: ").strip()
    if not email:
        raise SystemExit("Se requiere un email de prueba.")

    report_id = uuid.uuid4().hex[:8]
    base_url = "http://localhost:5000"

    checkout_args = {
        "line_items": [{"price": cfg["price_id"], "quantity": 1}],
        "mode": cfg["mode"],
        "customer_email": email,
        "success_url": f"{base_url}/success/{report_id}?domain={domain}&plan={plan}",
        "cancel_url": f"{base_url}",
        "metadata": {
            "report_id": report_id,
            "domain": domain,
            "email": email,
            "plan": plan,
            "environment": "test",
        },
    }
    if cfg["mode"] == "payment":
        checkout_args["customer_creation"] = "always"

    session = stripe.checkout.Session.create(**checkout_args)

    print("\nCHECKOUT CREADO")
    print("PLAN:", plan)
    print("REPORT ID:", report_id)
    print("SESSION:", session.id)
    print("URL:", session.url)
    print("\nUsa la tarjeta de prueba 4242 4242 4242 4242 en Checkout.")


if __name__ == "__main__":
    try:
        main()
    except stripe.error.StripeError as exc:
        print("Stripe error:", exc)
        sys.exit(1)
