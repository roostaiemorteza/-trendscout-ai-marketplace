"""
TrendScout AI — Pricing & Intelligence Engine
Fiyatlandırma, BuyBox simülasyonu, net kâr ve AI duygu analizi.
"""
import random
from collections import Counter

import numpy as np
import pandas as pd

# Piyasa komisyon oranları (yaklaşık, %)
COMMISSION_RATES = {
    "Trendyol": 0.15,
    "Hepsiburada": 0.14,
    "Amazon TR": 0.15,
}

# Kargo barem aralıkları (desi bazlı sabit maliyet, TL)
SHIPPING_BAREM = {
    "0-1 desi": 32.0,
    "1-3 desi": 45.0,
    "3-10 desi": 65.0,
    "10+ desi": 95.0,
}

POSITIVE_WORDS = {
    "harika", "mükemmel", "süper", "memnun", "kaliteli", "hızlı", "tavsiye",
    "beğendim", "sorunsuz", "teşekkür", "iyi", "faydalı", "beğendi", "öneririm",
}
NEGATIVE_WORDS = {
    "kötü", "berbat", "pişman", "iade", "sorun", "geç", "kırık", "çalışmıyor",
    "hata", "olumsuz", "vasat", "pahalı", "gecikme", "şikayet", "bozuk",
}


# ------------------------------------------------------------------
def compute_price_stats(df, product_id=None):
    """Ürün veya tüm katalog için fiyat istatistikleri.

    product_id verilirse yalnızca o ürünle ilgili satırlar dikkate alınır.
    """
    sub = df[df["product_id"] == product_id] if product_id is not None else df
    if len(sub) == 0:
        return {"n_products": 0, "mean_price": 0, "mean_margin": 0.0,
                "buybox_rate": 0.0, "trending": 0, "min_price": 0, "max_price": 0}

    margins = (sub["suggested_price"] - sub["buying_cost"]) / sub["suggested_price"] * 100
    buybox_rate = (sub["buybox_owner"].astype(str).str.lower() == "biz").mean() * 100
    return {
        "n_products": int(sub["product_id"].nunique()),
        "mean_price": round(float(sub["suggested_price"].mean()), 2),
        "mean_margin": round(float(margins.mean()), 1),
        "buybox_rate": round(float(buybox_rate), 1),
        "trending": int((sub["sales_velocity_daily"] > 25).sum()),
        "min_price": round(float(sub["suggested_price"].min()), 2),
        "max_price": round(float(sub["suggested_price"].max()), 2),
    }


# ------------------------------------------------------------------
def recommend_price(product_row, strategy="dengeli", min_margin=15.0, target_pos=1):
    """Ürün satırı için AI önerilen fiyat üretir.

    strategy: 'agresif' (en düşük rakibin altı), 'dengeli' (rakip civarı),
              'kar_maks' (kâr maksimize eden üst bant fiyat).
    """
    price = float(product_row.get("suggested_price", 0) or 0)
    cost = float(product_row.get("buying_cost", 0) or 0)
    comp_min = float(product_row.get("competitor_min_price", 0) or 0) or price
    comp_min = max(comp_min, 0.01)

    if strategy == "agresif":
        new_price = comp_min * 0.98
    elif strategy == "kar_maks":
        new_price = max(price, comp_min * 1.08)
    else:  # dengeli
        new_price = max((comp_min + price) / 2.0, comp_min * 1.01)

    # Kâr hedefi: konum kadar rakibin üstünde ama minimum marja uyumlu
    new_price = max(new_price, comp_min * (1.0 + 0.005 * target_pos))
    min_price = cost / max(1 - min_margin / 100.0, 0.05)
    if new_price < min_price:
        new_price = min_price
        note = f"Minimum maraj (%{min_margin}) zorunlu kıldı."
    else:
        note = f"{strategy.capitalize()} stratejiye göre optimize edildi."

    return {
        "suggested_price": round(new_price, 2),
        "strategy": strategy,
        "margin_pct": round((new_price - cost) / new_price * 100, 1),
        "note": note,
    }


# ------------------------------------------------------------------
def calculate_net_profit(selling_price, buying_cost, category,
                         shipping_barem="1-3 desi", kdv_rate=20.0):
    """Net kâr hesabı: KDV, komisyon ve kargo dahil (TL)."""
    shipping = SHIPPING_BAREM.get(shipping_barem, 45.0)
    commission_rate = COMMISSION_RATES.get(category, 0.15)
    commission = selling_price * commission_rate
    kdv = selling_price * (kdv_rate / 100.0) / (1 + kdv_rate / 100.0)  # dahil KDV payı
    net = selling_price - buying_cost - commission - shipping - kdv
    return {
        "selling_price": round(selling_price, 2),
        "buying_cost": round(buying_cost, 2),
        "commission": round(commission, 2),
        "commission_rate_pct": round(commission_rate * 100, 1),
        "shipping": round(shipping, 2),
        "kdv": round(kdv, 2),
        "net_profit": round(net, 2),
        "net_margin_pct": round(net / selling_price * 100, 1) if selling_price else 0.0,
    }


# ------------------------------------------------------------------
def simulate_buybox_traffic(hours=24, seed=42):
    """24 saatlik BuyBox trafiği / fiyat savaşı simülasyonu."""
    rng = np.random.default_rng(seed)
    hours_axis = list(range(hours))
    our_price = 900 + rng.normal(0, 12, hours).cumsum() * 0.05
    competitor = 900 + rng.normal(0, 15, hours).cumsum() * 0.06
    traffic = (400 + 250 * np.sin(np.linspace(0, 2 * np.pi, hours))
               + rng.normal(0, 25, hours)).clip(min=50)
    buybox_win = (our_price <= competitor).astype(int)
    return pd.DataFrame({
        "hour": hours_axis,
        "our_price": our_price.round(2),
        "competitor_price": competitor.round(2),
        "traffic": traffic.round(0).astype(int),
        "buybox_win": buybox_win,
    })


# ------------------------------------------------------------------
def analyze_competitor_reviews(sample_texts):
    """Basit kelime-tabanlı Türkçe duygu analizi (negatif / nötr / pozitif)."""
    results = []
    for text in sample_texts:
        t = str(text).lower()
        pos = sum(w in t for w in POSITIVE_WORDS)
        neg = sum(w in t for w in NEGATIVE_WORDS)
        if pos > neg:
            label = "Pozitif"
        elif neg > pos:
            label = "Negatif"
        else:
            label = "Nötr"
        score = 50 + 25 * (pos - neg)
        results.append({"text": text, "label": label, "score": int(np.clip(score, 0, 100))})
    counts = Counter(r["label"] for r in results)
    total = max(len(results), 1)
    summary = {
        "details": results,
        "negatif": counts.get("Negatif", 0),
        "notr": counts.get("Nötr", 0),
        "pozitif": counts.get("Pozitif", 0),
        "negatif_pct": round(counts.get("Negatif", 0) / total * 100, 1),
        "notr_pct": round(counts.get("Nötr", 0) / total * 100, 1),
        "pozitif_pct": round(counts.get("Pozitif", 0) / total * 100, 1),
        "overall_score": int(np.clip(50 + 25 * (counts.get("Pozitif", 0) - counts.get("Negatif", 0)), 0, 100)),
    }
    return summary
