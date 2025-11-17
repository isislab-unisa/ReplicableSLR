"""
Unified Academic Fetcher (Streamlit)
- Unifica fetcher per: GitHub, Zenodo, Scopus
- Permette: scelta campi, pulizia HTML, download CSV/XLSX (tabella Excel formattata, colonne auto-fit)
- Requisiti: streamlit, pandas, requests, openpyxl, python-dotenv
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

# importa i tuoi fetcher (metti i file nella stessa cartella)
from github_multifetcher_filtered import GitHubFetcher
from Zenodo_fetcher import ZenodoFetcher
from Scopus_Fetcher import ScopusFetcher

# ---------------------------
# Utilities
# ---------------------------
def clean_html(text):
    """Rimuove tag HTML e decode entità comuni; preserva testo pulito."""
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return s.strip()

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Esporta DataFrame in CSV UTF-8 with BOM."""
    return df.to_csv(index=False).encode("utf-8-sig")

def to_bib_bytes(records, prefix="entry") -> bytes:
    buf = ""
    for i, rec in enumerate(records):
        key = f"{prefix}{i+1}"
        buf += f"@misc{{{key},\n"
        for k, v in rec.items():
            val = "" if v is None else str(v)
            val = val.replace("{", "\\{").replace("}", "\\}")
            buf += f"  {k} = {{{val}}},\n"
        buf += "}\n\n"
    return buf.encode("utf-8")

def to_xlsx_bytes(df: pd.DataFrame, table_name="ResultsTable") -> bytes:
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    max_col = ws.max_column
    max_row = ws.max_row

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value is None:
                continue
            value = str(cell.value)
            if len(value) > 2000:
                value = value[:2000]
            max_len = max(max_len, len(value))
        width = (max_len + 2) if max_len > 0 else 10
        ws.column_dimensions[col_letter].width = min(width, 100)

    end_col_letter = ws.cell(row=1, column=max_col).column_letter
    range_ref = f"A1:{end_col_letter}{max_row}"
    table = Table(displayName=table_name, ref=range_ref)
    style = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
    table.tableStyleInfo = style
    ws.add_table(table)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()

# ---------------------------
# Field descriptions per motore
# ---------------------------
ENGINE_FIELDS = {
    "GitHub": {
        "title": "Nome del repository",
        "author": "Owner del repository (login)",
        "description": "Descrizione testuale del progetto",
        "created": "Data di creazione (ISO)",
        "updated": "Ultima modifica (ISO)",
        "language": "Linguaggio principale",
        "stars": "Numero di stelle",
        "url": "URL del repository",
        "license": "Nome della licenza (se presente)"
    },
    "Zenodo": {
        "title": "Titolo del dataset / record",
        "author": "Autori (stringa concatenata)",
        "description": "Descrizione del record",
        "created": "Data di pubblicazione",
        "updated": "Data di ultimo aggiornamento",
        "keywords": "Keyword associate",
        "url": "DOI o link html pubblico",
        "license": "Licenza (id o nome)"
    },
    "Scopus": {
        "scopus_id": "ID Scopus dell’articolo",
        "eid": "Elsevier EID",
        "title": "Titolo della pubblicazione",
        "authors": "Autori (stringa)",
        "doi": "Digital Object Identifier",
        "year": "Data di pubblicazione o anno",
        "source": "Nome della rivista / conference",
        "volume": "Volume",
        "issue": "Issue / numero",
        "pages": "Range pagine",
        "issn": "ISSN della rivista",
        "isbn": "ISBN (quando applicabile)",
        "affiliations": "Affiliazioni autori",
        "subject_areas": "Aree tematiche",
        "references": "Numero di references (count) - NOTA: search API restituisce solo count",
        "citations": "Numero di citazioni (count)",
        "url": "Link (es. Scopus URL)",
        "abstract": "Abstract dell'articolo",
        "language": "Lingua",
        "publisher": "Editore"
    }
}

# ---------------------------
# Streamlit UI setup
# ---------------------------
st.set_page_config(page_title="Unified Academic Fetcher", layout="wide", initial_sidebar_state="expanded")
st.title("🔎 Unified Academic Fetcher")
st.markdown(
    "Interfaccia unificata per interrogare **Scopus**, **GitHub** e **Zenodo**. "
    "Scegli il motore, scrivi la query (vedi istruzioni), seleziona campi da mostrare e scarica i risultati in CSV/XLSX."
)

st.divider()

# Sidebar
with st.sidebar:
    st.header("Configurazione")
    engine = st.radio("Motore di ricerca", ["Scopus", "GitHub", "Zenodo"], index=0)
    st.markdown("---")
    st.subheader("Credenziali")
    github_token = st.text_input("GitHub token (opzionale)", type="password") if engine=="GitHub" else None
    scopus_api_key = st.text_input("Elsevier API Key (richiesta per Scopus)", type="password") if engine=="Scopus" else None
    st.markdown("---")
    st.write("Cache & comportamento")
    enable_cache = st.checkbox("Abilita caching (1h)", value=True)
    st.caption("La cache evita chiamate duplicate durante lo sviluppo. Disabilita per forzare nuova richiesta.")
    st.markdown("---")
    st.markdown("Versione: 1.0 — Unified Fetcher")

st.divider()

# Query e campi
st.markdown("### 📘 Istruzioni query")
if engine == "Scopus":
    st.info("Usa la sintassi Scopus (TITLE-ABS-KEY, AUTHLASTNAME, DOI, PUBYEAR, ecc.). Esempi:\n\n"
            "`TITLE-ABS-KEY(\"cloud computing\" AND \"knowledge graph\")`\n"
            "`TITLE(\"virtual machine\") AND PUBYEAR > 2018`\n"
            "`DOI(10.1109/5.771073)`")
elif engine == "GitHub":
    st.info("Usa la sintassi GitHub Search. Esempi:\n\n"
            "`machine learning language:python`\n"
            "`openstack idle detector`\n"
            "`security monitoring stars:>100`")
else:
    st.info("Usa la sintassi Zenodo (tipo Lucene/Elastic). Esempi:\n\n"
            "`title:\"machine learning\"`\n"
            "`keywords:cloud`\n"
            "`creators.name:\"John Smith\"`")

query = st.text_area("Inserisci la query", height=120, placeholder="Scrivi qui la query secondo la sintassi del motore scelto")

with st.expander("📌 Campi disponibili e descrizione", expanded=False):
    st.markdown(f"**Motore selezionato:** {engine}")
    fields = ENGINE_FIELDS[engine]
    for k, v in fields.items():
        st.markdown(f"- **`{k}`** — {v}")

with st.expander("🔧 Seleziona colonne da includere (output)", expanded=True):
    all_fields = list(ENGINE_FIELDS[engine].keys())
    include_all = st.checkbox("Includi tutti i campi", value=True, key="include_all_fields")
    selected_columns = all_fields.copy() if include_all else st.multiselect("Scegli colonne", options=all_fields, default=all_fields[:6])

# ---------------------------
# Caching wrappers
# ---------------------------
if enable_cache:
    cache_decorator = st.cache_data
else:
    def cache_decorator(func):
        return func

@cache_decorator(ttl=3600)
def cached_fetch_github(q, token):
    return GitHubFetcher(token=token).fetch(q, max_results=5000)

@cache_decorator(ttl=3600)
def cached_fetch_zenodo(q):
    return ZenodoFetcher().fetch(q, max_results=5000)

@cache_decorator(ttl=3600)
def cached_fetch_scopus(q, api_key):
    return ScopusFetcher(api_key=api_key).fetch(q)

# ---------------------------
# Tabs
# ---------------------------
tab_run, tab_results, tab_help = st.tabs(["Run search", "Results", "Help & Notes"])

with tab_run:
    st.subheader("🚀 Avvia ricerca")
    col_run_left, col_run_right = st.columns([3,1])
    with col_run_left:
        run = st.button("Avvia ricerca", key="run_search")
    st.caption(
        "Nota: l'app recupera *tutti* i risultati disponibili dai fetcher, tenendo conto di paginazione e caching. "
        "Usa la cache per evitare chiamate duplicate durante lo sviluppo."
    )

    if run:
        if not query.strip():
            st.error("La query è vuota. Inserisci una query valida.")
            st.stop()
        if engine=="Scopus" and not scopus_api_key:
            st.error("Per Scopus è richiesta una API Key nella sidebar.")
            st.stop()

        with st.spinner(f"Eseguo ricerca su {engine}..."):
            try:
                records = (cached_fetch_github(query, github_token) if engine=="GitHub" else
                           cached_fetch_zenodo(query) if engine=="Zenodo" else
                           cached_fetch_scopus(query, scopus_api_key))
            except Exception as e:
                st.error(f"Errore durante la chiamata al motore: {e}")
                st.stop()

        # Pulizia dei record
        clean_records = [{k: clean_html(rec.get(k, "")) for k in rec.keys()} for rec in records]

        # Salvataggio in session state
        st.session_state["last_engine"] = engine
        st.session_state["last_query"] = query
        st.session_state["last_records"] = clean_records

        # Mostra subito il numero di risultati
        st.success(f"✅ Recuperati {len(clean_records)} risultati da {engine}")
        st.info(f"Puoi visualizzarli e scaricarli nella tab 'Results'.")

        st.rerun()  # aggiorna la pagina

with tab_results:
    st.subheader("📄 Risultati")
    records = st.session_state.get("last_records", None)
    last_engine = st.session_state.get("last_engine", engine)

    if not records:
        st.info("Nessuna ricerca eseguita in questa sessione. Vai su 'Run search' e avvia una query.")
    else:
        df = pd.DataFrame(records)

        # Colonne effettive selezionate
        available_columns = df.columns.tolist()
        selected_columns_effective = [c for c in selected_columns if c in available_columns]
        if not selected_columns_effective:
            st.warning("Nessuna delle colonne selezionate è presente nei risultati. Mostro tutte le colonne disponibili.")
            selected_columns_effective = available_columns

        # Mostra motore e query
        st.markdown(f"**Motore:** `{last_engine}`  •  **Query:** `{st.session_state.get('last_query','')}`")

        # Mostra numero totale di risultati trovati
        st.info(f"📊 Risultati totali ottenuti: {len(df)} — colonne disponibili: {len(available_columns)}")

        # Controlli di visualizzazione e download
        with st.expander("🔧 Controlli di visualizzazione e download", expanded=True):
            col1, col2 = st.columns([2, 2])

            with col1:
                # Anteprima tabella
                show_preview = st.checkbox("Mostra anteprima tabella", value=True)
                preview_rows = st.number_input(
                    "Numero righe anteprima",
                    min_value=5,
                    max_value=len(df),
                    value=min(50, len(df)),
                    step=5
                )

            with col2:
                st.markdown("**Download**")
                # CSV
                csv_bytes = to_csv_bytes(df[selected_columns_effective])
                st.download_button(
                    "⬇️ Scarica CSV",
                    data=csv_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                    mime="text/csv"
                )
                # XLSX
                xlsx_bytes = to_xlsx_bytes(df[selected_columns_effective])
                st.download_button(
                    "⬇️ Scarica XLSX",
                    data=xlsx_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                # BibTeX
                bib_bytes = to_bib_bytes(df[selected_columns_effective].to_dict(orient="records"), prefix=last_engine.lower())
                st.download_button(
                    "⬇️ Scarica BibTeX (visualizzati)",
                    data=bib_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.bib",
                    mime="text/plain"
                )

        # Anteprima tabella dinamica
        if show_preview:
            st.dataframe(df[selected_columns_effective].head(preview_rows), use_container_width=True, height=420)

        # Inspector JSON singolo record
        with st.expander("🔎 Ispeziona record (JSON)"):
            idx = st.number_input(
                "Indice record (0-based)",
                min_value=0,
                max_value=max(0, len(df)-1),
                value=0
            )
            st.json(records[int(idx)])

with tab_help:
    st.header("Help & Notes")
    st.markdown(
        "- L'app unifica fetcher per GitHub, Zenodo e Scopus. Le query devono rispettare la sintassi del motore prescelto.\n"
        "- Per Scopus è necessaria una API key Elsevier valida.\n"
        "- I fetcher sono paginati e cercano di recuperare **tutti** i risultati disponibili.\n"
        "- Il campo `references` restituito dalla Scopus Search API è il **count** (numero di riferimenti)."
    )
    with st.expander("Suggerimenti pratici"):
        st.write(
            "• Se vuoi rieseguire una ricerca forzando nuove chiamate disabilita la cache nella sidebar.\n"
            "• Se ottieni errori di rate-limit, prova a riprovare più tardi o ad usare le credenziali.\n"
            "• Il file XLSX scaricabile è una vera tabella Excel con stile e colonne auto-adattate."
        )
    with st.expander("Note tecniche"):
        st.write(
            "• La pulizia HTML rimuove i tag e alcune entità comuni.\n"
            "• L'esportazione XLSX utilizza openpyxl per creare una tabella Excel formattata."
        )

st.markdown("---")
st.caption("Unified Academic Fetcher — Developed for research data acquisition. Save often and check API quota when using institutional keys.")
