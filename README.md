# Bali–Nusa Tenggara Energy Pipeline

This pipeline collects hourly weather data for 10 locations across Bali, West Nusa Tenggara, and East Nusa Tenggara. Solar radiation, cloud cover, temperature, and wind speed are available as supporting variables for energy analysis.



## Data sources and modes

| Mode | API | Data type | How to run |
|---|---|---|---|
| `forecast` (default) | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) — `https://api.open-meteo.com/v1/forecast` | Forecast | `python -m src.pipeline` |
| `backfill` | [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) — `https://archive-api.open-meteo.com/v1/archive` | Historical archive observations/reanalysis | `python -m src.pipeline --mode backfill --start YYYY-MM-DD --end YYYY-MM-DD` |

Both modes request hourly data in the `Asia/Makassar` timezone for the locations listed in [`src/locations.py`](src/locations.py): Denpasar, Jembrana, Mataram, Sumbawa Besar, Bima, Ruteng, Maumere, Waikabubak, Kupang, and Atambua.

The archive data has a delay: the pipeline considers dates up to five days before the current UTC date to be available. If a backfill end date is more recent, it is reduced to the latest available date. Backfill requests are split into 14-day ranges by default.

## Columns and units

The cleaned SQLite table contains the following columns. Weather variable names and units follow Open-Meteo.

| Column | Unit | Description |
|---|---|---|
| `location` | — | City/location name. |
| `time` | Local time (`Asia/Makassar`) | Hourly forecast or archive timestamp. |
| `island` | — | Island name. |
| `province` | — | Province name. |
| `elevation_m` | meters (m) | Location elevation returned by the API. |
| `shortwave_radiation` | W/m² | Shortwave radiation reaching the surface. |
| `direct_radiation` | W/m² | Direct solar radiation. |
| `diffuse_radiation` | W/m² | Diffuse solar radiation. |
| `cloud_cover` | % | Cloud cover, from 0 to 100%. |
| `temperature_2m` | °C | Air temperature at 2 meters above ground. |
| `wind_speed_10m` | km/h | Wind speed at 10 meters above ground (API default). |
| `source` | — | Data mode: `forecast` or `archive`. |
| `loaded_at` | UTC timestamp | Time the row was inserted or updated by the pipeline. |

The three radiation columns measure radiation intensity, not energy accumulated over an hour. The pipeline does not retrieve electricity generation or consumption data.

## Requirements

- Python 3
- pip
- Internet access to call the Open-Meteo APIs

Dependencies are listed in [`requirements.txt`](requirements.txt).

## How to run

From the project root, create and activate a virtual environment (PowerShell example), then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Fetch the latest forecast

```powershell
python -m src.pipeline
```

Forecast mode is the default. It fetches forecast data, validates and cleans it, and upserts the results into the clean database.

### Backfill historical archive data

```powershell
python -m src.pipeline --mode backfill --start 2025-01-01 --end 2025-01-31
```

Both `--start` and `--end` are required in backfill mode and must use the `YYYY-MM-DD` format. The pipeline stores the resulting rows with `source = archive`, separate from forecast rows in the same table.

### Run from the notebook

The notebook [`notebooks/run.ipynb`](notebooks/run.ipynb) includes a pipeline example. From a notebook kernel started in the project environment, run the setup cell that adds the project root to `sys.path`, then run the `# Pipeline` cell. The CLI commands above are the recommended way to select forecast or backfill mode.

## Output and processing

- Raw API responses are saved as timestamped JSON files in `data/raw/`. Forecast files use the `open_meteo_` prefix; archive files use `open_meteo_archive_`.
- Cleaned data is stored in `data/clean/energy_clean.db`, table `energy_clean`.
- Rows are uniquely keyed by location and time. New runs insert or update matching rows; they do not replace the entire table.
- Cleaning removes duplicate location/time rows, clips radiation values to a minimum of zero and cloud cover to the 0–100% range, and interpolates missing numeric values per location.
- Validation summaries and run details are written to `logs/pipeline.log`.

Always check the `source` column before analysis: `forecast` rows are predictions and must not be treated as historical observations; `archive` rows come from the historical archive API.
