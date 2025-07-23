from utils import ScopusAPI

class ScopusSnowballing:
    def __init__(self, api_key):
        self.api = ScopusAPI(api_key)
    
    def _normalize_id(self, identifier):
        # Se DOI, converto in EID
        if identifier.startswith("10."):  # DOI tipico
            return self.api.get_eid_from_doi(identifier)
        elif identifier.startswith("2-s2.0-"):
            return identifier
        else:
            raise ValueError("Identificatore non valido. Inserire DOI o EID.")
    
    def get_cited_references(self, identifier):
        eid = self._normalize_id(identifier)
        url = f"{self.api.BASE_URL}/abstract/scopus_id/{eid}"
        data = self.api.get_json(url)
        
        refs = []
        try:
            ref_list = data["abstracts-retrieval-response"]["references"]["reference"]
            for ref in ref_list:
                refs.append({
                    "title": ref.get("ref-title", "Unknown"),
                    "eid": ref.get("ref-eid"),
                    "doi": ref.get("ref-doi")
                })
        except KeyError:
            # Nessun riferimento trovato
            pass
        return refs
    
    def get_citing_documents(self, identifier):
        eid = self._normalize_id(identifier)
        url = f"{self.api.BASE_URL}/search/scopus"
        query = f"REFEID({eid})"
        params = {"query": query, "count": 100}
        
        data = self.api.get_json(url, params)
        citing = []
        for entry in data.get("search-results", {}).get("entry", []):
            citing.append({
                "title": entry.get("dc:title", "Unknown"),
                "eid": entry.get("eid"),
                "doi": entry.get("prism:doi")
            })
        return citing
    
    def get_citation_count(self, identifier):
        eid = self._normalize_id(identifier)
        url = f"{self.api.BASE_URL}/abstract/scopus_id/{eid}"
        data = self.api.get_json(url)
        try:
            count = int(data["abstracts-retrieval-response"]["coredata"]["citedby-count"])
        except (KeyError, ValueError):
            count = 0
        return count
