"""
TrendScout AI — Veri yükleyici
Loads marketplace sample data and enriches it with derived fields.
"""
import os
import pandas as pd


def load_market_data(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data.csv")
    df = pd.read_csv(path)
    # Derived fields
    df["margin_pct"] = (
        (df["suggested_price"] - df["buying_cost"]) / df["suggested_price"] * 100
    ).round(1)
    return df


def load_reviews(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_reviews.csv")
    return pd.read_csv(path)
