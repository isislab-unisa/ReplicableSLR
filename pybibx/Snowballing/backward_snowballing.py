# backward_snowballing.py
import requests

class BackwardSnowball:
    """
    Recupera i references di un articolo Scopus dato il suo SCOPUS ID.
    Usa l'Abstract Retrieval API di Scopus e, se non disponibili, fa fallback su CrossRef tramite DOI.
    Restituisce lista di dict con: title, authors, doi, year, source.
    """

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key Scopus richiesta")
        self.api_key = api_key
        self.base_url = "https://api.elsevier.com/content/abstract/scopus_id/{scopus_id}?view=FULL"
        self.headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        self.crossref_url = "https://api.crossref.org/works/{doi}"

    def backward(self, scopus_id):
        if not scopus_id:
            raise ValueError("SCOPUS ID non fornito")

        references = []

        # 🔹 1) Abstract Retrieval API Scopus
        url = self.base_url.format(scopus_id=scopus_id)
        doi_main = None
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code == 200:
                data = r.json()

                # Salvo il DOI principale per fallback CrossRef
                doi_main = data.get("abstracts-retrieval-response", {}) \
                               .get("coredata", {}) \
                               .get("prism:doi", None)

                # Lista references
                ref_list = data.get("abstracts-retrieval-response", {}) \
                               .get("references", {}) \
                               .get("reference", [])

                for ref in ref_list:
                    ref_info = ref.get("ref-info", {})
                    title = ref_info.get("ref-title", {}).get("content", "")
                    
                    authors = ""
                    if "ref-authors" in ref and ref["ref-authors"]:
                        authors_list = ref["ref-authors"].get("author", [])
                        authors = "; ".join([a.get("ce:indexed-name", "") for a in authors_list if a])

                    doi = ref_info.get("ref-doi", "")
                    year = ref_info.get("ref-publicationyear", "")
                    source = ref_info.get("ref-publicationname", "")

                    references.append({
                        "title": title,
                        "authors": authors,
                        "doi": doi,
                        "year": year,
                        "source": source
                    })
            else:
                print(f"[WARN] Abstract API fallita per {scopus_id}, status {r.status_code}")

        except Exception as e:
            print(f"[ERROR] Errore durante il recupero Scopus: {e}")

        # 🔹 2) Fallback CrossRef se non ci sono references e c'è DOI
        if not references and doi_main:
            print(f"[INFO] Nessun reference trovato in Scopus, provo CrossRef per DOI {doi_main}")
            try:
                r = requests.get(self.crossref_url.format(doi=doi_main))
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("message", {}).get("reference", [])
                    for ref in items:
                        references.append({
                            "title": ref.get("article-title", ""),
                            "authors": ref.get("author", ""),
                            "doi": ref.get("DOI", ""),
                            "year": ref.get("year", ""),
                            "source": ref.get("journal-title", "")
                        })
                else:
                    print(f"[WARN] CrossRef fallita per DOI {doi_main}, status {r.status_code}")
            except Exception as e:
                print(f"[ERROR] Errore durante il fallback CrossRef: {e}")

        if not references:
            print(f"[INFO] Nessun reference recuperato per SCOPUS ID {scopus_id}")

        return references
