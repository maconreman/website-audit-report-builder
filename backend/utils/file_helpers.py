"""
File helper utilities.
Domain folder management, file path resolution, CSV I/O.
Replaces the Colab Google Drive path logic with local filesystem.
"""

import os
import pandas as pd
from backend.config import UPLOAD_DIR, OUTPUT_DIR, FILE_SUFFIXES


def clean_domain(raw_domain):
    """
    Clean a raw domain input string.
    Original logic from get_client_folder().
    """
    if not raw_domain:
        return None
    clean = raw_domain.strip()
    clean = clean.replace("https://", "").replace("http://", "")
    clean = clean.split("/")[0]
    return clean


def get_domain_upload_folder(domain):
    """
    Get (and create) the upload folder for a domain.
    Replaces Google Drive path: BASE_DRIVE_PATH / domain
    """
    clean = clean_domain(domain)
    if not clean:
        return None, None
    folder = os.path.join(UPLOAD_DIR, clean)
    os.makedirs(folder, exist_ok=True)
    return folder, clean


def get_domain_output_folder(domain):
    """
    Get (and create) the output folder for a domain.
    """
    clean = clean_domain(domain)
    if not clean:
        return None, None
    folder = os.path.join(OUTPUT_DIR, clean)
    os.makedirs(folder, exist_ok=True)
    return folder, clean


def get_file_path(domain, suffix_key):
    """
    Build the full file path for a given domain and file type.
    E.g., get_file_path("example.com", "sf") -> ".../example.com/example.com - SF.csv"
    """
    folder, clean = get_domain_upload_folder(domain)
    if not folder:
        return None
    suffix = FILE_SUFFIXES.get(suffix_key, suffix_key)
    return os.path.join(folder, f"{clean} - {suffix}.csv")


def get_output_path(domain, suffix_key):
    """
    Build the output file path for generated files.
    """
    folder, clean = get_domain_output_folder(domain)
    if not folder:
        return None
    suffix = FILE_SUFFIXES.get(suffix_key, suffix_key)
    return os.path.join(folder, f"{clean} - {suffix}.csv")


def file_exists(domain, suffix_key):
    """Check if a specific file exists for a domain."""
    path = get_file_path(domain, suffix_key)
    if path is None:
        return False
    # Also check output folder
    output_path = get_output_path(domain, suffix_key)
    return os.path.exists(path) or (output_path and os.path.exists(output_path))


def list_domain_files(domain):
    """
    List all files uploaded/generated for a domain.
    Returns a dict of {suffix_key: filepath} for existing files.
    """
    found = {}
    for key in FILE_SUFFIXES:
        # Check upload folder first, then output
        upload_path = get_file_path(domain, key)
        output_path = get_output_path(domain, key)

        if upload_path and os.path.exists(upload_path):
            found[key] = upload_path
        elif output_path and os.path.exists(output_path):
            found[key] = output_path

    return found


def save_upload(domain, suffix_key, file_content):
    """
    Save an uploaded file to the domain's upload folder.
    Returns the saved file path.
    """
    path = get_file_path(domain, suffix_key)
    if not path:
        raise ValueError("Invalid domain")

    with open(path, "wb") as f:
        f.write(file_content)

    return path


def read_csv_safe(filepath, **kwargs):
    """Read a CSV with error handling."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    return pd.read_csv(filepath, **kwargs)


def save_csv(df, filepath):
    """Save a DataFrame to CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    return filepath
