"""
extract.py
----------
Step 1 of the ETL Pipeline — Extract
Fetches current weather data for multiple cities from OpenWeatherMap API
and saves the raw data as JSON.

Author: Sujud Alatrash
"""

import requests
import json
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = "313c212cbf5c5b2ab5a4f3fc5df438e0"   # Replace with your OpenWeatherMap API key
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
RAW_DATA_DIR = "data/raw"

# Cities to track (you can add or change these)
CITIES = [
    "London", "New York", "Tokyo",
    "Berlin", "Sydney", "Tel Aviv"
]


# ── Core Functions ─────────────────────────────────────────────────────────────

def fetch_weather(city: str) -> dict | None:
    """
    Fetch current weather data for a single city.
    Returns a dict with the raw API response, or None on failure.
    """
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"   # Celsius
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Add our own timestamp so we know exactly when we fetched it
        data["fetched_at"] = datetime.utcnow().isoformat()

        print(f"  [OK] {city}: {data['main']['temp']}°C, {data['weather'][0]['description']}")
        return data

    except requests.exceptions.HTTPError as e:
        print(f"  [ERROR] {city}: HTTP error — {e}")
    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] {city}: No internet connection")
    except requests.exceptions.Timeout:
        print(f"  [ERROR] {city}: Request timed out")
    except Exception as e:
        print(f"  [ERROR] {city}: Unexpected error — {e}")

    return None


def save_raw_data(records: list[dict], output_dir: str = RAW_DATA_DIR) -> str:
    """
    Save raw weather records to a timestamped JSON file.
    Returns the path of the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"weather_raw_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(records, f, indent=2)

    print(f"\n  Saved {len(records)} records → {filepath}")
    return filepath


def extract(cities: list[str] = CITIES) -> str:
    """
    Main extract function.
    Fetches weather for all cities and saves raw JSON.
    Returns the path to the saved file.
    """
    print("=" * 50)
    print("STEP 1 — EXTRACT")
    print("=" * 50)
    print(f"Fetching weather for {len(cities)} cities...\n")

    records = []
    for city in cities:
        data = fetch_weather(city)
        if data:
            records.append(data)

    if not records:
        raise RuntimeError("No data fetched. Check your API key and internet connection.")

    filepath = save_raw_data(records)
    print(f"\nExtract complete. {len(records)}/{len(cities)} cities fetched successfully.")
    return filepath


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    extract()
