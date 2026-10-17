import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

# ------------------------------------------------------------
# MarketBot v0.2
# Crypto: CoinGecko public API (market data)
# FX: Frankfurter reference exchange rates (daily, not live broker quotes)
# Read-only dashboard: no broker connection and no order execution.
# ------------------------------------------------------------

st.set_page_config(
    page_title="MarketBot | Crypto & Forex",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BG = "#08111f"
PANEL = "#0d1a2b"
BORDER = "#20334d"
TEXT = "#e5eefc"
MUTED = "#8da6c6"
GREEN = "#00d3a7"
RED = "#ff4d6d"
BLUE = "#3285ff"
ORANGE = "#ffad42"

st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{ background: #091525; border-right: 1px solid {BORDER}; }}
    [data-testid="stHeader"] {{ background: rgba(8,17,31,0.9); }}
    h1, h2, h3 {{ color: {TEXT}; }}
    .brand {{ font-size: 1.65rem; font-weight: 800; letter-spacing: -0.5px; }}
    .subbrand {{ color: {MUTED}; font-size: .88rem; margin-top: -8px; }}
    .demo-pill {{ display:inline-block; border:1px solid #287e6f; color:#8cebd8;
                  background:#102e32; padding:5px 11px; border-radius:18px;
                  font-size:.78rem; font-weight:600; }}
    .metric-card {{ background:linear-gradient(135deg,#101f33,#0b1728);
                    border:1px solid {BORDER}; border-radius:13px;
                    padding:16px 18px; min-height:105px; }}
    .metric-label {{ color:{MUTED}; font-size:.82rem; }}
    .metric-value {{ color:{TEXT}; font-size:1.55rem; font-weight:750; margin-top:5px; }}
    .metric-note {{ color:{MUTED}; font-size:.78rem; margin-top:3px; }}
    .section-title {{ font-size:1.02rem; font-weight:700; color:{TEXT}; margin-bottom:10px; }}
    .small-muted {{ color:{MUTED}; font-size:.78rem; }}
    div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:10px; overflow:hidden; }}
    div.stButton > button {{ border-radius:9px; }}
    hr {{ border-color:{BORDER}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

CRYPTO = {
    "BTC/USDT": {"id": "bitcoin", "symbol": "BTC"},
    "ETH/USDT": {"id": "ethereum", "symbol": "ETH"},
    "SOL/USDT": {"id": "solana", "symbol": "SOL"},
    "BNB/USDT": {"id": "binancecoin", "symbol": "BNB"},
    "XRP/USDT": {"id": "ripple", "symbol": "XRP"},
}
FX_PAIRS = {
    "EUR/USD": ("EUR", "USD"),
    "GBP/USD": ("GBP", "USD"),
    "USD/JPY": ("USD", "JPY"),
    "AUD/USD": ("AUD", "USD"),
}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_crypto_markets():
    ids = ",".join(item["id"] for item in CRYPTO.values())
    url = "https://api.coingecko.com/api/v3/coins/markets"
    response = requests.get(
        url,
        params={
            "vs_currency": "usd",
            "ids": ids,
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        },
        timeout=15,
        headers={"accept": "application/json"},
    )
    response.raise_for_status()
    data = response.json()
    return {item["id"]: item for item in data}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_crypto_history(coin_id: str, days: int):
