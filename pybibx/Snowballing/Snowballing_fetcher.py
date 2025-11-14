# Snowballing_fetcher.py
import requests
import time
import csv
import os
from backward_snowballing import BackwardSnowball

class SnowballingFetcher:
    def __init__(self, api_key, per_page=25, max_retries=3, cookies=None):
        self.base_search_url = "https://api.elsevier.com/content/search/scopus"
        self.base_abstract_url = "https://api.elsevier.com/content/abstract/scopus_id/"
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": api_key
        }
        self.per_page = per_page
        self.max_retries = max_retries
        # cookies can be dict or list (selenium format); keep as-is and transform when needed
        if cookies is None:
            self.cookies = {}
        elif isinstance(cookies, dict):
            self.cookies = cookies
        else:
            # list of cookie dicts from selenium
            self.cookies = {c["name"]: c["value"] for c in cookies}

        # lazy import of BackwardSnowball to avoid import cycles; will be used when needed
        self._backward_impl = None

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

    # ---------------- Backward snowballing (integrated) ----------------
    def backward_snowball(self, scopus_id, doi=None):
        """
        Wrapper che prova:
         - scraping Scopus autenticato (usando cookie salvati)
         - fallback DOI from Abstract API -> CrossRef
        """
        # lazy import: evita dipendenze non richieste se non usi backward
        if self._backward_impl is None:
            try:
                self._backward_impl = BackwardSnowball(api_key=self.headers.get("X-ELS-APIKey"), cookies=self.cookies)
            except Exception as e:
                print(f"[ERROR] Impossibile inizializzare BackwardSnowball: {e}")
                return []

        # prova con l'implementazione combinata
        try:
            refs = self._backward_impl.backward(scopus_id)
            return refs
        except Exception as e:
            print(f"[ERROR] backward_snowball fallito: {e}")
            return []

    # ---------------- Forward snowballing ----------------
    def forward_snowball(self, scopus_id, origin_title="", origin_year=""):
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
                title = e.get("dc:title") or e.get("title") or "[missing]"
                authors = e.get("dc:creator") or "[missing]"
                doi = e.get("prism:doi") or "[missing]"
                year = e.get("prism:coverDate") or e.get("prism:coverDisplayDate") or "[missing]"
                source = e.get("prism:publicationName") or "[missing]"

                url = ""
                links = e.get("link", [])
                if isinstance(links, list):
                    for l in links:
                        if "@href" in l:
                            url = l["@href"]
                            break
                if not url:
                    url = "[missing]"

                results.append({
                    "scopus_id": citing_id or "[missing]",
                    "title": title,
                    "authors": authors,
                    "doi": doi,
                    "year": year,
                    "source": source,
                    "url": url,
                    "origin_title": origin_title,
                    "origin_year": origin_year
                })

            start += len(entries)
            total = int(data.get("search-results", {}).get("opensearch:totalResults", 0))
            if start >= total:
                break
            time.sleep(1)

        return results

    # ---------------- Salvataggio CSV ----------------
    def append_csv(self, records, path, origin_title, origin_year, mode="a"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not records:
            print(f"[INFO] Nessun record da scrivere per {origin_title}, CSV rimane intatto.")
            return

        fieldnames = list(records[0].keys())
        file_exists = os.path.exists(path)

        with open(path, mode, newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists or mode == "w":
                writer.writeheader()
            for r in records:
                writer.writerow(r)

        print(f"[INFO] Aggiunti {len(records)} record a {path}")
