"""Chargement et nettoyage des transactions Online Retail II.

Chaque étape de nettoyage est une fonction pure (DataFrame -> DataFrame) ; `clean` les enchaîne
et renvoie aussi un journal (une ligne par étape) pour documenter les décisions dans le notebook.
"""

import re
from pathlib import Path

import pandas as pd

from src.config import RAW_XLSX

# Codes qui ne correspondent pas à des produits vendus (frais de port, remises, ajustements, tests...)
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "C2", "D", "S", "B", "CRUK", "PADS", "BANK CHARGES",
    "AMAZONFEE", "ADJUST", "ADJUST2", "TEST001", "TEST002",
}
NON_PRODUCT_PATTERN = re.compile(r"^(gift_|TEST)", re.IGNORECASE)

COLUMN_NAMES = {"Customer ID": "CustomerID"}


def load_raw(path: Path = RAW_XLSX) -> pd.DataFrame:
    """Lit les deux feuilles du fichier Excel (2009-2010 et 2010-2011) et les concatène."""
    sheets = pd.read_excel(path, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
    return pd.concat(sheets.values(), ignore_index=True)


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme les colonnes et fixe les types."""
    df = df.rename(columns=COLUMN_NAMES).copy()
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].astype("string").str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["CustomerID"] = df["CustomerID"].astype("Int64")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates()


def drop_cancelled_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les commandes d'origine qui ont été annulées ensuite.

    Une annulation (« C... ») ne supprime pas la commande d'origine dans les données : sans cette étape,
    une commande de 80 995 articles annulée le jour même resterait comptée comme une vente.
    On apparie chaque annulation à la commande du même client, du même produit et de la même quantité,
    passée avant l'annulation.
    """
    is_cancel = df["Invoice"].str.startswith("C")
    cancels = df.loc[is_cancel & df["CustomerID"].notna(),
                     ["CustomerID", "StockCode", "Quantity", "InvoiceDate"]].copy()
    cancels["Quantity"] = -cancels["Quantity"]
    cancels = cancels.rename(columns={"InvoiceDate": "CancelDate"})

    orders = df[~is_cancel].reset_index()
    matched = orders.merge(cancels, on=["CustomerID", "StockCode", "Quantity"])
    matched = matched[matched["InvoiceDate"] <= matched["CancelDate"]]
    return df.drop(index=matched["index"].unique())


def drop_cancellations(df: pd.DataFrame) -> pd.DataFrame:
    """Les factures annulées ont un numéro commençant par « C »."""
    return df[~df["Invoice"].str.startswith("C")]


def drop_missing_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Sans identifiant client, une ligne est inutilisable pour la segmentation et le churn."""
    return df[df["CustomerID"].notna()]


def drop_non_positive(df: pd.DataFrame) -> pd.DataFrame:
    """Quantités ou prix nuls/négatifs : retours, ajustements ou erreurs de saisie."""
    return df[(df["Quantity"] > 0) & (df["Price"] > 0)]


def drop_non_products(df: pd.DataFrame) -> pd.DataFrame:
    codes = df["StockCode"]
    is_non_product = codes.str.upper().isin(NON_PRODUCT_CODES) | codes.str.match(NON_PRODUCT_PATTERN)
    return df[~is_non_product]


def add_total_price(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["TotalPrice"] = df["Quantity"] * df["Price"]
    return df


CLEANING_STEPS = [
    ("Doublons exacts", drop_duplicates,
     "Lignes identiques enregistrées plusieurs fois"),
    ("Commandes annulées ensuite", drop_cancelled_orders,
     "Commande d'origine appariée à une annulation (même client, produit et quantité)"),
    ("Factures d'annulation", drop_cancellations,
     "Numéro de facture commençant par « C »"),
    ("Client inconnu", drop_missing_customers,
     "Customer ID manquant : inutilisable pour l'analyse client"),
    ("Quantité ou prix ≤ 0", drop_non_positive,
     "Retours, ajustements ou erreurs de saisie"),
    ("Codes non-produits", drop_non_products,
     "Frais de port, remises, frais bancaires, tests..."),
]


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applique toutes les étapes et renvoie (données propres, journal de nettoyage)."""
    df = standardize(raw)
    log = []
    for name, step, reason in CLEANING_STEPS:
        before = len(df)
        df = step(df)
        log.append({"Étape": name, "Lignes avant": before, "Lignes supprimées": before - len(df),
                    "Lignes après": len(df), "Justification": reason})
    df = add_total_price(df).reset_index(drop=True)
    return df, pd.DataFrame(log)


def iqr_outlier_mask(values: pd.Series, k: float = 1.5) -> pd.Series:
    """True pour les valeurs en dehors de [Q1 - k*IQR, Q3 + k*IQR]."""
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (values < q1 - k * iqr) | (values > q3 + k * iqr)
