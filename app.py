import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone
import time

# ------------------------------------------------------------
# MarketBot v0.5
# Crypto: CoinGecko public API (market data)
# FX: Frankfurter reference exchange rates (daily, not live broker quotes)
# Metals: Alpha Vantage GOLD_SILVER_SPOT (API key required; latest provider quote)
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
METALS = {"Oro (XAU/USD)": "XAU", "Plata (XAG/USD)": "XAG"}

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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_metal_spot(symbol: str, api_key: str):
    """Latest gold/silver spot quote from Alpha Vantage; cache for 5 minutes."""
    url = "https://www.alphavantage.co/query"
    response = requests.get(
        url,
        params={"function": "GOLD_SILVER_SPOT", "symbol": symbol, "apikey": api_key},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if "Note" in payload or "Information" in payload or "Error Message" in payload:
        message = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
        raise RuntimeError(str(message))
    if not isinstance(payload, dict) or not payload.get("price"):
        raise ValueError("La API no devolvió un precio spot válido. Comprueba la clave y el límite de consultas.")
    return payload

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


def trend_label(change):
    """Etiqueta descriptiva basada únicamente en el cambio porcentual de 24 h."""
    if not isinstance(change, (int, float)):
        return "Sin datos"
    if change > 0.1:
        return "Alcista"
    if change < -0.1:
        return "Bajista"
    return "Lateral"


def add_technical_indicators(history):
    """Calcula SMA 20/50 y RSI 14 sobre la serie de precios disponible."""
    df = history.copy().sort_values("Hora").reset_index(drop=True)
    df["SMA 20"] = df["Precio"].rolling(window=20, min_periods=20).mean()
    df["SMA 50"] = df["Precio"].rolling(window=50, min_periods=50).mean()

    delta = df["Precio"].diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=14, min_periods=14).mean()
    avg_loss = losses.rolling(window=14, min_periods=14).mean()
    relative_strength = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI 14"] = 100 - (100 / (1 + relative_strength))
    # Handle a flat price series and a series with gains but no losses.
    df.loc[(avg_loss == 0) & (avg_gain > 0), "RSI 14"] = 100
    df.loc[(avg_loss == 0) & (avg_gain == 0), "RSI 14"] = 50
    return df


def rsi_description(value):
    if pd.isna(value):
        return "Datos insuficientes"
    if value >= 70:
        return "RSI elevado (≥ 70)"
    if value <= 30:
        return "RSI bajo (≤ 30)"
    return "RSI en zona intermedia"

with st.sidebar:
    st.markdown('<div class="brand">📊 Market<span style="color:#3285ff">Bot</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">Crypto & Forex · Panel de análisis</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "NAVEGACIÓN",
        ["Inicio", "Mercados", "Gráficos", "Análisis técnico", "Configuración"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown('<span class="demo-pill">● SOLO LECTURA</span>', unsafe_allow_html=True)
    st.caption("Datos externos; disponibilidad según cada proveedor.")
    st.caption("Sin conexión a cuentas de trading ni ejecución de órdenes.")
    st.markdown("---")
    st.caption("MarketBot v0.5")

st.markdown(
    '<div class="brand">Market<span style="color:#3285ff">Bot</span></div>'
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

    try:
        av_key = st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
    except Exception:
        av_key = ""
    metal_data = {}
    metal_errors = {}
    if av_key:
        for index, (label, symbol) in enumerate(METALS.items()):
            # Alpha Vantage free tier asks clients to keep requests at least
            # one second apart. Space out sequential metal lookups.
            if index > 0:
                time.sleep(1.2)
            try:
                metal_data[label] = fetch_metal_spot(symbol, av_key)
            except Exception as exc:
                metal_errors[label] = str(exc)

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
                            "Tendencia 24 h": trend_label(change),
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption("Tendencia descriptiva calculada solo con el cambio de las últimas 24 h: > +0,1 % alcista; < -0,1 % bajista; entre ambos, lateral. No es una predicción.")
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

        st.markdown("#### Metales preciosos · precio spot")
        if not av_key:
            st.info("Para activar cotizaciones recientes de oro y plata, añade ALPHA_VANTAGE_API_KEY en Settings → Secrets de Streamlit Cloud.")
        else:
            if metal_data:
                rows = []
                for label, data in metal_data.items():
                    rows.append({"Metal": label, "Precio USD/onza troy": round(float(data.get("price")), 2) if data.get("price") is not None else None, "Unidad": data.get("unit", "USD por onza troy"), "Última actualización fuente": data.get("last_refreshed") or data.get("timestamp") or data.get("更新时间") or "Ver fuente"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption("Fuente: Alpha Vantage GOLD_SILVER_SPOT. La caché local dura 5 minutos; la frecuencia real depende del proveedor.")
            if metal_errors:
                st.warning("No se pudieron cargar todos los metales: " + " | ".join(f"{label}: {error}" for label, error in metal_errors.items()))
            if not metal_data and not metal_errors:
                st.info("No hay cotizaciones de metales disponibles en este momento.")

    else:  # Mercados
        market_type = st.radio("Tipo de mercado", ["Todos", "Criptomonedas", "Forex", "Metales"], horizontal=True)
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
                            "Tendencia 24 h": trend_label(change),
                            "Capitalización USD": item.get("market_cap"),
                            "Volumen 24 h USD": item.get("total_volume"),
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption("Tendencia descriptiva calculada solo con el cambio de las últimas 24 h; no es una predicción ni una señal garantizada.")
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
        if market_type in ("Todos", "Metales"):
            st.markdown("#### Metales preciosos · Alpha Vantage")
            if not av_key:
                st.info("Configura ALPHA_VANTAGE_API_KEY en los Secrets de Streamlit Cloud para mostrar cotizaciones spot.")
            elif metal_data:
                rows = [{"Metal": label, "Precio USD/onza troy": round(float(data.get("price")), 2) if data.get("price") is not None else None, "Unidad": data.get("unit", "USD por onza troy"), "Última actualización fuente": data.get("更新时间") or data.get("last_refreshed") or data.get("timestamp") or "No indicada"} for label, data in metal_data.items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if metal_errors:
                st.warning("Errores de metales: " + "; ".join(metal_errors.values()))
            st.caption("Son precios spot informativos; pueden diferir de los precios de un bróker y no garantizan ejecución a ese precio.")

elif page == "Gráficos":
    market = st.radio("Mercado", ["Criptomonedas", "Forex", "Metales"], horizontal=True)
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
    elif market == "Forex":
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
    else:
        st.markdown("Los precios spot actuales se muestran en Inicio y Mercados. El gráfico histórico de metales requiere una consulta de historial de Alpha Vantage y no se mezclará con datos diarios de otra fuente.")
        if not av_key:
            st.info("Configura ALPHA_VANTAGE_API_KEY en los Secrets de Streamlit Cloud para activar los precios actuales.")
        elif metal_data:
            rows = [{"Metal": label, "Precio USD/onza troy": round(float(data.get("price")), 2) if data.get("price") is not None else None, "Unidad": data.get("unit", "USD por onza troy")} for label, data in metal_data.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if metal_errors:
            st.warning("No se pudieron cargar cotizaciones: " + "; ".join(metal_errors.values()))

elif page == "Análisis técnico":
    st.markdown("### Indicadores técnicos de criptomonedas")
    st.caption(
        "Análisis descriptivo con el histórico de CoinGecko. Los indicadores no predicen "
        "el futuro ni constituyen una recomendación de inversión."
    )
    selected = st.selectbox("Criptomoneda", list(CRYPTO.keys()), key="technical_crypto")
    coin_id = CRYPTO[selected]["id"]

    try:
        with st.spinner("Cargando histórico y calculando indicadores..."):
            hist = fetch_crypto_history(coin_id, 90)
            technical = add_technical_indicators(hist)

        latest = technical.iloc[-1]
        price = latest["Precio"]
        rsi_value = latest["RSI 14"]
        sma20 = latest["SMA 20"]
        sma50 = latest["SMA 50"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio más reciente", f"${price:,.4f}" if price < 1 else f"${price:,.2f}")
        m2.metric("RSI (14)", f"{rsi_value:.2f}" if pd.notna(rsi_value) else "N/D")
        m3.metric("SMA 20", f"${sma20:,.4f}" if pd.notna(sma20) and sma20 < 1 else (f"${sma20:,.2f}" if pd.notna(sma20) else "N/D"))
        m4.metric("SMA 50", f"${sma50:,.4f}" if pd.notna(sma50) and sma50 < 1 else (f"${sma50:,.2f}" if pd.notna(sma50) else "N/D"))

        st.write(f"**Lectura del RSI:** {rsi_description(rsi_value)}.")
        if pd.notna(sma20) and pd.notna(sma50):
            if sma20 > sma50:
                st.write("**Medias móviles:** SMA 20 está por encima de SMA 50 en el último dato disponible.")
            elif sma20 < sma50:
                st.write("**Medias móviles:** SMA 20 está por debajo de SMA 50 en el último dato disponible.")
            else:
                st.write("**Medias móviles:** SMA 20 y SMA 50 tienen el mismo valor en el último dato disponible.")
        else:
            st.info("Aún no hay suficientes puntos históricos para calcular ambas medias móviles.")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=technical["Hora"], y=technical["Precio"], name="Precio", line=dict(color=BLUE, width=2)))
        fig.add_trace(go.Scatter(x=technical["Hora"], y=technical["SMA 20"], name="SMA 20", line=dict(width=1.5)))
        fig.add_trace(go.Scatter(x=technical["Hora"], y=technical["SMA 50"], name="SMA 50", line=dict(width=1.5)))
        fig.update_layout(
            height=470, margin=dict(l=8, r=8, t=18, b=8),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT, size=11),
            xaxis=dict(gridcolor="#1b2b41", showgrid=True),
            yaxis=dict(gridcolor="#1b2b41", side="right", title="Precio (USD)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        rsi_chart = go.Figure()
        rsi_chart.add_trace(go.Scatter(x=technical["Hora"], y=technical["RSI 14"], name="RSI 14", line=dict(color=ORANGE, width=2)))
        rsi_chart.add_hline(y=70, line_dash="dash", line_color=RED, annotation_text="70")
        rsi_chart.add_hline(y=30, line_dash="dash", line_color=GREEN, annotation_text="30")
        rsi_chart.update_layout(
            height=260, margin=dict(l=8, r=8, t=18, b=8),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT, size=11),
            xaxis=dict(gridcolor="#1b2b41"), yaxis=dict(gridcolor="#1b2b41", side="right", title="RSI"),
            yaxis_range=[0, 100],
        )
        st.plotly_chart(rsi_chart, use_container_width=True)
        st.caption(
            "SMA 20/50 son medias móviles simples de los últimos 20/50 puntos del histórico devuelto. "
            "RSI 14 se calcula con 14 cambios de precio. La frecuencia de los puntos depende de CoinGecko."
        )
    except Exception as exc:
        st.error(f"No se pudo calcular el análisis técnico de {selected}: {exc}")

elif page == "Configuración":
    st.markdown("### Estado de las fuentes")
    st.write("**Criptomonedas:** CoinGecko API pública; la disponibilidad y los límites de consulta pueden variar.")
    st.write("**Forex:** Frankfurter; tipos de cambio de referencia diarios, no cotizaciones en vivo de MT5.")
    st.write("**Oro y plata:** Alpha Vantage GOLD_SILVER_SPOT; necesita ALPHA_VANTAGE_API_KEY en Streamlit Secrets. Caché de 5 minutos.")
    st.write("**MT5:** no conectado a Streamlit Cloud.")
    st.write("**Señales:** no se muestran señales de compra/venta ni resultados ficticios en esta versión.")
    st.write("**Órdenes:** ejecución desactivada.")
    if st.button("Limpiar caché y actualizar datos"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")
st.markdown(
    '<div class="small-muted">MarketBot v0.5 · Datos externos sujetos a disponibilidad y retrasos. '
    'Forex muestra tipos de cambio de referencia diarios. Panel informativo de solo lectura; no ejecuta operaciones.</div>',
    unsafe_allow_html=True,
)