import os
import pandas as pd
import sys

# Add the path where the 'venuerankchecker' folder resides
sys.path.insert(0, r"C:\Users\maria\Desktop\ReplicableSLR\pybibx")

from venuerankchecker.checker import VenueRankChecker
from venuerankchecker.core_source import CoreSource
from venuerankchecker.scimago_source import ScimagoSource

# Paths to the folders containing the CSV files (adjust paths to where you have the files)
core_dir = r"C:\Users\maria\Desktop\ReplicableSLR\Rankings-Core"
scimago_dir = r"C:\Users\maria\Desktop\ReplicableSLR\Rankings-Scimago"

# Load CORE data
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

# Load SCIMAGO data
scimago_rankings = {}
for file in os.listdir(scimago_dir):
    if file.endswith('.csv') and file.startswith('scimago_'):
        year = int(file.split('_')[1].split('.')[0])
        try:
            df = pd.read_csv(os.path.join(scimago_dir, file), sep=';', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(os.path.join(scimago_dir, file), sep=';', encoding='ISO-8859-1', low_memory=False)
        df = df.rename(columns=lambda x: x.strip())  # remove extra spaces
        if "Sourceid" in df.columns:
            df = df.rename(columns={"Sourceid": "ID"})
        scimago_rankings[year] = df

# Create CoreSource and ScimagoSource objects with the data dictionaries
core_source = CoreSource(core_rankings)
scimago_source = ScimagoSource(scimago_rankings)

# Create VenueRankChecker instance
vrc = VenueRankChecker(core_source, scimago_source)

# Example usage
venue_name = "ACM International Conference on Research and Development in Information Retrieval, 2013"
vrc.check_all(venue_name)
