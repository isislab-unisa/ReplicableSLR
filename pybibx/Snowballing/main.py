# main.py
import os
from dotenv import load_dotenv
import sys
BASE_DIR = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx"
sys.path.append(os.path.join(BASE_DIR, "fetcher"))
from fetcher.Scopus_Fetcher import ScopusFetcher
from Snowballing_analyzer import load_articles, find_article_by_title
from backward_snowballing import BackwardSnowball

# ---------------- CONFIG ----------------
BASE_DIR = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx"
CSV_PATH = os.path.join(BASE_DIR, "scopus_query.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "Results_Snowballing")
BACKWARD_CSV = os.path.join(RESULTS_DIR, "backward_snowballing.csv")
ENV_PATH = os.path.join(BASE_DIR, "scopus_key.env")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ---------------- LOAD API KEY ----------------
load_dotenv(ENV_PATH)
API_KEY = os.getenv("SCOPUS_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ SCOPUS_API_KEY non trovata!")

# ---------------- COSTRUISCI QUERY ----------------
print("Inserisci la query per Scopus (TITLE-ABS-KEY, AND, OR, NOT, ecc.)")
query = input("> ").strip()
if not query:
    raise ValueError("Query non può essere vuota")

# ---------------- FETCH RESULTS ----------------
fetcher = ScopusFetcher(api_key=API_KEY, per_page=25)
records = fetcher.fetch(query)
fetcher.save_csv(records, CSV_PATH)
print(f"[INFO] Risultati salvati in {CSV_PATH}")

# ---------------- LOAD CSV ----------------
records = load_articles(CSV_PATH)

# ---------------- SELEZIONE ARTICOLO ----------------
search_title = input("Inserisci il titolo dell'articolo su cui fare backward snowballing:\n> ").strip()
article = find_article_by_title(records, search_title)
if not article:
    print("❌ Articolo non trovato nel CSV. Esci.")
    exit(1)

scopus_id = article["scopus_id"]
print(f"[INFO] Articolo selezionato: {article['title']} (SCOPUS ID: {scopus_id})")

# ---------------- BACKWARD SNOWBALLING ----------------
backward = BackwardSnowball(API_KEY).backward(scopus_id)
print(f"[INFO] Articoli citati (backward) trovati: {len(backward)}")

# ---------------- SALVATAGGIO ----------------
if backward:
    fieldnames = list(backward[0].keys())
    os.makedirs(os.path.dirname(BACKWARD_CSV), exist_ok=True)
    import csv
    with open(BACKWARD_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(backward)
    print(f"[INFO] Backward snowballing salvato in {BACKWARD_CSV}")
else:
    print("[INFO] Nessun articolo citato trovato")
