import logging

log = logging.getLogger(__name__)

TIME_FORMAT = "%Y-%m-%dT%H:%M"


def validate(df, changes=None):
    changes = changes or {}
    clipped = changes.get("clipped", {})
    interpolated = changes.get("interpolated", {})

    rows_per_location = {name: int(n) for name, n in df.groupby("location").size().items()}
    remaining_nulls = int(df.isna().sum().sum())

    date_range = None
    if len(df) > 0:
        date_range = {
            "start": df["time"].min().strftime(TIME_FORMAT),
            "end": df["time"].max().strftime(TIME_FORMAT),
        }

    warnings = []
    if len(df) == 0:
        warnings.append("No rows after cleaning")
    if remaining_nulls > 0:
        warnings.append(f"{remaining_nulls} null values remain after cleaning")
    if rows_per_location and len(set(rows_per_location.values())) > 1:
        counts = rows_per_location.values()
        warnings.append(f"Rows per location are uneven (min {min(counts)}, max {max(counts)})")

    return {
        "rows": len(df),
        "locations": len(rows_per_location),
        "rows_per_location": rows_per_location,
        "date_range": date_range,
        "duplicates_removed": changes.get("duplicates_removed", 0),
        "values_clipped": {"total": sum(clipped.values()), "by_column": clipped},
        "values_interpolated": {"total": sum(interpolated.values()), "by_column": interpolated},
        "remaining_nulls": remaining_nulls,
        "warnings": warnings,
    }


def nonzero(by_column):
    return ", ".join(f"{col}={n}" for col, n in by_column.items() if n > 0)


def log_report(report):
    date_range = report["date_range"] or {"start": "-", "end": "-"}

    log.info(
        "Validation: rows=%s, locations=%s, range=%s to %s",
        report["rows"], report["locations"], date_range["start"], date_range["end"],
    )
    log.info(
        "Changes: duplicates_removed=%s, values_clipped=%s, values_interpolated=%s, remaining_nulls=%s",
        report["duplicates_removed"],
        report["values_clipped"]["total"],
        report["values_interpolated"]["total"],
        report["remaining_nulls"],
    )

    if report["values_clipped"]["total"] > 0:
        log.info("Clipped by column: %s", nonzero(report["values_clipped"]["by_column"]))
    if report["values_interpolated"]["total"] > 0:
        log.info("Interpolated by column: %s", nonzero(report["values_interpolated"]["by_column"]))

    log.info(
        "Rows per location: %s",
        ", ".join(f"{name}={n}" for name, n in report["rows_per_location"].items()),
    )

    for warning in report["warnings"]:
        log.warning("Validation warning: %s", warning)