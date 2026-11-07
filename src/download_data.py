"""Télécharge le jeu de données Online Retail II depuis l'UCI Machine Learning Repository.

Usage :
    python -m src.download_data
"""

import io
import urllib.request
import zipfile

from src.config import DATA_RAW, DATASET_URL, RAW_XLSX


def download(force: bool = False) -> None:
    if RAW_XLSX.exists() and not force:
        print(f"Déjà présent : {RAW_XLSX}")
        return

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement depuis {DATASET_URL} ...")
    with urllib.request.urlopen(DATASET_URL) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    xlsx_names = [n for n in archive.namelist() if n.lower().endswith(".xlsx")]
    if not xlsx_names:
        raise RuntimeError(f"Aucun fichier .xlsx dans l'archive : {archive.namelist()}")

    with archive.open(xlsx_names[0]) as src, open(RAW_XLSX, "wb") as dst:
        dst.write(src.read())
    print(f"Enregistré : {RAW_XLSX} ({RAW_XLSX.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    download()
