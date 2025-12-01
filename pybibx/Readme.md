# PyBibX Extended – Automated Bibliometric and Multivocal Literature Analysis

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

## Table of Contents

- [Introduction](#introduction)
- [Context and Motivation](#context-and-motivation)
- [Modules](#modules)
  - [Module 1 – Data Visualization Dashboard](#module-1--data-visualization-dashboard)
  - [Module 2 – Forward and Backward Snowballing](#module-2--forward-and-backward-snowballing)
  - [Module 3 – Venue Ranking (CORE + SCImago)](#module-3--venue-ranking-core--scimago)
  - [Module 4 – Multivocal Literature Analysis](#module-4--multivocal-literature-analysis)
- [Integrated Pipeline for SLR + MLR](#integrated-pipeline-for-slr--mlr)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage Example](#usage-example)
- [Important Notes](#important-notes)
- [License](#license)

---

## Introduction

**Author:** [Insert Name]  
**Project Objective:** Extend PyBibX, a Python library for automating scientific research and systematic literature reviews, adding support for additional sources, automated snowballing, venue ranking, and multivocal literature analysis.

PyBibX is an advanced Python library for bibliometric, scientometric, and textual analysis on datasets exported from scientific databases such as **Scopus**, **Web of Science**, and **PubMed**. The library supports common formats (BibTeX, CSV, TXT), preserving original metadata and enabling consistent analyses even on heterogeneous datasets.

**Main features of PyBibX:**  
- Data cleaning, normalization, and deduplication.  
- Exploratory Data Analysis (EDA) with over 20 bibliometric metrics.  
- Interactive visualizations: WordClouds, N-gram bar plots, semantic projections, Sankey diagrams, TreeMaps, Evolution Plots.  
- Scientific network analysis: co-citation, co-authorship, coupling, geographic mapping.  
- AI integration: Topic Modeling (BERTopic), embeddings (Word2Vec, Sentence Embeddings), text summarization (BERT, PEGASUS, ChatGPT, Gemini).  
- Advanced filtering and merging of datasets from multiple sources.

---

## Context and Motivation

Originally, PyBibX worked only with Scopus, Web of Science, and PubMed datasets. To perform **multivocal and up-to-date literature reviews**, extensions were developed for:  

- Integration with additional external sources (**GitHub, Zenodo, LodCloud, blogs, whitepapers, StackOverflow**).  
- Automated snowballing (forward and backward).  
- Venue ranking (**CORE and SCImago**).  
- Support for Multivocal Literature Review (MLR).

**The extensions enable:**  
- Automated collection of academic and non-academic data.  
- Metadata standardization (CSV/BibTeX).  
- Automatic expansion of relevant studies via snowballing.  
- Evaluation of venue quality to prioritize data.

---

## Modules

### Module 1 – Data Visualization Dashboard

A **Streamlit/Flask dashboard** provides centralized access to data collected by the fetchers.

**Features:**  
- Dataset overview: record counts, field completeness, main distributions.  
- Interactive table: dynamic filters, JSON view, export to CSV/XLSX/BibTeX.  
- Download section: files ready for advanced PyBibX visualizations (TreeMap, Sankey, Evolution Plot).  

---

### Module 2 – Forward and Backward Snowballing

**Forward Snowballing:**  
- Uses `REF(ID)` via Scopus API.  
- Retrieves all papers citing the target publication.  

**Backward Snowballing:**  
- Uses Scopus Abstract Retrieval API → references when available.  
- Fallback to CrossRef for missing data.  
- Reference normalization.  

**Result:** robust pipeline to automatically expand relevant study sets.  

**Limitations:**  
- Backward snowballing may return incomplete results.  
- Forward snowballing is more reliable due to dedicated queries.

---

### Module 3 – Venue Ranking (CORE + SCImago)

**Purpose:** evaluate the quality of academic venues.

**Features:**  
- Parse CORE (A*, A, B, C) and SCImago (Q1–Q4) datasets.  
- Handle inconsistencies: fuzzy matching, fallback, most recent match.  
- Annotate datasets with venue rankings to guide qualitative decisions.

**Limitations:**  
- Partial coverage.  
- Fuzzy matching may require manual review.  
- CORE and SCImago measure different constructs.

---

### Module 4 – Multivocal Literature Analysis

**Purpose:** include non-academic sources for MLR.

**Integrated sources:** GitHub, Zenodo, LodCloud, blogs, whitepapers, StackOverflow.  

**Features:**  
- Independent fetchers with rate-limit and pagination handling.  
- Metadata normalized to CSV/BibTeX.  
- Seamless integration into PyBibX pipeline.

**Limitations:**  
- IEEE Xplore and ACM Digital Library do not provide full public APIs.  
- Web scraping is prohibited.  
- Only coverage verification is possible.

---

## Integrated Pipeline for SLR + MLR

1. Define study: RQs, keywords, inclusion/exclusion criteria, temporal range.  
2. SLR data collection: automated Scopus fetcher, manual IEEE/ACM collection.  
3. MLR data collection: GitHub, Zenodo, LodCloud, blogs, whitepapers, StackOverflow.  
4. Data validation: dashboard for completeness, consistency, quality.  
5. Snowballing: forward/backward on SLR dataset.  
6. Venue Ranking: CORE and SCImago for SLR articles.  
7. Normalization & Integration: merge SLR + MLR into uniform CSV/BibTeX dataset.  
8. Analysis & Visualization: PyBibX + dashboard for trends, author networks, keyword analysis, TreeMaps, Sankey, Evolution Plots.

---

## Requirements

- Python 3.9+  
- Libraries: `pandas`, `numpy`, `requests`, `fuzzywuzzy`, `streamlit`, `pybibx`  
- API keys for Scopus and GitHub (optional, recommended for automated fetches)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pybibx-extended.git
cd pybibx-extended

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
