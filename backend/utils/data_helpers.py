"""
Data helper utilities.
Column detection, date formatting, reading time cleaning, metric filling.
Ported directly from the original Colab notebook helper functions.
"""

import re
import pandas as pd
from backend.config import METRIC_COLUMNS, CUSTOM_COLUMN_PATTERNS


def detect_custom_columns(df):
    """
    Detect custom columns matching specific patterns ending with '1'.
    Original: detect_custom_columns()
    """
    detected = {}

    for col in df.columns:
        col_lower = col.lower().strip()
        for custom_type, patterns in CUSTOM_COLUMN_PATTERNS.items():
            if any(col_lower == pattern for pattern in patterns):
                if custom_type not in detected:
                    detected[custom_type] = {
                        "first_column": col,
                        "all_columns": [],
                    }

                    base_name = re.sub(r"\s*\d+$", "", col).strip()
                    related_pattern = re.compile(
                        rf"^{re.escape(base_name)}\s*\d+$", re.IGNORECASE
                    )
                    related_cols = [c for c in df.columns if related_pattern.match(c)]
                    detected[custom_type]["all_columns"] = sorted(
                        related_cols,
                        key=lambda x: int(re.search(r"\d+$", x).group()),
                    )

    return detected


def combine_multiple_columns(df, column_prefix):
    """
    Combine multiple numbered columns into one comma-separated string.
    Original: combine_multiple_columns()
    """
    pattern = re.compile(
        rf"^{re.escape(column_prefix)}\s*\d+$", re.IGNORECASE
    )
    matching_cols = [col for col in df.columns if pattern.match(col)]

    def get_col_number(col_name):
        match = re.search(r"\d+$", col_name)
        return int(match.group()) if match else 0

    matching_cols = sorted(matching_cols, key=get_col_number)

    if not matching_cols:
        return None, None, []

    def combine_row(row):
        values = []
        for col in matching_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() != "":
                values.append(str(val).strip())
        combined = ", ".join(values)
        count = len(values)
        return combined, count

    results = df.apply(combine_row, axis=1)
    combined = results.apply(lambda x: x[0])
    counts = results.apply(lambda x: x[1])

    return combined, counts, matching_cols


def format_date_column(series):
    """
    Convert date column to YYYY-MM-DD format, taking first available date.
    Original: format_date_column()
    """

    def parse_date(val):
        if pd.isna(val) or str(val).strip() == "":
            return None
        try:
            parsed = pd.to_datetime(str(val).split(",")[0].strip(), errors="coerce")
            if pd.notna(parsed):
                return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass
        return None

    return series.apply(parse_date)


def clean_reading_time(val):
    """
    Clean reading time values by removing extra spaces and normalizing format.
    Original: clean_reading_time()
    """
    if pd.isna(val) or not val:
        return None

    val_str = str(val).strip()
    if val_str == "":
        return None

    val_str = re.sub(r"\s+", " ", val_str)
    val_str = val_str.strip()

    return val_str if val_str else None


def fill_blank_metrics_with_zero(df):
    """
    Fill blank/NaN values with 0 for all numeric metric columns.
    Original: fill_blank_metrics_with_zero()
    """
    for col in METRIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(0)

    return df


def get_numeric_value(val):
    """
    Safely convert value to numeric, returning 0 for invalid/empty values.
    Original: get_numeric_value()
    """
    if pd.isna(val):
        return 0
    try:
        if isinstance(val, str):
            val = val.replace("%", "").replace(",", "").strip()
            if val == "" or val == "-":
                return 0
        return float(val)
    except (ValueError, TypeError):
        return 0
