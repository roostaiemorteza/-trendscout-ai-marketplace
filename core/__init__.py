"""TrendScout AI — core package."""
from core.pricing_engine import (  # noqa: F401
    compute_price_stats,
    recommend_price,
    calculate_net_profit,
    simulate_buybox_traffic,
    analyze_competitor_reviews,
)
from core.data_loader import load_market_data, load_reviews  # noqa: F401
