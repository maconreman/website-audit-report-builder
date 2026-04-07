"""
Step 4: Page Categorization — Service layer.
Ported from: analyze_url_patterns(), suggest_category_for_pattern(),
             build_category_recommendations(), apply_page_categories(),
             finalize_page_categories()
"""

import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse

from backend.config import PREDEFINED_CATEGORIES
from backend.utils.file_helpers import get_output_path, read_csv_safe, save_csv
from backend.session_state import get_session, update_session, mark_step_complete


def run_step4(domain):
    """
    Execute Step 4: Analyze URL patterns and build recommendations.
    Returns recommendations for user approval workflow.
    """
    session = get_session(domain)
    logs = []

    logs.append({"type": "heading", "message": "STEP 4: Assign Page Categories"})

    audit_path = get_output_path(domain, "audit")
    try:
        df_audit = read_csv_safe(audit_path)
    except FileNotFoundError:
        raise FileNotFoundError("Website Audit file not found. Run Steps 2 and 3 first.")

    update_session(domain, {"audit_records": df_audit.to_dict(orient="records")})
    logs.append({"type": "info", "message": f"Loaded Website Audit: {len(df_audit)} rows"})
    logs.append({"type": "info", "message": "Analyzing URL patterns..."})

    recommendations = _build_category_recommendations(df_audit)

    rec_count = len(recommendations)
    logs.append({"type": "info", "message": f"Found {rec_count} URL patterns to review."})

    # Store in session
    update_session(domain, {
        "category_recommendations": recommendations,
        "category_keys": list(recommendations.keys()),
        "current_category_index": 0,
        "category_approvals": {},
    })

    if rec_count == 0:
        # No patterns; finalize immediately
        result = finalize_categories(domain)
        logs.extend(result["logs"])
        return {
            "status": "complete",
            "recommendations": {},
            "keys": [],
            "logs": logs,
            **result,
        }

    # Serialize recommendations for JSON response
    rec_json = {}
    for k, v in recommendations.items():
        rec_json[k] = {
            "suggested_category": v["suggested_category"],
            "url_count": v["url_count"],
            "example_urls": v["example_urls"],
            "pattern_type": v["pattern_type"],
            "pattern_value": v["pattern_value"],
        }

    return {
        "status": "awaiting_approval",
        "recommendations": rec_json,
        "keys": list(recommendations.keys()),
        "total_patterns": rec_count,
        "logs": logs,
    }


def approve_category(domain, pattern_key):
    """Approve a single category recommendation."""
    session = get_session(domain)
    recs = session.get("category_recommendations", {})

    if pattern_key not in recs:
        raise ValueError(f"Unknown pattern key: {pattern_key}")

    rec = recs[pattern_key]
    session["category_approvals"][pattern_key] = rec["suggested_category"]

    return {
        "pattern_key": pattern_key,
        "category": rec["suggested_category"],
        "action": "approved",
    }


def reject_category(domain, pattern_key):
    """Reject (manual check) a single category recommendation."""
    session = get_session(domain)
    recs = session.get("category_recommendations", {})

    if pattern_key not in recs:
        raise ValueError(f"Unknown pattern key: {pattern_key}")

    session["category_approvals"][pattern_key] = "Manual Check"

    return {
        "pattern_key": pattern_key,
        "category": "Manual Check",
        "action": "rejected",
    }


def approve_all_remaining(domain):
    """Approve all remaining unapproved patterns, then finalize."""
    session = get_session(domain)
    recs = session.get("category_recommendations", {})
    approvals = session.get("category_approvals", {})

    count = 0
    for key, rec in recs.items():
        if key not in approvals:
            approvals[key] = rec["suggested_category"]
            count += 1

    session["category_approvals"] = approvals

    result = finalize_categories(domain)
    result["approved_remaining"] = count

    return result


def finalize_categories(domain):
    """
    Apply all approved categories to the dataframe and save.
    Ported from: finalize_page_categories() + apply_page_categories()
    """
    session = get_session(domain)
    logs = []

    audit_records = session.get("audit_records")
    if not audit_records:
        raise ValueError("No audit data in session.")

    df = pd.DataFrame(audit_records)

    # Apply categories
    df = _apply_page_categories(df, session)

    # Summary
    category_counts = df['Page Category'].value_counts().to_dict()

    logs.append({"type": "info", "message": "Page Category Summary:"})
    for category, count in category_counts.items():
        logs.append({"type": "info", "message": f"  {category}: {count} pages"})

    # Update session & documentation
    session["documentation"]["category_approvals"] = dict(session.get("category_approvals", {}))
    session["documentation"]["category_summary"] = category_counts

    update_session(domain, {"audit_records": df.to_dict(orient="records")})

    output_path = get_output_path(domain, "audit")
    save_csv(df, output_path)

    mark_step_complete(domain, 4)

    logs.append({"type": "success", "message": f"Saved: {domain} - Website Audit.csv"})

    return {
        "status": "complete",
        "category_summary": category_counts,
        "rows": len(df),
        "logs": logs,
    }


# --- Internal helpers (ported 1:1 from Colab) ---

def _analyze_url_patterns(df):
    """Analyze URLs to detect page categories. (analyze_url_patterns)"""
    if 'Address' not in df.columns:
        return {}

    pattern_urls = defaultdict(list)

    for url in df['Address'].dropna().unique():
        try:
            parsed = urlparse(str(url))

            subdomain = parsed.netloc.split('.')[0] if parsed.netloc.count('.') > 1 else None
            if subdomain and subdomain not in ['www', 'mail', 'ftp', 'api']:
                pattern_urls[f"subdomain:{subdomain}"].append(url)

            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                first_segment = path_parts[0].lower()
                pattern_urls[f"path:{first_segment}"].append(url)
        except Exception:
            continue

    return pattern_urls


def _suggest_category_for_pattern(pattern):
    """Suggest a category name based on the detected pattern. (suggest_category_for_pattern)"""
    _, pattern_value = pattern.split(':', 1)
    pattern_lower = pattern_value.lower()

    for category, keywords in PREDEFINED_CATEGORIES.items():
        if pattern_lower in keywords:
            return category

    return pattern_lower.replace('-', ' ').replace('_', ' ').title()


def _build_category_recommendations(df):
    """Build category recommendations, excluding pages that already have a category."""
    pattern_urls = _analyze_url_patterns(df)
    recommendations = {}

    # Item 3: If Page Category column exists, find already-categorized URLs
    already_categorized = set()
    if 'Page Category' in df.columns:
        mask = df['Page Category'].fillna('').str.strip() != ''
        mask = mask & (df['Page Category'] != 'Uncategorized')
        already_categorized = set(df.loc[mask, 'Address'].dropna().unique())

    for pattern, urls in pattern_urls.items():
        # Filter out already-categorized URLs
        uncategorized_urls = [u for u in urls if u not in already_categorized]
        if len(uncategorized_urls) >= 1:
            suggested = _suggest_category_for_pattern(pattern)
            recommendations[pattern] = {
                'suggested_category': suggested,
                'url_count': len(uncategorized_urls),
                'example_urls': uncategorized_urls[:3],
                'pattern_type': pattern.split(':')[0],
                'pattern_value': pattern.split(':')[1],
            }

    return dict(sorted(recommendations.items(), key=lambda x: x[1]['url_count'], reverse=True))


def _apply_page_categories(df, session):
    """Apply approved categories to the dataframe."""
    approvals = session.get("category_approvals", {})
    recs = session.get("category_recommendations", {})

    if 'Page Category' not in df.columns:
        df['Page Category'] = 'Uncategorized'

    # Ensure string columns exist and are string type
    for col in ['Nexus Notes', 'Next Action for Nexus']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('').astype(str)

    for pattern_key, category in approvals.items():
        rec = recs.get(pattern_key, {})
        pattern_type = rec.get('pattern_type', '')
        pattern_value = rec.get('pattern_value', '')

        if not pattern_type or not pattern_value:
            continue

        for idx, row in df.iterrows():
            url = str(row.get('Address', ''))
            try:
                parsed = urlparse(url)

                if pattern_type == 'subdomain':
                    subdomain = parsed.netloc.split('.')[0] if parsed.netloc.count('.') > 1 else None
                    if subdomain and subdomain.lower() == pattern_value.lower():
                        if df.at[idx, 'Page Category'] == 'Uncategorized':
                            df.at[idx, 'Page Category'] = category

                elif pattern_type == 'path':
                    path_parts = [p for p in parsed.path.split('/') if p]
                    if path_parts and path_parts[0].lower() == pattern_value.lower():
                        if df.at[idx, 'Page Category'] == 'Uncategorized':
                            df.at[idx, 'Page Category'] = category
            except Exception:
                continue

    # --- Item 5: Manual Check -> Next Action for Nexus ---
    if 'Next Action for Nexus' not in df.columns:
        df['Next Action for Nexus'] = ''

    manual_mask = df['Page Category'] == 'Manual Check'
    df.loc[manual_mask, 'Next Action for Nexus'] = _append_note(
        df.loc[manual_mask, 'Next Action for Nexus'],
        'No category. Manually check the page to determine'
    )

    return df


def _append_note(series, note):
    """Append a note to existing values without overwriting. Uses || delimiter."""
    def append_single(existing):
        existing = str(existing).strip() if pd.notna(existing) else ''
        if not existing:
            return note
        if note in existing:
            return existing
        return existing + ' || ' + note
    return series.apply(append_single)
