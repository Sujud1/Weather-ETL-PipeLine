"""
load.py
-------
Step 3 of the ETL Pipeline — Load
Reads the latest cleaned CSV produced by transform.py and loads
it into a SQLite database with a proper schema.

Author: Sujud Alatrash
"""

import sqlite3
import pandas as pd
import glob
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

CLEAN_DATA_DIR = "data/clean"
DB_PATH        = "data/weather.db"


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_WEATHER_TABLE = """
CREATE TABLE IF NOT EXISTS weather_readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Location
    city            TEXT    NOT NULL,
    country         TEXT,

    -- Temperature (Celsius)
    temp_c          REAL,
    feels_like_c    REAL,
    temp_min_c      REAL,
    temp_max_c      REAL,
    temp_category   TEXT,

    -- Atmosphere
    humidity_pct    INTEGER,
    pressure_hpa    INTEGER,
    visibility_m    INTEGER,
    cloudiness_pct  INTEGER,

    -- Wind
    wind_speed_ms   REAL,
    wind_deg        INTEGER,

    -- Conditions
    weather_main    TEXT,
    description     TEXT,

    -- Daylight
    sunrise_utc     TEXT,
    sunset_utc      TEXT,
    daylight_hours  REAL,

    -- Metadata
    fetched_at      TEXT    NOT NULL,
    loaded_at       TEXT    NOT NULL
);
"""

CREATE_RUN_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_run_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT    NOT NULL,
    rows_loaded     INTEGER NOT NULL,
    source_file     TEXT    NOT NULL,
    status          TEXT    NOT NULL   -- 'success' or 'failed'
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_city       ON weather_readings(city);",
    "CREATE INDEX IF NOT EXISTS idx_fetched_at ON weather_readings(fetched_at);",
    "CREATE INDEX IF NOT EXISTS idx_temp_cat   ON weather_readings(temp_category);",
]


# ── Database Setup ─────────────────────────────────────────────────────────────

def init_database(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Create the database file and tables if they don't exist yet.
    Returns an open connection.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(CREATE_WEATHER_TABLE)
    cursor.execute(CREATE_RUN_LOG_TABLE)

    for index_sql in CREATE_INDEXES:
        cursor.execute(index_sql)

    conn.commit()
    print(f"  Database ready: {db_path}")
    return conn


# ── Load Helpers ───────────────────────────────────────────────────────────────

def load_latest_clean_file(clean_dir: str = CLEAN_DATA_DIR) -> tuple[pd.DataFrame, str]:
    """
    Find and load the most recently created clean CSV file.
    Returns (DataFrame, filepath).
    """
    pattern = os.path.join(clean_dir, "weather_clean_*.csv")
    files   = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No clean files found in '{clean_dir}'. Run transform.py first."
        )

    latest = files[-1]
    print(f"  Loading clean file: {latest}")
    df = pd.read_csv(latest)
    return df, latest


def insert_records(conn: sqlite3.Connection,
                   df: pd.DataFrame,
                   source_file: str) -> int:
    """
    Insert all rows from the DataFrame into weather_readings.
    Logs the run in pipeline_run_log.
    Returns the number of rows inserted.
    """
    loaded_at = datetime.utcnow().isoformat()
    df = df.copy()
    df["loaded_at"] = loaded_at

    # Columns that map directly to the table (same names)
    columns = [
        "city", "country",
        "temp_c", "feels_like_c", "temp_min_c", "temp_max_c", "temp_category",
        "humidity_pct", "pressure_hpa", "visibility_m", "cloudiness_pct",
        "wind_speed_ms", "wind_deg",
        "weather_main", "description",
        "sunrise_utc", "sunset_utc", "daylight_hours",
        "fetched_at", "loaded_at",
    ]

    # Keep only columns that exist in both the df and our schema
    cols_to_insert = [c for c in columns if c in df.columns]
    df_to_insert   = df[cols_to_insert]

    cursor = conn.cursor()

    placeholders = ", ".join(["?"] * len(cols_to_insert))
    col_names    = ", ".join(cols_to_insert)
    sql          = f"INSERT INTO weather_readings ({col_names}) VALUES ({placeholders})"

    rows = [tuple(row) for row in df_to_insert.itertuples(index=False)]
    cursor.executemany(sql, rows)

    # Log this pipeline run
    cursor.execute(
        "INSERT INTO pipeline_run_log (run_at, rows_loaded, source_file, status) VALUES (?,?,?,?)",
        (loaded_at, len(rows), os.path.basename(source_file), "success")
    )

    conn.commit()
    return len(rows)


# ── Query Helpers (bonus — shows SQL skill) ───────────────────────────────────

def run_sample_queries(conn: sqlite3.Connection) -> None:
    """
    Run a few SQL queries against the loaded data and print results.
    This shows that the data landed correctly and demonstrates SQL skill.
    """
    print("\n  --- Sample Queries ---")

    queries = [
        (
            "Hottest cities right now",
            """
            SELECT city, country, temp_c, description
            FROM   weather_readings
            ORDER  BY temp_c DESC
            LIMIT  3;
            """
        ),
        (
            "Average humidity by temperature category",
            """
            SELECT   temp_category,
                     ROUND(AVG(humidity_pct), 1) AS avg_humidity,
                     COUNT(*)                    AS city_count
            FROM     weather_readings
            GROUP BY temp_category
            ORDER BY avg_humidity DESC;
            """
        ),
        (
            "Cities with most daylight hours",
            """
            SELECT city, ROUND(daylight_hours, 2) AS daylight_hours
            FROM   weather_readings
            ORDER  BY daylight_hours DESC
            LIMIT  3;
            """
        ),
        (
            "Pipeline run history",
            """
            SELECT run_at, rows_loaded, source_file, status
            FROM   pipeline_run_log
            ORDER  BY run_at DESC
            LIMIT  5;
            """
        ),
    ]

    for title, sql in queries:
        print(f"\n  {title}:")
        result = pd.read_sql_query(sql, conn)
        print(result.to_string(index=False))


# ── Main Load Function ─────────────────────────────────────────────────────────

def load(clean_dir: str = CLEAN_DATA_DIR, db_path: str = DB_PATH) -> int:
    """
    Main load function.
    Initialises the database, inserts clean data, and runs sample queries.
    Returns the number of rows inserted.
    """
    print("=" * 50)
    print("STEP 3 — LOAD")
    print("=" * 50)

    # 1. Connect / create DB
    conn = init_database(db_path)

    # 2. Read latest clean CSV
    df, source_file = load_latest_clean_file(clean_dir)
    print(f"  Rows to insert: {len(df)}\n")

    # 3. Insert
    rows_inserted = insert_records(conn, df, source_file)
    print(f"  Inserted {rows_inserted} rows into weather_readings")

    # 4. Verify with sample queries
    run_sample_queries(conn)

    conn.close()

    print(f"\nLoad complete. Database: {db_path}")
    return rows_inserted


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load()