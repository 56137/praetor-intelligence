"""Production startup wrapper for PRAETOR.

The current app.py contains a partially completed PostgreSQL migration and
references helper functions that are not present in the repository.  This
module supplies safe file-backed compatibility helpers so the service can
boot while the persistent database migration is completed separately.
"""

import json
import os

from seo_server import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(BASE_DIR, "leads.json")


def _load_leads():
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _save_leads(leads):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)


def db_get_all_leads():
    """Compatibility storage until PostgreSQL helpers are implemented."""
    return _load_leads()


def _use_db():
    """Report whether a real DB backend is active.

    The current repository does not contain the DB helper implementation, so
    DATABASE_URL alone must not make the app claim PostgreSQL is active.
    """
    return False


def find_lead_by_email(email, leads):
    if not email:
        return None, None
    target = email.strip().lower()
    for idx, lead in enumerate(leads):
        if str(lead.get("email", "")).strip().lower() == target:
            return idx, lead
    return None, None


def find_lead_by_report_id(report_id, leads):
    if not report_id:
        return None, None
    for idx, lead in enumerate(leads):
        if lead.get("report_id") == report_id:
            return idx, lead
    return None, None


def get_pdf_for_report_id(report_id):
    leads = _load_leads()
    for lead in leads:
        if lead.get("report_id") == report_id:
            return lead.get("pdf_file") or f"REPORT_{report_id}.pdf"
    return f"REPORT_{report_id}.pdf"


# Inject the missing helpers into the already-created Flask module.
import app as _app_module

_app_module.db_get_all_leads = db_get_all_leads
_app_module._use_db = _use_db
_app_module.find_lead_by_email = find_lead_by_email
_app_module.find_lead_by_report_id = find_lead_by_report_id
_app_module.get_pdf_for_report_id = get_pdf_for_report_id
