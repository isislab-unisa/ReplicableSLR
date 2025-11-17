# main_simple.py
"""
Unified Academic Fetcher - CLI version
- Permette di scegliere tra Scopus, GitHub, Zenodo
- Inserire query da console
- Salva risultati puliti in CSV nella cartella fetcher-results
"""

import os
import pandas as pd
import re
from datetime import datetime

from github_multifetcher_filtered import GitHubFetcher
from Zenodo_fetcher import ZenodoFetcher
from Scopus_Fetcher import ScopusFetcher

# ---------------------------
# Utilities
# ---------------------------
def clean_html(text):
    """Rimuove tag HTML e decode entità comuni; preserva testo pulito."""
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return s.strip()

def save_csv(records, engine_name):
    """Salva records come CSV in fetcher-results"""
    if not records:
        print("⚠️ Nessun record da salvare.")
        return
    df = pd.DataFrame(records)
    os.makedirs("C:\\Users\\maria\\Desktop\\ReplicableSLR\\pybibx\\fetcher-results", exist_ok=True)
    filename = f"C:\\Users\\maria\\Desktop\\ReplicableSLR\\pybibx\\fetcher-results\\{engine_name.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"✅ Risultati salvati in {filename}")

# ---------------------------
# Main CLI
# ---------------------------
def main():
    print("=== Unified Academic Fetcher (CLI) ===")
    engines = ["Scopus", "GitHub", "Zenodo"]
    print("Scegli il motore di ricerca:")
    for i, e in enumerate(engines, start=1):
        print(f"{i}. {e}")
    
    while True:
        choice = input("Inserisci il numero del motore (1-3): ").strip()
        if choice in ["1", "2", "3"]:
            engine = engines[int(choice)-1]
            break
        else:
            print("⚠️ Scelta non valida. Riprova.")

    while True:
        query = input(f"Inserisci la query per {engine}: ").strip()
        if query:
            break
        print("⚠️ La query non può essere vuota. Riprova.")

    # Chiedi eventuali credenziali
    github_token = None
    scopus_api_key = None
    if engine == "GitHub":
        github_token = input("GitHub token (opzionale, premi invio se non disponibile): ").strip() or None
    if engine == "Scopus":
        scopus_api_key = input("Scopus API Key (necessaria): ").strip()
        if not scopus_api_key:
            print("❌ API Key richiesta. Uscita.")
            return

    # Recupero risultati
    print(f"🚀 Eseguo ricerca su {engine}...")
    try:
        if engine == "GitHub":
            fetcher = GitHubFetcher(token=github_token)
            records = fetcher.fetch(query, max_results=5000)
        elif engine == "Zenodo":
            fetcher = ZenodoFetcher()
            records = fetcher.fetch(query, max_results=5000)
        elif engine == "Scopus":
            fetcher = ScopusFetcher(api_key=scopus_api_key)
            records = fetcher.fetch(query)
        else:
            print("❌ Motore non supportato.")
            return
    except Exception as e:
        print(f"❌ Errore durante la chiamata al motore: {e}")
        return

    # Pulizia HTML
    clean_records = []
    for rec in records:
        clean_rec = {k: clean_html(rec.get(k, "")) for k in rec.keys()}
        clean_records.append(clean_rec)

    print(f"✅ Recuperati {len(clean_records)} risultati da {engine}")
    save_csv(clean_records, engine)

if __name__ == "__main__":
    main()
