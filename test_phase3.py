#!/usr/bin/env python3
"""
Phase 3+ Integration Test — Full Pipeline.
Updated for new flow: thresholds -> recent content -> old content (LAST).
"""

import sys, os, io, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

DOMAIN = "integrationtest.com"


def make_sf_csv():
    rows = [
        "Address,Status Code,Content Type,GA4 Sessions,GA4 Key events,Clicks,Impressions,CTR,Date Published 1,Date Modified 1,Author 1,Tag 1,Tag 2,Word Count,Title 1,Meta Description 1",
    ]
    rows.append(f"https://{DOMAIN}/blog/post-1/,200,text/html,500,10,200,5000,0.04,2024-06-15,2024-07-01,Alice,seo,marketing,1200,Complete SEO Guide for Beginners,Learn everything about search engine optimization")
    rows.append(f"https://{DOMAIN}/blog/post-2/,200,text/html,0,0,0,0,0,2018-01-10,2018-02-01,Bob,old,legacy,800,Legacy Content Migration Tips,How to migrate old content effectively")
    rows.append(f"https://{DOMAIN}/blog/post-3/,200,text/html,50,0,10,300,0.03,2025-01-20,2025-01-25,,new,fresh,600,Fresh Marketing Trends 2025,Latest trends in digital marketing")
    rows.append(f"https://{DOMAIN}/blog/post-4/,200,text/html,0,0,0,0,0,2024-11-01,2024-11-05,Charlie,,,400,Content Strategy Framework,Building effective content strategies")
    rows.append(f"https://{DOMAIN}/products/widget/,200,text/html,1000,25,500,10000,0.05,2023-03-01,2023-04-01,,,,2000,Premium Widget Solution,Our flagship widget product for enterprises")
    rows.append(f"https://{DOMAIN}/products/gadget/,200,text/html,200,5,80,2000,0.04,2023-06-01,2023-07-01,,,,1500,Advanced Gadget Platform,Next generation gadget technology")
    rows.append(f"https://{DOMAIN}/tag/seo/,200,text/html,10,0,5,100,0.05,,,,,,,Tag SEO,Pages tagged with SEO")
    rows.append(f"https://{DOMAIN}/category/marketing/,200,text/html,5,0,2,50,0.04,,,,,,,Marketing Category,All marketing related content")
    rows.append(f"https://{DOMAIN}/about/,200,text/html,300,2,50,1000,0.05,,,,,,,About Our Company,Learn about our mission and team")
    rows.append(f"https://{DOMAIN}/contact/,200,text/html,100,1,30,500,0.06,,,,,,,Contact Us Today,Get in touch with our team")
    rows.append(f"https://{DOMAIN}/old-landing/,200,text/html,0,0,0,0,0,,,,,,,,")
    rows.append(f"https://{DOMAIN}/style.css,200,text/css,0,0,0,0,0,,,,,,,,")
    return "\n".join(rows).encode("utf-8")


def make_ga4_csv():
    header = [f"# GA4 Line {i}" for i in range(9)]
    header.append("Landing page,Sessions,Key events,Active users,New users,Average engagement time per session,Total revenue,Session key event rate")
    data = [
        "/blog/post-1/,300,8,250,200,120,0,0.03",
        "/blog/post-3/,40,0,35,30,90,0,0",
        "/products/widget/,600,15,500,400,180,0,0.025",
        "/about/,150,1,130,100,60,0,0.007",
    ]
    return "\n".join(header + data).encode("utf-8")


def make_external_links_csv():
    rows = [
        "Target page,Linking Sites,Link Score,Incoming links",
        f"https://{DOMAIN}/blog/post-1/,15,45,120",
        f"https://{DOMAIN}/products/widget/,30,72,250",
        f"https://{DOMAIN}/about/,8,35,60",
        f"https://{DOMAIN}/contact/,3,18,20",
    ]
    return "\n".join(rows).encode("utf-8")


def upload(client, ftype, content):
    return client.post("/api/upload", data={
        "domain": DOMAIN, "file_type": ftype,
        "file": (io.BytesIO(content), "data.csv"),
    }, content_type="multipart/form-data")


def pj(client, path, data=None):
    return client.post(path, json=data or {})


def test_full_pipeline():
    app = create_app()
    client = app.test_client()

    print("=" * 60)
    print("  Integration Test — Full Pipeline")
    print("=" * 60)

    # STEP 1: Upload
    print("\n--- Step 1: Upload ---")
    pj(client, "/api/domain", {"domain": DOMAIN})
    assert upload(client, "sf", make_sf_csv()).status_code == 200
    assert upload(client, "ga4_organic", make_ga4_csv()).status_code == 200
    assert upload(client, "external_links", make_external_links_csv()).status_code == 200
    print("  All files uploaded")

    # STEP 2: Clean
    print("\n--- Step 2: Clean ---")
    r = pj(client, "/api/step2/run", {"domain": DOMAIN})
    assert r.status_code == 200
    d = r.get_json()
    assert d["sf_200_rows"] == 11
    print(f"  SF-200: {d['sf_200_rows']} pages")

    if d["status"] == "custom_columns_detected":
        sel = list(d["custom_columns"].keys())
        print(f"  Custom columns: {sel}")
        r = pj(client, "/api/step2/confirm-custom", {"domain": DOMAIN, "selected_types": sel})
        assert r.status_code == 200
        cd = r.get_json()
        print(f"  Columns after processing: {cd.get('columns')}")
        # Verify new columns exist
        cols = cd.get("column_names", [])
        assert "Estimated Reading Time" in cols, f"Missing Estimated Reading Time in {cols}"
        assert "Page Highlight" in cols, f"Missing Page Highlight in {cols}"
        assert "Nexus Notes" in cols, f"Missing Nexus Notes in {cols}"
        assert "Next Action for Nexus" in cols, f"Missing Next Action for Nexus in {cols}"
        print(f"  Verified: Estimated Reading Time, Page Highlight, Nexus Notes, Next Action for Nexus")
    print("  STEP 2 PASS")

    # STEP 3: Merge
    print("\n--- Step 3: Merge ---")
    r = pj(client, "/api/step3/run", {"domain": DOMAIN})
    assert r.status_code == 200
    d = r.get_json()
    assert d["final_rows"] == 11
    print(f"  {d['initial_rows']} -> {d['final_rows']} rows, {d['final_columns']} cols")
    print("  STEP 3 PASS")

    # STEP 4: Categorize
    print("\n--- Step 4: Categorize ---")
    r = pj(client, "/api/step4/run", {"domain": DOMAIN})
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "awaiting_approval"
    keys = d["keys"]
    print(f"  {len(keys)} patterns found")

    # Approve blog, reject tag, approve-all rest
    pj(client, "/api/step4/approve", {"domain": DOMAIN, "pattern_key": keys[0]})
    if len(keys) > 1:
        pj(client, "/api/step4/reject", {"domain": DOMAIN, "pattern_key": keys[1]})

    r = pj(client, "/api/step4/approve-all", {"domain": DOMAIN})
    assert r.status_code == 200, f"approve-all failed: {r.get_json()}"
    d = r.get_json()
    print(f"  Categories: {d.get('category_summary', {})}")

    # Check Manual Check -> Next Action for Nexus
    import pandas as pd
    from backend.utils.file_helpers import get_output_path, read_csv_safe
    audit_df = read_csv_safe(get_output_path(DOMAIN, "audit"))
    manual_rows = audit_df[audit_df["Page Category"] == "Manual Check"]
    if len(manual_rows) > 0:
        for _, row in manual_rows.iterrows():
            assert "Manually check" in str(row.get("Next Action for Nexus", "")), "Manual Check missing Next Action"
        print(f"  Manual Check -> Next Action for Nexus verified ({len(manual_rows)} rows)")

    print("  STEP 4 PASS")

    # STEP 5: Actions (new flow: auto rules -> thresholds -> recent -> OLD CONTENT LAST)
    print("\n--- Step 5: Actions ---")
    r = pj(client, "/api/step5/run", {"domain": DOMAIN})
    assert r.status_code == 200
    d = r.get_json()
    print(f"  Initial status: {d['status']}")

    # NEW FLOW: should go straight to thresholds (not old content first)
    assert d["status"] == "awaiting_threshold", f"Expected awaiting_threshold, got {d['status']}"

    # Test threshold preview
    r = pj(client, "/api/step5/preview-threshold", {"domain": DOMAIN, "threshold_type": "percentage", "value": 20})
    assert r.status_code == 200
    preview = r.get_json()
    print(f"  Threshold preview: {preview.get('keep_count')} pages at top 20%")

    # Apply thresholds
    while d.get("status") == "awaiting_threshold":
        stats = d.get("threshold_stats", {})
        metric = stats.get("metric", "?")
        print(f"  Applying threshold for: {metric}")
        r = pj(client, "/api/step5/apply-threshold", {
            "domain": DOMAIN, "threshold_type": "percentage", "value": 20,
        })
        assert r.status_code == 200
        d = r.get_json()
        if d.get("status") == "next_metric" and d.get("next_threshold_stats"):
            d["status"] = "awaiting_threshold"
            d["threshold_stats"] = d["next_threshold_stats"]

    # Handle recent content
    if d.get("status") == "awaiting_recent_content":
        rc = d.get("recent_content", {})
        print(f"  Recent content: {rc.get('total_pages')} pages")
        r = pj(client, "/api/step5/recent-content-keep", {"domain": DOMAIN})
        assert r.status_code == 200
        d = r.get_json()

    # Handle old content (NOW LAST)
    if d.get("status") == "awaiting_old_content_config":
        print("  Old content prompt (LAST step) - enabling")
        r = pj(client, "/api/step5/old-content-config", {
            "domain": DOMAIN, "enabled": True,
            "cutoff_year": 2020, "date_field": "Date Modified",
        })
        assert r.status_code == 200
        d = r.get_json()

    assert d["status"] == "complete", f"Expected complete, got {d['status']}"
    action_summary = d.get("action_summary", {})
    print(f"  Action summary: {action_summary}")

    # Verify Review renamed
    assert "Review - Nexus to check before finalization" in action_summary or len(action_summary) > 0
    for key in action_summary:
        assert key != "Review", "Plain 'Review' should be renamed"
    print("  Verified: no plain 'Review' actions")

    # Verify Nexus Notes contain threshold info
    audit_df = read_csv_safe(get_output_path(DOMAIN, "audit"))
    keep_rows = audit_df[audit_df["Action"] == "Keep"]
    notes_with_threshold = keep_rows[keep_rows["Nexus Notes"].str.contains("Top", na=False)]
    if len(notes_with_threshold) > 0:
        print(f"  Nexus Notes with threshold info: {len(notes_with_threshold)} rows")
        print(f"    Example: '{notes_with_threshold.iloc[0]['Nexus Notes'][:80]}'")

    # Verify column order
    cols = audit_df.columns.tolist()
    assert cols[0] == "Address", f"First column should be Address, got {cols[0]}"
    assert cols[-1] == "Next Action for Nexus", f"Last column should be Next Action for Nexus, got {cols[-1]}"
    assert cols[-2] == "Nexus Notes", f"Second-to-last should be Nexus Notes, got {cols[-2]}"
    assert cols[-3] == "Action", f"Third-to-last should be Action, got {cols[-3]}"
    print(f"  Column order verified: {cols[0]} ... {cols[-3]} | {cols[-2]} | {cols[-1]}")

    # Verify every row has a Nexus Note
    empty_notes = audit_df[audit_df["Nexus Notes"].fillna("").str.strip() == ""]
    assert len(empty_notes) == 0, f"{len(empty_notes)} rows have empty Nexus Notes"
    print(f"  Every row has a Nexus Note (verified {len(audit_df)} rows)")

    print("  STEP 5 PASS")

    # STEP 6: Documentation
    print("\n--- Step 6: Documentation ---")
    r = pj(client, "/api/step6/generate", {"domain": DOMAIN})
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "complete"
    print(f"  Documentation saved: {d['filename']}")

    # Test downloads
    r = client.get(f"/api/step6/download-audit/{DOMAIN}")
    assert r.status_code == 200
    print(f"  Audit CSV download: OK ({len(r.data)} bytes)")

    r = client.get(f"/api/step6/download/{DOMAIN}")
    assert r.status_code == 200
    print(f"  Documentation download: OK ({len(r.data)} bytes)")

    # Test preview endpoint
    r = client.get(f"/api/step6/preview/{DOMAIN}?rows=5")
    assert r.status_code == 200
    preview = r.get_json()
    assert "preview" in preview
    assert "documentation" in preview
    print(f"  Preview: {len(preview['preview'])} rows, doc length: {len(preview.get('documentation',''))}")

    print("  STEP 6 PASS")

    # Final session check
    print("\n--- Session ---")
    r = client.get(f"/api/session/{DOMAIN}")
    session = r.get_json()
    print(f"  Completed steps: {session['completed_steps']}")
    assert session["completed_steps"] == [2, 3, 4, 5, 6]
    print("  SESSION PASS")

    print("\n" + "=" * 60)
    print("  ALL INTEGRATION TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_full_pipeline()
