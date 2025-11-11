# snowballing_fetcher.py
import requests
import time
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

class SnowballingFetcher:
    def __init__(self, api_key, per_page=25, max_retries=3):
        """
        api_key: API Key Elsevier
        per_page: numero di risultati per pagina (max 25/200)
        max_retries: tentativi per errori temporanei
        """
        self.base_search_url = "https://api.elsevier.com/content/search/scopus"
        self.base_abstract_url = "https://api.elsevier.com/content/abstract/scopus_id/"
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": api_key
        }
        self.per_page = per_page
        self.max_retries = max_retries

    # ---------------------------------------------------------
    # QUERY PRINCIPALE
    # ---------------------------------------------------------
    def fetch_query(self, query):
        results = []
        start = 0
        total = None

        while True:
            params = {"query": query, "start": start, "count": self.per_page}
            retries = 0

            while retries < self.max_retries:
                r = requests.get(self.base_search_url, headers=self.headers, params=params)
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 30))
                    print(f"[WARN] Rate limit, attendo {retry_after}s...")
                    time.sleep(retry_after + 1)
                    continue
                elif r.status_code >= 500:
                    retries += 1
                    print(f"[WARN] Errore {r.status_code} (tentativo {retries}/{self.max_retries}) su start={start}.")
                    time.sleep(3)
                    continue
                elif r.status_code != 200:
                    print(f"[ERROR] Status {r.status_code} per start={start}")
                    r.raise_for_status()
                break
            else:
                print(f"[ERROR] Falliti {self.max_retries} tentativi su start={start}. Stop.")
                break

            data = r.json()
            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                print("[INFO] Nessun altro risultato.")
                break

            for e in entries:
                results.append({
                    "scopus_id": e.get("dc:identifier", "").replace("SCOPUS_ID:", ""),
                    "eid": e.get("eid", ""),
                    "title": e.get("dc:title") or "",
                    "authors": e.get("dc:creator") or "",
                    "doi": e.get("prism:doi") or "",
                    "year": e.get("prism:coverDate") or "",
                    "source": e.get("prism:publicationName") or "",
                    "url": e.get("link", [{}])[0].get("@href") or ""
                })

            start += len(entries)
            total = int(data.get("search-results", {}).get("opensearch:totalResults", 0))
            print(f"[INFO] Recuperati {start}/{total} risultati...")
            if start >= total:
                break
            time.sleep(1)

        print(f"[INFO] Totale risultati recuperati: {len(results)}")
        return results

    # ---------------------------------------------------------
    # DETTAGLI ARTICOLO
    # ---------------------------------------------------------
    def get_article_details(self, scopus_id):
        url = self.base_abstract_url + scopus_id
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            print(f"[WARN] Articolo {scopus_id} non recuperato.")
            return {}
        data = r.json().get("abstracts-retrieval-response", {})
        core = data.get("coredata", {})
        return {
            "scopus_id": scopus_id,
            "title": core.get("dc:title", ""),
            "authors": core.get("dc:creator", ""),
            "doi": core.get("prism:doi", ""),
            "year": core.get("prism:coverDate", ""),
            "source": core.get("prism:publicationName", ""),
            "citedby_count": int(core.get("citedby-count", 0)),
            "reference_count": int(core.get("reference-count", 0)),
            "url": f"https://www.scopus.com/record/display.uri?eid=2-s2.0-{scopus_id}"
        }

    # ---------------------------------------------------------
    # BACKWARD SNOWBALLING
    # ---------------------------------------------------------
    def backward_snowball(self, scopus_id):
        url = self.base_abstract_url + scopus_id
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            print(f"[WARN] Articolo {scopus_id} non trovato per backward snowballing.")
            return []
        data = r.json().get("abstracts-retrieval-response", {})
        refs = data.get("item", {}).get("bibrecord", {}).get("tail", {}).get("bibliography", {}).get("reference", [])
        results = []
        for ref in refs:
            results.append({
                "title": ref.get("ref-title", {}).get("title", ""),
                "authors": "; ".join([a.get("authname") for a in ref.get("author", [])]) if ref.get("author") else "",
                "year": ref.get("ref-info", {}).get("year", ""),
                "doi": ref.get("ref-info", {}).get("doi", "")
            })
        return results

    # ---------------------------------------------------------
    # FORWARD SNOWBALLING
    # ---------------------------------------------------------
    def forward_snowball(self, scopus_id):
        if not scopus_id:
            print("[WARN] Scopus ID non disponibile per forward snowballing.")
            return []

        results = []
        start = 0

        while True:
            params = {"query": f"REF({scopus_id})", "start": start, "count": self.per_page}
            r = requests.get(self.base_search_url, headers=self.headers, params=params)

            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 30))
                print(f"[WARN] Rate limit, attendo {retry_after}s...")
                time.sleep(retry_after + 1)
                continue
            elif r.status_code == 400:
                print(f"[WARN] REF query non valida per {scopus_id}")
                break
            elif r.status_code >= 500:
                print(f"[WARN] Errore server {r.status_code} su REF({scopus_id}).")
                time.sleep(3)
                continue

            data = r.json()
            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                break

            for e in entries:
                citing_id = e.get("dc:identifier", "").replace("SCOPUS_ID:", "")
                results.append({
                    "scopus_id": citing_id,
                    "title": e.get("dc:title") or "",
                    "authors": e.get("dc:creator") or "",
                    "doi": e.get("prism:doi") or "",
                    "year": e.get("prism:coverDate") or "",
                    "source": e.get("prism:publicationName") or "",
                    "url": e.get("link", [{}])[0].get("@href") or ""
                })

            start += len(entries)
            total = int(data.get("search-results", {}).get("opensearch:totalResults", 0))
            if start >= total:
                break
            time.sleep(1)

        print(f"[INFO] Forward snowballing: trovati {len(results)} articoli citanti")
        return results

    # ---------------------------------------------------------
    # SALVATAGGIO FILE
    # ---------------------------------------------------------
    def save_csv(self, records, path):
        fieldnames = ["scopus_id", "eid", "title", "authors", "doi", "year", "source", "url"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"[INFO] File CSV salvato come: {path}")

    def save_bib(self, records, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for i, rec in enumerate(records):
                key = f"scopus{i+1}"
                title = (rec.get('title') or "").replace('{', '\\{').replace('}', '\\}')
                authors = (rec.get('authors') or "").replace('{', '\\{').replace('}', '\\}')
                year = ''
                if rec.get('year'):
                    try:
                        year = datetime.strptime(rec['year'], '%Y-%m-%d').year
                    except Exception:
                        year = rec['year'][:4]
                entry = f"""@article{{{key},
  title={{ {title} }},
  author={{ {authors} }},
  journal={{ {rec.get('source', '')} }},
  year={{ {year} }},
  doi={{ {rec.get('doi', '')} }},
  url={{ {rec.get('url', '')} }}
}}

"""
                f.write(entry)
        print(f"[INFO] File BibTeX salvato come: {path}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    load_dotenv(r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\Snowballing\scopus_key.env")
    API_KEY = os.getenv("SCOPUS_API_KEY")
    if not API_KEY:
        raise ValueError("⚠️ SCOPUS_API_KEY non trovata!")

    fetcher = SnowballingFetcher(API_KEY, per_page=25)

    query = 'TITLE-ABS-KEY("cloud computing" AND "ontology")'
    records = fetcher.fetch_query(query)

    base_dir = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\Snowballing"
    fetcher.save_csv(records, os.path.join(base_dir, "scopus_query.csv"))
    fetcher.save_bib(records, os.path.join(base_dir, "scopus_query.bib"))

    if records:
        scopus_id = records[0]["scopus_id"]
        backward = fetcher.backward_snowball(scopus_id)
        forward = fetcher.forward_snowball(scopus_id)
        print(f"[INFO] Backward snowballing ({len(backward)} articoli citati)")
        print(f"[INFO] Forward snowballing ({len(forward)} articoli citanti)")
