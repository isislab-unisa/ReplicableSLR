"""
snowballing.py

Modulo principale per gestire l'attività di snowballing su articoli Scopus.
Fornisce:
- conversione da DOI a EID (usando utils.ScopusAPI)
- recupero degli articoli citati (backward snowballing)
- recupero degli articoli citanti (forward snowballing), con paginazione automatica
- conteggio citazioni ricevute
Tutti i dati vengono memorizzati nella cache per efficienza.
"""

from pybibx.scopus.snowballing.utils import ScopusAPI

class ScopusSnowballing:
    def __init__(self, api_key):
        """
        Inizializza con chiave API e crea un'istanza di ScopusAPI per gestire le richieste.
        """
        self.api = ScopusAPI(api_key)
    
    def _normalize_id(self, identifier):
        """
        Data una stringa (DOI o EID), restituisce l'EID corrispondente.
        - Se DOI (inizia con "10."), converte in EID tramite API.
        - Se già EID (es. "2-s2.0-..."), ritorna così com'è.
        - Altrimenti solleva errore.
        """
        if identifier.startswith("10."):  # DOI tipico
            return self.api.get_eid_from_doi(identifier)
        elif identifier.startswith("2-s2.0-"):
            return identifier
        else:
            raise ValueError("Identificatore non valido. Inserire DOI o EID.")
    
    def get_cited_references(self, identifier):
        """
        Recupera gli articoli citati dall'articolo specificato (backward snowballing).
        Ritorna lista di dizionari con title, eid e doi dei riferimenti.
        Usa cache per salvare i dati.
        """
        eid = self._normalize_id(identifier)
        key = f"backward-{eid}"
        cached = self.api._load_cache(key)
        if cached is not None:
            return cached
        
        url = f"{self.api.BASE_URL}/abstract/scopus_id/{eid}"
        data = self.api.get_json(url)
        
        refs = []
        try:
            # Accesso profondo nella risposta JSON agli elenchi riferimenti
            ref_list = data["abstracts-retrieval-response"]["references"]["reference"]
            for ref in ref_list:
                refs.append({
                    "title": ref.get("ref-title", "Unknown"),
                    "eid": ref.get("ref-eid"),
                    "doi": ref.get("ref-doi")
                })
        except KeyError:
            # Nessun riferimento trovato (articolo senza references)
            pass
        
        self.api._save_cache(key, refs)
        return refs
    
    def get_citing_documents(self, identifier):
        """
        Recupera gli articoli che citano quello dato (forward snowballing).
        Usa paginazione automatica (start/count).
        Ritorna lista di dizionari con title, eid e doi dei citanti.
        """
        eid = self._normalize_id(identifier)
        citing = []
        start = 0
        count = 25  # dimensione pagina API Scopus
        total = None
        
        while total is None or start < total:
            params = {
                "query": f"REFEID({eid})",
                "count": count,
                "start": start
            }
            key = f"forward-{eid}-start{start}"
            cached = self.api._load_cache(key)
            if cached is not None:
                data = cached
            else:
                url = f"{self.api.BASE_URL}/search/scopus"
                data = self.api.get_json(url, params)
                self.api._save_cache(key, data)
            
            results = data.get("search-results", {})
            total = int(results.get("opensearch:totalResults", 0))
            entries = results.get("entry", [])
            for entry in entries:
                citing.append({
                    "title": entry.get("dc:title", "Unknown"),
                    "eid": entry.get("eid"),
                    "doi": entry.get("prism:doi")
                })
            start += count
        
        return citing
    
    def get_citation_count(self, identifier):
        """
        Recupera il numero totale di citazioni ricevute da un articolo.
        Estrae il campo "citedby-count" dall'abstract.
        """
        eid = self._normalize_id(identifier)
        key = f"citcount-{eid}"
        cached = self.api._load_cache(key)
        if cached is not None:
            return cached
        
        url = f"{self.api.BASE_URL}/abstract/scopus_id/{eid}"
        data = self.api.get_json(url)
        try:
            count = int(data["abstracts-retrieval-response"]["coredata"]["citedby-count"])
        except (KeyError, ValueError):
            count = 0
        
        self.api._save_cache(key, count)
        return count
