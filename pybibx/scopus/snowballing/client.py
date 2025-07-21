import requests
import csv
import os


class ScopusSnowballing:
    BASE_URL = "https://api.elsevier.com/content"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key
        }

    def _get_eid_from_identifier(self, identifier: str) -> str:
        if identifier.startswith("2-s2.0-"):
            return identifier
        url = f"{self.BASE_URL}/search/scopus"
        params = {"query": f"DOI({identifier})"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        results = r.json().get("search-results", {}).get("entry", [])
        if not results:
            raise ValueError(f"DOI non trovato: {identifier}")
        return results[0].get("eid")

    def get_citations_count(self, identifier: str) -> int:
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/abstract/eid/{eid}"
        params = {"field": "citedby-count"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        data = r.json()
        return int(data['abstracts-retrieval-response']['coredata'].get('citedby-count', 0))

    def get_forward_citations(self, identifier: str, max_results: int = 25) -> list:
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/search/scopus"
        params = {"query": f"refeid({eid})", "count": max_results}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json().get('search-results', {}).get('entry', [])

    def get_references(self, identifier: str) -> list:
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/abstract/eid/{eid}"
        params = {"view": "REF"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json().get('abstracts-retrieval-response', {}).get('references', {}).get('reference', [])

    def save_forward_to_csv(self, identifier: str, filename: str = "forward_citations.csv", max_results: int = 25):
        forward = self.get_forward_citations(identifier, max_results)
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Authors", "Publication Name", "Date", "DOI"])
            for entry in forward:
                writer.writerow([
                    entry.get("dc:title", ""),
                    entry.get("dc:creator", ""),
                    entry.get("prism:publicationName", ""),
                    entry.get("prism:coverDate", ""),
                    entry.get("prism:doi", "")
                ])
        print(f"[✓] Forward citations salvati in {filename}")

    def save_backward_to_csv(self, identifier: str, filename: str = "backward_references.csv"):
        references = self.get_references(identifier)
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Authors", "Source Title", "Publication Year"])
            for ref in references:
                writer.writerow([
                    ref.get("ref-title", ""),
                    ref.get("ref-authors", ""),
                    ref.get("source-title", ""),
                    ref.get("publicationyear", "")
                ])
        print(f"[✓] Backward references salvati in {filename}")
