"""
Configuration & constants for the Website Audit Report Builder.
"""

import os

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# On Vercel serverless, use /tmp (ephemeral writable directory)
# Locally, use project-relative data/ folder
_is_vercel = os.environ.get("VERCEL", "") == "1"
if _is_vercel:
    DATA_DIR = "/tmp/audit_data"
else:
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

for d in [UPLOAD_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# --- SERVER ---
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# --- FILE SUFFIXES ---
FILE_SUFFIXES = {
    "sf": "SF",
    "ga4_organic": "GA4 Organic",
    "external_links": "External Links",
    "audit": "Website Audit",
    "ga4_cleaned": "GA4 Organic Cleaned",
}

# --- PREDEFINED PAGE CATEGORIES ---
PREDEFINED_CATEGORIES = {
    'blog': ['blog', 'blogs', 'articles', 'article', 'posts', 'post'],
    'tag': ['tag', 'tags'],
    'category': ['category', 'categories', 'cat'],
    'news': ['news', 'press', 'press-release', 'press-releases', 'media'],
    'product': ['product', 'products', 'shop', 'store', 'item', 'items'],
    'service': ['service', 'services', 'solutions', 'solution'],
    'about': ['about', 'about-us', 'team', 'our-team', 'company'],
    'contact': ['contact', 'contact-us', 'get-in-touch', 'reach-us'],
    'faq': ['faq', 'faqs', 'help', 'support', 'knowledge-base', 'kb'],
    'case-study': ['case-study', 'case-studies', 'success-stories', 'portfolio', 'work', 'projects'],
    'resource': ['resource', 'resources', 'downloads', 'download', 'whitepaper', 'whitepapers', 'ebook', 'ebooks'],
    'event': ['event', 'events', 'webinar', 'webinars', 'conference'],
    'career': ['career', 'careers', 'jobs', 'job', 'hiring', 'join-us'],
    'legal': ['privacy', 'privacy-policy', 'terms', 'terms-of-service', 'tos', 'legal', 'disclaimer'],
    'landing-page': ['lp', 'landing', 'promo', 'campaign'],
    'author': ['author', 'authors', 'contributor', 'contributors', 'writer', 'writers'],
}

# --- METRIC COLUMNS ---
METRIC_COLUMNS = [
    'Landing Page Traffic', 'Landing Page Leads',
    'Organic Traffic', 'Organic Leads',
    'Clicks', 'Impressions', 'CTR',
    'Linking Sites', 'Link Score',
]

ZERO_CHECK_COLUMNS = [
    'Landing Page Traffic', 'Landing Page Leads',
    'Organic Traffic', 'Organic Leads',
    'Clicks', 'Impressions', 'CTR', 'Linking Sites',
]

ACTION_THRESHOLD_METRICS = [
    'Landing Page Traffic',
    'Impressions',
    'Clicks',
]

LEADS_COLUMNS = ['Landing Page Leads', 'Organic Leads']

# --- CUSTOM COLUMN DETECTION PATTERNS ---
CUSTOM_COLUMN_PATTERNS = {
    # Date Published excluded — not treated as custom data
    'Date Modified': ['date modified 1', 'modified 1', 'last modified 1', 'updated 1'],
    'Author': ['author 1', 'authors 1', 'writer 1'],
    'Tags': ['tag 1', 'tags 1'],
    'Categories': ['category 1', 'categories 1'],
    # Reading Time excluded — only Estimated Reading Time (from Word Count) is used
}

# --- BASE COLUMNS kept from Screaming Frog ---
SF_BASE_COLUMNS = [
    'Address', 'GA4 Sessions', 'GA4 Key events',
    'Clicks', 'Impressions', 'CTR',
]

SF_RENAME_MAP = {
    'GA4 Sessions': 'Landing Page Traffic',
    'GA4 Key events': 'Landing Page Leads',
}

# --- GA4 ORGANIC MERGE SETTINGS ---
GA4_COLUMNS_TO_DELETE = [
    'Landing page', 'Active users', 'New users',
    'Average engagement time per session', 'Total revenue',
    'Session key event rate', 'Address',
]

GA4_RENAME_MAP = {
    'Sessions': 'Organic Traffic',
    'Key events': 'Organic Leads',
}

GA4_SKIP_ROWS = 9

# --- WORDS PER MINUTE for Estimated Reading Time ---
READING_SPEED_WPM = 200

# --- FINAL OUTPUT COLUMN ORDER (item 8) ---
# Columns listed here appear first in order; unlisted columns appear after.
FINAL_COLUMN_ORDER = [
    'Address',
    'Landing Page Traffic',
    'Landing Page Leads',
    'Organic Traffic',
    'Organic Leads',
    'Clicks',
    'Impressions',
    'CTR',
    'Linking Sites',
    'Page Category',
    'Page Highlight',
    'Estimated Reading Time',
    'Date Modified',
    # -- custom extraction columns go here dynamically --
    # Then at the end:
    'Action',
    'Nexus Notes',
    'Next Action for Nexus',
]

# Columns that must always appear at the very end (in this order)
FINAL_TAIL_COLUMNS = ['Action', 'Nexus Notes', 'Next Action for Nexus']

# --- NLP STOP WORDS for Page Highlight extraction ---
NLP_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'it', 'its', 'this',
    'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she', 'they', 'me',
    'us', 'him', 'her', 'them', 'my', 'our', 'your', 'his', 'their', 'who',
    'whom', 'which', 'what', 'when', 'where', 'why', 'how', 'not', 'no',
    'nor', 'so', 'if', 'then', 'than', 'too', 'very', 'just', 'about',
    'up', 'out', 'into', 'over', 'after', 'before', 'between', 'under',
    'above', 'below', 'each', 'every', 'all', 'any', 'both', 'few', 'more',
    'most', 'other', 'some', 'such', 'only', 'own', 'same', 'also', 'as',
    'get', 'got', 'here', 'there', 'now', 'new', 'one', 'two', 'first',
    'best', 'top', 'way', 'ways', 'make', 'like', 'need', 'know', 'see',
    'use', 'used', 'using', 'find', 'go', 'going', 'come', 'take', 'look',
    'give', 'good', 'great', 'well', 'still', 'even', 'back', 'right',
    'through', 'much', 'many', 'while', 'during', 'without', 'within',
    'along', 'however', 'yet', 'since', 'because', 'although', 'though',
    'per', 'via', 'vs', 'etc', 'ie', 'eg', 'amp',
}
