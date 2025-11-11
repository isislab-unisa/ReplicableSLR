# core_source.py
from .base import BaseSource
from .utils import fuzzy_match
from .decorators import log_call
import pandas as pd
import os
import re

class CoreSource(BaseSource):
    @log_call
    def check(self, venue_name, log=True, results_dir=r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\VenueRank-Results"):
        # 🔹 Pulizia nome: rimuove eventuale anno dopo la virgola
        name_only = re.split(r",\s*\d{4}$", venue_name.strip(), flags=re.IGNORECASE)[0].lower()
        input_year = None
        if "," in venue_name:
            try:
                input_year = int(venue_name.split(",")[-1])
            except:
                pass

        best_title = None

        # 🔹 Step 1: controllo anno inserito, se disponibile
        if input_year in self.data_by_year:
            df_check = self.data_by_year[input_year].copy()
            df_check['Title'] = df_check['Title'].str.strip().str.lower()
            titles_list = df_check['Title'].tolist()
            if name_only in titles_list:
                best_title = name_only
            else:
                best_title = fuzzy_match(name_only, titles_list)

        # 🔹 Step 2: se non trovato, fuzzy match globale tra tutti gli anni
        if not best_title:
            all_titles = []
            for df in self.data_by_year.values():
                all_titles += df['Title'].str.strip().str.lower().tolist()
            best_title = fuzzy_match(name_only, all_titles)

        if not best_title:
            print(f"[CORE] ❌ Venue non trovata: '{venue_name}'")
            return

        # 🔹 Step 3: trovo il record più recente
        matches = []
        for y, df in sorted(self.data_by_year.items(), reverse=True):
            df_copy = df.copy()
            df_copy['Title'] = df_copy['Title'].str.strip().str.lower()
            match = df_copy[df_copy['Title'] == best_title]
            if not match.empty:
                matches.append((y, match))

        if not matches:
            print(f"[CORE] ❌ Nessun record trovato per '{best_title}'")
            return

        most_recent_year, df_match = max(matches, key=lambda x: x[0])
        row = df_match.iloc[0]
        rank = row.get("Rank", "N/A")

        print(f"[CORE] ✅ Trovato → Anno più recente: {most_recent_year}")
        print(f"   🏷️ Rank: {rank}")

        # 🔹 Step 4: Salvataggio cumulativo CSV
        if log:
            os.makedirs(results_dir, exist_ok=True)
            csv_path = os.path.join(results_dir, "CORE-results.csv")
            new_df = pd.DataFrame([{
                "Source": "CORE",
                "ID": row.get("ID", "N/A"),
                "Venue": row["Title"],
                "Year": most_recent_year,
                "Rank": rank
            }])
            if os.path.exists(csv_path):
                old_df = pd.read_csv(csv_path)
                df_final = pd.concat([old_df, new_df], ignore_index=True)
            else:
                df_final = new_df
            df_final.to_csv(csv_path, index=False)
            print(f"\n💾 Risultati aggiunti a: {csv_path}")

    def available_years(self):
        return sorted(self.data_by_year.keys())
