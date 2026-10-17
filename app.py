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
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    response = requests.get(
        url,
        params={"vs_currency": "usd", "days": str(days)},
        timeout=15,
        headers={"accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    prices = payload.get("prices", [])
    if not prices:
        raise ValueError("La API no devolvió histórico de precios.")
    df = pd.DataFrame(prices, columns=["timestamp_ms", "Precio"])
    df["Hora"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True).dt.tz_convert(None)
    return df[["Hora", "Precio"]]

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx_rate(base: str, quote: str):
    # Frankfurter provides daily reference rates, not broker ticks or intraday quotes.
    url = f"https://api.frankfurter.dev/v2/rate/{base.lower()}/{quote.lower()}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx_history(base: str, quote: str, start_date: str, end_date: str):
    url = "https://api.frankfurter.dev/v2/rates"
    response = requests.get(
        url,
        params={"base": base, "quotes": quote, "from": start_date, "to": end_date},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        raise ValueError("No hay datos históricos para el periodo solicitado.")
    df = pd.DataFrame(payload)
    df["Fecha"] = pd.to_datetime(df["date"])
    df["Precio"] = df["rate"]
    return df[["Fecha", "Precio"]]

def fmt_price(value, digits=2):
    return f"{value:,.{digits}f}"

with st.sidebar:
    st.markdown('<div class="brand">📊 Market<span style="color:#3285ff">Bot</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">Crypto & Forex · Panel de análisis</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "NAVEGACIÓN",
        ["Inicio", "Mercados", "Gráficos", "Configuración"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown('<span class="demo-pill">● SOLO LECTURA</span>', unsafe_allow_html=True)
    st.caption("Datos externos; disponibilidad según cada proveedor.")
    st.caption("Sin conexión a cuentas de trading ni ejecución de órdenes.")
    st.markdown("---")
    st.caption("MarketBot v0.2")

st.markdown(
    '<div class="brand">Market<span style="color:#3285ff">Bot</span></div>'
    '<div class="subbrand">Crypto & Forex · Cotizaciones e históricos</div>',
    unsafe_allow_html=True,
