import os
import pandas as pd
from difflib import get_close_matches

def fuzzy_match(name, options, cutoff=0.8):
    matches = get_close_matches(name, options, n=1, cutoff=cutoff)
    return matches[0] if matches else None

def parse_coverage(coverage, year):
    try:
        coverage = str(coverage).replace('–', '-').replace('\u2013', '-')
        intervals = [part.strip() for part in coverage.split(',')]
        for interval in intervals:
            years = interval.split('-')
            if len(years) == 2:
                if int(years[0]) <= year <= int(years[1]):
                    return True
            elif len(years) == 1 and int(years[0]) == year:
                return True
    except:
        pass
    return False

def log_result(source, venue, year, rank_type, rank_value, log_path="venue_rank_log.csv"):
    if os.path.exists(log_path):
        log_df = pd.read_csv(log_path)
    else:
        log_df = pd.DataFrame(columns=["Source", "Venue", "Year", "Rank_Type", "Rank_Value"])

    is_duplicate = (
        (log_df["Source"] == source) &
        (log_df["Venue"].str.lower() == venue.lower()) &
        (log_df["Year"] == year) &
        (log_df["Rank_Type"] == rank_type) &
        (log_df["Rank_Value"] == rank_value)
    ).any()

    if not is_duplicate:
        new_entry = pd.DataFrame([{
            "Source": source,
            "Venue": venue,
            "Year": year,
            "Rank_Type": rank_type,
            "Rank_Value": rank_value
        }])
        log_df = pd.concat([log_df, new_entry], ignore_index=True)
        log_df.to_csv(log_path, index=False)
