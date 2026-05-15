"""
transform.py
------------
Step 2 of the ETL Pipeline — Transform
Reads raw JSON files produced by extract.py, cleans and reshapes
the data into a structured DataFrame ready for loading into SQLite.

Author: Sujud Alatrash
"""

import json
import os
import glob
import pandas as pd
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

RAW_DATA_DIR  = "data/raw"
CLEAN_DATA_DIR = "data/clean"


# ── Helper Functions ───────────────────────────────────────────────────────────

def load_latest_raw_file(raw_dir: str = RAW_DATA_DIR) -> list[dict]:
    """
    Find and load the most recently created raw JSON file.
    Raises FileNotFoundError if no raw files exist yet.
    """
    pattern = os.path.join(raw_dir, "weather_raw_*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No raw files found in '{raw_dir}'. Run extract.py first."
        )

    latest = files[-1]
    print(f"  Loading raw file: {latest}")

    with open(latest) as f:
        return json.load(f)


def flatten_record(record: dict) -> dict:
    """
    Flatten one raw API response dict into a clean, flat dict.

    The OpenWeatherMap API nests data like:
        record["main"]["temp"]
        record["wind"]["speed"]
        record["weather"][0]["description"]

    We pull everything out into a single-level dict so Pandas
    can turn it into one clean row per city.
    """
    return {
        # Identity
        "city":          record.get("name"),
        "country":       record.get("sys", {}).get("country"),

        # Temperature (all in Celsius)
        "temp_c":        record.get("main", {}).get("temp"),
        "feels_like_c":  record.get("main", {}).get("feels_like"),
        "temp_min_c":    record.get("main", {}).get("temp_min"),
        "temp_max_c":    record.get("main", {}).get("temp_max"),

        # Atmosphere
        "humidity_pct":  record.get("main", {}).get("humidity"),
        "pressure_hpa":  record.get("main", {}).get("pressure"),
        "visibility_m":  record.get("visibility"),

        # Wind
        "wind_speed_ms": record.get("wind", {}).get("speed"),
        "wind_deg":      record.get("wind", {}).get("deg"),

        # Conditions
        "weather_main":  record.get("weather", [{}])[0].get("main"),
        "description":   record.get("weather", [{}])[0].get("description"),
        "cloudiness_pct":record.get("clouds", {}).get("all"),

        # Timestamps
        "sunrise_utc":   pd.to_datetime(
                             record.get("sys", {}).get("sunrise"), unit="s", utc=True
                         ),
        "sunset_utc":    pd.to_datetime(
                             record.get("sys", {}).get("sunset"), unit="s", utc=True
                         ),
        "fetched_at":    record.get("fetched_at"),
    }


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply cleaning rules to the flattened DataFrame.

    Steps:
      1. Drop rows where the city name is missing (bad API response)
      2. Round float columns to 2 decimal places
      3. Add a derived column: daylight_hours
      4. Add a derived column: temp_category (Cold / Mild / Hot)
      5. Convert fetched_at to proper datetime
      6. Sort by temperature descending
    """
    print(f"  Rows before cleaning: {len(df)}")

    # 1. Drop rows with no city name
    df = df.dropna(subset=["city"])

    # 2. Round floats
    float_cols = ["temp_c", "feels_like_c", "temp_min_c",
                  "temp_max_c", "wind_speed_ms"]
    df[float_cols] = df[float_cols].round(2)

    # 3. Derived: daylight duration in hours
    df["daylight_hours"] = (
        (df["sunset_utc"] - df["sunrise_utc"])
        .dt.total_seconds() / 3600
    ).round(2)

    # 4. Derived: temperature category
    df["temp_category"] = pd.cut(
        df["temp_c"],
        bins=[-float("inf"), 10, 25, float("inf")],
        labels=["Cold", "Mild", "Hot"]
    )

    # 5. Parse fetched_at to datetime
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])

    # 6. Sort hottest → coldest
    df = df.sort_values("temp_c", ascending=False).reset_index(drop=True)

    print(f"  Rows after cleaning:  {len(df)}")
    return df


def save_clean_data(df: pd.DataFrame, output_dir: str = CLEAN_DATA_DIR) -> str:
    """
    Save the cleaned DataFrame to a timestamped CSV file.
    Returns the path of the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename  = f"weather_clean_{timestamp}.csv"
    filepath  = os.path.join(output_dir, filename)

    df.to_csv(filepath, index=False)
    print(f"  Saved clean data → {filepath}")
    return filepath


def print_summary(df: pd.DataFrame) -> None:
    """Print a quick summary of the cleaned data to the console."""
    print("\n  --- Summary ---")
    print(f"  Cities tracked : {df['city'].tolist()}")
    print(f"  Hottest city   : {df.iloc[0]['city']} ({df.iloc[0]['temp_c']}°C)")
    print(f"  Coldest city   : {df.iloc[-1]['city']} ({df.iloc[-1]['temp_c']}°C)")
    print(f"  Avg humidity   : {df['humidity_pct'].mean():.1f}%")
    print(f"  Temp breakdown : {df['temp_category'].value_counts().to_dict()}")


# ── Main Transform Function ────────────────────────────────────────────────────

def transform(raw_dir: str = RAW_DATA_DIR) -> tuple[pd.DataFrame, str]:
    """
    Main transform function.
    Loads the latest raw file, flattens, cleans, and saves to CSV.
    Returns (cleaned DataFrame, output filepath).
    """
    print("=" * 50)
    print("STEP 2 — TRANSFORM")
    print("=" * 50)

    # Load raw JSON
    raw_records = load_latest_raw_file(raw_dir)
    print(f"  Loaded {len(raw_records)} raw records\n")

    # Flatten each record into a row
    flat_records = [flatten_record(r) for r in raw_records]

    # Build DataFrame
    df = pd.DataFrame(flat_records)

    # Clean
    print()
    df = clean_dataframe(df)

    # Summary
    print_summary(df)

    # Save
    print()
    filepath = save_clean_data(df)

    print(f"\nTransform complete. Shape: {df.shape[0]} rows × {df.shape[1]} columns.")
    return df, filepath


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df, path = transform()
    print("\nPreview:")
    print(df[["city", "country", "temp_c", "humidity_pct",
              "weather_main", "temp_category", "daylight_hours"]].to_string(index=False))