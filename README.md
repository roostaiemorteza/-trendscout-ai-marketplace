# 🛰️ TrendScout AI — Pazaryeri & E-Ticaret Otomasyonu

سامانه هوشمند قیمت‌گذاری، رصد رقبا و مدیریت مارکت‌پلیس‌ها
Veri Odaklı Akıllı Fiyatlandırma = Maksimum Satış ve Kâr

## Genel Bakış / Overview
TrendScout AI, Trendyol / Hepsiburada / Amazon TR pazar yerleri için geliştirilmiş
Streamlit tabanlı bir otomasyon panelidir. Fiyat savaşları (BuyBox), akıllı repricing,
stok erken uyarısı, net kâr hesaplama ve AI duygu analizini tek ekranda toplar.

## Mimari / Architecture
```
trendscout_ai/
├── app.py                    # Streamlit dashboard (5 sekmeli panel)
├── core/
│   ├── __init__.py           # Paket dışa aktarımları
│   ├── pricing_engine.py     # Fiyatlandırma, BuyBox, kâr, duygu analizi
│   └── data_loader.py        # CSV yükleme + türetilmiş alanlar
├── sample_data.csv           # 16 gerçekçi Türk pazaryeri ürünü
├── sample_reviews.csv        # Örnek müşteri yorumları
├── .streamlit/config.toml    # Koyu tema (neon yeşil / lacivert)
├── requirements.txt
└── README.md
```

## Özellikler / Features
- **Panel / Genel Görünüm:** metrik kartları (Toplam Ürün, Aktif BuyBox %84, Ortalama Kâr %22,
  Kritik Stok), Fiyat Savaşları (BuyBox) trafik grafiği, akıllı fiyatlandırma tablosu,
  kanal bazlı satış (donut) ve AI rakip yorum gauge'ı.
- **Akıllı Fiyatlandırma (Repricer):** `dengeli / agresif / kar_maks` stratejileri,
  minimum marj ve hedef BuyBox konumu ile fiyat önerisi.
- **Stok & Erken Uyarı:** satış hızına göre predictive stockout (runway days) ve renkli durum.
- **Finans & Net Kâr:** KDV, platform komisyonu ve kargo barem dahil net kâr hesabı.
- **AI Sentiment:** kelime tabanlı Türkçe duygu analizi (Negatif / Nötr / Pozitif) + gauge.

## Kurulum ve Çalıştırma / Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Tarayıcıda `http://localhost:8501` adresini açın.

## API Özeti
- `compute_price_stats(df, product_id=None)` — fiyat/marj/BuyBox istatistikleri
- `recommend_price(product_row, strategy, min_margin, target_pos)` — AI fiyat önerisi
- `calculate_net_profit(selling_price, buying_cost, category, shipping_barem, kdv_rate)` — net kâr
- `simulate_buybox_traffic(hours=24)` — 24 saatlik fiyat/trafik simülasyonu
- `analyze_competitor_reviews(sample_texts)` — duygu analizi özeti

Sürüm 1.0 — Demo verilerle çalışır; canlı API entegrasyonu için hazırdır.
