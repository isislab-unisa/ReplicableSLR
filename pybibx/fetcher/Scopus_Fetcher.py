import requests
import time
import csv
from datetime import datetime
import os

class ScopusFetcher:
    def __init__(self, api_key, per_page=25, max_retries=3):
        """
        api_key: Elsevier API Key
        per_page: results per page (max 25/200)
        max_retries: number of retries in case of network/rate limit errors
        """
        self.base_url = "https://api.elsevier.com/content/search/scopus"
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": api_key
        }
        self.per_page = per_page
        self.max_retries = max_retries

    def fetch(self, query):
        """
        Retrieves all results for a Scopus query,
        trying to extract as many fields as possible.
        """
        results = []
        start = 0
        total_retrieved = 0

        while True:
            params = {
                "query": query,
                "start": start,
                "count": self.per_page
            }

            for attempt in range(self.max_retries):
                r = requests.get(self.base_url, headers=self.headers, params=params)
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 30))
                    print(f"[WARN] Rate limit reached, waiting {retry_after}s...")
                    time.sleep(retry_after + 1)
                    continue
                elif r.status_code >= 500:
                    print(f"[WARN] Server error {r.status_code}, retrying...")
                    time.sleep(3)
                    continue
                else:
                    break
            else:
                print(f"[ERROR] Unable to complete request for start={start}")
                break

            data = r.json()
            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                break

            for e in entries:
                # extract main fields and "as many as possible"
                results.append({
                    "scopus_id": e.get("dc:identifier", "").replace("SCOPUS_ID:", ""),
                    "eid": e.get("eid", ""),
                    "title": e.get("dc:title") or "",
                    "authors": e.get("dc:creator") or "",
                    "doi": e.get("prism:doi") or "",
                    "year": e.get("prism:coverDate") or "",
                    "source": e.get("prism:publicationName") or "",
                    "volume": e.get("prism:volume") or "",
                    "issue": e.get("prism:issueIdentifier") or "",
                    "pages": e.get("prism:pageRange") or "",
                    "issn": e.get("prism:issn") or "",
                    "isbn": e.get("prism:isbn") or "",
                    "affiliations": e.get("affiliation") or "",
                    "subject_areas": e.get("subject-areas") or "",
                    "references": e.get("citedby-count", 0),  # number of references
                    "citations": e.get("citedby-count", 0),   # number of citations (can differentiate if using another API)
                    "url": e.get("link", [{}])[0].get("@href") or "",
                    "abstract": e.get("dc:description") or "",
                    "language": e.get("language") or "",
                    "publisher": e.get("prism:publisher") or "",
                })

            total_retrieved += len(entries)
            total_results = int(data.get("search-results", {}).get("opensearch:totalResults", 0))
            print(f"[INFO] Retrieved {total_retrieved}/{total_results} results...")

            start += len(entries)
            if start >= total_results:
                break

            time.sleep(1)  # polite pause between requests

        print(f"[INFO] Total results retrieved: {len(results)}")
        return results

    def save_csv(self, records, path):
        if not records:
            print("[WARN] No records to save.")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fieldnames = list(records[0].keys())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"[INFO] CSV saved to: {path}")
