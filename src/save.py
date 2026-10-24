import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pandas as pd

from .config import CLEAN_DB, CLEAN_TABLE, RAW_DIR

KEY_COLUMNS = ["location", "time"]
VALUE_COLUMNS = [
    "island",
    "province",
    "elevation_m",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
    "temperature_2m",
    "wind_speed_10m",
    "source",
    "loaded_at",
]
ALL_COLUMNS = KEY_COLUMNS + VALUE_COLUMNS


def save_raw_json(data, source):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RAW_DIR / f"{source}_{timestamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return path


def load_raw_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def init_table(conn):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {CLEAN_TABLE} (
            location            TEXT NOT NULL,
            time                TEXT NOT NULL,
            island              TEXT,
            province            TEXT,
            elevation_m         REAL,
            shortwave_radiation REAL,
            direct_radiation    REAL,
            diffuse_radiation   REAL,
            cloud_cover         REAL,
            temperature_2m      REAL,
            wind_speed_10m      REAL,
            source              TEXT NOT NULL CHECK (source IN ('forecast', 'archive')),
            loaded_at           TEXT NOT NULL,
            PRIMARY KEY (location, time)
        )
    """)
    conn.commit()


def upsert(df, conn):
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["loaded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df[ALL_COLUMNS].astype(object).where(df[ALL_COLUMNS].notna(), None)

    placeholders = ", ".join("?" for _ in ALL_COLUMNS)
    updates = ", ".join(f"{col} = excluded.{col}" for col in VALUE_COLUMNS)

    sql = f"""
        INSERT INTO {CLEAN_TABLE} ({", ".join(ALL_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT (location, time) DO UPDATE SET {updates}
    """

    with conn:
        conn.executemany(sql, df.itertuples(index=False, name=None))

    return len(df)


def save_clean(df, source="forecast"):
    CLEAN_DB.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(CLEAN_DB)) as conn:
        init_table(conn)
        return upsert(df.assign(source=source), conn)


def load_clean():
    with closing(sqlite3.connect(CLEAN_DB)) as conn:
        return pd.read_sql(f"SELECT * FROM {CLEAN_TABLE}", conn, parse_dates=["time"])