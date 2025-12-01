# Snowballing_analyzer.py
import os
import csv
from difflib import get_close_matches
import re

def load_articles(csv_path):
    """Load articles from the main CSV of the initial query."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ File not found: {csv_path}")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def normalize_title(title):
    """Remove extra spaces and non-significant characters."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"\s+", " ", title)       # reduce multiple spaces
    title = re.sub(r"[^\w\s]", "", title)    # remove punctuation
    return title.strip()

def find_article_by_title(records, input_title):
    """Search for an article in the CSV by title (fuzzy match)."""
    normalized_titles = [normalize_title(r.get("title", "")) for r in records]
    norm_input = normalize_title(input_title)

    matches = get_close_matches(norm_input, normalized_titles, n=1, cutoff=0.6)
    if not matches:
        print("❌ No article found with this title.")
        return None

    match_norm_title = matches[0]
    for r in records:
        if normalize_title(r.get("title", "")) == match_norm_title:
            return r

    return None
