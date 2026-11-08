"""Regression tests for PRAETOR's Stripe Checkout session creation."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app as app_module


class CheckoutSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir_patch = patch.object(app_module, "BASE_DIR", self.temp_dir.name)
        self.base_dir_patch.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.base_dir_patch.stop()
        self.temp_dir.cleanup()

    def test_express_checkout_uses_dashboard_payment_method_configuration(self):
        fake_session = SimpleNamespace(
            id="cs_test_express_123",
            url="https://checkout.stripe.com/c/pay/cs_test_express_123",
        )

        with patch.object(
            app_module.stripe.checkout.Session,
            "create",
            return_value=fake_session,
        ) as create_session:
            response = self.client.post(
                "/create-checkout-session",
                json={
                    "domain": "example.com",
                    "email": "buyer@example.com",
                    "plan": "express",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["session_id"], fake_session.id)
        self.assertEqual(payload["url"], fake_session.url)

        kwargs = create_session.call_args.kwargs
        self.assertNotIn("payment_method_types", kwargs)
        self.assertEqual(kwargs["mode"], "payment")
        self.assertEqual(kwargs["line_items"][0]["price_data"]["currency"], "mxn")
        self.assertEqual(kwargs["line_items"][0]["price_data"]["unit_amount"], 299900)
        self.assertEqual(kwargs["metadata"]["plan"], "express")

    def test_monitoring_checkout_keeps_subscription_pricing(self):
        fake_session = SimpleNamespace(
            id="cs_test_monitoring_123",
            url="https://checkout.stripe.com/c/pay/cs_test_monitoring_123",
        )

        with patch.object(
            app_module.stripe.checkout.Session,
            "create",
            return_value=fake_session,
        ) as create_session:
            response = self.client.post(
                "/create-checkout-session",
                json={
                    "domain": "example.com",
                    "email": "buyer@example.com",
                    "plan": "monitoring",
                },
            )

        self.assertEqual(response.status_code, 200)
        kwargs = create_session.call_args.kwargs
        self.assertNotIn("payment_method_types", kwargs)
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(
            kwargs["line_items"][0]["price_data"]["recurring"],
            {"interval": "month"},
        )
        self.assertEqual(kwargs["line_items"][0]["price_data"]["unit_amount"], 399900)

    def test_unknown_plan_is_rejected_without_calling_stripe(self):
        with patch.object(
            app_module.stripe.checkout.Session,
            "create",
        ) as create_session:
            response = self.client.post(
                "/create-checkout-session",
                json={
                    "domain": "example.com",
                    "email": "buyer@example.com",
                    "plan": "not-a-plan",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Plan no válido")
        create_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
