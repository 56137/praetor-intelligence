"""PRAETOR Stripe TEST-only configuration.

No secrets are stored here. These IDs belong to the Stripe TEST account only.
"""

STRIPE_TEST_ACCOUNT = "acct_1TeX3LLnvxqSkKBI"

STRIPE_TEST_PRICES = {
    "express": {
        "price_id": "price_1UBHRlLnvxqSkKBIC5WHqwKC",
        "amount_mxn": 2999,
        "mode": "payment",
    },
    "pro": {
        "price_id": "price_1UBHRsLnvxqSkKBIEhzQH5hJ",
        "amount_mxn": 6999,
        "mode": "payment",
    },
    "corporate": {
        "price_id": "price_1UBHRwLnvxqSkKBIwzr5uOvm",
        "amount_mxn": 10999,
        "mode": "payment",
    },
    "monitoring": {
        "price_id": "price_1UBHS1LnvxqSkKBIjbugr64M",
        "amount_mxn": 3999,
        "mode": "subscription",
    },
}
