# Snowballing_analyzer.py
import os
import csv
from difflib import get_close_matches
import re

def load_articles(csv_path):
    """Carica articoli dal CSV principale della query iniziale."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ File non trovato: {csv_path}")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def normalize_title(title):
    """Rimuove spazi extra e caratteri non significativi."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"\s+", " ", title)       # riduce spazi multipli
    title = re.sub(r"[^\w\s]", "", title)    # rimuove punteggiatura
    return title.strip()

def find_article_by_title(records, input_title):
    """Cerca un articolo nel CSV per titolo (match fuzzy)."""
    normalized_titles = [normalize_title(r.get("title", "")) for r in records]
    norm_input = normalize_title(input_title)

    matches = get_close_matches(norm_input, normalized_titles, n=1, cutoff=0.6)
    if not matches:
        print("❌ Nessun articolo trovato con questo titolo.")
        return None

    match_norm_title = matches[0]
    for r in records:
        if normalize_title(r.get("title", "")) == match_norm_title:
            return r

    return None
