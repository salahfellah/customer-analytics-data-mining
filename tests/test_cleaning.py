import pandas as pd
import pytest

from src.cleaning import clean, iqr_outlier_mask


@pytest.fixture
def raw():
    return pd.DataFrame({
        "Invoice": ["1001", "1001", "C1002", "1003", "1004", "1005", "1006", "1007"],
        "StockCode": ["85123A", "85123A", "85123A", "22423", "POST", "22423", "21232", "gift_0001_10"],
        "Description": ["WHITE HEART", "WHITE HEART", "WHITE HEART", "CAKESTAND", "POSTAGE",
                        "CAKESTAND", "TRELLIS", "GIFT VOUCHER"],
        # l'annulation C1002 (-3) ne correspond à aucune commande : 1001 doit rester
        "Quantity": [6, 6, -3, 2, 1, 0, 3, 1],
        "InvoiceDate": pd.to_datetime(["2010-12-01 08:26"] * 2 + ["2010-12-02 10:00"] * 6),
        "Price": [2.55, 2.55, 2.55, 12.75, 18.0, 12.75, 1.25, 10.0],
        "Customer ID": [17850.0, 17850.0, 17850.0, None, 12583.0, 13047.0, 13047.0, 13047.0],
        "Country": ["United Kingdom"] * 8,
    })


def test_clean_keeps_only_valid_product_lines(raw):
    df, _ = clean(raw)
    # restent : la facture 1001 (dédoublonnée) et la facture 1006
    assert sorted(df["Invoice"]) == ["1001", "1006"]


def test_clean_adds_total_price(raw):
    df, _ = clean(raw)
    row = df[df["Invoice"] == "1001"].iloc[0]
    assert row["TotalPrice"] == pytest.approx(6 * 2.55)


def test_cleaning_log_is_consistent(raw):
    df, log = clean(raw)
    assert log["Lignes avant"].iloc[0] == len(raw)
    assert log["Lignes après"].iloc[-1] == len(df)
    assert (log["Lignes avant"] - log["Lignes supprimées"] == log["Lignes après"]).all()


def test_cancelled_original_order_is_removed():
    raw = pd.DataFrame({
        "Invoice": ["2001", "C2002", "2003"],
        "StockCode": ["23843", "23843", "23843"],
        "Description": ["PAPER CRAFT"] * 3,
        "Quantity": [80995, -80995, 12],
        "InvoiceDate": pd.to_datetime(["2011-12-09 09:15", "2011-12-09 09:27", "2011-12-10 10:00"]),
        "Price": [2.08, 2.08, 2.08],
        "Customer ID": [16446.0, 16446.0, 16446.0],
        "Country": ["United Kingdom"] * 3,
    })
    df, _ = clean(raw)
    # la commande géante annulée disparaît, la commande normale reste
    assert df["Invoice"].tolist() == ["2003"]


def test_customer_id_is_integer(raw):
    df, _ = clean(raw)
    assert str(df["CustomerID"].dtype) == "Int64"


def test_iqr_outlier_mask_flags_extremes():
    values = pd.Series([1, 2, 2, 3, 3, 3, 4, 4, 5, 100])
    mask = iqr_outlier_mask(values)
    assert mask.tolist() == [False] * 9 + [True]
