"""Téléchargement de la météo historique horaire à Passy via l'API Open-Meteo.

Source : https://open-meteo.com/en/docs/historical-weather-api (gratuit, sans clé).
Les données sont récupérées année par année puis sauvegardées brutes dans
data/raw/meteo_passy_hourly.csv. L'agrégation journalière se fera dans features.py.

Usage (depuis la racine du projet) :
    python -m src.collect.meteo
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

# --- Paramètres ---------------------------------------------------------------

API_URL = "https://archive-api.open-meteo.com/v1/archive"

# Coordonnées approximatives du fond de vallée à Passy.
# À remplacer par les coordonnées exactes de la station Atmo une fois connues.
LATITUDE = 45.918
LONGITUDE = 6.712

START_YEAR = 2015
# Les réanalyses ont quelques jours de retard : on s'arrête une semaine avant aujourd'hui.
END_DATE = date.today() - timedelta(days=7)

HOURLY_VARIABLES = [
    "temperature_2m",          # °C
    "relative_humidity_2m",    # %
    "dew_point_2m",            # °C
    "pressure_msl",            # hPa
    "surface_pressure",        # hPa
    "precipitation",           # mm
    "snowfall",                # cm
    "wind_speed_10m",          # km/h
    "wind_direction_10m",      # °
    "cloud_cover",             # %
    "shortwave_radiation",     # W/m²
    "boundary_layer_height",   # m — clé pour détecter les inversions
]

OUTPUT_PATH = Path("data/raw/meteo_passy_hourly.csv")


# --- Fonctions ----------------------------------------------------------------

def fetch_period(start: date, end: date, retries: int = 3) -> pd.DataFrame:
    """Télécharge la météo horaire entre deux dates (incluses)."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Europe/Paris",
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as err:
            print(f"  Tentative {attempt}/{retries} échouée : {err}")
            if attempt == retries:
                raise
            time.sleep(5 * attempt)

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    for year in range(START_YEAR, END_DATE.year + 1):
        start = date(year, 1, 1)
        end = min(date(year, 12, 31), END_DATE)
        print(f"Téléchargement {start} → {end} ...")
        frames.append(fetch_period(start, end))
        time.sleep(1)  # on reste poli avec l'API gratuite

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="time").sort_values("time")
    df.to_csv(OUTPUT_PATH, index=False)

    # Petit résumé pour vérifier que tout va bien
    print(f"\n{len(df):,} lignes sauvegardées dans {OUTPUT_PATH}")
    print(f"Période : {df['time'].min()} → {df['time'].max()}")
    print("\nValeurs manquantes par variable (%) :")
    print((df.isna().mean() * 100).round(2).to_string())


if __name__ == "__main__":
    main()
