"""
Step 5: Action Assignment — Service layer.
Updated: Old content check LAST, threshold preview, appending Nexus Notes,
final column ordering, Review renamed.
"""

import re
import pandas as pd
from datetime import timedelta

from backend.config import (
    ZERO_CHECK_COLUMNS, ACTION_THRESHOLD_METRICS, LEADS_COLUMNS,
    FINAL_COLUMN_ORDER, FINAL_TAIL_COLUMNS,
)
from backend.utils.url_helpers import contains_tag_or_category
from backend.utils.data_helpers import get_numeric_value
from backend.utils.file_helpers import get_output_path, read_csv_safe, save_csv
from backend.session_state import get_session, update_session, mark_step_complete


_NOTE_SEP = ' || '  # Internal delimiter for multi-note values


def _append_note(df, mask, col, note):
    """Append note to column without overwriting existing values. Uses || as delimiter."""
    for idx in df.index[mask]:
        existing = str(df.at[idx, col]).strip() if pd.notna(df.at[idx, col]) else ''
        if not existing:
            df.at[idx, col] = note
        elif note not in existing:
            df.at[idx, col] = existing + _NOTE_SEP + note
    return df


def run_step5(domain):
    """Execute Step 5: Start action workflow. Old content comes LAST."""
    session = get_session(domain)
    logs = []
    logs.append({"type": "heading", "message": "STEP 5: Assign Actions"})

    audit_path = get_output_path(domain, "audit")
    try:
        df = read_csv_safe(audit_path)
    except FileNotFoundError:
        raise FileNotFoundError("Website Audit file not found. Run previous steps first.")

    update_session(domain, {"audit_records": df.to_dict(orient="records")})
    logs.append({"type": "info", "message": f"Loaded {len(df)} rows"})

    # Go straight to action workflow (no old content prompt yet — it's moved to last)
    result = _start_action_workflow(domain, logs)
    return result


def configure_old_content(domain, enabled, cutoff_year=None, date_field=None):
    """Set old content config and apply it as the LAST rule, then finalize."""
    session = get_session(domain)
    logs = []

    if enabled:
        update_session(domain, {
            "old_content_enabled": True,
            "old_content_year": cutoff_year,
            "old_content_date_field": date_field,
        })
        logs.append({"type": "info", "message": f"Old content: flagging before {cutoff_year} using {date_field}"})

        # Apply old content rule NOW (as last rule)
        audit_records = session.get("audit_records")
        df = pd.DataFrame(audit_records)

        if date_field in df.columns:
            def is_old_content(row):
                if row.get('Action', '') != '' and row.get('Action', '') != 'Review':
                    return False
                date_val = row.get(date_field)
                if pd.isna(date_val) or not date_val:
                    return False
                try:
                    parsed = pd.to_datetime(str(date_val), errors='coerce')
                    if pd.notna(parsed) and parsed.year < cutoff_year:
                        return True
                except Exception:
                    pass
                return False

            old_mask = df.apply(is_old_content, axis=1)

            # Exclude tag/category pages from old content flagging (by category AND URL)
            is_tag_cat = df['Address'].str.lower().str.contains('/tag|/category', na=False)
            if 'Page Category' in df.columns:
                cat_lower = df['Page Category'].fillna('').str.lower()
                is_tag_cat = is_tag_cat | cat_lower.isin(['tag', 'category'])
            old_mask = old_mask & (~is_tag_cat)

            df.loc[old_mask, 'Action'] = 'Remove/Redirect'
            df = _append_note(df, old_mask, 'Nexus Notes', 'Old Content')
            df = _append_note(df, old_mask, 'Next Action for Nexus', 'Manually check old content relevance.')
            old_count = int(old_mask.sum())
            logs.append({"type": "info", "message": f"  Old content: {old_count} pages marked 'Remove/Redirect'"})

            session["documentation"]["old_content_settings"] = {
                "enabled": True, "cutoff_year": cutoff_year,
                "date_field": date_field, "pages_flagged": old_count,
            }

            update_session(domain, {"audit_records": df.to_dict(orient="records")})
    else:
        update_session(domain, {"old_content_enabled": False})
        logs.append({"type": "info", "message": "Old content check skipped."})

    return _finalize_action_column(domain, logs)


def get_threshold_stats(domain):
    """Return stats for current metric INCLUDING a preview calculation."""
    session = get_session(domain)
    metrics = session.get("action_metrics", [])
    index = session.get("current_metric_index", 0)

    if index >= len(metrics):
        return {"status": "no_more_metrics"}

    current_metric = metrics[index]
    audit_records = session.get("audit_records")
    if not audit_records:
        raise ValueError("No audit data in session.")

    df = pd.DataFrame(audit_records)
    unmarked_df = df[df['Action'] == '']

    if len(unmarked_df) == 0:
        return {"status": "no_unmarked_pages"}

    values = unmarked_df[current_metric].apply(get_numeric_value)

    # Compute percentile distribution for preview
    percentiles = {}
    for pct in [5, 10, 15, 20, 25, 30, 50]:
        cutoff = float(values.quantile((100 - pct) / 100))
        count = int((values >= cutoff).sum()) if cutoff > 0 else 0
        percentiles[pct] = {"threshold": cutoff, "keep_count": count}

    return {
        "status": "ready",
        "metric": current_metric,
        "metric_index": index,
        "total_metrics": len(metrics),
        "unmarked_count": len(unmarked_df),
        "stats": {
            "max": float(values.max()),
            "min": float(values.min()),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "non_zero_count": int((values > 0).sum()),
            "p90": float(values.quantile(0.9)),
            "p75": float(values.quantile(0.75)),
        },
        "percentile_preview": percentiles,
    }


def preview_threshold(domain, threshold_type, value):
    """Preview how many pages would be kept without applying."""
    session = get_session(domain)
    metrics = session.get("action_metrics", [])
    index = session.get("current_metric_index", 0)
    if index >= len(metrics):
        return {"keep_count": 0, "actual_threshold": 0}

    current_metric = metrics[index]
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)
    unmarked_df = df[df['Action'] == '']
    values = unmarked_df[current_metric].apply(get_numeric_value)

    if threshold_type == 'percentage':
        actual = float(values.quantile((100 - value) / 100))
    else:
        actual = float(value)

    keep_count = int((values >= actual).sum()) if actual > 0 else 0

    return {
        "keep_count": keep_count,
        "actual_threshold": actual,
        "total_unmarked": len(unmarked_df),
    }


def apply_threshold(domain, threshold_type, value):
    """Apply threshold with appending Nexus Notes."""
    session = get_session(domain)
    logs = []

    metrics = session.get("action_metrics", [])
    index = session.get("current_metric_index", 0)

    if index >= len(metrics):
        return {"status": "no_more_metrics", "logs": logs}

    current_metric = metrics[index]
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)

    unmarked_df = df[df['Action'] == '']
    values = unmarked_df[current_metric].apply(get_numeric_value)

    if threshold_type == 'percentage':
        percentile = 100 - value
        actual_threshold = float(values.quantile(percentile / 100))
    else:
        actual_threshold = float(value)

    # Build Nexus Note text
    if threshold_type == 'percentage':
        note_text = f"Marked as keep. {current_metric} is part of the Top {value:.0f}%."
    else:
        note_text = f"Marked as keep. {current_metric} >= {actual_threshold:,.0f}."

    # Apply
    keep_mask = (df['Action'] == '') & (df[current_metric].apply(get_numeric_value) >= actual_threshold)
    df.loc[keep_mask, 'Action'] = 'Keep'

    # Append to Nexus Notes (not overwrite)
    df = _append_note(df, keep_mask, 'Nexus Notes', note_text)

    keep_count = int(keep_mask.sum())

    thresholds = session.get("metric_thresholds", {})
    thresholds[current_metric] = {'type': threshold_type, 'input': value, 'actual': actual_threshold}

    update_session(domain, {
        "audit_records": df.to_dict(orient="records"),
        "metric_thresholds": thresholds,
        "current_metric_index": index + 1,
    })

    if threshold_type == 'percentage':
        logs.append({"type": "info", "message": f"{current_metric}: Top {value:.0f}% (>= {actual_threshold:,.2f}). {keep_count} pages marked Keep."})
    else:
        logs.append({"type": "info", "message": f"{current_metric}: >= {actual_threshold:,.2f}. {keep_count} pages marked Keep."})

    next_index = index + 1
    if next_index >= len(metrics):
        # Thresholds done -> check recent content then old content
        recent_result = _check_recent_content(domain, logs)
        return recent_result
    else:
        next_stats = get_threshold_stats(domain)
        return {
            "status": "next_metric",
            "keep_count": keep_count,
            "threshold_applied": thresholds[current_metric],
            "next_threshold_stats": next_stats,
            "logs": logs,
        }


def skip_threshold(domain):
    """Skip current metric."""
    session = get_session(domain)
    logs = []
    metrics = session.get("action_metrics", [])
    index = session.get("current_metric_index", 0)
    if index < len(metrics):
        logs.append({"type": "info", "message": f"{metrics[index]}: Skipped"})
    update_session(domain, {"current_metric_index": index + 1})
    next_index = index + 1
    if next_index >= len(metrics):
        return _check_recent_content(domain, logs)
    else:
        return {"status": "next_metric", "next_threshold_stats": get_threshold_stats(domain), "logs": logs}


def recent_content_keep(domain):
    """Override recent content actions to Keep."""
    session = get_session(domain)
    logs = []
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)

    # Ensure string types
    for col in ['Action', 'Nexus Notes', 'Next Action for Nexus']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)

    mask_indices = session.get("recent_content_mask_indices", [])
    if mask_indices:
        for idx in mask_indices:
            if idx < len(df):
                df.at[idx, 'Action'] = 'Keep'
                existing = str(df.at[idx, 'Nexus Notes']).strip()
                note = 'Recent content'
                if not existing:
                    df.at[idx, 'Nexus Notes'] = note
                elif note not in existing:
                    df.at[idx, 'Nexus Notes'] = existing + _NOTE_SEP + note
        logs.append({"type": "info", "message": f"Changed {len(mask_indices)} recent pages to Keep"})
        session["documentation"]["recent_content_override"] = {
            "enabled": True, "pages_overridden": len(mask_indices),
            "original_actions": session.get("recent_content_actions", {}),
            "cutoff_date": session.get("recent_content_cutoff_date", ""),
        }
    update_session(domain, {"audit_records": df.to_dict(orient="records")})
    return _prompt_old_content(domain, logs)


def recent_content_skip(domain):
    """Skip recent content override."""
    session = get_session(domain)
    logs = []
    session["documentation"]["recent_content_override"] = {
        "enabled": False,
        "pages_skipped": sum(session.get("recent_content_actions", {}).values()),
        "original_actions": session.get("recent_content_actions", {}),
        "cutoff_date": session.get("recent_content_cutoff_date", ""),
    }
    logs.append({"type": "info", "message": "Recent content check skipped."})
    return _prompt_old_content(domain, logs)


# --- Internal ---

def _start_action_workflow(domain, logs):
    """Initialize Action column, apply auto rules, then go to thresholds."""
    session = get_session(domain)
    audit_records = session.get("audit_records")
    if not audit_records:
        raise ValueError("No audit data in session.")

    df = pd.DataFrame(audit_records)

    # Initialize Action column (keep existing Nexus Notes/Next Action)
    for col in ['Action', 'Nexus Notes', 'Next Action for Nexus']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('').astype(str)

    # Reset all actions for re-run
    df['Action'] = ''

    logs.append({"type": "info", "message": "Applying automatic action rules..."})

    # Rule 1: All zeros -> Remove/Redirect (VECTORIZED)
    available_zero_cols = [c for c in ZERO_CHECK_COLUMNS if c in df.columns]
    if available_zero_cols:
        numeric_df = df[available_zero_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        all_zero_mask = (numeric_df == 0).all(axis=1)
        df.loc[all_zero_mask, 'Action'] = 'Remove/Redirect'
        logs.append({"type": "info", "message": f"  All metrics zero: {int(all_zero_mask.sum())} pages"})

    # Rule 2: /tag or /category -> Discuss Further + auto-assign Page Category
    addr_lower = df['Address'].str.lower()
    tag_mask = addr_lower.str.contains('/tag', na=False) & (df['Action'] == '')
    cat_mask = addr_lower.str.contains('/category', na=False) & (df['Action'] == '')
    tag_cat_mask = tag_mask | cat_mask

    df.loc[tag_cat_mask, 'Action'] = 'Discuss Further'
    df = _append_note(df, tag_cat_mask, 'Nexus Notes', 'Is this tag/category still relevant?')

    # Auto-assign Page Category if not already set
    if 'Page Category' in df.columns:
        tag_uncat = tag_mask & (df['Page Category'].fillna('').isin(['', 'Uncategorized']))
        cat_uncat = cat_mask & (df['Page Category'].fillna('').isin(['', 'Uncategorized']))
        df.loc[tag_uncat, 'Page Category'] = 'Tag'
        df.loc[cat_uncat, 'Page Category'] = 'Category'

    logs.append({"type": "info", "message": f"  Tag/category URLs: {int(tag_cat_mask.sum())} pages (auto-categorized)"})

    # Rule 3: Has leads -> Keep (VECTORIZED)
    available_leads = [c for c in LEADS_COLUMNS if c in df.columns]
    if available_leads:
        leads_numeric = df[available_leads].apply(pd.to_numeric, errors='coerce').fillna(0)
        leads_mask = (leads_numeric >= 1).any(axis=1) & (df['Action'] == '')
        df.loc[leads_mask, 'Action'] = 'Keep'
        df = _append_note(df, leads_mask, 'Nexus Notes', 'Has lead conversions')
        logs.append({"type": "info", "message": f"  Has leads: {int(leads_mask.sum())} pages"})

    # NOTE: Old content check is NOT here anymore — moved to LAST

    update_session(domain, {"audit_records": df.to_dict(orient="records")})

    # Determine threshold metrics
    available_metrics = []
    for metric in ACTION_THRESHOLD_METRICS:
        if metric in df.columns:
            unmarked = df[df['Action'] == '']
            if len(unmarked) > 0 and unmarked[metric].apply(get_numeric_value).max() > 0:
                available_metrics.append(metric)

    update_session(domain, {
        "action_metrics": available_metrics,
        "current_metric_index": 0,
        "metric_thresholds": {},
    })

    unmarked_count = int((df['Action'] == '').sum())
    logs.append({"type": "info", "message": f"Remaining unmarked: {unmarked_count}"})

    if available_metrics:
        stats = get_threshold_stats(domain)
        return {
            "status": "awaiting_threshold",
            "rules_applied": True,
            "unmarked_count": unmarked_count,
            "available_metrics": available_metrics,
            "threshold_stats": stats,
            "logs": logs,
        }
    else:
        return _check_recent_content(domain, logs)


def _check_recent_content(domain, logs):
    """Check for recent content flagged for non-Keep."""
    session = get_session(domain)
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)

    # Use Date Modified if available, else Date Published
    date_col = None
    for col in ['Date Modified', 'Date Published']:
        if col in df.columns:
            date_col = col
            break

    if date_col is None:
        logs.append({"type": "info", "message": "No date column. Skipping recent content check."})
        return _prompt_old_content(domain, logs)

    df['_parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
    valid_dates = df['_parsed_date'].dropna()

    if len(valid_dates) == 0:
        df = df.drop(columns=['_parsed_date'])
        update_session(domain, {"audit_records": df.to_dict(orient="records")})
        return _prompt_old_content(domain, logs)

    latest = valid_dates.max()
    cutoff = latest - timedelta(days=180)  # Last 6 months

    recent_not_keep = df[
        (df['_parsed_date'] >= cutoff) & (df['Action'] != 'Keep') & (df['Action'] != '')
    ]

    # Exclude tag/category pages by both Page Category AND URL pattern
    is_tag_cat = df['Address'].str.lower().str.contains('/tag|/category', na=False)
    if 'Page Category' in df.columns:
        is_tag_cat = is_tag_cat | df['Page Category'].fillna('').str.lower().isin(['tag', 'category'])
    recent_not_keep = recent_not_keep[~is_tag_cat.reindex(recent_not_keep.index, fill_value=False)]

    if len(recent_not_keep) == 0:
        df = df.drop(columns=['_parsed_date'])
        update_session(domain, {"audit_records": df.to_dict(orient="records")})
        return _prompt_old_content(domain, logs)

    action_counts = recent_not_keep['Action'].value_counts().to_dict()
    mask_indices = recent_not_keep.index.tolist()

    df = df.drop(columns=['_parsed_date'])
    update_session(domain, {
        "audit_records": df.to_dict(orient="records"),
        "recent_content_actions": action_counts,
        "recent_content_mask_indices": mask_indices,
        "recent_content_cutoff_date": cutoff.strftime('%Y-%m-%d'),
    })

    logs.append({"type": "info", "message": f"Found {len(recent_not_keep)} recent pages with non-Keep actions."})

    return {
        "status": "awaiting_recent_content",
        "recent_content": {
            "total_pages": len(recent_not_keep),
            "cutoff_date": cutoff.strftime('%Y-%m-%d'),
            "action_counts": action_counts,
        },
        "logs": logs,
    }


def _prompt_old_content(domain, logs):
    """Prompt for old content check (LAST step before finalize)."""
    session = get_session(domain)
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)

    # Check what date columns are available
    has_date_modified = 'Date Modified' in df.columns
    has_date_published = 'Date Published' in df.columns

    if has_date_modified or has_date_published:
        return {
            "status": "awaiting_old_content_config",
            "has_date_modified": has_date_modified,
            "has_date_published": has_date_published,
            "logs": logs,
        }
    else:
        return _finalize_action_column(domain, logs)


def _finalize_action_column(domain, logs):
    """Finalize: Discuss Further for unmarked, lettered Nexus Notes, capitalize categories, order columns."""
    session = get_session(domain)
    audit_records = session.get("audit_records")
    df = pd.DataFrame(audit_records)

    # Ensure string types
    for col in ['Action', 'Nexus Notes', 'Next Action for Nexus']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)

    # Item 7: Unmarked → "Discuss Further" with Next Action for Nexus
    unmarked = df['Action'] == ''
    df.loc[unmarked, 'Action'] = 'Discuss Further'
    df = _append_note(df, unmarked, 'Next Action for Nexus', 'Nexus to check before finalization')

    # Ensure every row has a Nexus Note
    if 'Nexus Notes' in df.columns:
        empty_notes = df['Nexus Notes'].fillna('').str.strip() == ''
        keep_no_note = empty_notes & (df['Action'] == 'Keep')
        df.loc[keep_no_note, 'Nexus Notes'] = 'Retained by audit rules'
        remove_no_note = empty_notes & (df['Action'] == 'Remove/Redirect')
        df.loc[remove_no_note, 'Nexus Notes'] = 'All metrics are zero'
        discuss_no_note = empty_notes & (df['Action'] == 'Discuss Further')
        df.loc[discuss_no_note, 'Nexus Notes'] = 'Requires manual evaluation'

    # Item 8: Format Nexus Notes as lettered list (a), (b), (c)
    if 'Nexus Notes' in df.columns:
        df['Nexus Notes'] = df['Nexus Notes'].apply(_format_notes_lettered)

    # Item 6: Capitalize Page Categories
    if 'Page Category' in df.columns:
        df['Page Category'] = df['Page Category'].apply(
            lambda x: str(x).strip().title() if pd.notna(x) and str(x).strip() else x
        )

    # Final column ordering
    df = _order_columns(df)

    action_counts = df['Action'].value_counts().to_dict()
    logs.append({"type": "heading", "message": "Action Assignment Complete"})
    for action, count in action_counts.items():
        logs.append({"type": "info", "message": f"  {action}: {count} pages"})

    session["documentation"]["action_thresholds"] = session.get("metric_thresholds", {})
    session["documentation"]["action_summary"] = action_counts
    session["documentation"]["final_row_count"] = len(df)
    session["documentation"]["final_columns"] = df.columns.tolist()

    update_session(domain, {"audit_records": df.to_dict(orient="records")})
    output_path = get_output_path(domain, "audit")
    save_csv(df, output_path)

    mark_step_complete(domain, 5)
    logs.append({"type": "success", "message": f"Saved: {len(df)} pages, {len(df.columns)} columns"})

    return {
        "status": "complete",
        "action_summary": action_counts,
        "rows": len(df),
        "logs": logs,
    }


def _format_notes_lettered(notes_str):
    """Convert multi-note string 'X || Y || Z' into '(a) X (b) Y (c) Z'."""
    if pd.isna(notes_str) or not str(notes_str).strip():
        return ''
    raw = str(notes_str).strip()
    # Split on the internal delimiter
    if _NOTE_SEP.strip() in raw:
        parts = [p.strip() for p in raw.split(_NOTE_SEP.strip()) if p.strip()]
    else:
        # Single note — return as-is
        return raw
    if len(parts) <= 1:
        return parts[0] if parts else ''
    letters = 'abcdefghijklmnopqrstuvwxyz'
    formatted = []
    for i, part in enumerate(parts):
        letter = letters[i] if i < len(letters) else str(i + 1)
        formatted.append(f"({letter}) {part}")
    return ' '.join(formatted)


def _order_columns(df):
    """Reorder columns per FINAL_COLUMN_ORDER spec."""
    ordered = []
    # First: columns from FINAL_COLUMN_ORDER that exist (minus tail)
    head_order = [c for c in FINAL_COLUMN_ORDER if c not in FINAL_TAIL_COLUMNS]
    for col in head_order:
        if col in df.columns:
            ordered.append(col)

    # Middle: all remaining columns not in head or tail
    all_specified = set(FINAL_COLUMN_ORDER) | set(FINAL_TAIL_COLUMNS)
    middle = [c for c in df.columns if c not in all_specified and c not in ordered]
    ordered.extend(middle)

    # Tail: Action, Nexus Notes, Next Action for Nexus
    for col in FINAL_TAIL_COLUMNS:
        if col in df.columns:
            ordered.append(col)

    # Add any remaining
    for col in df.columns:
        if col not in ordered:
            ordered.append(col)

    return df[ordered]
