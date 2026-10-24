# Bali–Nusa Tenggara Energy Pipeline

This pipeline retrieves hourly weather data for 10 locations across Bali, West Nusa Tenggara, and East Nusa Tenggara. Solar radiation, cloud cover, temperature, and wind speed are provided as supporting data for energy analysis.

> **Important: the data produced by this pipeline is forecast data, not historical observational data.** Forecast values and their time range may change each time data is fetched as Open-Meteo updates its weather models.

## Data source

- **Provider:** [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Frequency:** hourly (`hourly`)
- **Timezone:** `Asia/Makassar`
- **Locations:** Denpasar, Jembrana, Mataram, Sumbawa Besar, Bima, Ruteng, Maumere, Waikabubak, Kupang, and Atambua. Their coordinates are defined in [`src/locations.py`](src/locations.py).
- **Time coverage:** follows the API's default forecast range because the pipeline does not set `forecast_days` or `past_days` parameters.

The API returns elevation information for each coordinate. Raw and cleaned data are stored in SQLite tables.

## Columns and units

The following columns are available in both the raw and cleaned data. Weather variable names and units follow Open-Meteo.

| Column | Unit | Description |
|---|---|---|
| `time` | Local time (`Asia/Makassar`) | Hourly forecast timestamp. |
| `shortwave_radiation` | W/m² | Shortwave radiation reaching the surface. |
| `direct_radiation` | W/m² | Direct solar radiation. |
| `diffuse_radiation` | W/m² | Diffuse solar radiation. |
| `cloud_cover` | % | Cloud cover, in the range 0–100%. |
| `temperature_2m` | °C | Air temperature at 2 meters above ground. |
| `wind_speed_10m` | km/h | Wind speed at 10 meters above ground (the API's default unit). |
| `lokasi` | — | City/location name. |
| `pulau` | — | Island name. |
| `provinsi` | — | Province name. |
| `elevasi_m` | meters (m) | Location elevation returned by the API. |

The `shortwave_radiation`, `direct_radiation`, and `diffuse_radiation` columns represent radiation intensity, not energy accumulated over an hour. This dataset contains energy-related weather variables; the pipeline does not retrieve electricity generation or consumption data.

## How to run

Requirements: Python 3 and pip. Project dependencies are listed in [`requirements.txt`](requirements.txt).

1. Open a terminal in the project directory, then create and activate a virtual environment (PowerShell example):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Launch Jupyter from the `notebooks` directory:

   ```powershell
   Set-Location notebooks
   jupyter notebook run.ipynb
   ```

4. In the [`notebooks/run.ipynb`](notebooks/run.ipynb) notebook, run the cells in order. The notebook fetches data from the API, creates a DataFrame, saves the raw data, cleans it, and then saves the cleaned data.

Fetching data requires an internet connection. Each run replaces the contents of the existing tables.

## Output and cleaning

- Raw data: `data/raw/energy_raw.db`, table `energy_raw`.
- Cleaned data: `data/clean/energy_clean.db`, table `energy_clean`.
- Cleaning removes duplicates based on location and time, clips radiation values to a minimum of zero and cloud cover to the 0–100% range, then interpolates missing numeric values separately for each location.

Since the source is a forecast, use this data as a prediction for the period returned by the API. Do not interpret it as past weather measurements or a historical record.
