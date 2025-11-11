import os
import pandas as pd
import sys

# Aggiungo il path dove risiede la cartella 'venuerankchecker'
sys.path.insert(0, r"C:\Users\maria\Desktop\ReplicableSLR\pybibx")

from venuerankchecker.checker import VenueRankChecker
from venuerankchecker.core_source import CoreSource
from venuerankchecker.scimago_source import ScimagoSource

# Percorsi delle cartelle con i CSV (adatta i path a dove hai i file)
core_dir = r"C:\Users\maria\Desktop\ReplicableSLR\Rankings-Core"
scimago_dir = r"C:\Users\maria\Desktop\ReplicableSLR\Rankings-Scimago"

# Caricamento dati CORE
core_rankings = {}
for file in os.listdir(core_dir):
    if file.endswith('.csv') and file.startswith('core_'):
        year = int(file.split('_')[1].split('.')[0])
        df = pd.read_csv(
            os.path.join(core_dir, file),
            header=None,
            names=["ID", "Title", "Acronym", "Conference", "Rank", "ERA", "Field1", "Field2", "Field3"]
        )
        core_rankings[year] = df

# Caricamento dati SCIMAGO
scimago_rankings = {}
for file in os.listdir(scimago_dir):
    if file.endswith('.csv') and file.startswith('scimago_'):
        year = int(file.split('_')[1].split('.')[0])
        try:
            df = pd.read_csv(os.path.join(scimago_dir, file), sep=';', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(os.path.join(scimago_dir, file), sep=';', encoding='ISO-8859-1', low_memory=False)
        df = df.rename(columns=lambda x: x.strip())  # rimuove spazi
        if "Sourceid" in df.columns:
            df = df.rename(columns={"Sourceid": "ID"})
        scimago_rankings[year] = df

# crea gli oggetti CoreSource e ScimagoSource con i dizionari dati
core_source = CoreSource(core_rankings)
scimago_source = ScimagoSource(scimago_rankings)

# Creazione istanza di VenueRankChecker
vrc = VenueRankChecker(core_source, scimago_source)

# Esempio di utilizzo
venue_name = "ACM International Conference on Research and Development in Information Retrieval, 2013"
vrc.check_all(venue_name)
