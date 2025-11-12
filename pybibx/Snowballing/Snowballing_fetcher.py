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

    # ---------------- Backward snowballing (Full Text API + CrossRef) ----------------
    def backward_snowball(self, scopus_id, doi=None):
        """
        Recupera gli articoli CITATI (backward snowballing) da un paper Scopus.
        1️⃣ Prova a usare la Full Text API di Scopus (view=FULL)
        2️⃣ Se fallisce, fa fallback su CrossRef (se il DOI è noto)
        """
        refs = []

        # ===== 1️⃣ Full Text API Scopus =====
        try:
            url = self.base_abstract_url + scopus_id
            params = {"view": "FULL"}
            r = requests.get(url, headers=self.headers, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json().get("abstracts-retrieval-response", {})
                ref_list = (
                    data.get("item", {})
                        .get("bibrecord", {})
                        .get("tail", {})
                        .get("bibliography", {})
                        .get("reference", [])
                )
                for ref in ref_list:
                    title = ref.get("ref-info", {}).get("ref-title", {}).get("title") or ""
                    authors = "; ".join(
                        [a.get("authname") for a in ref.get("author", []) if a.get("authname")]
                    )
                    year = ref.get("ref-info", {}).get("year") or ""
                    doi_ref = ref.get("ref-info", {}).get("doi") or ""
                    refs.append({
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "doi": doi_ref
                    })
                if refs:
                    print(f"[INFO] Trovati {len(refs)} riferimenti via Full Text API Scopus.")
            else:
                print(f"[WARN] Full Text API Scopus non disponibile ({r.status_code}).")
        except Exception as e:
            print(f"[ERROR] Errore chiamata Full Text API Scopus: {e}")

        # ===== 2️⃣ Fallback su CrossRef =====
        if not refs and doi:
            try:
                print(f"[INFO] Tentativo fallback CrossRef per DOI {doi}...")
                url_crossref = f"https://api.crossref.org/works/{doi}"
                r = requests.get(url_crossref, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    cross_refs = data.get("message", {}).get("reference", [])
                    for ref in cross_refs:
                        refs.append({
                            "title": ref.get("unstructured") or ref.get("article-title") or "[no title]",
                            "authors": ref.get("author", "[no author]"),
                            "year": ref.get("year", "[no year]"),
                            "doi": ref.get("DOI", "")
                        })
                    print(f"[INFO] Trovati {len(refs)} riferimenti via CrossRef.")
                else:
                    print(f"[WARN] Nessun riferimento disponibile su CrossRef ({r.status_code}).")
            except Exception as e:
                print(f"[ERROR] Errore chiamata CrossRef: {e}")

        if not refs:
            print(f"[WARN] Nessun riferimento trovato per {scopus_id} (Full Text + CrossRef falliti).")

        return refs

    # ---------------- Forward snowballing ----------------
    def forward_snowball(self, scopus_id, origin_title="", origin_year=""):
        """
        Recupera tutti gli articoli che citano lo scopus_id dato.
        Salva sempre il record, anche se incompleto.
        """
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
