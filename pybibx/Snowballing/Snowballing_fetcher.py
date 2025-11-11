import requests
import time
import csv
import os

class SnowballingFetcher:
    def __init__(self, api_key, per_page=25, max_retries=3):
        self.base_search_url = "https://api.elsevier.com/content/search/scopus"
        self.base_abstract_url = "https://api.elsevier.com/content/abstract/scopus_id/"
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": api_key
        }
        self.per_page = per_page
        self.max_retries = max_retries

    # ---------------- Query principale ----------------
    def fetch_query(self, query):
        results = []
        start = 0
        while True:
            params = {"query": query, "start": start, "count": self.per_page}
            r = requests.get(self.base_search_url, headers=self.headers, params=params)

            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 30))
                print(f"[WARN] Rate limit, attendo {retry_after}s...")
                time.sleep(retry_after + 1)
                continue
            elif r.status_code >= 500:
                print(f"[WARN] Errore {r.status_code}, riprovo...")
                time.sleep(3)
                continue
            elif r.status_code != 200:
                print(f"[ERROR] Status {r.status_code}")
                break

            data = r.json()
            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
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

    # ---------------- Backward snowballing ----------------
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
                "scopus_id": "",  # non disponibile nel backward
                "eid": "",
                "title": ref.get("ref-title", {}).get("title", ""),
                "authors": "; ".join([a.get("authname") for a in ref.get("author", [])]) if ref.get("author") else "",
                "doi": ref.get("ref-info", {}).get("doi", ""),
                "year": ref.get("ref-info", {}).get("year", ""),
                "source": "",
                "url": ""
            })
        return results

    # ---------------- Forward snowballing ----------------
    def forward_snowball(self, scopus_id):
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
            if start >= total:
                break
            time.sleep(1)

        return results

    # ---------------- Salvataggio CSV ----------------
    def save_csv(self, records, path):
        records = [r for r in records if r.get("title") or r.get("scopus_id")]
        if not records:
            print(f"[WARN] Nessun record valido da salvare in {path}")
            return
        fieldnames = ["scopus_id", "eid", "title", "authors", "doi", "year", "source", "url"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"[INFO] File CSV salvato come: {path}")
