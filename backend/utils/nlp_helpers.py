"""
NLP helpers for Page Highlight extraction and reading time.
Improved: extracts meaningful topic phrases, not just keyword soup.
"""

import re
import math
import pandas as pd
from collections import Counter
from backend.config import NLP_STOP_WORDS, READING_SPEED_WPM


def extract_page_highlight(title, meta_description):
    """
    Extract a concise 2-5 word topic phrase from Title and Meta Description.
    
    Strategy:
    1. Try to extract a clean noun phrase from the title (before any separator like | - :)
    2. Score candidate phrases by keyword overlap with meta description
    3. Fall back to top weighted keywords if no good phrase found
    """
    title_str = str(title).strip() if pd.notna(title) else ''
    meta_str = str(meta_description).strip() if pd.notna(meta_description) else ''

    if not title_str and not meta_str:
        return ''

    # Step 1: Clean the title — take the part before separators (| - : —)
    title_core = re.split(r'\s*[|\-:—]+\s*', title_str)[0].strip()
    if len(title_core) < 5:
        title_core = title_str

    # Step 2: Build keyword weights from meta description
    meta_keywords = set(_tokenize(meta_str))

    # Step 3: Extract candidate phrases from the title core
    candidates = _extract_noun_phrases(title_core)

    if candidates:
        # Score each candidate by: length preference (3-4 words ideal) + meta overlap
        scored = []
        for phrase in candidates:
            words = phrase.lower().split()
            meaningful = [w for w in words if w not in NLP_STOP_WORDS and len(w) > 2]
            if len(meaningful) < 1:
                continue
            meta_overlap = sum(1 for w in meaningful if w in meta_keywords)
            # Prefer 2-4 meaningful words, penalize too short or too long
            length_score = 3 if 2 <= len(meaningful) <= 4 else (2 if len(meaningful) == 1 else 1)
            score = meta_overlap * 2 + length_score + len(meaningful)
            scored.append((phrase, score, len(meaningful)))

        scored.sort(key=lambda x: (-x[1], -x[2]))

        if scored:
            best = scored[0][0]
            # Trim to max 5 words
            words = best.split()
            if len(words) > 5:
                best = ' '.join(words[:5])
            return _title_case_smart(best)

    # Fallback: use top weighted keywords
    counter = Counter()
    for w in _tokenize(title_core):
        counter[w] += 3
    for w in _tokenize(meta_str):
        counter[w] += 1

    top = [w for w, _ in counter.most_common(4)]
    if top:
        return _title_case_smart(' '.join(top[:3]))

    return ''


def _tokenize(text):
    """Extract meaningful words, removing stop words."""
    words = re.findall(r'[a-zA-Z]{2,}', text.lower())
    return [w for w in words if w not in NLP_STOP_WORDS and len(w) > 2]


def _extract_noun_phrases(text):
    """
    Extract candidate noun phrases by splitting on function words and punctuation.
    Returns phrases of 2-5 words that contain at least one meaningful word.
    """
    # Split on common function word boundaries and punctuation
    text_clean = re.sub(r'[^\w\s]', ' ', text)
    words = text_clean.split()

    if not words:
        return []

    phrases = []

    # Strategy A: Sliding window of 2-5 words, keep those with good content
    for window_size in range(5, 1, -1):
        for i in range(len(words) - window_size + 1):
            chunk = words[i:i + window_size]
            chunk_lower = [w.lower() for w in chunk]
            meaningful = [w for w in chunk_lower if w not in NLP_STOP_WORDS and len(w) > 2]
            # At least half the words should be meaningful
            if len(meaningful) >= max(1, len(chunk) // 2):
                # Don't start or end with a stop word
                if chunk_lower[0] not in NLP_STOP_WORDS and chunk_lower[-1] not in NLP_STOP_WORDS:
                    phrases.append(' '.join(chunk))

    # Strategy B: Just the first 2-4 meaningful words
    meaningful_words = [w for w in words if w.lower() not in NLP_STOP_WORDS and len(w) > 2]
    if meaningful_words and len(meaningful_words) >= 2:
        phrases.append(' '.join(meaningful_words[:min(4, len(meaningful_words))]))

    return phrases


def _title_case_smart(text):
    """Title case that keeps short prepositions lowercase (except first word)."""
    small_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'vs'}
    words = text.split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small_words:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return ' '.join(result)


def calculate_estimated_reading_time(word_count):
    """Calculate reading time from word count. Returns 'X min read'."""
    if pd.isna(word_count):
        return ''
    try:
        wc = float(word_count)
        if wc <= 0:
            return ''
        minutes = math.ceil(wc / READING_SPEED_WPM)
        return f"{minutes} min read"
    except (ValueError, TypeError):
        return ''


def apply_page_highlights(df):
    """Add 'Page Highlight' column from Title and Meta Description."""
    title_col = None
    for col in df.columns:
        if col.lower().strip() in ('title 1', 'title', 'page title', 'seo title'):
            title_col = col
            break
    if title_col is None:
        for col in df.columns:
            if 'title' in col.lower() and 'meta' not in col.lower():
                title_col = col
                break

    meta_col = None
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ('meta description 1', 'meta description', 'description 1'):
            meta_col = col
            break
    if meta_col is None:
        for col in df.columns:
            if 'meta' in col.lower() and 'description' in col.lower():
                meta_col = col
                break

    if title_col is None and meta_col is None:
        df['Page Highlight'] = ''
        return df, None, None

    df['Page Highlight'] = df.apply(
        lambda row: extract_page_highlight(
            row.get(title_col, '') if title_col else '',
            row.get(meta_col, '') if meta_col else '',
        ), axis=1,
    )
    return df, title_col, meta_col


def apply_estimated_reading_time(df):
    """Add 'Estimated Reading Time' from Word Count column."""
    wc_col = None
    for col in df.columns:
        if col.lower().strip() in ('word count', 'wordcount', 'word count 1'):
            wc_col = col
            break
    if wc_col is None:
        for col in df.columns:
            if 'word' in col.lower() and 'count' in col.lower():
                wc_col = col
                break
    if wc_col is None:
        df['Estimated Reading Time'] = ''
        return df, None
    df['Estimated Reading Time'] = df[wc_col].apply(calculate_estimated_reading_time)
    return df, wc_col
