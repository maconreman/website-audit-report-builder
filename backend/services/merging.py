"""
Step 3: Merge Data Sources — Service layer.
Ported from: run_merge()
"""

import pandas as pd

from backend.config import GA4_COLUMNS_TO_DELETE, GA4_RENAME_MAP
from backend.utils.url_helpers import normalize_url_for_matching
from backend.utils.data_helpers import fill_blank_metrics_with_zero
from backend.utils.file_helpers import (
    get_output_path, get_file_path, read_csv_safe, save_csv,
)
from backend.session_state import get_session, update_session, mark_step_complete


def run_step3(domain):
    """
    Execute Step 3: Merge GA4 Organic and External Links into the audit.
    Ported 1:1 from run_merge().
    """
    session = get_session(domain)
    logs = []

    logs.append({"type": "heading", "message": "STEP 3: Merge Data Sources"})

    # Load the audit file
    audit_path = get_output_path(domain, "audit")
    try:
        df_audit = read_csv_safe(audit_path)
    except FileNotFoundError:
        raise FileNotFoundError("Website Audit file not found. Run Step 2 first.")

    initial_rows = len(df_audit)
    logs.append({"type": "info", "message": f"Loaded Website Audit: {initial_rows} rows"})

    # Ensure normalized address column
    if 'Address_Normalized' not in df_audit.columns:
        df_audit['Address_Normalized'] = df_audit['Address'].apply(normalize_url_for_matching)

    # --- MERGE GA4 ORGANIC ---
    logs.append({"type": "info", "message": "Merging GA4 Organic data..."})
    ga4_merge_info = _merge_ga4_organic(domain, df_audit, logs)
    if ga4_merge_info.get("merged_df") is not None:
        df_audit = ga4_merge_info["merged_df"]
    session["documentation"]["ga4_merge_info"] = ga4_merge_info.get("doc_info", {})

    # --- MERGE EXTERNAL LINKS ---
    logs.append({"type": "info", "message": "Merging External Links data..."})
    ext_merge_info = _merge_external_links(domain, df_audit, logs)
    if ext_merge_info.get("merged_df") is not None:
        df_audit = ext_merge_info["merged_df"]
    session["documentation"]["external_links_merge_info"] = ext_merge_info.get("doc_info", {})

    # Fill blank metrics with zero
    logs.append({"type": "info", "message": "Filling blank metrics with zero..."})
    df_audit = fill_blank_metrics_with_zero(df_audit)

    # Drop normalized column before save
    if 'Address_Normalized' in df_audit.columns:
        df_audit = df_audit.drop(columns=['Address_Normalized'])

    # Final duplicate guard — catches any regression from future merge changes
    before_dedup = len(df_audit)
    df_audit = df_audit.drop_duplicates(subset=['Address'], keep='first')
    after_dedup = len(df_audit)
    if before_dedup != after_dedup:
        logs.append({"type": "warning", "message": f"  Removed {before_dedup - after_dedup} duplicate rows after merge"})

    # Save
    update_session(domain, {"audit_records": df_audit.to_dict(orient="records")})
    output_path = get_output_path(domain, "audit")
    save_csv(df_audit, output_path)

    mark_step_complete(domain, 3)

    logs.append({"type": "info", "message": f"Merge summary: {initial_rows} initial → {len(df_audit)} final rows, {len(df_audit.columns)} columns"})
    logs.append({"type": "success", "message": f"Saved: {domain} - Website Audit.csv"})

    return {
        "initial_rows": initial_rows,
        "final_rows": len(df_audit),
        "final_columns": len(df_audit.columns),
        "column_names": df_audit.columns.tolist(),
        "logs": logs,
    }


def _merge_ga4_organic(domain, df_audit, logs):
    """Merge GA4 Organic Cleaned data. Returns dict with merged_df and doc_info."""
    ga4_path = get_output_path(domain, "ga4_cleaned")
    try:
        df_ga4 = read_csv_safe(ga4_path)
    except FileNotFoundError:
        logs.append({"type": "info", "message": "  GA4 Organic Cleaned file not found, skipping..."})
        return {"merged_df": None, "doc_info": {"status": "File not found"}}

    logs.append({"type": "info", "message": f"  Loaded {len(df_ga4)} rows from GA4 Organic Cleaned"})

    if 'Address_Normalized' not in df_ga4.columns:
        df_ga4['Address_Normalized'] = df_ga4['Address'].apply(normalize_url_for_matching)

    # Remove unwanted columns
    cols_to_delete = GA4_COLUMNS_TO_DELETE
    ga4_cols_to_keep = [col for col in df_ga4.columns if col not in cols_to_delete]
    df_ga4_filtered = df_ga4[ga4_cols_to_keep].copy()

    # Rename
    df_ga4_filtered.rename(
        columns={k: v for k, v in GA4_RENAME_MAP.items() if k in df_ga4_filtered.columns},
        inplace=True,
    )

    # FIX 1: Deduplicate GA4 on Address_Normalized before merging.
    # GA4 exports can contain the same landing page multiple times (trailing slash
    # variants, query strings that normalize identically, or channel sub-rows).
    # A left join against a non-unique right key multiplies rows 1:N — this is
    # the primary source of the 23 duplicate rows reported.
    # Strategy: keep the row with the highest Sessions/Organic Traffic value,
    # which represents the most complete traffic picture for that URL.
    rows_before_dedup = len(df_ga4_filtered)
    sort_col = 'Organic Traffic' if 'Organic Traffic' in df_ga4_filtered.columns else (
                'Sessions' if 'Sessions' in df_ga4_filtered.columns else None)
    if sort_col:
        df_ga4_filtered = (
            df_ga4_filtered
            .sort_values(sort_col, ascending=False)
            .drop_duplicates(subset=['Address_Normalized'], keep='first')
        )
    else:
        df_ga4_filtered = df_ga4_filtered.drop_duplicates(subset=['Address_Normalized'], keep='first')

    rows_after_dedup = len(df_ga4_filtered)
    dupes_removed = rows_before_dedup - rows_after_dedup
    if dupes_removed > 0:
        logs.append({"type": "info", "message": f"  Deduplicated GA4: removed {dupes_removed} duplicate URL rows before merge"})

    # Merge — left join; df_audit rows must not increase
    rows_before = len(df_audit)
    df_merged = df_audit.merge(df_ga4_filtered, on='Address_Normalized', how='left')
    rows_after = len(df_merged)

    if rows_after != rows_before:
        # Should never happen after dedup — log a warning and force-dedup
        logs.append({"type": "warning", "message": f"  GA4 merge expanded rows {rows_before} → {rows_after}; deduplicating on Address"})
        df_merged = df_merged.drop_duplicates(subset=['Address'], keep='first')

    matched_rows = 0
    if 'Organic Traffic' in df_merged.columns:
        matched_rows = int(df_merged['Organic Traffic'].notna().sum())

    logs.append({"type": "info", "message": f"  Matched {matched_rows} rows out of {rows_before}"})
    logs.append({"type": "info", "message": f"  Renamed: Sessions → Organic Traffic, Key events → Organic Leads"})

    deleted_cols = [col for col in cols_to_delete if col in df_ga4.columns]
    logs.append({"type": "info", "message": f"  Deleted columns: {', '.join(deleted_cols)}"})

    doc_info = {
        "rows_merged": len(df_ga4),
        "rows_matched": matched_rows,
        "ga4_dupes_removed": dupes_removed,
        "columns_deleted": deleted_cols,
        "columns_renamed": GA4_RENAME_MAP,
    }

    return {"merged_df": df_merged, "doc_info": doc_info}


def _merge_external_links(domain, df_audit, logs):
    """Merge External Links data. Returns dict with merged_df and doc_info."""
    ext_path = get_file_path(domain, "external_links")
    try:
        df_external = read_csv_safe(ext_path)
    except FileNotFoundError:
        logs.append({"type": "info", "message": "  External Links file not found, skipping..."})
        return {"merged_df": None, "doc_info": {"status": "File not found"}}

    logs.append({"type": "info", "message": f"  Loaded {len(df_external)} rows from External Links"})

    # Find target page column
    target_col = None
    for col in df_external.columns:
        if 'target' in str(col).lower() and 'page' in str(col).lower():
            target_col = col
            break
    if target_col is None:
        for col in df_external.columns:
            if str(col).lower() in ['target', 'target page', 'target url', 'url']:
                target_col = col
                break

    if not target_col:
        logs.append({"type": "info", "message": "  Could not find target page column, skipping..."})
        return {"merged_df": None, "doc_info": {"status": "Target column not found"}}

    # Normalize
    df_external['Address_Normalized'] = df_external[target_col].apply(normalize_url_for_matching)

    # Remove unwanted columns
    cols_to_remove = ['Incoming links', target_col]
    df_ext_filtered = df_external.drop(
        columns=[c for c in cols_to_remove if c in df_external.columns]
    ).copy()

    # FIX 2: Deduplicate External Links on Address_Normalized before merging.
    # GSC "Top linked pages" can list the same target page on multiple rows
    # (e.g., one row per linking domain). A non-unique right key causes the
    # same SF row to be duplicated once per matching external links row.
    # Strategy: aggregate Linking Sites by taking the max (largest count wins).
    rows_before_dedup = len(df_ext_filtered)
    linking_col = 'Linking Sites' if 'Linking Sites' in df_ext_filtered.columns else None

    if linking_col:
        # Convert to numeric first so max() is meaningful
        df_ext_filtered[linking_col] = pd.to_numeric(df_ext_filtered[linking_col], errors='coerce').fillna(0)
        df_ext_filtered = (
            df_ext_filtered
            .sort_values(linking_col, ascending=False)
            .drop_duplicates(subset=['Address_Normalized'], keep='first')
        )
    else:
        df_ext_filtered = df_ext_filtered.drop_duplicates(subset=['Address_Normalized'], keep='first')

    rows_after_dedup = len(df_ext_filtered)
    dupes_removed = rows_before_dedup - rows_after_dedup
    if dupes_removed > 0:
        logs.append({"type": "info", "message": f"  Deduplicated External Links: removed {dupes_removed} duplicate URL rows before merge"})

    # Merge — left join; df_audit rows must not increase
    rows_before = len(df_audit)
    df_merged = df_audit.merge(df_ext_filtered, on='Address_Normalized', how='left')
    rows_after = len(df_merged)

    if rows_after != rows_before:
        logs.append({"type": "warning", "message": f"  External links merge expanded rows {rows_before} → {rows_after}; deduplicating on Address"})
        df_merged = df_merged.drop_duplicates(subset=['Address'], keep='first')

    ext_cols = [c for c in df_ext_filtered.columns if c != 'Address_Normalized']
    matched_rows = 0
    if ext_cols:
        matched_rows = int(df_merged[ext_cols[0]].notna().sum())

    logs.append({"type": "info", "message": f"  Used '{target_col}' as merge key"})
    logs.append({"type": "info", "message": f"  Matched {matched_rows} rows out of {rows_before}"})

    removed_cols = ["Incoming links"] if 'Incoming links' in df_external.columns else []
    if removed_cols:
        logs.append({"type": "info", "message": f"  Removed column: {', '.join(removed_cols)}"})

    doc_info = {
        "rows_in_source": len(df_external),
        "target_column_used": target_col,
        "ext_dupes_removed": dupes_removed,
        "columns_removed": removed_cols,
    }

    return {"merged_df": df_merged, "doc_info": doc_info}
