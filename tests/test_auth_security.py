import os

import pytest

import app as praetor


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(praetor, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(praetor, "TEMPLATE_FILE", str(tmp_path / "missing-template.html"))
    with praetor.app.test_client() as test_client:
        yield test_client


def test_status_does_not_expose_customer_or_revenue_counts(client, monkeypatch):
    monkeypatch.setattr(
        praetor,
        "db_get_all_leads",
        lambda: (_ for _ in ()).throw(AssertionError("health check must not read leads")),
    )
    response = client.get("/status")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "online"
    assert "lead_count" not in body
    assert "paid_count" not in body
    assert "pdf_count" not in body


def test_leads_fails_closed_when_admin_token_is_missing(client, monkeypatch):
    monkeypatch.setattr(praetor, "ADMIN_TOKEN", "")
    response = client.get("/leads")
    assert response.status_code == 503


def test_leads_rejects_invalid_bearer_token(client, monkeypatch):
    monkeypatch.setattr(praetor, "ADMIN_TOKEN", "expected-secret")
    response = client.get("/leads", headers={"Authorization": "Bearer wrong-secret"})
    assert response.status_code == 401


def test_checkout_fails_closed_without_stripe_secret(client, monkeypatch):
    monkeypatch.setattr(praetor, "STRIPE_SECRET_KEY", "")
    response = client.post("/create-checkout-session", json={"plan": "express"})
    assert response.status_code == 503


def test_webhook_fails_closed_without_signing_secret(client, monkeypatch):
    monkeypatch.setattr(praetor, "STRIPE_WEBHOOK_SECRET", "")
    response = client.post("/webhook/stripe", data="{}")
    assert response.status_code == 503


def test_cron_fails_closed_without_secret_and_rejects_get(client, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    response = client.post("/cron/monitor")
    assert response.status_code == 503
    get_response = client.get("/cron/monitor")
    assert get_response.status_code == 405


def test_download_denies_unpaid_report(client, monkeypatch):
    monkeypatch.setattr(
        praetor,
        "db_get_all_leads",
        lambda: [{"report_id": "a" * 32, "status": "pending", "pdf_file": "paid.pdf"}],
    )
    (tmp_path := __import__("pathlib").Path(praetor.PDF_DIR) / "paid.pdf").write_bytes(b"%PDF-test")
    response = client.get(f"/download/{'a' * 32}")
    assert response.status_code == 404


def test_download_serves_paid_report(client, monkeypatch):
    report_id = "b" * 32
    monkeypatch.setattr(
        praetor,
        "db_get_all_leads",
        lambda: [{"report_id": report_id, "status": "paid", "pdf_file": "paid.pdf"}],
    )
    from pathlib import Path
    (Path(praetor.PDF_DIR) / "paid.pdf").write_bytes(b"%PDF-test")
    response = client.get(f"/download/{report_id}")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"


def test_download_rejects_path_like_report_ids(client):
    response = client.get("/download/../../etc/passwd")
    assert response.status_code in (404, 308)


def test_success_page_denies_unpaid_report(client, monkeypatch):
    report_id = "c" * 32
    monkeypatch.setattr(
        praetor,
        "db_get_all_leads",
        lambda: [{"report_id": report_id, "status": "pending"}],
    )
    response = client.get(f"/success/{report_id}")
    assert response.status_code == 404
