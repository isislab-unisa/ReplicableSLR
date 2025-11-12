import os
import csv
from difflib import get_close_matches


def load_articles(csv_path):
    """Carica articoli dal CSV principale della query iniziale."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ File non trovato: {csv_path}")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def find_article_by_title(records, title):
    """Cerca un articolo nel CSV per titolo (match fuzzy)."""
    titles = [r["title"] for r in records if r.get("title")]
    matches = get_close_matches(title.lower(), [t.lower() for t in titles], n=1, cutoff=0.6)
    if not matches:
        print("❌ Nessun articolo trovato con questo titolo.")
        return None

    match_title = matches[0]
    for r in records:
        if r["title"].lower() == match_title:
            return r
    return None


def analyze_article(fetcher, records, base_dir):
    """Esegue backward e forward snowballing per l’articolo selezionato."""
    search_title = input("Inserisci (anche parziale) il titolo dell’articolo da analizzare:\n> ").strip()
    article = find_article_by_title(records, search_title)
    if not article:
        return

    print(f"\n[INFO] Articolo selezionato: {article['title']}")
    scopus_id = article["scopus_id"]
    origin_title = article["title"]
    origin_year = article.get("year", "")

    # --- Backward e Forward Snowballing ---
    backward = fetcher.backward_snowball(scopus_id)
    forward = fetcher.forward_snowball(scopus_id, origin_title, origin_year)

    print(f"[INFO] Articoli citati (backward): {len(backward)}")
    print(f"[INFO] Articoli citanti (forward): {len(forward)}")

    # --- Percorsi file ---
    back_path = os.path.join(base_dir, "snowball_backward.csv")
    fwd_path = os.path.join(base_dir, "snowball_forward.csv")

    # --- Salvataggio progressivo ---
    fetcher.append_csv(backward, back_path, origin_title, origin_year)
    fetcher.append_csv(forward, fwd_path, origin_title, origin_year)

    print("\n✅ Iterazione completata.")
    print(f" - Citati salvati in:  {back_path}")
    print(f" - Citanti salvati in: {fwd_path}")
