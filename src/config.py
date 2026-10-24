from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"

RAW_DB = RAW_DIR / "energy_raw.db"
CLEAN_DB = CLEAN_DIR / "energy_clean.db"

RAW_TABLE = "energy_raw"
CLEAN_TABLE = "energy_clean"