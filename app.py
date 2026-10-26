"""
TrendScout AI — Pazaryeri & E-Ticaret Otomasyonu
سامانه هوشمند قیمت‌گذاری، رصد رقبا و مدیریت مارکت‌پلیس‌ها
اجرا:  streamlit run app.py
"""
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.pricing_engine import (
    compute_price_stats,
    recommend_price,
    calculate_net_profit,
    simulate_buybox_traffic,
    analyze_competitor_reviews,
    SHIPPING_BAREM,
)
from core.data_loader import load_market_data

# ------------------------------------------------------------------
st.set_page_config(
    page_title="TrendScout AI — Pazaryeri Otomasyonu",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
LOGO = os.path.join(ASSETS, "logo.svg")

CARD = "background:#1e293b;border:1px solid #334155;border-radius:14px;padding:14px 18px;"
GREEN = "#22c55e"

# ==================================================================
# ROBUST COLUMN HANDLING
# ------------------------------------------------------------------
# Canonical column names app.py expects, mapped from possible aliases
# found in different versions of sample_data.csv. Any canonical column
# that is still missing after aliasing is created with a safe default
# so the app never raises a KeyError (fix for line-112 style crash).
COLUMN_ALIASES = {
    "product_id": ["product_id", "id", "sku", "urun_id", "کد_محصول"],
    "title": ["title", "name", "product_name", "urun_adi", "عنوان"],
    "category": ["category", "kategori", "دسته"],
    "buying_cost": ["buying_cost", "cost", "maliyet", "alis_fiyati",
                    "purchase_price", "هزینه_خرید"],
    "current_price": ["current_price", "price", "fiyat", "list_price",
                      "قیمت_فعلی"],
    "competitor_min_price": ["competitor_min_price", "competitor_price",
                             "min_competitor_price", "rakip_fiyat",
                             "lowest_competitor_price"],
    "suggested_price": ["suggested_price", "recommended_price", "onerilen_fiyat"],
    "buybox_owner": ["buybox_owner", "buy_box_owner", "buybox", "owner",
                     "sahibi", "buybox_sahibi"],
    "stock_quantity": ["stock_quantity", "stock", "qty", "stok", "inventory",
                       "موجودی"],
    "sales_velocity_daily": ["sales_velocity_daily", "daily_sales",
                             "sales_velocity", "gunluk_satis", "sales_per_day"],
    "return_rate": ["return_rate", "iade_orani", "refund_rate"],
    "kdv_rate": ["kdv_rate", "vat_rate", "tax_rate", "vergi_orani"],
    "commission_rate": ["commission_rate", "komisyon_orani", "fee_rate"],
    "platform": ["platform", "channel", "marketplace", "kanal"],
}

COLUMN_DEFAULTS = {
    "product_id": lambda i: f"TRT-{1000 + i}",
    "title": lambda i: f"Ürün {1000 + i}",
    "category": lambda i: "Genel",
    "buying_cost": lambda i: 0.0,
    "current_price": lambda i: np.nan,
    "competitor_min_price": lambda i: np.nan,
    "suggested_price": lambda i: np.nan,
    "buybox_owner": lambda i: "Rakip",
    "stock_quantity": lambda i: 0,
    "sales_velocity_daily": lambda i: 1,
    "return_rate": lambda i: 0.0,
    "kdv_rate": lambda i: 20,
    "commission_rate": lambda i: 15,
    "platform": lambda i: "Trendyol",
}


def _norm(s):
    return str(s).strip().lower().replace(" ", "_")


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename aliased columns to canonical names and fill any missing
    canonical column with a sensible default. Never raises KeyError."""
    df = df.copy()
    df.columns = [_norm(c) for c in df.columns]

    renamed = {}
    for canon, aliases in COLUMN_ALIASES.items():
        if canon in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                renamed[alias] = canon
                break
    if renamed:
        df = df.rename(columns=renamed)

    for canon, default_fn in COLUMN_DEFAULTS.items():
        if canon not in df.columns:
            df[canon] = [default_fn(i) for i in range(len(df))]

    # Numeric coercion + imputation so math never breaks
    num_cols = ["buying_cost", "current_price", "competitor_min_price",
                "suggested_price", "stock_quantity", "sales_velocity_daily",
                "return_rate", "kdv_rate", "commission_rate"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["current_price", "competitor_min_price", "suggested_price"]:
        fill = df[c].fillna(df["buying_cost"] * 1.3).clip(lower=1.0)
        df[c] = df[c].fillna(fill).clip(lower=1.0)
    df["buying_cost"] = df["buying_cost"].fillna(0.0)
    df["stock_quantity"] = df["stock_quantity"].fillna(0).astype(int)
    df["sales_velocity_daily"] = (
        df["sales_velocity_daily"].fillna(1).clip(lower=0.1).astype(float))
    df["kdv_rate"] = df["kdv_rate"].fillna(20)
    df["buybox_owner"] = df["buybox_owner"].astype(str)

    # Derived margin, guard against divide-by-zero
    df["margin_pct"] = np.where(
        df["suggested_price"] > 0,
        (df["suggested_price"] - df["buying_cost"]) / df["suggested_price"] * 100,
        0.0,
    ).round(1)
    return df


# ---------------------------- Header ------------------------------
st.markdown(
    """
    <div style="text-align:center;padding:4px 0 10px 0;">
        <div style="font-size:20px;font-weight:700;color:#22c55e;direction:rtl;">
            Pazaryeri Entegrasyonu, Akıllı Fiyatlandırma ve Rakip Analiz Otomasyonu
        </div>
        <h1 style="margin:6px 0 2px 0;color:#f8fafc;">TrendScout AI — Pazaryeri &amp; E-Ticaret Otomasyonu</h1>
        <div style="color:#94a3b8;">Veri Odaklı Akıllı Fiyatlandırma = Maksimum Satış ve Kâr</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Data --------------------------------
try:
    df = ensure_columns(load_market_data())
except Exception as e:
    st.error(f"Veri yüklenemedi: {e}")
    st.stop()
stats = compute_price_stats(df)

# ---------------------------- Metrics -----------------------------
kritik = df[df["stock_quantity"] <= 20]
buybox_biz = (df["buybox_owner"].str.lower() == "biz").sum()

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div style="{CARD}"><div style="color:#94a3b8;font-size:13px;">TOPLAM ÜRÜN</div>'
            f'<div style="font-size:30px;font-weight:800;color:#22c55e;">{len(df):,}</div></div>',
            unsafe_allow_html=True)
c2.markdown(f'<div style="{CARD}"><div style="color:#94a3b8;font-size:13px;">AKTİF BUYBOX</div>'
            f'<div style="font-size:30px;font-weight:800;color:#22c55e;">'
            f'%{stats["buybox_rate"]:.1f}</div></div>',
            unsafe_allow_html=True)
c3.markdown(f'<div style="{CARD}"><div style="color:#94a3b8;font-size:13px;">ORTALAMA KAR</div>'
            f'<div style="font-size:30px;font-weight:800;color:#22c55e;">'
            f'%{stats["mean_margin"]}</div></div>',
            unsafe_allow_html=True)
c4.markdown(f'<div style="{CARD}"><div style="color:#94a3b8;font-size:13px;">KRİTİK STOK UYARISI</div>'
            f'<div style="font-size:30px;font-weight:800;color:#f87171;">{len(kritik)} Ürün</div></div>',
            unsafe_allow_html=True)
st.write("")

# ---------------------------- Tabs --------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Panel / Genel Görünüm",
    "💰 Akıllı Fiyatlandırma & BuyBox",
    "📦 Stok & Erken Uyarı",
    "🧾 Finans & Net Kâr Hesaplayıcı",
    "🧠 Müşteri Yorum Analizi (AI)",
])

# ===================== TAB 1 — PANEL ==============================
with tab1:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("⚔️ Fiyat Savaşları (BuyBox) Trafiği")
        traffic = simulate_buybox_traffic(24)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=traffic["hour"], y=traffic["our_price"],
                                 name="Bizim Fiyat", line=dict(color=GREEN, width=2)))
        fig.add_trace(go.Scatter(x=traffic["hour"], y=traffic["competitor_price"],
                                 name="Rakip Fiyat", line=dict(color="#f97316", width=2)))
        fig.add_trace(go.Bar(x=traffic["hour"], y=traffic["traffic"], name="Trafik",
                             marker_color="#3b82f6", opacity=0.35, yaxis="y2"))
        fig.update_layout(
            template="plotly_dark", height=340, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#0b1120", plot_bgcolor="#0b1120",
            yaxis=dict(title="Fiyat (TL)"), yaxis2=dict(overlaying="y", side="right",
                                                        title="Trafik", showgrid=False),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🤖 Akıllı Fiyatlandırma ve Rakip Eşleştirme")
        table = df.head(8).copy()
        table["Aksiyon"] = np.where(
            table["buybox_owner"].str.lower() == "biz", "✅ Koru", "🔄 Repricing")
        st.dataframe(
            table.rename(columns={
                "product_id": "Kod", "title": "Ürün",
                "suggested_price": "Birim Fiyat (TL)",
                "competitor_min_price": "Rakip Fiyat (TL)",
                "buybox_owner": "BuyBox Sahibi",
            })[["Kod", "Ürün", "Birim Fiyat (TL)", "Rakip Fiyat (TL)",
                "BuyBox Sahibi", "Aksiyon"]],
            use_container_width=True, hide_index=True,
        )
        st.warning(f"⚠️ **Kritik Durum:** {len(kritik)} üründe stok kritik seviyede, "
                   f"{len(df) - buybox_biz} üründe BuyBox rakipte. "
                   "Onay ile otomatik repricing başlatılabilir.")

    with right:
        st.subheader("🥧 Kanal Bazlı Satış")
        kanal = (df.groupby("platform")["sales_velocity_daily"].sum()
                 .reset_index())
        kanal.columns = ["Kanal", "Satış"]
        figd = px.pie(kanal, names="Kanal", values="Satış", hole=0.55,
                      color_discrete_sequence=["#3b82f6", "#f97316", "#14b8a6"])
        figd.update_layout(template="plotly_dark", height=300,
                           margin=dict(l=10, r=10, t=10, b=10),
                           paper_bgcolor="#0b1120", legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(figd, use_container_width=True)

        st.subheader("🧠 Yapay Zeka Rakip Yorum Analizi")
        reviews = [
            "Ürün harika, çok hızlı geldi, tavsiye ederim!",
            "Kutu kırık geldi, pişman oldum.",
            "Kaliteli ve sorunsuz, memnun kaldım.",
            "Kargo geçti ama ürün iyi.",
            "Çalışmıyor, iade ettim.",
            "Mükemmel, beklediğimden iyi.",
        ]
        sent = analyze_competitor_reviews(reviews)
        figg = go.Figure(go.Indicator(
            mode="gauge+number", value=sent["overall_score"],
            gauge=dict(axis=dict(range=[0, 100]),
                       bar=dict(color=GREEN),
                       steps=[dict(range=[0, 40], color="#7f1d1d"),
                              dict(range=[40, 60], color="#78350f"),
                              dict(range=[60, 100], color="#14532d")]),
            number=dict(suffix=" / 100")))
        figg.update_layout(template="plotly_dark", height=240,
                           margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="#0b1120")
        st.plotly_chart(figg, use_container_width=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Negatif", f"%{sent['negatif_pct']}", delta_color="inverse")
        m2.metric("Nötr", f"%{sent['notr_pct']}")
        m3.metric("Pozitif", f"%{sent['pozitif_pct']}", delta_color="off")

# ============== TAB 2 — AKILLI FİYATLANDIRMA ======================
with tab2:
    st.subheader("💰 Akıllı Fiyatlandırma (Repricer) & BuyBox Stratejileri")
    labels = df["product_id"].astype(str) + " — " + df["title"].astype(str)
    pid = st.selectbox("Ürün seçin", labels)
    sel_id = str(pid).split(" — ")[0]
    match = df[df["product_id"].astype(str) == sel_id]
    row = match.iloc[0] if len(match) else df.iloc[0]
    s1, s2, s3 = st.columns(3)
    strategy = s1.selectbox("Strateji", ["dengeli", "agresif", "kar_maks"])
    min_margin = s2.number_input("Min. marj (%)", 5.0, 60.0, 15.0, 1.0)
    target_pos = s3.slider("Hedef BuyBox konumu", 1, 5, 1)
    rec = recommend_price(row, strategy, min_margin, target_pos)
    st.success(f"Önerilen fiyat: **{rec['suggested_price']:,.2f} TL** — beklenen marj: "
               f"**%{rec['margin_pct']}** — {rec['note']}")
    st.dataframe(df[["product_id", "title", "current_price", "competitor_min_price",
                     "suggested_price", "buybox_owner", "platform"]],
                 use_container_width=True, hide_index=True)

# ============== TAB 3 — STOK & ERKEN UYARI ========================
with tab3:
    st.subheader("📦 Stok & Erken Uyarı (Predictive Stockout)")
    view = df.copy()
    view["runway_days"] = (view["stock_quantity"] /
                           view["sales_velocity_daily"].clip(lower=0.1)).round(1)
    def durum(d):
        return "🔴 Kritik" if d <= 3 else ("🟠 Uyarı" if d <= 10 else "🟢 Güvenli")
    view["Durum"] = view["runway_days"].apply(durum)
    a, b = st.columns(2)
    a.metric("Kritik stok (≤3 gün)", int((view["runway_days"] <= 3).sum()))
    b.metric("Sıfırlanma riski (≤10 gün)", int((view["runway_days"] <= 10).sum()))
    figs = px.bar(view.sort_values("runway_days"), x="title", y="runway_days",
                  color="Durum", color_discrete_map={
                      "🔴 Kritik": "#ef4444", "🟠 Uyarı": "#f97316", "🟢 Güvenli": GREEN},
                  labels={"title": "Ürün", "runway_days": "Kalan gün (runway)"})
    figs.update_layout(template="plotly_dark", height=420,
                       paper_bgcolor="#0b1120", plot_bgcolor="#0b1120",
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(figs, use_container_width=True)

# ============== TAB 4 — FİNANS ====================================
with tab4:
    st.subheader("🧾 Finans & Net Kâr Hesaplayıcı (E-Fatura / KDV / Komisyon)")
    f1, f2, f3, f4 = st.columns(4)
    sp = f1.number_input("Satış fiyatı (TL)", 1.0, 1e6, float(row["suggested_price"]), 10.0)
    bc = f2.number_input("Alış maliyeti (TL)", 0.0, 1e6, float(row["buying_cost"]), 10.0)
    cat = f3.selectbox("Platform / Komisyon",
                       ["Trendyol", "Hepsiburada", "Amazon TR"])
    barem = f4.selectbox("Kargo barem", list(SHIPPING_BAREM.keys()))
    kdv = st.slider("KDV oranı (%)", 0, 27, int(float(row["kdv_rate"])))
    np_ = calculate_net_profit(sp, bc, cat, barem, kdv)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Komisyon", f"{np_['commission']:,.0f} TL", f"%{np_['commission_rate_pct']}")
    m2.metric("Kargo", f"{np_['shipping']:,.0f} TL")
    m3.metric("KDV payı", f"{np_['kdv']:,.0f} TL")
    m4.metric("Net Kâr", f"{np_['net_profit']:,.0f} TL")
    m5.metric("Net Marj", f"%{np_['net_margin_pct']}")
    st.info("Hesaplama: Satış − Maliyet − Komisyon − Kargo − KDV payı = Net Kâr "
            "(KDV satış fiyatının içinde kabul edilir).")

# ============== TAB 5 — YORUM ANALİZİ =============================
with tab5:
    st.subheader("🧠 Müşteri / Rakip Yorum Analizi (AI Sentiment)")
    default_txt = "\n".join([
        "Ürün harika, çok hızlı geldi, tavsiye ederim!",
        "Kutu kırık geldi, pişman oldum.",
        "Kaliteli ve sorunsuz, memnun kaldım.",
        "Kargo geçti ama ürün iyi.",
        "Çalışmıyor, iade ettim.",
        "Mükemmel, beklediğimden iyi.",
    ])
    txt = st.text_area("Yorumları satır satır girin", default_txt, height=160)
    texts = [l.strip() for l in txt.split("\n") if l.strip()]
    if st.button("🔍 Analizi Çalıştır"):
        res = analyze_competitor_reviews(texts)
        g1, g2, g3 = st.columns(3)
        g1.metric("Negatif", f"%{res['negatif_pct']}", delta_color="inverse")
        g2.metric("Nötr", f"%{res['notr_pct']}")
        g3.metric("Pozitif", f"%{res['pozitif_pct']}", delta_color="off")
        det = pd.DataFrame(res["details"])
        st.dataframe(det.rename(columns={"text": "Yorum", "label": "Duygu", "score": "Skor"}),
                     use_container_width=True, hide_index=True)
        figs = go.Figure(go.Indicator(
            mode="gauge+number", value=res["overall_score"],
            gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=GREEN),
                       steps=[dict(range=[0, 40], color="#7f1d1d"),
                              dict(range=[40, 60], color="#78350f"),
                              dict(range=[60, 100], color="#14532d")]),
            number=dict(suffix=" / 100"),
            title=dict(text="Genel Duygu Skoru")))
        figs.update_layout(template="plotly_dark", height=300,
                           margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="#0b1120")
        st.plotly_chart(figs, use_container_width=True)

# ---------------------------- Footer ------------------------------
st.divider()
f1, f2, f3, f4 = st.columns(4)
f1.markdown("💥 **Maksimum Kâr ve Hızlı Satış**")
f2.markdown("📈 **BuyBox Oranı Artışı**")
f3.markdown("⏱️ **7/24 Kesintisiz Takip**")
f4.markdown("🧾 **Entegre Faturalandırma**")
