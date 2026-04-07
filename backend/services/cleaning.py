"""
Step 2: Clean and Process Data — Service layer.
Updated with: first-column extraction for all custom types,
Estimated Reading Time, Page Highlight, date detection warnings.
"""

import re
import math
import pandas as pd

from backend.config import (
    SF_BASE_COLUMNS, SF_RENAME_MAP, GA4_SKIP_ROWS,
)
from backend.utils.url_helpers import (
    extract_url_prefix, normalize_url_for_matching, normalize_trailing_slash,
)
from backend.utils.data_helpers import (
    detect_custom_columns, combine_multiple_columns,
    format_date_column, clean_reading_time, fill_blank_metrics_with_zero,
)
from backend.utils.nlp_helpers import apply_page_highlights, apply_estimated_reading_time
from backend.utils.file_helpers import (
    get_file_path, get_output_path, read_csv_safe, save_csv,
)
from backend.session_state import get_session, update_session, mark_step_complete


def run_step2(domain):
    """Execute Step 2: Load SF crawl, filter to HTML 200, detect custom columns."""
    session = get_session(domain)
    logs = []
    logs.append({"type": "heading", "message": "STEP 2: Clean and Process Data"})

    sf_path = get_file_path(domain, "sf")
    if sf_path is None:
        raise FileNotFoundError("Missing Screaming Frog file. Upload it in Step 1.")
    try:
        df_sf = read_csv_safe(sf_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing file: {domain} - SF.csv. Upload it in Step 1.")

    logs.append({"type": "info", "message": f"Loaded {len(df_sf)} rows from SF crawl"})

    df_sf_200 = df_sf[
        (df_sf['Content Type'].str.contains('text/html', na=False)) &
        (df_sf['Status Code'] == 200)
    ].copy()
    logs.append({"type": "info", "message": f"Filtered to {len(df_sf_200)} HTML pages with 200 status"})

    if len(df_sf_200) == 0:
        raise ValueError("No HTML pages with status 200 found in the SF crawl.")

    sample_url = str(df_sf_200['Address'].iloc[0])
    has_trailing_slash = sample_url.endswith('/')
    url_prefix = extract_url_prefix(sample_url)
    logs.append({"type": "info", "message": f"URL prefix: {url_prefix}, trailing slash: {'Yes' if has_trailing_slash else 'No'}"})

    update_session(domain, {
        "has_trailing_slash": has_trailing_slash,
        "url_prefix": url_prefix,
        "sf_200_records": df_sf_200.to_dict(orient="records"),
    })
    session["documentation"]["sf_200_rows"] = len(df_sf_200)

    detected = detect_custom_columns(df_sf_200)
    # Item 2: Remove Date Published from detected — not treated as custom data
    detected.pop('Date Published', None)
    update_session(domain, {"custom_columns_detected": detected})

    # Check for Date Modified presence
    has_date_modified = 'Date Modified' in detected
    date_warning = None
    if not has_date_modified:
        date_cols = [c for c in df_sf_200.columns if 'date' in c.lower() or 'modified' in c.lower()]
        if not date_cols:
            date_warning = "no_date_detected"

    # Item 2: Auto-select all custom columns — no confirmation step needed
    if detected:
        logs.append({"type": "info", "message": "Custom data auto-detected:"})
        for ct, ci in detected.items():
            logs.append({"type": "info", "message": f"  {ct}: {len(ci['all_columns'])} column(s)"})

    # Always finalize immediately with all detected columns
    all_types = list(detected.keys())
    finalize_result = finalize_sf_200(domain, all_types)
    logs.extend(finalize_result["logs"])

    # Also clean GA4
    ga4_logs = clean_ga4_organic(domain)
    logs.extend(ga4_logs)

    return {
        "status": "complete",
        "sf_200_rows": len(df_sf_200),
        "url_prefix": url_prefix,
        "has_trailing_slash": has_trailing_slash,
        "custom_columns_auto_selected": all_types,
        "date_warning": date_warning,
        "logs": logs,
        **finalize_result,
    }


def confirm_custom_columns(domain, selected_types):
    """Process SF-200 with user-selected custom columns and clean GA4 data."""
    result = finalize_sf_200(domain, selected_types)
    ga4_logs = clean_ga4_organic(domain)
    result["logs"].extend(ga4_logs)
    return result


def finalize_sf_200(domain, selected_types):
    """Complete SF-200 processing with selected custom columns."""
    session = get_session(domain)
    logs = []

    sf_200_records = session.get("sf_200_records")
    if not sf_200_records:
        raise ValueError("No SF-200 data in session. Run Step 2 first.")

    df_sf_200 = pd.DataFrame(sf_200_records)
    detected = session.get("custom_columns_detected", {})

    # Start with base columns
    available_base = [col for col in SF_BASE_COLUMNS if col in df_sf_200.columns]
    result_df = df_sf_200[available_base].copy()
    result_df.rename(columns={k: v for k, v in SF_RENAME_MAP.items() if k in result_df.columns}, inplace=True)

    # --- Process custom columns: FIRST COLUMN with valid value for each row ---
    for custom_type in selected_types:
        if custom_type not in detected:
            continue
        col_info = detected[custom_type]
        all_cols = col_info['all_columns']

        if custom_type == 'Author':
            # First column with Author value per row
            result_df['Author'] = _first_valid_value(df_sf_200, all_cols)
            logs.append({"type": "info", "message": f"  Author: first valid value from {len(all_cols)} column(s)"})

        elif custom_type == 'Date Published':
            result_df['Date Published'] = format_date_column(
                _first_valid_value(df_sf_200, all_cols)
            )
            logs.append({"type": "info", "message": f"  Date Published: first valid date"})

        elif custom_type == 'Date Modified':
            result_df['Date Modified'] = format_date_column(
                _first_valid_value(df_sf_200, all_cols)
            )
            logs.append({"type": "info", "message": f"  Date Modified: first valid date"})

        elif custom_type == 'Tags':
            # Combine all tag columns into comma-separated + count
            combined, counts, _ = combine_multiple_columns(df_sf_200, re.sub(r'\s*\d+$', '', all_cols[0]).strip())
            if combined is not None:
                result_df['Tags'] = combined
                result_df['Tag Count'] = counts
            else:
                result_df['Tags'] = _first_valid_value(df_sf_200, all_cols)
                result_df['Tag Count'] = result_df['Tags'].apply(lambda x: len(str(x).split(',')) if x and str(x).strip() else 0)
            logs.append({"type": "info", "message": f"  Tags: combined {len(all_cols)} column(s) + Tag Count"})

        elif custom_type == 'Categories':
            result_df['Categories'] = _first_valid_value(df_sf_200, all_cols)
            logs.append({"type": "info", "message": f"  Categories: first valid value"})

    # --- Estimated Reading Time (from Word Count) ---
    result_df_with_wc = df_sf_200.copy()
    result_df_with_wc, wc_col = apply_estimated_reading_time(result_df_with_wc)
    if wc_col:
        result_df['Estimated Reading Time'] = result_df_with_wc['Estimated Reading Time'].values
        logs.append({"type": "info", "message": f"  Estimated Reading Time: calculated from '{wc_col}' (Word Count / 200)"})
    else:
        result_df['Estimated Reading Time'] = ''
        logs.append({"type": "info", "message": "  Estimated Reading Time: no Word Count column found"})

    # --- Page Highlight (NLP from Title + Meta Description) ---
    temp_df = df_sf_200.copy()
    temp_df, title_col, meta_col = apply_page_highlights(temp_df)
    result_df['Page Highlight'] = temp_df['Page Highlight'].values
    if title_col or meta_col:
        logs.append({"type": "info", "message": f"  Page Highlight: extracted from '{title_col or 'N/A'}' + '{meta_col or 'N/A'}'"})
    else:
        logs.append({"type": "info", "message": "  Page Highlight: no Title/Meta Description columns found"})

    # --- Initialize Nexus columns ---
    result_df['Nexus Notes'] = ''
    result_df['Next Action for Nexus'] = ''

    # Fill blank metrics
    result_df = fill_blank_metrics_with_zero(result_df)

    # Add normalized address for matching
    result_df['Address_Normalized'] = result_df['Address'].apply(normalize_url_for_matching)

    # Save
    output_path = get_output_path(domain, "audit")
    save_csv(result_df, output_path)

    update_session(domain, {"audit_records": result_df.to_dict(orient="records")})
    session["documentation"]["custom_data_included"] = selected_types
    for ct in selected_types:
        if ct in detected:
            ci = detected[ct]
            session["documentation"]["custom_data_details"][ct] = {
                "columns_combined": len(ci['all_columns']),
                "source_columns": ci['all_columns'],
            }

    mark_step_complete(domain, 2)
    logs.append({"type": "success", "message": f"Saved: {len(result_df)} rows, {len(result_df.columns)} columns"})

    return {
        "rows": len(result_df),
        "columns": len(result_df.columns),
        "column_names": result_df.columns.tolist(),
        "logs": logs,
    }


def _first_valid_value(df, columns):
    """For each row, return the value from the first column that has a non-empty value."""
    def pick_first(row):
        for col in columns:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() != '':
                return str(val).strip()
        return ''
    return df.apply(pick_first, axis=1)


def clean_ga4_organic(domain):
    """Clean GA4 Organic data."""
    session = get_session(domain)
    logs = []
    ga4_path = get_file_path(domain, "ga4_organic")
    if ga4_path is None:
        logs.append({"type": "info", "message": "GA4 Organic file not found, skipping..."})
        return logs
    try:
        df_ga4 = read_csv_safe(ga4_path, skiprows=GA4_SKIP_ROWS)
    except FileNotFoundError:
        logs.append({"type": "info", "message": "GA4 Organic file not found, skipping..."})
        return logs

    logs.append({"type": "info", "message": f"Processing GA4 Organic: {len(df_ga4)} rows"})

    # FIX 1: Guard against url_prefix being None (extract_url_prefix can return None)
    url_prefix = session.get("url_prefix") or ""
    has_trailing_slash = session.get("has_trailing_slash", False)

    # FIX 2: Accept both 'Landing page' (GA4 UI export) and 'Landing Page' (some API exports)
    landing_col = None
    for candidate in ['Landing page', 'Landing Page', 'landing_page', 'Page']:
        if candidate in df_ga4.columns:
            landing_col = candidate
            break

    if landing_col is not None:
        # FIX 3: Cast to str FIRST, then apply string logic — never call .startswith on raw column
        landing_page = (
            df_ga4[landing_col]
            .fillna('')           # replace NaN floats with empty string
            .astype(str)          # guarantee str type before any string method
            .str.strip()
            .apply(lambda x: ('/' + x) if x and not x.startswith('/') else (x or '/'))
        )
        df_ga4['Address'] = url_prefix + landing_page
        df_ga4['Address'] = df_ga4['Address'].apply(
            lambda x: normalize_trailing_slash(x, has_trailing_slash)
        )
    else:
        logs.append({"type": "info", "message": "  Warning: could not find Landing page column in GA4 export"})

    df_ga4['Address_Normalized'] = df_ga4['Address'].apply(normalize_url_for_matching)
    cleaned_path = get_output_path(domain, "ga4_cleaned")
    save_csv(df_ga4, cleaned_path)
    logs.append({"type": "success", "message": f"GA4 Organic cleaned ({len(df_ga4)} rows)"})
    return logs
