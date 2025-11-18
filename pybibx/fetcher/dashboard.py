"""
Unified Academic Fetcher (Streamlit)
- Unifies fetchers for: GitHub, Zenodo, Scopus
- Provides: field selection, HTML cleaning, CSV/XLSX/BibTeX download
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
from pybibx.fetcher.github_fetcher import GitHubFetcher
from Zenodo_fetcher import ZenodoFetcher
from Scopus_Fetcher import ScopusFetcher

# ---------------------------
# Utilities
# ---------------------------
def clean_html(text):
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return s.strip()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
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
# Engine fields
# ---------------------------
ENGINE_FIELDS = {
    "GitHub": {
        "title": "Repository name",
        "author": "Repository owner (login)",
        "description": "Project description",
        "created": "Creation date (ISO)",
        "updated": "Last update (ISO)",
        "language": "Primary language",
        "stars": "Number of stars",
        "url": "Repository URL",
        "license": "License name (if present)"
    },
    "Zenodo": {
        "title": "Dataset / record title",
        "author": "Authors (concatenated string)",
        "description": "Record description",
        "created": "Publication date",
        "updated": "Last update date",
        "keywords": "Associated keywords",
        "url": "DOI or public HTML link",
        "license": "License (id or name)"
    },
    "Scopus": {
        "scopus_id": "Scopus ID",
        "eid": "Elsevier EID",
        "title": "Publication title",
        "authors": "Authors (string)",
        "doi": "Digital Object Identifier",
        "year": "Publication date or year",
        "source": "Journal / conference name",
        "volume": "Volume",
        "issue": "Issue / number",
        "pages": "Page range",
        "issn": "Journal ISSN",
        "isbn": "ISBN (when applicable)",
        "affiliations": "Author affiliations",
        "subject_areas": "Subject areas",
        "references": "Number of references (count)",
        "citations": "Number of citations (count)",
        "url": "Link (e.g. Scopus URL)",
        "abstract": "Article abstract",
        "language": "Language",
        "publisher": "Publisher"
    }
}


# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Unified Academic Fetcher", layout="wide")
st.title("🔎 Unified Academic Fetcher")
st.markdown("Unified interface to query **Scopus**, **GitHub** and **Zenodo**.")

with st.sidebar:
    st.header("Configuration")
    engine = st.radio("Search engine", ["Scopus", "GitHub", "Zenodo"], index=0)
    st.markdown("---")
    github_token = st.text_input("GitHub token (optional)", type="password") if engine == "GitHub" else None
    scopus_api_key = st.text_input("Elsevier API Key (required for Scopus)", type="password") if engine == "Scopus" else None
    st.markdown("---")
    st.checkbox("Enable caching (1h)", value=True, key="enable_cache")
    st.markdown("---")

# ---------------------------
# Query instructions
# ---------------------------
st.markdown("### 📘 Query instructions")
if engine == "Scopus":
    st.info(
        "Use Scopus syntax. Expand plurals manually. Example query:\n\n"
        "TITLE-ABS-KEY (\n"
        "    (\"cloud computing\" OR \"cloud-computing\" OR \"multi-cloud\")\n"
        "    AND (\"ontology\" OR \"ontologies\" OR \"semantic web\" OR \"knowledge graph\" OR "
        "\"knowledge graphs\" OR \"linked data\" OR \"linked open data\")\n"
        "    AND NOT (\"internet of things\" OR iot)\n"
        ")\n"
        "AND PUBYEAR > 2014\n"
        "AND PUBYEAR < 2027\n"
        "AND (DOCTYPE(ar) OR DOCTYPE(cp))\n"
        "AND LANGUAGE(English)"
    )
elif engine == "GitHub":
    st.info(
        "Use GitHub search syntax. Examples:\n"
        "- Exact phrase: \"machine learning\"\n"
        "- Exclude term: -iot\n"
        "- Combine multiple terms (AND by default): \"cloud computing\" ontology -iot -\"internet of things\"\n\n"
        "- created:2014-01-01..2027-12-31"
        "⚠️ Note: GitHub Search API returns a maximum of 1000 results per query even with pagination."
    )
else:  # Zenodo
    st.info(
        "Use Zenodo syntax. Wildcards (*) and LIMIT-TO are not supported. Use AND, OR, NOT and publication_date. Example:\n\n"
        "(\"cloud computing\" OR \"cloud-computing\" OR \"multi-cloud\")\n"
        "AND (\"ontolog*\" OR \"semantic web\" OR \"knowledge graph\" "
        "OR \"linked data\" OR \"linked open data\")\n"
        "AND NOT (\"internet of things\" OR \"iot\")\n"
        "AND publication_date:[2014-01-01 TO 2027-12-31]"
    )

query = st.text_area("Enter query", height=120, placeholder="Write the query following engine syntax")

with st.expander("📌 Available fields"):
    fields = list(ENGINE_FIELDS[engine].items())
    n_cols = 3  # numero di colonne
    cols = st.columns(n_cols)
    for i, (field, desc) in enumerate(fields):
        col = cols[i % n_cols]
        col.markdown(f"- **`{field}`** — {desc}")

with st.expander("🔧 Select columns", expanded=True):
    all_fields = list(ENGINE_FIELDS[engine].keys())
    include_all = st.checkbox("Include all fields", value=True)
    selected_columns = all_fields.copy() if include_all else st.multiselect("Choose columns", options=all_fields, default=all_fields[:6])

# ---------------------------
# Caching wrappers
# ---------------------------
enable_cache = st.session_state.get("enable_cache", True)
cache_decorator = st.cache_data if enable_cache else lambda f: f

@cache_decorator(ttl=3600)
def cached_fetch_github(q, token=None, max_results=200):
    fetcher = GitHubFetcher(token=token)
    return fetcher.fetch_repositories(q, max_results=max_results)

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
    st.subheader("🚀 Run search")
    if st.button("Run search"):
        if not query.strip():
            st.error("The query is empty.")
            st.stop()
        if engine == "Scopus" and not scopus_api_key:
            st.error("API Key required for Scopus.")
            st.stop()

        with st.spinner(f"Executing search on {engine}..."):
            try:
                if engine == "GitHub":
                    # Directly use the query as entered
                    records = cached_fetch_github(query, github_token)
                elif engine == "Zenodo":
                    records = cached_fetch_zenodo(query)
                else:
                    records = cached_fetch_scopus(query, scopus_api_key)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        clean_records = [{k: clean_html(v) for k, v in rec.items()} for rec in records]
        st.session_state["last_records"] = clean_records
        st.session_state["last_engine"] = engine
        st.session_state["last_query"] = query
        st.success(f"✅ Retrieved {len(clean_records)} results from {engine}")
        st.info("Go to the 'Results' tab to view/download them.")

with tab_results:
    st.subheader("📄 Results")
    records = st.session_state.get("last_records")
    last_engine = st.session_state.get("last_engine", engine)

    if not records:
        st.info("No search executed.")
    else:
        df = pd.DataFrame(records)
        selected_columns_effective = [c for c in selected_columns if c in df.columns] or df.columns.tolist()

        st.markdown(f"**Engine:** `{last_engine}`  •  **Query:** `{st.session_state.get('last_query','')}`")
        st.info(f"📊 Total results: {len(df)}")

        with st.expander("🔧 Display & download controls", expanded=True):
            col1, col2 = st.columns([2, 2])
            with col1:
                show_preview = st.checkbox("Show table preview", value=True)
                preview_rows = st.number_input("Preview rows", min_value=5, max_value=len(df),
                                               value=min(50, len(df)), step=5)
            with col2:
                st.markdown("**Download**")
                st.download_button("⬇️ CSV", data=to_csv_bytes(df[selected_columns_effective]),
                                   file_name=f"{last_engine.lower()}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv")
                st.download_button("⬇️ XLSX", data=to_xlsx_bytes(df[selected_columns_effective]),
                                   file_name=f"{last_engine.lower()}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx")
                st.download_button("⬇️ BibTeX", data=to_bib_bytes(df[selected_columns_effective].to_dict(orient="records"),
                                                                   prefix=last_engine.lower()),
                                   file_name=f"{last_engine.lower()}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.bib")

        if show_preview:
            st.dataframe(df[selected_columns_effective].head(preview_rows), use_container_width=True)

        with st.expander("🔎 Inspect record (JSON)"):
            idx = st.number_input("Record index", min_value=0, max_value=max(0, len(df)-1), value=0)
            st.json(records[int(idx)])

with tab_help:
    st.header("Help & Notes")
    st.markdown(
        "- Queries must follow the engine syntax.\n"
        "- GitHub queries use quotes for exact phrases and `-term` for exclusions.\n"
        "- Zenodo supports AND, OR, NOT and date ranges.\n"
        "- Scopus queries should expand plurals and respect original Scopus syntax.\n"
        "- The app fetches all available results with pagination and caching.\n"
        "- XLSX export creates a formatted Excel table."
    )
