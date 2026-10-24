import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from .config import CLEAN_DB, CLEAN_TABLE, RAW_DB, RAW_TABLE


def save(df, db_path, table_name, if_exists="replace"):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        conn.commit()


def load(db_path, table_name):
    with closing(sqlite3.connect(db_path)) as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=["time"])


def save_raw(df, if_exists="replace"):
    save(df, RAW_DB, RAW_TABLE, if_exists)

def save_clean(df, if_exists="replace"):
    save(df, CLEAN_DB, CLEAN_TABLE, if_exists)

def load_raw():
    return load(RAW_DB, RAW_TABLE)

def load_clean():
    return load(CLEAN_DB, CLEAN_TABLE)