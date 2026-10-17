import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

# ------------------------------------------------------------
# MarketBot — dashboard inicial (datos completamente simulados)
# No conecta a exchanges, brokers ni ejecuta operaciones reales.
# ------------------------------------------------------------

st.set_page_config(
    page_title="MarketBot | Crypto & Forex",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta visual
BG = "#08111f"
PANEL = "#0d1a2b"
BORDER = "#20334d"
TEXT = "#e5eefc"
MUTED = "#8da6c6"
GREEN = "#00d3a7"
RED = "#ff4d6d"
BLUE = "#3285ff"
PURPLE = "#8b6cff"
ORANGE = "#ffad42"

st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{ background: #091525; border-right: 1px solid {BORDER}; }}
    [data-testid="stHeader"] {{ background: rgba(8,17,31,0.9); }}
    h1, h2, h3 {{ color: {TEXT}; }}
    p, label, span {{ }}
    .brand {{ font-size: 1.65rem; font-weight: 800; letter-spacing: -0.5px; }}
    .subbrand {{ color: {MUTED}; font-size: .88rem; margin-top: -8px; }}
    .demo-pill {{ display:inline-block; border:1px solid #6451c8; color:#b9aaff;
                  background:#201b43; padding:5px 11px; border-radius:18px;
                  font-size:.78rem; font-weight:600; }}
    .metric-card {{ background:linear-gradient(135deg,#101f33,#0b1728);
                    border:1px solid {BORDER}; border-radius:13px;
                    padding:16px 18px; min-height:112px; }}
    .metric-label {{ color:{MUTED}; font-size:.82rem; }}
    .metric-value {{ color:{TEXT}; font-size:1.8rem; font-weight:750; margin-top:5px; }}
    .metric-note {{ color:{GREEN}; font-size:.78rem; margin-top:3px; }}
    .section-title {{ font-size:1.02rem; font-weight:700; color:{TEXT}; margin-bottom:10px; }}
    .small-muted {{ color:{MUTED}; font-size:.78rem; }}
    div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:10px; overflow:hidden; }}
    div.stButton > button {{ border-radius:9px; }}
    hr {{ border-color:{BORDER}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Datos ficticios reproducibles para que la web funcione sin claves ni conexiones.
rng = np.random.default_rng(21)

CRYPTO = {
    "BTC/USDT": {"price": 67125.40, "change": 1.24, "digits": 2},
    "ETH/USDT": {"price": 3482.70, "change": 0.68, "digits": 2},
    "SOL/USDT": {"price": 162.85, "change": 3.24, "digits": 2},
    "BNB/USDT": {"price": 592.30, "change": -0.42, "digits": 2},
    "XRP/USDT": {"price": 0.5421, "change": -1.08, "digits": 4},
}
FOREX = {
    "EUR/USD": {"price": 1.08452, "change": 0.12, "digits": 5},
    "GBP/USD": {"price": 1.30124, "change": -0.21, "digits": 5},
    "USD/JPY": {"price": 149.385, "change": 0.31, "digits": 3},
    "AUD/USD": {"price": 0.66125, "change": 0.08, "digits": 5},
}
ALL_MARKETS = {**CRYPTO, **FOREX}

def make_candles(start_price: float, n: int = 100) -> pd.DataFrame:
    """Genera velas OHLC ficticias; no son cotizaciones actuales."""
    changes = rng.normal(0.00025, 0.0045, n)
    closes = start_price * np.cumprod(1 + changes)
    opens = np.r_[start_price, closes[:-1]]
    spread = np.abs(rng.normal(0.0022, 0.0012, n)) * closes
    highs = np.maximum(opens, closes) + spread
    lows = np.minimum(opens, closes) - spread
    times = pd.date_range(end=pd.Timestamp.now().floor("min"), periods=n, freq="15min")
    volume = rng.integers(80, 800, n)
    df = pd.DataFrame({
        "Hora": times, "Open": opens, "High": highs, "Low": lows,
        "Close": closes, "Volume": volume
    })
    df["MA 9"] = df["Close"].rolling(9).mean()
    df["MA 21"] = df["Close"].rolling(21).mean()
    return df

def build_signals() -> pd.DataFrame:
    now = datetime.now()
    rows = [
        (now - timedelta(minutes=4), "BTC/USDT", "Compra (Long)", 67125.40, "Activa", "—"),
        (now - timedelta(minutes=32), "ETH/USDT", "Venta (Short)", 3482.70, "Cerrada", "+1.31%"),
        (now - timedelta(hours=1, minutes=12), "EUR/USD", "Compra (Long)", 1.08452, "Cerrada", "+0.42%"),
        (now - timedelta(hours=2, minutes=5), "GBP/USD", "Venta (Short)", 1.30124, "Cerrada", "-0.35%"),
        (now - timedelta(hours=3), "SOL/USDT", "Compra (Long)", 162.85, "Cerrada", "+2.14%"),
        (now - timedelta(hours=5), "XRP/USDT", "Venta (Short)", 0.5421, "Cerrada", "+0.66%"),
        (now - timedelta(hours=7), "BTC/USDT", "Compra (Long)", 66840.20, "Cerrada", "-0.28%"),
        (now - timedelta(hours=9), "USD/JPY", "Compra (Long)", 149.385, "Cerrada", "+0.19%"),
    ]
    return pd.DataFrame(rows, columns=["Fecha/Hora", "Activo", "Dirección", "Precio entrada", "Estado", "Resultado"])

# Sidebar navigation
with st.sidebar:
    st.markdown('<div class="brand">📊 Market<span style="color:#3285ff">Bot</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">Crypto & Forex · Señales automáticas</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "NAVEGACIÓN",
        ["Inicio", "Mercados", "Señales", "Historial", "Configuración"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown('<span class="demo-pill">● MODO SIMULACIÓN</span>', unsafe_allow_html=True)
    st.markdown("")
    st.caption("Estado del sistema")
    st.markdown("🟢 Interfaz en línea")
    st.caption("Los datos de mercado y resultados son ficticios.")
    st.markdown("---")
    st.caption("MarketBot v0.1 · Prototipo")

st.markdown(
    '<div class="brand">Market<span style="color:#3285ff">Bot</span></div>'
    '<div class="subbrand">Crypto & Forex · Centro de análisis de señales</div>',
    unsafe_allow_html=True,
)
st.markdown("")

# Header controls
left, right = st.columns([4, 1])
with left:
    st.markdown("### " + page)
with right:
    st.markdown('<div style="text-align:right"><span class="demo-pill">MODO SIMULACIÓN</span></div>', unsafe_allow_html=True)

signals = build_signals()

if page == "Inicio":
    # Summary metrics are intentionally labelled as demo metrics.
    metric_cols = st.columns(4)
    metrics = [
        ("Señales generadas", "24", "+20% vs. periodo anterior", GREEN),
        ("Operaciones simuladas", "18", "Solo datos de ejemplo", BLUE),
        ("Tasa de acierto simulada", "66,7%", "Muestra ilustrativa", GREEN),
        ("Resultado simulado", "+4,82%", "No representa rentabilidad real", PURPLE),
    ]
    for col, (label, value, note, accent) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f'<div class="metric-note" style="color:{accent}">● {note}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    chart_col, signal_col = st.columns([1.72, 1], gap="medium")
    with chart_col:
        st.markdown('<div class="section-title">Gráfico de mercado</div>', unsafe_allow_html=True)
        market = st.selectbox("Activo", list(ALL_MARKETS.keys()), index=0, label_visibility="collapsed")
        timeframe = st.select_slider("Temporalidad", options=["5m", "15m", "1h", "4h", "1D"], value="15m")
        candles = make_candles(ALL_MARKETS[market]["price"])
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=candles["Hora"], open=candles["Open"], high=candles["High"],
            low=candles["Low"], close=candles["Close"], name=market,
            increasing_line_color=GREEN, decreasing_line_color=RED,
        ))
        fig.add_trace(go.Scatter(x=candles["Hora"], y=candles["MA 9"], name="MA 9",
                                 line=dict(color=BLUE, width=1.5)))
        fig.add_trace(go.Scatter(x=candles["Hora"], y=candles["MA 21"], name="MA 21",
                                 line=dict(color=ORANGE, width=1.5)))
        fig.update_layout(
            height=390, margin=dict(l=8, r=8, t=18, b=8),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TEXT, size=11),
            xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.08, x=0),
            xaxis=dict(gridcolor="#1b2b41", showgrid=True),
            yaxis=dict(gridcolor="#1b2b41", side="right"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Gráfico de demostración · {market} · Temporalidad seleccionada: {timeframe}")

    with signal_col:
        st.markdown('<div class="section-title">Últimas señales</div>', unsafe_allow_html=True)
        for _, row in signals.head(5).iterrows():
            is_buy = "Compra" in row["Dirección"]
            color = GREEN if is_buy else RED
            icon = "↑" if is_buy else "↓"
            status_color = GREEN if row["Estado"] == "Activa" else MUTED
            price = f'{row["Precio entrada"]:,.5f}' if row["Activo"] in FOREX else f'{row["Precio entrada"]:,.2f}'
            st.markdown(
                f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:10px;'
                f'padding:12px;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;gap:8px;">'
                f'<b>{icon} {row["Activo"]}</b><span style="color:{color};font-size:.83rem">{row["Dirección"]}</span></div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:7px;color:{MUTED};font-size:.78rem;">'
                f'<span>Entrada: {price}</span><span style="color:{status_color}">{row["Estado"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.info("Las señales de esta pantalla son ejemplos inventados; no las uses para operar.")

    st.markdown("")
    table_col, market_col = st.columns([1.65, 1], gap="medium")
    with table_col:
        st.markdown('<div class="section-title">Historial reciente</div>', unsafe_allow_html=True)
        display = signals.copy()
        display["Fecha/Hora"] = pd.to_datetime(display["Fecha/Hora"]).dt.strftime("%d %b · %H:%M")
        st.dataframe(display, use_container_width=True, hide_index=True, height=300)
    with market_col:
        st.markdown('<div class="section-title">Mercados vigilados</div>', unsafe_allow_html=True)
        rows = []
        for name, item in ALL_MARKETS.items():
            rows.append({
                "Activo": name,
                "Precio de ejemplo": f'{item["price"]:,.{item["digits"]}f}',
                "Variación ficticia": f'{item["change"]:+.2f}%',
                "Tendencia": "Alza" if item["change"] >= 0 else "Baja",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)

elif page == "Mercados":
    st.markdown("Consulta la lista de activos de demostración. Aún no hay conexión a cotizaciones en vivo.")
    market_type = st.radio("Tipo de mercado", ["Todos", "Criptomonedas", "Forex"], horizontal=True)
    names = list(ALL_MARKETS.keys()) if market_type == "Todos" else (list(CRYPTO.keys()) if market_type == "Criptomonedas" else list(FOREX.keys()))
    rows = []
    for name in names:
        item = ALL_MARKETS[name]
        rows.append({"Activo": name, "Precio ficticio": f'{item["price"]:,.{item["digits"]}f}',
                     "Variación ficticia": f'{item["change"]:+.2f}%', "Estado": "Solo demostración"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning("Los precios y las variaciones no son cotizaciones reales.")

elif page == "Señales":
    st.markdown("### Señales generadas")
    direction = st.multiselect("Filtrar dirección", ["Compra (Long)", "Venta (Short)"], default=["Compra (Long)", "Venta (Short)"])
    status = st.multiselect("Filtrar estado", ["Activa", "Cerrada"], default=["Activa", "Cerrada"])
    filtered = signals[signals["Dirección"].isin(direction) & signals["Estado"].isin(status)].copy()
    filtered["Fecha/Hora"] = pd.to_datetime(filtered["Fecha/Hora"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption("Las reglas de estrategia todavía no están conectadas; esta tabla contiene datos de ejemplo.")

elif page == "Historial":
    st.markdown("### Historial de operaciones simuladas")
    st.dataframe(signals, use_container_width=True, hide_index=True)
    st.markdown("**Estadísticas de ejemplo**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Operaciones cerradas", "7")
    c2.metric("Operaciones positivas", "5")
    c3.metric("Resultado ilustrativo", "+4,09%")
    st.caption("No se ha realizado ninguna operación real. Las estadísticas son ficticias.")

elif page == "Configuración":
    st.markdown("### Preferencias del dashboard")
    st.selectbox("Mercado predeterminado", ["BTC/USDT", "ETH/USDT", "EUR/USD", "GBP/USD"])
    st.selectbox("Temporalidad predeterminada", ["5m", "15m", "1h", "4h", "1D"], index=1)
    st.multiselect("Indicadores visibles", ["MA 9", "MA 21", "RSI", "MACD"], default=["MA 9", "MA 21"])
    st.toggle("Mostrar alertas visuales", value=True)
    st.toggle("Permitir ejecución de órdenes reales", value=False, disabled=True)
    st.warning("La ejecución real está deshabilitada. Antes de habilitarla se necesitarán integración segura con un broker/exchange, pruebas, límites de riesgo y controles de seguridad.")

st.markdown("---")
st.markdown(
    '<div class="small-muted">MarketBot v0.1 · Prototipo visual · Datos ficticios · '
    'No es asesoramiento financiero y no ejecuta operaciones reales.</div>',
    unsafe_allow_html=True,
)
