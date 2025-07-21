import requests


class ScopusSnowballing:
    BASE_URL = "https://api.elsevier.com/content"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key
        }

    def _get_eid_from_identifier(self, identifier: str) -> str:
        """
        Ritorna l'EID dato un identificatore. Se è già un EID, lo ritorna.
        Se è un DOI, lo converte in EID.
        """
        if identifier.startswith("2-s2.0-"):
            return identifier  # Già un EID

        # Altrimenti assumiamo sia DOI
        url = f"{self.BASE_URL}/search/scopus"
        params = {"query": f"DOI({identifier})"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        results = r.json().get("search-results", {}).get("entry", [])
        if not results:
            raise ValueError(f"DOI non trovato: {identifier}")
        return results[0].get("eid")

    def get_citations_count(self, identifier: str) -> int:
        """
        Restituisce il numero totale di citazioni ricevute da un articolo, dato un DOI o EID.
        """
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/abstract/eid/{eid}"
        params = {"field": "citedby-count"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        data = r.json()
        count = data['abstracts-retrieval-response']['coredata'].get('citedby-count', 0)
        return int(count)

    def get_forward_citations(self, identifier: str, max_results: int = 25) -> list:
        """
        Restituisce gli articoli che citano quello dato (forward snowballing).
        Accetta DOI o EID.
        """
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/search/scopus"
        query = f"refeid({eid})"
        params = {
            "query": query,
            "count": max_results
        }
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json().get('search-results', {}).get('entry', [])

    def get_references(self, identifier: str) -> list:
        """
        Restituisce gli articoli citati da quello dato (backward snowballing).
        Accetta DOI o EID.
        """
        eid = self._get_eid_from_identifier(identifier)
        url = f"{self.BASE_URL}/abstract/eid/{eid}"
        params = {"view": "REF"}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json().get('abstracts-retrieval-response', {}).get('references', {}).get('reference', [])
