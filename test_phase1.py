#!/usr/bin/env python3
"""
Phase 1 Verification Script.
Run this to confirm all modules import correctly and the app starts.

Usage:
    python test_phase1.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    print("Testing imports...")

    from backend.config import (
        UPLOAD_DIR, OUTPUT_DIR, PREDEFINED_CATEGORIES,
        METRIC_COLUMNS, CUSTOM_COLUMN_PATTERNS, SF_BASE_COLUMNS,
    )
    print(f"  config.py               OK  ({len(PREDEFINED_CATEGORIES)} predefined categories)")

    from backend.session_state import (
        get_session, reset_session, update_session,
        mark_step_complete, is_step_complete, get_session_summary,
    )
    print("  session_state.py        OK")

    from backend.utils.url_helpers import (
        extract_url_prefix, normalize_url_for_matching,
        normalize_trailing_slash, contains_tag_or_category,
    )
    print("  utils/url_helpers.py    OK")

    from backend.utils.data_helpers import (
        detect_custom_columns, combine_multiple_columns,
        format_date_column, clean_reading_time,
        fill_blank_metrics_with_zero, get_numeric_value,
    )
    print("  utils/data_helpers.py   OK")

    from backend.utils.file_helpers import (
        clean_domain, get_domain_upload_folder, get_file_path,
        save_upload, list_domain_files,
    )
    print("  utils/file_helpers.py   OK")

    from backend.app import create_app
    print("  app.py                  OK")

    return True


def test_url_helpers():
    print("\nTesting URL helpers...")

    from backend.utils.url_helpers import (
        extract_url_prefix, normalize_url_for_matching,
        normalize_trailing_slash, contains_tag_or_category,
    )

    # extract_url_prefix
    assert extract_url_prefix("https://example.com/blog/post") == "https://example.com"
    print("  extract_url_prefix      PASS")

    # normalize_url_for_matching
    assert normalize_url_for_matching("https://www.Example.COM/Blog/") == "https://example.com/blog"
    assert normalize_url_for_matching("https://example.com/page/") == "https://example.com/page"
    assert normalize_url_for_matching(None) == ""
    print("  normalize_url           PASS")

    # normalize_trailing_slash
    assert normalize_trailing_slash("https://example.com/page", True) == "https://example.com/page/"
    assert normalize_trailing_slash("https://example.com/page/", False) == "https://example.com/page"
    assert normalize_trailing_slash("https://example.com/page/", True) == "https://example.com/page/"
    print("  normalize_trailing      PASS")

    # contains_tag_or_category
    assert contains_tag_or_category("https://example.com/tag/python") == True
    assert contains_tag_or_category("https://example.com/category/tech") == True
    assert contains_tag_or_category("https://example.com/blog/post") == False
    print("  contains_tag_or_cat     PASS")

    return True


def test_data_helpers():
    print("\nTesting data helpers...")

    from backend.utils.data_helpers import get_numeric_value, clean_reading_time
    import pandas as pd

    # get_numeric_value
    assert get_numeric_value(42) == 42.0
    assert get_numeric_value("1,234") == 1234.0
    assert get_numeric_value("50%") == 50.0
    assert get_numeric_value("") == 0
    assert get_numeric_value(None) == 0
    assert get_numeric_value(pd.NA) == 0
    print("  get_numeric_value       PASS")

    # clean_reading_time
    assert clean_reading_time("  5  min  ") == "5 min"
    assert clean_reading_time(None) is None
    assert clean_reading_time("") is None
    print("  clean_reading_time      PASS")

    return True


def test_session_state():
    print("\nTesting session state...")

    from backend.session_state import (
        get_session, reset_session, mark_step_complete, is_step_complete,
        get_session_summary, list_sessions,
    )

    # Create session
    session = get_session("test-domain.com")
    assert session["domain"] == "test-domain.com"
    print("  get_session             PASS")

    # Mark steps
    mark_step_complete("test-domain.com", 2)
    assert is_step_complete("test-domain.com", 2) == True
    assert is_step_complete("test-domain.com", 3) == False
    print("  mark_step_complete      PASS")

    # Summary
    summary = get_session_summary("test-domain.com")
    assert summary["domain"] == "test-domain.com"
    assert 2 in summary["completed_steps"]
    print("  get_session_summary     PASS")

    # List sessions
    sessions = list_sessions()
    assert "test-domain.com" in sessions
    print("  list_sessions           PASS")

    # Reset
    reset_session("test-domain.com")
    assert is_step_complete("test-domain.com", 2) == False
    print("  reset_session           PASS")

    return True


def test_file_helpers():
    print("\nTesting file helpers...")

    from backend.utils.file_helpers import clean_domain, get_domain_upload_folder, get_file_path

    # clean_domain
    assert clean_domain("https://www.example.com/path") == "www.example.com"
    assert clean_domain("example.com") == "example.com"
    print("  clean_domain            PASS")

    # get_domain_upload_folder
    folder, domain = get_domain_upload_folder("example.com")
    assert folder is not None
    assert domain == "example.com"
    assert os.path.exists(folder)
    print("  get_domain_upload_folder PASS")

    # get_file_path
    path = get_file_path("example.com", "sf")
    assert path.endswith("example.com - SF.csv")
    print("  get_file_path           PASS")

    return True


def test_flask_app():
    print("\nTesting Flask app...")

    from backend.app import create_app

    app = create_app()
    client = app.test_client()

    # Health check
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "running"
    print("  GET /                   PASS")

    # API status
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    print("  GET /api/status         PASS")

    # Set domain
    resp = client.post("/api/domain", json={"domain": "test.com"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["domain"] == "test.com"
    print("  POST /api/domain        PASS")

    # List files (empty)
    resp = client.get("/api/files/test.com")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["domain"] == "test.com"
    print("  GET /api/files          PASS")

    # Session info
    resp = client.get("/api/session/test.com")
    assert resp.status_code == 200
    print("  GET /api/session        PASS")

    # Upload (missing file — should return 400)
    resp = client.post("/api/upload", data={"domain": "test.com", "file_type": "sf"})
    assert resp.status_code == 400
    print("  POST /api/upload (err)  PASS")

    # Step 2 now returns 400 for missing domain (no longer a stub)
    resp = client.post("/api/step2/run", json={})
    assert resp.status_code == 400
    print("  POST /api/step2/run     PASS (400 — no domain)")

    # Step 2 returns 404 when SF file is missing
    resp = client.post("/api/step2/run", json={"domain": "test.com"})
    assert resp.status_code == 404
    print("  POST /api/step2/run     PASS (404 — no SF file)")

    # Step 3 returns 404 when audit file is missing
    resp = client.post("/api/step3/run", json={"domain": "noexist.com"})
    assert resp.status_code == 404
    print("  POST /api/step3/run     PASS (404 — no audit file)")

    # Step 6 download returns 404 when no docs generated
    resp = client.get("/api/step6/download/test.com")
    assert resp.status_code == 404
    print("  GET /api/step6/download PASS (404 — no docs)")

    return True


if __name__ == "__main__":
    print("=" * 55)
    print("  Phase 1 Verification Tests")
    print("=" * 55)
    print()

    all_passed = True
    tests = [
        test_imports,
        test_url_helpers,
        test_data_helpers,
        test_session_state,
        test_file_helpers,
        test_flask_app,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            print(f"\n  FAILED: {e}")
            all_passed = False

    print()
    print("=" * 55)
    if all_passed:
        print("  ALL TESTS PASSED — Phase 1 is ready!")
    else:
        print("  SOME TESTS FAILED — check errors above")
    print("=" * 55)
