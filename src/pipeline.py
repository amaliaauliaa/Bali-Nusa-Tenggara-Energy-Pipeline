import argparse
import logging
import sys
import time
from datetime import date

from .config import LOG_DIR
from .fetch import fetch_data, fetch_historical
from .locations import LOCATIONS
from .save import load_raw_json, save_clean, save_raw_json
from .transform import clean, transform
from .validate import log_report, validate

LOGGER_NAME = "src"

MODES = {
    "forecast": {"raw_source": "open_meteo", "clean_source": "forecast"},
    "backfill": {"raw_source": "open_meteo_archive", "clean_source": "archive"},
}

log = logging.getLogger(f"{LOGGER_NAME}.pipeline")


def setup_logging():
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    handlers = [
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False


def fetch_raw(mode, start, end, stats):
    if mode == "forecast":
        return fetch_data(LOCATIONS, stats=stats)
    return fetch_historical(LOCATIONS, start, end, stats=stats)


def run(mode="forecast", start=None, end=None, raw_path=None):
    setup_logging()

    if mode not in MODES:
        raise ValueError(f"mode must be one of {list(MODES)}")
    if mode == "backfill" and raw_path is None and (start is None or end is None):
        raise ValueError("backfill needs start and end")

    settings = MODES[mode]
    stats = {"requests": 0, "retries": 0}
    started_at = time.perf_counter()

    log.info("Run started: mode=%s, locations=%s", mode, len(LOCATIONS))

    try:
        if raw_path is None:
            data = fetch_raw(mode, start, end, stats)
            raw_path = save_raw_json(data, settings["raw_source"])
            log.info("Raw JSON saved: %s", raw_path)

        log.info("Reading raw JSON: %s", raw_path)
        data = load_raw_json(raw_path)

        df = transform(data, LOCATIONS)
        log.info("Transform done: %s rows", len(df))

        df_clean, changes = clean(df)
        report = validate(df_clean, changes)
        log_report(report)

        rows_upserted = save_clean(df_clean, source=settings["clean_source"])
    except Exception:
        log.exception(
            "Run failed: mode=%s, retries=%s, duration=%.1fs",
            mode, stats["retries"], time.perf_counter() - started_at,
        )
        raise

    log.info(
        "Run finished: mode=%s, locations=%s, rows_upserted=%s, requests=%s, retries=%s, duration=%.1fs",
        mode, len(LOCATIONS), rows_upserted, stats["requests"], stats["retries"],
        time.perf_counter() - started_at,
    )

    return df_clean


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date '{value}', use YYYY-MM-DD")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="python -m src.pipeline", description="Open-Meteo energy pipeline")
    parser.add_argument("--mode", choices=list(MODES), default="forecast", help="forecast (default) or backfill")
    parser.add_argument("--start", type=parse_date, help="backfill start date, YYYY-MM-DD")
    parser.add_argument("--end", type=parse_date, help="backfill end date, YYYY-MM-DD")
    args = parser.parse_args(argv)

    if args.mode == "backfill":
        if args.start is None or args.end is None:
            parser.error("--start and --end are required with --mode backfill")
        if args.start > args.end:
            parser.error("--start must not be after --end")
    elif args.start is not None or args.end is not None:
        parser.error("--start and --end can only be used with --mode backfill")

    return args


def main(argv=None):
    args = parse_args(argv)

    try:
        run(args.mode, args.start, args.end)
    except Exception:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())