"""
QUOTEX SIGNAL PRO - Générateur de signaux manuels 24/7
⚠️ AUCUN AUTO-TRADE : l'utilisateur place manuellement les trades sur Quotex.
Usage :  streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
import math

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Quotex Signal Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# PWA : permet d'installer l'app sur l'écran d'accueil du téléphone
# ============================================================
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="Quotex Pro" />
    <meta name="theme-color" content="#0a0e17" />
    <link rel="manifest" href="https://cdn.jsdelivr.net/gh/streamlit/streamlit@1.30.0/frontend/public/manifest.json" />
    """,
    unsafe_allow_html=True,
)

# ============================================================
# INDICATEURS TECHNIQUES (sans pandas_ta, pur pandas/numpy)
# ============================================================
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def bollinger(series: pd.Series, period: int = 20, std: float = 2.0):
    sma = series.rolling(window=period, min_periods=period).mean()
    rstd = series.rolling(window=period, min_periods=period).std()
    upper = sma + std * rstd
    lower = sma - std * rstd
    return upper, sma, lower


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k: int = 14, d: int = 3):
    lowest_low = low.rolling(window=k, min_periods=k).min()
    highest_high = high.rolling(window=k, min_periods=k).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    k_pct = 100 * ((close - lowest_low) / denom)
    d_pct = k_pct.rolling(window=d, min_periods=d).mean()
    return k_pct, d_pct


# ============================================================
# CSS DARK MODERNE
# ============================================================
st.markdown("""
<style>
    :root {
        --bg: #0a0e17;
        --bg-2: #121826;
        --card: #161d2f;
        --border: #1f2937;
        --txt: #e5e7eb;
        --muted: #9ca3af;
        --green: #00e676;
        --green-dark: #0a2a18;
        --red: #ff3b3b;
        --red-dark: #2a0a0f;
        --accent: #00d4ff;
    }
    html, body, .stApp {
        background: radial-gradient(1200px 600px at 10% -10%, #0f1b34 0%, transparent 60%),
                    radial-gradient(1000px 500px at 100% 0%, #1a0f2e 0%, transparent 60%),
                    #0a0e17;
        color: var(--txt);
    }
    .stApp > header { background: transparent; }
    section[data-testid="stSidebar"] {
        background: rgba(10,14,23,0.85);
        backdrop-filter: blur(12px);
        border-right: 1px solid var(--border);
    }
    h1, h2, h3 { color: #fff; letter-spacing: -0.02em; }
    .hero {
        background: linear-gradient(135deg, rgba(0,212,255,0.08), rgba(0,230,118,0.06));
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 28px 28px;
        margin-bottom: 18px;
    }
    .hero h1 {
        font-size: 40px;
        font-weight: 900;
        background: linear-gradient(90deg, #00d4ff, #00e676);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero .sub { color: var(--muted); margin-top: 6px; font-size: 15px; }
    .status-pill {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .04em;
        text-transform: uppercase;
        border: 1px solid var(--border);
    }
    .pill-otc { background: rgba(0,230,118,0.1); color: #00e676; border-color: rgba(0,230,118,0.4); }
    .pill-demo { background: rgba(255,196,0,0.1); color: #ffc400; border-color: rgba(255,196,0,0.4); }

    .big-btn > div > button {
        background: linear-gradient(135deg, #00e676, #00b359) !important;
        color: #06140a !important;
        font-size: 24px !important;
        font-weight: 900 !important;
        height: 80px !important;
        border-radius: 14px !important;
        border: none !important;
        letter-spacing: 0.02em;
        box-shadow: 0 12px 40px rgba(0,230,118,0.25);
        transition: transform .15s ease;
    }
    .big-btn > div > button:hover { transform: translateY(-2px); }

    .signal-card {
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 14px;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
    }
    .signal-card::before {
        content: "";
        position: absolute; inset: 0;
        background: radial-gradient(400px 120px at 0% 0%, currentColor, transparent 70%);
        opacity: 0.08;
    }
    .signal-call { background: linear-gradient(135deg, #0a2a18, #0c1a14); color: #00e676; border-left: 5px solid #00e676; }
    .signal-put  { background: linear-gradient(135deg, #2a0a0f, #1a0c10); color: #ff3b3b; border-left: 5px solid #ff3b3b; }
    .signal-card .inner { color: var(--txt); }
    .signal-card h2 { margin: 0 0 10px 0; font-size: 22px; }
    .signal-card .meta { display:flex; flex-wrap:wrap; gap: 10px; font-size: 13px; color: var(--muted); }
    .signal-card .chip {
        background: rgba(255,255,255,0.06);
        padding: 4px 10px; border-radius: 8px;
        color: #fff; font-weight: 600;
    }
    .conf-bar { background: #0a0e17; border-radius: 999px; height: 10px; overflow: hidden; margin-top: 10px; }
    .conf-bar > div { height: 100%; border-radius: 999px; }

    .stat-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
    }
    .stat-card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .stat-card .value { color: #fff; font-size: 26px; font-weight: 800; margin-top: 4px; }

    .warning-banner {
        background: rgba(255,59,59,0.08);
        border: 1px solid rgba(255,59,59,0.3);
        color: #ffb4b4;
        padding: 12px 16px; border-radius: 12px;
        font-size: 13px;
    }

    .stDataFrame { border-radius: 12px; }

    /* ===== RESPONSIVE MOBILE ===== */
    @media (max-width: 768px) {
        .hero { padding: 20px 18px; }
        .hero h1 { font-size: 28px; }
        .hero .sub { font-size: 13px; }
        .big-btn > div > button {
            font-size: 18px !important;
            height: 64px !important;
        }
        .signal-card { padding: 16px; }
        .signal-card h2 { font-size: 18px; }
        .signal-card .meta { font-size: 12px; }
        .stat-card .value { font-size: 20px; }
        section[data-testid="stSidebar"] { width: 85% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HERO
# ============================================================
st.markdown("""
<div class="hero">
  <h1>📈 QUOTEX SIGNAL PRO</h1>
  <div class="sub">Générateur de signaux manuels OTC 24/7 — Aucun auto-trade. <b>C'est toi qui cliques sur Quotex.</b></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# BANNIÈRE "INSTALLER SUR TÉLÉPHONE"
# ============================================================
with st.expander("📱 **Installer l'app sur mon téléphone**", expanded=False):
    st.markdown("""
    ### 🍏 iPhone (Safari)
    1. Ouvre cette page dans **Safari**
    2. Appuie sur le bouton **Partager** ⬆️ (en bas)
    3. Choisis **« Sur l'écran d'accueil »**
    4. Valide → l'icône **Quotex Pro** apparaît comme une vraie app ✅

    ### 🤖 Android (Chrome)
    1. Ouvre cette page dans **Chrome**
    2. Appuie sur les **3 points** en haut à droite ⋮
    3. Choisis **« Ajouter à l'écran d'accueil »** ou **« Installer l'application »**
    4. L'icône apparaît → lance en plein écran comme une vraie app ✅

    > 💡 **Astuce** : pour que l'app soit disponible 24/7, déploie-la gratuitement sur
    > [streamlit.io/cloud](https://streamlit.io/cloud) puis installe-la sur ton téléphone.
    """)

# ============================================================
# SESSION STATE
# ============================================================
if "signals_history" not in st.session_state:
    st.session_state.signals_history = []
if "client" not in st.session_state:
    st.session_state.client = None
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("### 🔐 Mode OTC 24/7 — Quotex")
    email = st.text_input("Email Quotex", placeholder="trader@email.com")
    password = st.text_input("Mot de passe", type="password")

    if st.button("🔌 Se connecter à Quotex", use_container_width=True):
        if not email or not password:
            st.error("Email et mot de passe requis.")
        else:
            try:
                from quotexapi.stable_api import Quotex  # type: ignore
                with st.spinner("Connexion en cours..."):
                    client = Quotex(email=email, password=password)
                    check, msg = client.connect()
                    if check:
                        st.session_state.client = client
                        st.success(f"✅ Connecté : {msg}")
                    else:
                        st.error(f"❌ {msg}")
            except ImportError:
                st.error("Lib `quotexapi` manquante. Lance : `pip install quotexapi`")
            except Exception as e:
                st.error(f"Erreur : {e}")

    if st.session_state.client is not None and st.button("Déconnexion"):
        st.session_state.client = None
        st.experimental_rerun()

    is_connected = st.session_state.client is not None
    if is_connected:
        st.markdown('<span class="status-pill pill-otc">● OTC ACTIF</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill pill-demo">● MODE DÉMO (Yahoo Finance)</span>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📊 Paramètres de scan")
    timeframe = st.selectbox("Timeframe", ["1 min", "5 min"], index=0)
    tf_seconds = 60 if timeframe == "1 min" else 300
    expiry = "2-3 min" if tf_seconds == 60 else "5-7 min"

    assets = st.multiselect(
        "Actifs à scanner",
        ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "GBPJPY_otc",
         "AUDUSD_otc", "BTC_otc", "ETH_otc"],
        default=["EURUSD_otc", "GBPUSD_otc", "BTC_otc"],
    )

    st.divider()
    st.markdown("""
    <div class="warning-banner">
      ⚠️ <b>Trading risqué.</b> Teste toujours en démo avant. Cet outil n'est
      <b>pas un conseil financier</b>. Aucun ordre n'est passé automatiquement.
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# KPI (mini-stats)
# ============================================================
c1, c2, c3, c4 = st.columns(4)
hist = st.session_state.signals_history
with c1:
    st.markdown(f"""<div class="stat-card">
        <div class="label">Statut</div>
        <div class="value">{'🟢 OTC' if is_connected else '🟡 Démo'}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="stat-card">
        <div class="label">Timeframe</div>
        <div class="value">{timeframe}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="stat-card">
        <div class="label">Signaux trouvés</div>
        <div class="value">{len(hist)}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="stat-card">
        <div class="label">Expiration</div>
        <div class="value">{expiry}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ============================================================
# BOUTON ANALYSER
# ============================================================
st.markdown('<div class="big-btn">', unsafe_allow_html=True)
analyser = st.button("🔍 ANALYSER MAINTENANT", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# LOGIQUE DE SCAN
# ============================================================
YF_MAP = {
    "EURUSD_otc": "EURUSD=X",
    "GBPUSD_otc": "GBPUSD=X",
    "USDJPY_otc": "USDJPY=X",
    "GBPJPY_otc": "GBPJPY=X",
    "AUDUSD_otc": "AUDUSD=X",
    "BTC_otc": "BTC-USD",
    "ETH_otc": "ETH-USD",
}


def fetch_data_quotex(asset: str, tf_seconds: int, count: int = 100):
    """Récupère les bougies via la lib Quotex."""
    if st.session_state.client is None:
        return None
    try:
        candles = st.session_state.client.get_candles(asset, tf_seconds, count, time.time())
        if not candles:
            return None
        df = pd.DataFrame(candles)
        df = df.iloc[:, :5].copy()
        df.columns = ["time", "open", "high", "low", "close"]
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna().reset_index(drop=True)
    except Exception as e:
        st.warning(f"Quotex {asset}: {e}")
        return None


def fetch_data_yahoo(asset: str, tf_seconds: int):
    """Fallback Yahoo Finance."""
    if not YF_OK:
        return None
    try:
        ticker = YF_MAP.get(asset, "EURUSD=X")
        interval = "1m" if tf_seconds == 60 else "5m"
        period = "1d" if tf_seconds == 60 else "5d"
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data is None or data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0].lower() for c in data.columns]
        else:
            data.columns = [c.lower() for c in data.columns]
        df = data.reset_index()
        df = df.rename(columns={"datetime": "time", "date": "time"})
        return df[["time", "open", "high", "low", "close"]].dropna().tail(200).reset_index(drop=True)
    except Exception as e:
        st.warning(f"Yahoo {asset}: {e}")
        return None


def compute_signal(df: pd.DataFrame):
    """Calcule indicateurs et retourne (signal, confiance, ligne)."""
    df["rsi"] = rsi(df["close"], 14)
    df["ema21"] = ema(df["close"], 21)
    df["ema50"] = ema(df["close"], 50)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger(df["close"], 20, 2.0)
    df["stoch_k"], df["stoch_d"] = stochastic(df["high"], df["low"], df["close"], 14, 3)

    last = df.iloc[-2]  # bougie clôturée

    close = float(last["close"])
    rsi_v = float(last["rsi"])
    stoch_v = float(last["stoch_k"])
    ema50_v = float(last["ema50"])
    bb_up = float(last["bb_upper"])
    bb_lo = float(last["bb_lower"])

    band_tol = (bb_up - bb_lo) * 0.02 if (bb_up - bb_lo) > 0 else 0

    signal = None
    confidence = 0.0

    # CALL : close <= bande basse + RSI < 32 + stoch < 25 + close > ema50
    if (close <= bb_lo + band_tol) and rsi_v < 32 and stoch_v < 25 and close > ema50_v:
        signal = "CALL"
        confidence = 60 + (32 - rsi_v) * 1.5 + (25 - stoch_v) * 0.6
    # PUT  : close >= bande haute + RSI > 68 + stoch > 75 + close < ema50
    elif (close >= bb_up - band_tol) and rsi_v > 68 and stoch_v > 75 and close < ema50_v:
        signal = "PUT"
        confidence = 60 + (rsi_v - 68) * 1.5 + (stoch_v - 75) * 0.6

    if signal:
        confidence = int(min(95, max(60, confidence)))

    return signal, confidence, last


def render_signal_card(sig_data: dict):
    """Rend une carte HTML pour un signal."""
    cls = "signal-call" if sig_data["dir"] == "CALL" else "signal-put"
    icon = "🟢" if sig_data["dir"] == "CALL" else "🔴"
    bar_color = "#00e676" if sig_data["dir"] == "CALL" else "#ff3b3b"
    st.markdown(f"""
    <div class="signal-card {cls}">
      <div class="inner">
        <h2>{icon} {sig_data['dir']} sur <b>{sig_data['asset']}</b></h2>
        <div class="meta">
          <span class="chip">🎯 Confiance {sig_data['conf']}%</span>
          <span class="chip">RSI {sig_data['rsi']}</span>
          <span class="chip">Stoch {sig_data['stoch']}</span>
          <span class="chip">Prix {sig_data['price']}</span>
          <span class="chip">⏱ {sig_data['time']}</span>
          <span class="chip">⌛ Exp. {sig_data['expiry']}</span>
        </div>
        <div class="conf-bar"><div style="width:{sig_data['conf']}%; background:{bar_color};"></div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# EXÉCUTION DU SCAN
# ============================================================
if analyser:
    if not assets:
        st.error("Sélectionne au moins un actif dans la barre latérale.")
    else:
        st.session_state.last_scan = datetime.datetime.now().strftime("%H:%M:%S")
        progress = st.progress(0, text="Préparation du scan...")
        found_count = 0

        for i, asset in enumerate(assets):
            progress.progress((i) / len(assets), text=f"🔎 Analyse de {asset}...")

            df = fetch_data_quotex(asset, tf_seconds, 100)
            source = "OTC"
            if df is None or len(df) < 55:
                df = fetch_data_yahoo(asset, tf_seconds)
                source = "Démo"

            if df is None or len(df) < 55:
                st.warning(f"⚠️ {asset} : données insuffisantes (source={source}).")
                continue

            signal, confidence, last = compute_signal(df)

            if signal:
                found_count += 1
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                sig_data = {
                    "time": now_str,
                    "asset": asset,
                    "dir": signal,
                    "conf": confidence,
                    "rsi": round(float(last["rsi"]), 1),
                    "stoch": round(float(last["stoch_k"]), 1),
                    "price": round(float(last["close"]), 5),
                    "expiry": expiry,
                    "source": source,
                }
                st.session_state.signals_history.insert(0, sig_data)
                st.session_state.signals_history = st.session_state.signals_history[:50]

                render_signal_card(sig_data)

                # Bip sonore
                st.components.v1.html(
                    "<audio autoplay>"
                    "<source src='https://actions.google.com/sounds/v1/alarms/beep_short.ogg' type='audio/ogg'>"
                    "</audio>",
                    height=0,
                )

        progress.progress(1.0, text=f"✅ Scan terminé — {found_count} signal(aux) trouvé(s) sur {len(assets)} actifs")

        if found_count == 0:
            st.info(
                "Aucun signal fort sur cette bougie. Attends la prochaine clôture "
                "puis re-clique sur **ANALYSER**."
            )

# ============================================================
# HISTORIQUE
# ============================================================
st.divider()
col_a, col_b = st.columns([3, 1])
with col_a:
    st.subheader("📜 Historique des signaux")
with col_b:
    if st.session_state.signals_history and st.button("🗑 Effacer l'historique", use_container_width=True):
        st.session_state.signals_history = []
        st.rerun()

if st.session_state.signals_history:
    hist_df = pd.DataFrame(st.session_state.signals_history)
    cols = ["time", "asset", "dir", "conf", "rsi", "stoch", "price", "expiry", "source"]
    hist_df = hist_df[[c for c in cols if c in hist_df.columns]]
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
else:
    st.caption("Aucun signal généré pour le moment.")

st.caption("Quotex Signal Pro • v1.1 • Signaux manuels uniquement")
