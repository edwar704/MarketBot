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
    '<div class="brand">Market<span style="color:#3285ff">Bot</span></div>' +
    '<div class="subbrand">Crypto & Forex · Cotizaciones e históricos</div>',
    unsafe_allow_html=True,
)
st.markdown("")

left, right = st.columns([4, 1])
with left:
    st.markdown(f"### {page}")
with right:
    st.markdown('<div style="text-align:right"><span class="demo-pill">SOLO LECTURA</span></div>', unsafe_allow_html=True)

if page in ("Inicio", "Mercados"):
    try:
        crypto_data = fetch_crypto_markets()
        crypto_error = None
    except Exception as exc:
        crypto_data = {}
        crypto_error = str(exc)

    fx_data = {}
    fx_errors = {}
    for pair, (base, quote) in FX_PAIRS.items():
        try:
            fx_data[pair] = fetch_fx_rate(base, quote)
        except Exception as exc:
            fx_errors[pair] = str(exc)

    if page == "Inicio":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Criptoactivos", str(len(crypto_data)), "Datos de mercado externos" if crypto_data else "API no disponible")
        c2.metric("Pares FX de referencia", str(len(fx_data)), "Tipos de cambio diarios")
        c3.metric("Ejecución de órdenes", "Desactivada", "Este panel es de solo lectura")
        c4.metric("Actualizado (UTC)", datetime.now(timezone.utc).strftime("%H:%M:%S"), "Hora de carga del panel")

        st.markdown("")
        chart_col, table_col = st.columns([1.35, 1], gap="medium")
        with chart_col:
            st.markdown('<div class="section-title">Histórico de criptomonedas</div>', unsafe_allow_html=True)
            selected_crypto = st.selectbox("Activo", list(CRYPTO.keys()), label_visibility="collapsed")
            days_label = st.select_slider("Periodo histórico", options=["1 día", "7 días", "30 días"], value="7 días")
            days = {"1 día": 1, "7 días": 7, "30 días": 30}[days_label]
            coin_id = CRYPTO[selected_crypto]["id"]
            try:
                hist = fetch_crypto_history(coin_id, days)
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist["Hora"], y=hist["Precio"], name=selected_crypto,
                    line=dict(color=BLUE, width=2), mode="lines",
                ))
                fig.update_layout(
                    height=380, margin=dict(l=8, r=8, t=18, b=8),
                    paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT, size=11),
                    xaxis=dict(gridcolor="#1b2b41", showgrid=True),
                    yaxis=dict(gridcolor="#1b2b41", side="right", title="Precio (USD)"),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Histórico de precios suministrado por CoinGecko; no son velas OHLC.")
            except Exception as exc:
                st.error(f"No se pudo cargar el histórico de {selected_crypto}: {exc}")

        with table_col:
            st.markdown('<div class="section-title">Criptomonedas</div>', unsafe_allow_html=True)
            if crypto_error:
                st.warning(f"No se pudo consultar CoinGecko: {crypto_error}")
            elif crypto_data:
                rows = []
                for pair, info in CRYPTO.items():
                    item = crypto_data.get(info["id"])
                    if item:
                        change = item.get("price_change_percentage_24h")
                        rows.append({
                            "Activo": pair,
                            "Precio USD": fmt_price(item.get("current_price") or 0, 4 if pair == "XRP/USDT" else 2),
                            "Cambio 24 h": f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/D",
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("La API no devolvió datos de criptomonedas.")

        st.markdown("")
        st.markdown('<div class="section-title">Forex · tipos de cambio de referencia</div>', unsafe_allow_html=True)
        if fx_data:
            rows = []
            for pair, data in fx_data.items():
                rows.append({"Par": pair, "Tipo de cambio": data.get("rate"), "Fecha publicada": data.get("date")})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if fx_errors:
            st.warning("No se pudieron consultar algunos pares FX: " + "; ".join(fx_errors.keys()))
        st.caption("Forex usa tipos de cambio de referencia diarios de Frankfurter; no son cotizaciones en tiempo real de un bróker.")

    else:  # Mercados
        market_type = st.radio("Tipo de mercado", ["Todos", "Criptomonedas", "Forex"], horizontal=True)
        if market_type in ("Todos", "Criptomonedas"):
            st.markdown("#### Criptomonedas · CoinGecko")
            if crypto_error:
                st.error(f"Error de consulta: {crypto_error}")
            elif crypto_data:
                rows = []
                for pair, info in CRYPTO.items():
                    item = crypto_data.get(info["id"])
                    if item:
                        change = item.get("price_change_percentage_24h")
                        rows.append({
                            "Activo": pair,
                            "Precio USD": item.get("current_price"),
                            "Cambio 24 h (%)": change,
                            "Capitalización USD": item.get("market_cap"),
                            "Volumen 24 h USD": item.get("total_volume"),
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos disponibles.")
        if market_type in ("Todos", "Forex"):
            st.markdown("#### Forex · tipos de cambio diarios")
            if fx_data:
                rows = [{"Par": pair, "Tipo de cambio": data.get("rate"), "Fecha": data.get("date")} for pair, data in fx_data.items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if fx_errors:
                st.warning("Fallaron estas consultas: " + ", ".join(fx_errors.keys()))
            st.caption("Estos tipos de cambio no son intradía ni necesariamente coinciden con los precios de tu bróker.")

elif page == "Gráficos":
    market = st.radio("Mercado", ["Criptomonedas", "Forex"], horizontal=True)
    if market == "Criptomonedas":
        selected = st.selectbox("Activo", list(CRYPTO.keys()))
        days_label = st.select_slider("Periodo", options=["1 día", "7 días", "30 días"], value="7 días")
        days = {"1 día": 1, "7 días": 7, "30 días": 30}[days_label]
        try:
            hist = fetch_crypto_history(CRYPTO[selected]["id"], days)
            fig = go.Figure(go.Scatter(x=hist["Hora"], y=hist["Precio"], mode="lines", name=selected))
            fig.update_layout(
                height=480, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT),
                margin=dict(l=8, r=8, t=18, b=8),
                xaxis=dict(gridcolor="#1b2b41"), yaxis=dict(gridcolor="#1b2b41", side="right", title="USD"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Datos históricos de precios de CoinGecko.")
        except Exception as exc:
            st.error(f"No se pudo cargar el gráfico: {exc}")
    else:
        selected = st.selectbox("Par", list(FX_PAIRS.keys()))
        base, quote = FX_PAIRS[selected]
        end = pd.Timestamp.utcnow().date()
        start = end - pd.Timedelta(days=90)
        try:
            hist = fetch_fx_history(base, quote, start.isoformat(), end.isoformat())
            fig = go.Figure(go.Scatter(x=hist["Fecha"], y=hist["Precio"], mode="lines+markers", name=selected))
            fig.update_layout(
                height=480, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT),
                margin=dict(l=8, r=8, t=18, b=8),
                xaxis=dict(gridcolor="#1b2b41"), yaxis=dict(gridcolor="#1b2b41", side="right"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Histórico diario de tipos de cambio de referencia, no cotizaciones intradía de bróker.")
        except Exception as exc:
            st.error(f"No se pudo cargar el histórico: {exc}")

elif page == "Configuración":
    st.markdown("### Estado de las fuentes")
    st.write("**Criptomonedas:** CoinGecko API pública; la disponibilidad y los límites de consulta pueden variar.")
    st.write("**Forex:** Frankfurter; tipos de cambio de referencia diarios, no cotizaciones en vivo de MT5.")
    st.write("**MT5:** no conectado a Streamlit Cloud.")
    st.write("**Señales:** no se muestran señales de compra/venta ni resultados ficticios en esta versión.")
    st.write("**Órdenes:** ejecución desactivada.")
    if st.button("Limpiar caché y actualizar datos"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")
st.markdown(
    '<div class="small-muted">MarketBot v0.2 · Datos externos sujetos a disponibilidad y retrasos. '
    'Forex muestra tipos de cambio de referencia diarios. Panel informativo de solo lectura; no ejecuta operaciones.</div>',
    unsafe_allow_html=True,
)
