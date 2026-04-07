"""
Session state management with JSON file persistence.
Sessions auto-save to disk after each mutation for crash recovery.
"""

import os
import json
from datetime import datetime
from backend.config import OUTPUT_DIR


def _default_state():
    return {
        "domain": "",
        "has_trailing_slash": False,
        "url_prefix": "",
        "sf_200_records": None,
        "audit_records": None,
        "custom_columns_detected": {},
        "category_recommendations": {},
        "category_approvals": {},
        "current_category_index": 0,
        "category_keys": [],
        "action_metrics": ["Landing Page Traffic", "Impressions", "Clicks"],
        "current_metric_index": 0,
        "metric_thresholds": {},
        "old_content_enabled": False,
        "old_content_year": None,
        "old_content_date_field": None,
        "recent_content_actions": {},
        "recent_content_mask_indices": [],
        "completed_steps": [],
        "documentation": {
            "domain": "", "timestamp": "", "sf_200_rows": 0,
            "custom_data_included": [], "custom_data_details": {},
            "ga4_merge_info": {}, "external_links_merge_info": {},
            "category_approvals": {}, "category_summary": {},
            "action_thresholds": {}, "action_summary": {},
            "old_content_settings": {}, "recent_content_override": {},
            "final_row_count": 0, "final_columns": [],
        },
    }


_sessions = {}


def _session_file(domain):
    """Path to session JSON file."""
    folder = os.path.join(OUTPUT_DIR, domain)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, ".session.json")


def _persist(domain):
    """Save session to disk (skip large record fields to keep file small)."""
    if domain not in _sessions:
        return
    try:
        # Save metadata only — not the full dataframe records
        saveable = {}
        for k, v in _sessions[domain].items():
            if k in ("sf_200_records", "audit_records"):
                continue  # Too large; the CSV on disk is the source of truth
            saveable[k] = v
        with open(_session_file(domain), "w") as f:
            json.dump(saveable, f, default=str)
    except Exception:
        pass  # Non-critical; in-memory state is authoritative


def _load_from_disk(domain):
    """Try to load session from disk."""
    path = _session_file(domain)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                saved = json.load(f)
            state = _default_state()
            state.update(saved)
            return state
        except Exception:
            pass
    return None


def get_session(domain):
    clean = _clean_domain(domain)
    if clean not in _sessions:
        # Try loading from disk first
        loaded = _load_from_disk(clean)
        if loaded:
            _sessions[clean] = loaded
        else:
            _sessions[clean] = _default_state()
            _sessions[clean]["domain"] = clean
            _sessions[clean]["documentation"]["domain"] = clean
            _sessions[clean]["documentation"]["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return _sessions[clean]


def reset_session(domain):
    clean = _clean_domain(domain)
    _sessions[clean] = _default_state()
    _sessions[clean]["domain"] = clean
    _persist(clean)
    return _sessions[clean]


def update_session(domain, updates):
    session = get_session(domain)
    session.update(updates)
    _persist(_clean_domain(domain))
    return session


def mark_step_complete(domain, step_number):
    session = get_session(domain)
    if step_number not in session["completed_steps"]:
        session["completed_steps"].append(step_number)
        session["completed_steps"].sort()
    _persist(_clean_domain(domain))
    return session


def is_step_complete(domain, step_number):
    session = get_session(domain)
    return step_number in session["completed_steps"]


def get_session_summary(domain):
    session = get_session(domain)
    return {
        "domain": session["domain"],
        "has_trailing_slash": session["has_trailing_slash"],
        "url_prefix": session["url_prefix"],
        "completed_steps": session["completed_steps"],
        "custom_columns_detected": list(session["custom_columns_detected"].keys()),
        "category_approvals_count": len(session["category_approvals"]),
        "metric_thresholds": session["metric_thresholds"],
        "old_content_enabled": session["old_content_enabled"],
        "documentation": session["documentation"],
    }


def list_sessions():
    return list(_sessions.keys())


def _clean_domain(domain):
    d = domain.strip()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/")[0]
    return d
