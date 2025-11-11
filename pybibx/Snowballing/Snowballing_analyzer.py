import os
import csv
from difflib import get_close_matches

def load_articles(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ File non trovato: {csv_path}")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def find_article_by_title(records, title):
    titles = [r["title"] for r in records if r["title"]]
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
    search_title = input("Inserisci (anche parziale) il titolo dell’articolo da analizzare:\n> ").strip()
    article = find_article_by_title(records, search_title)
    if not article:
        return

    print(f"\n[INFO] Articolo selezionato: {article['title']}")
    scopus_id = article["scopus_id"]

    backward = fetcher.backward_snowball(scopus_id)
    forward = fetcher.forward_snowball(scopus_id)

    print(f"[INFO] Articoli citati (backward): {len(backward)}")
    print(f"[INFO] Articoli citanti (forward): {len(forward)}")

    back_path = os.path.join(base_dir, "snowball_backward.csv")
    fwd_path = os.path.join(base_dir, "snowball_forward.csv")

    fetcher.save_csv(backward, back_path)
    fetcher.save_csv(forward, fwd_path)

    print("\n✅ Analisi completata. File salvati:")
    print(f" - Citati:   {back_path}")
    print(f" - Citanti:  {fwd_path}")
