import requests
import time
from bs4 import BeautifulSoup

class BackwardSnowball:
    """
    Recupera i riferimenti (References) di un articolo Scopus dato il suo Scopus ID.
    Usa i cookie salvati per l'autenticazione se necessario.
    """
    def __init__(self, cookies=None, api_key=None, per_page=25):
        """
        cookies: dizionario con i cookie di sessione (opzionale)
        api_key: chiave Scopus (per fallback Abstract API)
        """
        self.cookies = cookies
        self.api_key = api_key
        self.per_page = per_page
        self.base_abstract_url = "https://api.elsevier.com/content/abstract/scopus_id/"

    def backward(self, scopus_id):
        """
        Recupera la lista dei riferimenti (References) dell'articolo Scopus ID.
        Ritorna lista di dict con campi principali: title, authors, doi, year, source.
        """
        if not scopus_id:
            raise ValueError("Scopus ID non fornito")

        references = []

        # 🔹 1) Prova con Abstract API (richiede api_key)
        if self.api_key:
            url = f"{self.base_abstract_url}{scopus_id}?view=FULL"
            headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
            try:
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    ref_list = data.get("abstracts-retrieval-response", {}) \
                                   .get("references", {}) \
                                   .get("reference", [])
                    for ref in ref_list:
                        references.append({
                            "title": ref.get("ref-info", {}).get("ref-title", {}).get("content", ""),
                            "authors": "; ".join([a.get("ce:indexed-name", "") for a in ref.get("ref-authors", {}).get("author", [])]) if ref.get("ref-authors") else "",
                            "doi": ref.get("ref-info", {}).get("ref-doi", ""),
                            "year": ref.get("ref-info", {}).get("ref-publicationyear", ""),
                            "source": ref.get("ref-info", {}).get("ref-publicationname", "")
                        })
                    return references
                else:
                    print(f"[WARN] Abstract API fallita per {scopus_id}, status {r.status_code}")
            except Exception as e:
                print(f"[ERROR] Errore API Abstract: {e}")

        # 🔹 2) Fallback scraping (richiede cookie Scopus)
        if self.cookies:
            url = f"https://www.scopus.com/record/display.uri?eid=SCOPUS_ID:{scopus_id}&origin=recordpage"
            try:
                r = requests.get(url, cookies=self.cookies)
                if r.status_code != 200:
                    print(f"[WARN] Pagina HTML Scopus non accessibile: {r.status_code}")
                    return references

                soup = BeautifulSoup(r.text, "html.parser")
                ref_items = soup.select(".reference .docTitle")  # selettore da adattare se cambia HTML
                for item in ref_items:
                    title = item.get_text(strip=True)
                    references.append({"title": title})
                return references
            except Exception as e:
                print(f"[ERROR] Scraping fallito: {e}")

        print(f"[INFO] Nessun riferimento recuperato per {scopus_id}")
        return references
