"""
Unified Academic Fetcher (Streamlit)
- Unifies fetchers for: GitHub, Zenodo, Scopus
- Provides: field selection, HTML cleaning, CSV/XLSX/BibTeX download (formatted Excel table, auto-fit columns)
- Requirements: streamlit, pandas, requests, openpyxl
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

# import your fetchers (place the files in the same folder)
from github_multifetcher_filtered import GitHubFetcher
from Zenodo_fetcher import ZenodoFetcher
from Scopus_Fetcher import ScopusFetcher

# ---------------------------
# Utilities
# ---------------------------
def clean_html(text):
    """Remove HTML tags and decode common entities; return clean text."""
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return s.strip()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Export DataFrame to CSV (UTF-8 with BOM) as bytes."""
    return df.to_csv(index=False).encode("utf-8-sig")


def to_bib_bytes(records, prefix="entry") -> bytes:
    """Serialize a list of dict records into a simple BibTeX-like @misc collection (bytes)."""
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
    """
    Create a formatted Excel workbook (openpyxl) from a DataFrame and return bytes.
    - Auto-resizes columns (bounded)
    - Adds an Excel table with style and row stripes
    - Truncates extremely long cell values (>2000 chars) to avoid performance issues
    """
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    # Append rows (header included)
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    max_col = ws.max_column
    max_row = ws.max_row

    # Auto-fit columns (simple heuristic based on max string length)
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
        # Prevent absurdly wide columns
        ws.column_dimensions[col_letter].width = min(width, 100)

    # Create a table over the full range and apply style
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
# Field descriptions per engine
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
        "references": "Number of references (count) - NOTE: search API returns only count",
        "citations": "Number of citations (count)",
        "url": "Link (e.g. Scopus URL)",
        "abstract": "Article abstract",
        "language": "Language",
        "publisher": "Publisher"
    }
}

# ---------------------------
# Streamlit UI setup
# ---------------------------
st.set_page_config(page_title="Unified Academic Fetcher", layout="wide", initial_sidebar_state="expanded")
st.title("🔎 Unified Academic Fetcher")
st.markdown(
    "Unified interface to query **Scopus**, **GitHub** and **Zenodo**. "
    "Choose the engine, compose the query (see instructions), select fields to display and download results as CSV/XLSX/BibTeX."
)

st.divider()

# --- NEW: minimum query terms warning ---
st.info(
    "⚠️ Please note: the query should contain at least **3 propositions/terms** "
    "(e.g., keywords, operators) to return meaningful results."
)

st.divider()

# Sidebar
with st.sidebar:
    st.header("Configuration")
    engine = st.radio("Search engine", ["Scopus", "GitHub", "Zenodo"], index=0)
    st.markdown("---")
    st.subheader("Credentials")
    github_token = st.text_input("GitHub token (optional)", type="password") if engine == "GitHub" else None
    scopus_api_key = st.text_input("Elsevier API Key (required for Scopus)", type="password") if engine == "Scopus" else None
    st.markdown("---")
    st.write("Cache & behavior")
    enable_cache = st.checkbox("Enable caching (1h)", value=True)
    st.caption("Cache avoids duplicate calls during development. Disable to force fresh requests.")
    st.markdown("---")
    st.markdown("Version: 1.0 — Unified Fetcher")

# Query and fields
st.markdown("### 📘 Query instructions")
if engine == "Scopus":
    st.info(
        "Use Scopus syntax (TITLE-ABS-KEY, AUTHLASTNAME, DOI, PUBYEAR, etc.). Examples:\n\n"
        "`TITLE-ABS-KEY(\"cloud computing\" AND \"knowledge graph\")`\n"
        "`TITLE(\"virtual machine\") AND PUBYEAR > 2018`\n"
        "`DOI(10.1109/5.771073)`"
    )
elif engine == "GitHub":
    st.info(
        "Use GitHub Search syntax. Examples:\n\n"
        "`machine learning language:python`\n"
        "`openstack idle detector`\n"
        "`security monitoring stars:>100`"
    )
else:
    st.info(
        "Use Zenodo (Lucene/Elastic-like) syntax. Examples:\n\n"
        "`title:\"machine learning\"`\n"
        "`keywords:cloud`\n"
        "`creators.name:\"John Smith\"`"
    )

query = st.text_area("Enter query", height=120, placeholder="Write the query following the chosen engine syntax")

with st.expander("📌 Available fields and descriptions", expanded=False):
    st.markdown(f"**Selected engine:** {engine}")
    fields = ENGINE_FIELDS[engine]
    for k, v in fields.items():
        st.markdown(f"- **`{k}`** — {v}")

with st.expander("🔧 Select columns to include (output)", expanded=True):
    all_fields = list(ENGINE_FIELDS[engine].keys())
    include_all = st.checkbox("Include all fields", value=True, key="include_all_fields")
    selected_columns = all_fields.copy() if include_all else st.multiselect("Choose columns", options=all_fields, default=all_fields[:6])

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
    st.subheader("🚀 Run search")
    col_run_left, col_run_right = st.columns([3, 1])
    with col_run_left:
        run = st.button("Run search", key="run_search")
    st.caption(
        "Note: the app attempts to retrieve *all* available results from the fetchers, handling pagination and caching. "
        "Use cache to avoid duplicate calls during development."
    )

    if run:
        if not query.strip():
            st.error("The query is empty. Please enter a valid query.")
            st.stop()
        if engine == "Scopus" and not scopus_api_key:
            st.error("A valid Elsevier API Key is required for Scopus.")
            st.stop()

        with st.spinner(f"Executing search on {engine}..."):
            try:
                records = (cached_fetch_github(query, github_token) if engine == "GitHub" else
                           cached_fetch_zenodo(query) if engine == "Zenodo" else
                           cached_fetch_scopus(query, scopus_api_key))
            except Exception as e:
                st.error(f"Error while calling the engine: {e}")
                st.stop()

        # Clean records (HTML cleaning)
        clean_records = [{k: clean_html(rec.get(k, "")) for k in rec.keys()} for rec in records]

        # Save in session state
        st.session_state["last_engine"] = engine
        st.session_state["last_query"] = query
        st.session_state["last_records"] = clean_records

        # Show immediate feedback dynamically
        st.success(f"✅ Retrieved {len(clean_records)} results from {engine}")
        st.info("You can now go to the 'Results' tab to view and download them.")

with tab_results:
    st.subheader("📄 Results")
    records = st.session_state.get("last_records", None)
    last_engine = st.session_state.get("last_engine", engine)

    if not records:
        st.info("No search executed in this session. Go to 'Run search' and run a query.")
    else:
        df = pd.DataFrame(records)

        # Effective selected columns (present in dataframe)
        available_columns = df.columns.tolist()
        selected_columns_effective = [c for c in selected_columns if c in available_columns]
        if not selected_columns_effective:
            st.warning("None of the selected columns are present in the results. Showing all available columns.")
            selected_columns_effective = available_columns

        # Show engine and query
        st.markdown(f"**Engine:** `{last_engine}`  •  **Query:** `{st.session_state.get('last_query','')}`")

        # Show totals
        st.info(f"📊 Total results obtained: {len(df)} — available columns: {len(available_columns)}")

        # Display controls and download
        with st.expander("🔧 Display & download controls", expanded=True):
            col1, col2 = st.columns([2, 2])

            with col1:
                # Table preview controls
                show_preview = st.checkbox("Show table preview", value=True)
                preview_rows = st.number_input(
                    "Preview rows",
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
                    "⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                    mime="text/csv"
                )
                # XLSX
                xlsx_bytes = to_xlsx_bytes(df[selected_columns_effective])
                st.download_button(
                    "⬇️ Download XLSX",
                    data=xlsx_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                # BibTeX
                bib_bytes = to_bib_bytes(df[selected_columns_effective].to_dict(orient="records"), prefix=last_engine.lower())
                st.download_button(
                    "⬇️ Download BibTeX (displayed)",
                    data=bib_bytes,
                    file_name=f"{last_engine.lower()}_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.bib",
                    mime="text/plain"
                )

        # Dynamic table preview
        if show_preview:
            st.dataframe(df[selected_columns_effective].head(preview_rows), use_container_width=True, height=420)

        # Single record JSON inspector
        with st.expander("🔎 Inspect record (JSON)"):
            idx = st.number_input(
                "Record index (0-based)",
                min_value=0,
                max_value=max(0, len(df) - 1),
                value=0
            )
            st.json(records[int(idx)])

with tab_help:
    st.header("Help & Notes")
    st.markdown(
        "- The app unifies fetchers for GitHub, Zenodo and Scopus. Queries must follow the chosen engine syntax.\n"
        "- A valid Elsevier API key is required for Scopus.\n"
        "- Fetchers are paginated and attempt to retrieve **all** available results.\n"
        "- The `references` field returned by the Scopus Search API is the **count** of references."
    )
    with st.expander("Practical tips"):
        st.write(
            "• To force fresh calls, disable caching in the sidebar.\n"
            "• If you encounter rate-limit errors, try again later or use credentials.\n"
            "• The downloaded XLSX file is a real Excel table with style and auto-resized columns."
        )
    with st.expander("Technical notes"):
        st.write(
            "• HTML cleaning removes tags and decodes some common entities.\n"
            "• XLSX export uses openpyxl to create a formatted Excel table."
        )

st.markdown("---")
st.caption("Unified Academic Fetcher — Developed for research data acquisition. Save often and check API quota when using institutional keys.")
