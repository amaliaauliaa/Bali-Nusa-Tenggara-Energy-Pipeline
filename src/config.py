from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
LOG_DIR = ROOT / "logs"

CLEAN_DB = CLEAN_DIR / "energy_clean.db"
CLEAN_TABLE = "energy_clean"

REQUEST_TIMEOUT = 30
MAX_ATTEMPTS = 4

BATCH_SIZE = 5
REQUEST_DELAY = 1
MAX_RETRY_AFTER = 120

ARCHIVE_DELAY_DAYS = 5
ARCHIVE_STEP_DAYS = 14