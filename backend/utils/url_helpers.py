"""
URL helper utilities.
Ported directly from the original Colab notebook helper functions.
"""

import pandas as pd
from urllib.parse import urlparse


def extract_url_prefix(url):
    """
    Extract the URL prefix (scheme + netloc) from a URL.
    Original: extract_url_prefix()
    """
    try:
        parsed = urlparse(str(url))
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None


def normalize_url_for_matching(url):
    """
    Normalize URL for matching purposes.
    Strips www, trailing slash, lowercases.
    Original: normalize_url_for_matching()
    """
    if pd.isna(url) or not url:
        return ""

    url_str = str(url).strip().lower()

    try:
        parsed = urlparse(url_str)

        netloc = parsed.netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed.path.rstrip("/")

        normalized = f"{parsed.scheme}://{netloc}{path}"
        return normalized
    except Exception:
        return url_str.rstrip("/").replace("://www.", "://")


def normalize_trailing_slash(url, should_have_slash):
    """
    Normalize URL trailing slash based on site convention.
    Original: normalize_trailing_slash()
    """
    if pd.isna(url) or not url:
        return url

    url_str = str(url)
    has_slash = url_str.endswith("/")

    if should_have_slash and not has_slash:
        return url_str + "/"
    if not should_have_slash and has_slash:
        return url_str.rstrip("/")
    return url_str


def detect_trailing_slash_convention(sample_url):
    """
    Detect whether the site uses trailing slashes from a sample URL.
    Returns True if the URL ends with '/'.
    """
    return str(sample_url).endswith("/")


def contains_tag_or_category(url):
    """
    Check if a URL contains /tag or /category segments.
    Used in action assignment Rule 2.
    """
    url_lower = str(url).lower()
    return "/tag" in url_lower or "/category" in url_lower
