"""
utils.py

Modulo di supporto per l'interazione con l'API Scopus di Elsevier.
Gestisce:
- le richieste HTTP con caching su file per evitare chiamate ripetute
- la conversione da DOI a EID (identificatore Scopus)
"""

import requests
import os
import json
import hashlib

class ScopusAPI:
    BASE_URL = "https://api.elsevier.com/content"
    
    def __init__(self, api_key, cache_dir="cache"):
        """
        Inizializza l'istanza con la chiave API e la directory di cache.
        Crea la directory di cache se non esiste.
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def headers(self):
        """Restituisce gli header necessari per le richieste API."""
        return {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        }
    
    def _cache_path(self, key):
        """
        Genera un percorso file per la cache basandosi sull'hash MD5 della chiave.
        Serve per avere nomi file sicuri e univoci.
        """
        hashed = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed}.json")
    
    def _load_cache(self, key):
        """
        Prova a caricare dalla cache il contenuto relativo alla chiave.
        Restituisce il contenuto JSON se esiste, altrimenti None.
        """
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def _save_cache(self, key, data):
        """
        Salva i dati serializzati in JSON nel file cache corrispondente alla chiave.
        """
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def get_json(self, url, params=None, use_cache=True):
        """
        Esegue una richiesta GET all'URL specificato con eventuali parametri.
        Usa la cache se abilitata per evitare chiamate ripetute.
        In caso di errore HTTP solleva eccezione.
        """
        key = url + (json.dumps(params, sort_keys=True) if params else "")
        if use_cache:
            cached = self._load_cache(key)
            if cached is not None:
                return cached
        
        response = requests.get(url, headers=self.headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")
        data = response.json()
        
        if use_cache:
            self._save_cache(key, data)
        return data
    
    def get_eid_from_doi(self, doi):
        """
        Converte un DOI in EID (Scopus ID) effettuando una ricerca su Scopus.
        Usa la cache per evitare richieste ripetute.
        """
        key = f"doi2eid-{doi}"
        cached = self._load_cache(key)
        if cached is not None:
            return cached
        
        url = f"{self.BASE_URL}/search/scopus"
        params = {"query": f"DOI({doi})"}
        data = self.get_json(url, params)
        entries = data.get("search-results", {}).get("entry", [])
        if not entries:
            raise Exception(f"No EID found for DOI {doi}")
        eid = entries[0]["eid"]
        self._save_cache(key, eid)
        return eid  
