"""Chemins et constantes partagés par tout le projet."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"
MODELS = ROOT / "models"

DATASET_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_XLSX = DATA_RAW / "online_retail_II.xlsx"
CLEAN_PARQUET = DATA_PROCESSED / "transactions_clean.parquet"

RANDOM_STATE = 42
