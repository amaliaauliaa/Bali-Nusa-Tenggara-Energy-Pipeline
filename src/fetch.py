import copy
import logging
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from .config import (
    ARCHIVE_DELAY_DAYS,
    ARCHIVE_STEP_DAYS,
    BATCH_SIZE,
    MAX_ATTEMPTS,
    MAX_RETRY_AFTER,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
)

URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARS = [
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
    "temperature_2m",
    "wind_speed_10m",
]

log = logging.getLogger(__name__)


def count(stats, key):
    if stats is not None:
        stats[key] = stats.get(key, 0) + 1


def chunk(items, size):
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[i:i + size] for i in range(0, len(items), size)]


def is_retryable(exc):
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True

    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        return status == 429 or 500 <= status < 600

    return False


def describe_error(exc):
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
    return f"{type(exc).__name__}: {exc}"


def get_retry_after(exc):
    response = getattr(exc, "response", None)
    if response is None or response.status_code != 429:
        return None

    value = response.headers.get("Retry-After")
    if value is None:
        return None

    if value.strip().isdigit():
        return int(value)

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    return max(0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def fetch_with_retry(url, params, timeout=REQUEST_TIMEOUT, max_attempts=MAX_ATTEMPTS, stats=None):
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            count(stats, "requests")
            return data
        except requests.RequestException as exc:
            if not is_retryable(exc):
                raise RuntimeError(f"Request failed, not retryable. {describe_error(exc)}") from exc

            if attempt == max_attempts:
                raise RuntimeError(
                    f"Request failed after {max_attempts} attempts. Last error: {describe_error(exc)}"
                ) from exc

            retry_after = get_retry_after(exc)
            if retry_after is not None and retry_after > MAX_RETRY_AFTER:
                raise RuntimeError(
                    f"Server asked to wait {retry_after:.0f}s, longer than the {MAX_RETRY_AFTER}s limit. "
                    f"{describe_error(exc)}"
                ) from exc

            delay = retry_after if retry_after is not None else 2 ** attempt
            count(stats, "retries")
            log.warning(
                "Attempt %s/%s failed (%s). Retrying in %ss",
                attempt, max_attempts, describe_error(exc), delay,
            )
            time.sleep(delay)


def fetch_batch(url, locations, hourly_vars, timezone_name, extra_params=None, stats=None):
    params = {
        "latitude": ",".join(str(loc["lat"]) for loc in locations),
        "longitude": ",".join(str(loc["lon"]) for loc in locations),
        "hourly": ",".join(hourly_vars),
        "timezone": timezone_name,
    }
    if extra_params:
        params.update(extra_params)

    data = fetch_with_retry(url, params, stats=stats)

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(locations):
        raise ValueError(f"Got {len(data)} responses for {len(locations)} locations")

    return data


def fetch_data(
    locations,
    hourly_vars=HOURLY_VARS,
    timezone_name="Asia/Makassar",
    batch_size=BATCH_SIZE,
    delay=REQUEST_DELAY,
    stats=None,
):
    batches = chunk(locations, batch_size)
    data = []

    for i, batch in enumerate(batches, start=1):
        if i > 1:
            time.sleep(delay)

        log.info("Fetching batch %s/%s (%s locations)", i, len(batches), len(batch))
        data.extend(fetch_batch(URL, batch, hourly_vars, timezone_name, stats=stats))

    return data


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def date_ranges(start, end, step_days):
    if step_days < 1:
        raise ValueError("step_days must be at least 1")

    start, end = to_date(start), to_date(end)
    if start > end:
        raise ValueError(f"start ({start}) is after end ({end})")

    ranges = []
    current = start
    while current <= end:
        range_end = min(current + timedelta(days=step_days - 1), end)
        ranges.append((current, range_end))
        current = range_end + timedelta(days=1)

    return ranges


def latest_available_date():
    return datetime.now(timezone.utc).date() - timedelta(days=ARCHIVE_DELAY_DAYS)


def merge_responses(parts):
    merged = copy.deepcopy(parts[0])
    for part in parts[1:]:
        for key, values in part["hourly"].items():
            merged["hourly"][key].extend(values)
    return merged


def fetch_historical(
    locations,
    start,
    end,
    hourly_vars=HOURLY_VARS,
    timezone_name="Asia/Makassar",
    step_days=ARCHIVE_STEP_DAYS,
    batch_size=BATCH_SIZE,
    delay=REQUEST_DELAY,
    stats=None,
):
    start, end = to_date(start), to_date(end)
    latest = latest_available_date()

    if start > latest:
        raise ValueError(f"start ({start}) is after the latest available date ({latest})")
    if end > latest:
        log.warning("end %s is too recent for the archive, using %s instead", end, latest)
        end = latest

    ranges = date_ranges(start, end, step_days)
    batches = chunk(locations, batch_size)
    parts = [[] for _ in locations]
    total_requests = len(ranges) * len(batches)
    request_number = 0

    for range_start, range_end in ranges:
        extra_params = {"start_date": range_start.isoformat(), "end_date": range_end.isoformat()}

        for batch_index, batch in enumerate(batches):
            if request_number > 0:
                time.sleep(delay)
            request_number += 1

            log.info(
                "Fetching archive %s to %s, batch %s/%s (request %s/%s)",
                range_start, range_end, batch_index + 1, len(batches), request_number, total_requests,
            )
            responses = fetch_batch(ARCHIVE_URL, batch, hourly_vars, timezone_name, extra_params, stats)

            offset = batch_index * batch_size
            for i, response in enumerate(responses):
                parts[offset + i].append(response)

    return [merge_responses(location_parts) for location_parts in parts]