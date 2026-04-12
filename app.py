"""
PROJECT JANUSTECH — Complete Trading Terminal
All features: terminal, dashboard, strategy, backtest, history, parameters, logs, alerts
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone

from config.config import BotConfig
from bot import SMCBot
from backtesting.backtest_page_v2 import render_backtest_page
from ui.terminal import get_stock_data, get_quick_stats, get_smc_analysis, STOCK_CATALOG, ALL_SYMBOLS
from ui.log_viewer import render_log_viewer
from ui.trade_history import render_trade_history
from ui.setup_page import render_setup_page

st.set_page_config(page_title="PROJECT JANUSTECH", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Rajdhani:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
* { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0d1117 !important; }
[data-testid="stAppViewContainer"] { background: #0d1117 !important; }
[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none !important; }
[data-testid="stDecoration"] { display: none; }
h1,h2,h3,h4,h5,h6 { color: #e6edf3 !important; font-weight: 500 !important; }
p, span, label, div { color: #8b949e; }
[data-testid="metric-container"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important; padding: 12px 16px !important; }
[data-testid="metric-container"] label { font-size: 10px !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; color: #484f58 !important; font-family: 'JetBrains Mono', monospace !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: 600 !important; color: #e6edf3 !important; font-family: 'JetBrains Mono', monospace !important; }
.stButton > button { background: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 6px !important; font-size: 13px !important; font-weight: 500 !important; transition: all 0.15s !important; }
.stButton > button:hover { background: #21262d !important; border-color: #484f58 !important; color: #ffffff !important; }
.stTextInput > div > div > input, .stNumberInput > div > div > input { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important; color: #e6edf3 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
hr { border-color: #21262d !important; }
.pill { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; font-family: 'JetBrains Mono', monospace; }
.pill-green { background: rgba(35,134,54,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.pill-yellow { background: rgba(187,128,9,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.pill-blue { background: rgba(31,111,235,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.3); }
.pill-red { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.card-header { font-size: 10px; color: #484f58; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'JetBrains Mono', monospace; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }
.stTabs [data-baseweb="tab-list"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important; padding: 3px !important; }
.stTabs [data-baseweb="tab"] { color: #484f58 !important; font-size: 13px !important; border-radius: 4px !important; }
.stTabs [aria-selected="true"] { background: #21262d !important; color: #e6edf3 !important; }
.stCheckbox label { color: #8b949e !important; font-size: 13px !important; }
.stRadio label { color: #8b949e !important; font-size: 13px !important; }
.stToggle label { color: #8b949e !important; font-size: 13px !important; }
.stProgress > div > div { background: #58a6ff !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
defaults = {
    "bot": None, "connected": False, "config": BotConfig(),
    "equity_history": [], "selected_symbol": "SPY",
    "page": "Setup", "menu_open": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── TOP BAR ────────────────────────────────────────────────────────────────────
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_left:
    if st.session_state.bot and st.session_state.bot.is_running:
        st.markdown('<span class="pill pill-green">● LIVE</span>', unsafe_allow_html=True)
    elif st.session_state.connected:
        st.markdown('<span class="pill pill-yellow">● CONNECTED</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill pill-red">● OFFLINE</span>', unsafe_allow_html=True)
    mode = "PAPER" if st.session_state.config.api.paper_trading else "LIVE"
    st.markdown(f'<span class="pill pill-blue" style="margin-left:6px;">{mode}</span>', unsafe_allow_html=True)
with col_center:
    st.markdown("""
    <div style='text-align:center;padding:4px 0;'>
        <div style='font-family:Rajdhani,sans-serif;font-size:22px;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:#e6edf3;'>PROJECT JANUSTECH</div>
        <div style='font-family:JetBrains Mono,monospace;font-size:9px;letter-spacing:3px;color:#484f58;text-transform:uppercase;'>Smart Money Concepts Trading Engine</div>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    r1, r2 = st.columns([2, 1])
    with r2:
        if st.button("☰", key="menu_btn"):
            st.session_state.menu_open = not st.session_state.menu_open
            st.rerun()

st.markdown("<div style='border-bottom:1px solid #21262d;margin-bottom:12px;'></div>", unsafe_allow_html=True)

# ── HAMBURGER MENU ─────────────────────────────────────────────────────────────
if st.session_state.menu_open:
    st.markdown('<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Rajdhani,sans-serif;font-size:13px;font-weight:700;letter-spacing:3px;color:#484f58;margin-bottom:12px;">NAVIGATION</div>', unsafe_allow_html=True)
    pages = ["Setup","Terminal","Dashboard","Strategy","Backtest","History","Parameters","Logs"]
    icons = {"Setup":"⚙","Terminal":"◈","Dashboard":"▣","Strategy":"◎","Backtest":"▷","History":"📋","Parameters":"≡","Logs":"▤"}
    cols = st.columns(len(pages))
    for i, p in enumerate(pages):
        with cols[i]:
            if st.button(f"{icons.get(p,'')} {p}", key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p
                st.session_state.menu_open = False
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page

# ── SETUP ──────────────────────────────────────────────────────────────────────
if page == "Setup":
    st.markdown("### Connect Brokerage")
    col1, col2 = st.columns([3, 2], gap="large")
    with col1:
        st.markdown('<div class="card"><div class="card-header">API Configuration</div>', unsafe_allow_html=True)
        trading_mode = st.radio("Account Type", ["Paper Trading", "Live Trading"], horizontal=True)
        paper = trading_mode == "Paper Trading"

        if not paper:
            st.markdown('<div style="padding:10px;background:rgba(248,81,73,0.08);border:1px solid rgba(248,81,73,0.3);border-radius:6px;margin-bottom:12px;font-size:13px;color:#f85149;">⚠️ WARNING: Live Trading uses REAL money. Make sure you have tested on paper trading first. Losses can exceed your deposit.</div>', unsafe_allow_html=True)
            confirm_live = st.checkbox("I understand this uses real money and I accept all risks")
        else:
            confirm_live = True

        api_key = st.text_input("API Key ID", placeholder="PKXXXXXXXXXXXXXXXXXXXXXXXX")
        secret_key = st.text_input("Secret Key", placeholder="••••••••••••••••••••••••••••••••", type="password")
        ca, cb = st.columns(2)
        with ca:
            risk_pct = st.number_input("Risk / Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        with cb:
            max_loss = st.number_input("Max Daily Loss (%)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)

        if st.button("Connect", use_container_width=True, type="primary"):
            if not api_key or not secret_key:
                st.error("Both keys required.")
            elif not paper and not confirm_live:
                st.error("You must confirm you understand the risks of live trading.")
            else:
                with st.spinner("Verifying credentials..."):
                    config = st.session_state.config
                    config.risk.risk_per_trade = risk_pct / 100
                    config.risk.max_daily_loss = max_loss / 100
                    config.api.paper_trading = paper
                    bot = SMCBot(config)
                    ok, msg = bot.connect(api_key, secret_key, paper)
                    if ok:
                        st.session_state.bot = bot
                        st.session_state.connected = True
                        st.session_state.config = config
                        st.session_state.page = "Terminal"
                        st.rerun()
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

        # Onboarding guide
        st.markdown('<div class="card"><div class="card-header">Getting Started</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:13px;color:#8b949e;line-height:1.9;'>
            <div style='margin-bottom:8px;'><span style='color:#58a6ff;font-weight:600;'>1. Connect</span> — Enter your Alpaca paper trading API keys above</div>
            <div style='margin-bottom:8px;'><span style='color:#58a6ff;font-weight:600;'>2. Terminal</span> — Browse stocks, view candlestick charts with SMC analysis</div>
            <div style='margin-bottom:8px;'><span style='color:#58a6ff;font-weight:600;'>3. Backtest</span> — Test the strategy on historical data before going live</div>
            <div style='margin-bottom:8px;'><span style='color:#58a6ff;font-weight:600;'>4. Dashboard</span> — Start the bot and monitor live trading</div>
            <div style='margin-bottom:8px;'><span style='color:#58a6ff;font-weight:600;'>5. History</span> — Review every trade the bot has taken</div>
        </div>
        <div style='margin-top:12px;padding:10px;background:rgba(88,166,255,0.06);border:1px solid rgba(88,166,255,0.15);border-radius:6px;font-size:12px;color:#58a6ff;'>
            💡 SMC = Smart Money Concepts. The bot looks for institutional footprints: liquidity sweeps, breaks of structure, fair value gaps, and order blocks.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-header">How to get API Keys</div>
            <div style='font-size:13px;color:#8b949e;line-height:1.9;'>
                1. Go to <span style='color:#58a6ff;'>alpaca.markets</span><br>
                2. Create a free account<br>
                3. Navigate to Paper Trading<br>
                4. Click Your API Keys<br>
                5. Generate a new key pair<br>
                6. Paste both keys above
            </div>
            <div style='margin-top:12px;padding:10px;background:rgba(187,128,9,0.08);border:1px solid rgba(210,153,34,0.2);border-radius:6px;font-size:12px;color:#d29922;'>
                ⚠ Always start on Paper Trading. Run for 2-4 weeks before considering live.
            </div>
        </div>
        <div class="card" style="margin-top:12px;">
            <div class="card-header">SMC Signal Glossary</div>
            <div style='font-size:12px;color:#8b949e;line-height:2;font-family:JetBrains Mono,monospace;'>
                <div><span style='color:#58a6ff;'>Daily Bias</span> — Bullish or bearish based on HTF structure</div>
                <div><span style='color:#58a6ff;'>Liquidity Sweep</span> — Price grabs stops then reverses</div>
                <div><span style='color:#58a6ff;'>BoS</span> — Break of Structure confirms new direction</div>
                <div><span style='color:#58a6ff;'>FVG</span> — Fair Value Gap — 3-candle imbalance zone</div>
                <div><span style='color:#58a6ff;'>OB</span> — Order Block — last opposing candle before move</div>
                <div><span style='color:#58a6ff;'>Confluence</span> — Score out of 6 — higher = stronger signal</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── TERMINAL ───────────────────────────────────────────────────────────────────
elif page == "Terminal":
    s1, s2, s3 = st.columns([3, 2, 1])
    with s1:
        search = st.text_input("Search", placeholder="Search any symbol — AAPL, TSLA, NVDA...", label_visibility="collapsed", key="sym_search")
    with s2:
        timeframe = st.selectbox("TF", ["5Min","15Min","1Hour","4Hour","1Day"], index=4, label_visibility="collapsed")
    with s3:
        show_smc = st.toggle("SMC", value=True)

    ind_cols = st.columns(7)
    with ind_cols[0]: show_ema20 = st.checkbox("EMA 20", value=True)
    with ind_cols[1]: show_ema50 = st.checkbox("EMA 50", value=True)
    with ind_cols[2]: show_ema200 = st.checkbox("EMA 200", value=False)
    with ind_cols[3]: show_vwap = st.checkbox("VWAP", value=False)
    with ind_cols[4]: show_rsi = st.checkbox("RSI", value=False)
    with ind_cols[5]: show_vol = st.checkbox("Volume", value=True)
    with ind_cols[6]: show_bb = st.checkbox("BB", value=False)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    cat_col, chart_col, analysis_col = st.columns([1, 4, 1], gap="small")

    with cat_col:
        search_term = search.upper().strip() if search else ""
        selected = st.session_state.get("selected_symbol", "SPY")
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:10px;margin-bottom:4px;"><div style="font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:1.5px;font-family:JetBrains Mono,monospace;">Watchlist</div></div>', unsafe_allow_html=True)
        for group, symbols in STOCK_CATALOG.items():
            filtered = [s for s in symbols if search_term in s] if search_term else symbols
            if not filtered:
                continue
            st.markdown(f'<div style="font-size:9px;color:#484f58;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin:6px 0 2px;padding:0 2px;">{group}</div>', unsafe_allow_html=True)
            for sym in filtered:
                is_active = sym == selected
                if is_active:
                    st.markdown(f"<style>.active-btn-{sym} button{{background:rgba(88,166,255,0.12) !important;color:#58a6ff !important;border:1px solid rgba(88,166,255,0.3) !important;border-radius:4px !important;font-family:JetBrains Mono,monospace !important;font-size:12px !important;font-weight:600 !important;text-align:left !important;padding:5px 8px !important;margin-bottom:2px !important;}}</style>", unsafe_allow_html=True)
                    st.markdown(f"<div class='active-btn-{sym}'>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<style>.inactive-btn-{sym} button{{background:transparent !important;color:#8b949e !important;border:1px solid transparent !important;border-radius:4px !important;font-family:JetBrains Mono,monospace !important;font-size:12px !important;text-align:left !important;padding:5px 8px !important;margin-bottom:2px !important;}} .inactive-btn-{sym} button:hover{{background:rgba(88,166,255,0.06) !important;color:#58a6ff !important;}}</style>", unsafe_allow_html=True)
                    st.markdown(f"<div class='inactive-btn-{sym}'>", unsafe_allow_html=True)
                if st.button(sym, key=f"wl_{sym}", use_container_width=True):
                    st.session_state.selected_symbol = sym
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    with chart_col:
        symbol = st.session_state.get("selected_symbol", "SPY")
        if search and search.upper() in ALL_SYMBOLS:
            symbol = search.upper()
            st.session_state.selected_symbol = symbol

        tf_days = {"5Min":7,"15Min":14,"1Hour":30,"4Hour":60,"1Day":180}
        days = tf_days.get(timeframe, 90)

        if st.session_state.bot and st.session_state.bot.client and st.session_state.bot.client.connected:
            df = get_stock_data(st.session_state.bot.client, symbol, timeframe, days)
            stats = get_quick_stats(df)
            smc_data = get_smc_analysis(st.session_state.bot, symbol) if show_smc else {}
        else:
            df = pd.DataFrame()
            stats = {}
            smc_data = {}

        price = stats.get("price", 0)
        change = stats.get("change", 0)
        change_pct = stats.get("change_pct", 0)
        change_color = "#3fb950" if change >= 0 else "#f85149"
        arrow = "▲" if change >= 0 else "▼"

        st.markdown(f"""
        <div style='display:flex;align-items:baseline;gap:16px;margin-bottom:8px;'>
            <span style='font-family:Rajdhani,sans-serif;font-size:24px;font-weight:700;color:#e6edf3;letter-spacing:2px;'>{symbol}</span>
            <span style='font-family:JetBrains Mono,monospace;font-size:22px;font-weight:600;color:#e6edf3;'>${price:,.2f}</span>
            <span style='font-family:JetBrains Mono,monospace;font-size:14px;color:{change_color};'>{arrow} ${abs(change):.2f} ({change_pct:+.2f}%)</span>
            <span style='font-size:11px;color:#484f58;font-family:JetBrains Mono,monospace;margin-left:auto;'>{timeframe} · {len(df)} bars</span>
        </div>
        """, unsafe_allow_html=True)

        if not df.empty:
            df_chart = df.tail(150).copy()
            if show_ema20 and len(df_chart) >= 20:
                df_chart["ema20"] = df_chart["close"].ewm(span=20).mean()
            if show_ema50 and len(df_chart) >= 50:
                df_chart["ema50"] = df_chart["close"].ewm(span=50).mean()
            if show_ema200 and len(df) >= 200:
                df_chart["ema200"] = df["close"].ewm(span=200).mean().tail(150).values
            if show_vwap and "volume" in df_chart.columns:
                df_chart["vwap"] = (df_chart["close"] * df_chart["volume"]).cumsum() / df_chart["volume"].cumsum()
            if show_bb:
                df_chart["bb_mid"] = df_chart["close"].rolling(20).mean()
                bb_std = df_chart["close"].rolling(20).std()
                df_chart["bb_upper"] = df_chart["bb_mid"] + 2 * bb_std
                df_chart["bb_lower"] = df_chart["bb_mid"] - 2 * bb_std
            if show_rsi:
                delta = df_chart["close"].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss
                df_chart["rsi"] = 100 - (100 / (1 + rs))

            rows = 1
            row_heights = [1.0]
            if show_vol and show_rsi:
                rows = 3
                row_heights = [0.62, 0.16, 0.22]
            elif show_vol or show_rsi:
                rows = 2
                row_heights = [0.75, 0.25]

            fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_heights, vertical_spacing=0.02)

            fig.add_trace(go.Candlestick(
                x=df_chart.index,
                open=df_chart["open"], high=df_chart["high"],
                low=df_chart["low"], close=df_chart["close"],
                name=symbol,
                increasing=dict(line=dict(color="#3fb950", width=1), fillcolor="#3fb950"),
                decreasing=dict(line=dict(color="#f85149", width=1), fillcolor="#f85149"),
            ), row=1, col=1)

            if show_ema20 and "ema20" in df_chart:
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["ema20"], mode="lines", line=dict(color="#58a6ff", width=1.5), name="EMA20"), row=1, col=1)
            if show_ema50 and "ema50" in df_chart:
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["ema50"], mode="lines", line=dict(color="#d29922", width=1.5), name="EMA50"), row=1, col=1)
            if show_ema200 and "ema200" in df_chart:
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["ema200"], mode="lines", line=dict(color="#f0883e", width=1.5), name="EMA200"), row=1, col=1)
            if show_vwap and "vwap" in df_chart:
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["vwap"], mode="lines", line=dict(color="#bc8cff", width=1.5, dash="dash"), name="VWAP"), row=1, col=1)
            if show_bb and "bb_upper" in df_chart:
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["bb_upper"], mode="lines", line=dict(color="#484f58", width=1, dash="dot"), showlegend=False), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["bb_lower"], mode="lines", line=dict(color="#484f58", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(72,79,88,0.05)", showlegend=False), row=1, col=1)

            if smc_data and show_smc:
                for fvg in smc_data.get("fvgs", []):
                    fc = "rgba(63,185,80,0.07)" if "bullish" in fvg.get("type","") else "rgba(248,81,73,0.07)"
                    bc = "#3fb950" if "bullish" in fvg.get("type","") else "#f85149"
                    fig.add_hrect(y0=fvg["bottom"], y1=fvg["top"], fillcolor=fc, line=dict(color=bc, width=0.5, dash="dot"), row=1, col=1)
                for ob in smc_data.get("obs", []):
                    oc = "rgba(88,166,255,0.07)" if "bullish" in ob.get("type","") else "rgba(240,136,62,0.07)"
                    bc2 = "#58a6ff" if "bullish" in ob.get("type","") else "#f0883e"
                    fig.add_hrect(y0=ob["bottom"], y1=ob["top"], fillcolor=oc, line=dict(color=bc2, width=0.5, dash="dash"), row=1, col=1)
                if smc_data.get("equilibrium"):
                    fig.add_hline(y=smc_data["equilibrium"], line_color="#484f58", line_dash="dot", line_width=1, row=1, col=1)

            vol_row = 2 if show_vol else None
            if show_vol:
                colors = ["#3fb950" if c >= o else "#f85149" for c, o in zip(df_chart["close"], df_chart["open"])]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart["volume"], marker_color=colors, opacity=0.5, name="Vol", showlegend=False), row=2, col=1)

            if show_rsi and "rsi" in df_chart:
                rsi_row = 3 if show_vol else 2
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["rsi"], mode="lines", line=dict(color="#bc8cff", width=1.5), name="RSI14"), row=rsi_row, col=1)
                fig.add_hline(y=70, line_color="#f85149", line_dash="dot", line_width=1, row=rsi_row, col=1)
                fig.add_hline(y=30, line_color="#3fb950", line_dash="dot", line_width=1, row=rsi_row, col=1)

            chart_height = 560 if rows == 1 else 640 if rows == 2 else 720

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
                margin=dict(l=0, r=60, t=8, b=0), height=chart_height,
                xaxis=dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, zeroline=False, rangeslider=dict(visible=False), type="date"),
                yaxis=dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, zeroline=False, side="right", tickformat="$.2f"),
                showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#484f58", size=10), orientation="h", y=1.02, x=0),
                hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font=dict(color="#e6edf3", family="JetBrains Mono", size=11)),
                xaxis_rangeslider_visible=False,
            )
            for i in range(2, rows + 1):
                fig.update_layout(**{f"yaxis{i}": dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, zeroline=False, side="right")})

            st.plotly_chart(fig, use_container_width=True)

            if stats:
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1: st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#484f58;'>H </span><span style='color:#3fb950;'>${stats.get('high',0):,.2f}</span></div>", unsafe_allow_html=True)
                with sc2: st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#484f58;'>L </span><span style='color:#f85149;'>${stats.get('low',0):,.2f}</span></div>", unsafe_allow_html=True)
                with sc3:
                    vol = stats.get("volume", 0)
                    vol_str = f"{vol/1e6:.1f}M" if vol > 1e6 else f"{vol/1e3:.0f}K"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#484f58;'>VOL </span><span style='color:#e6edf3;'>{vol_str}</span></div>", unsafe_allow_html=True)
                with sc4:
                    avg = stats.get("avg_volume", 0)
                    avg_str = f"{avg/1e6:.1f}M" if avg > 1e6 else f"{avg/1e3:.0f}K"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#484f58;'>AVG </span><span style='color:#e6edf3;'>{avg_str}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='height:560px;display:flex;align-items:center;justify-content:center;background:#0d1117;border:1px solid #21262d;border-radius:8px;color:#484f58;font-family:JetBrains Mono,monospace;font-size:13px;'>Connect API to view charts</div>", unsafe_allow_html=True)

    with analysis_col:
        st.markdown('<div class="card"><div class="card-header">SMC Analysis</div>', unsafe_allow_html=True)
        if smc_data and show_smc:
            bias = smc_data.get("bias", "neutral")
            score = smc_data.get("score", 0)
            bias_color = "#3fb950" if bias == "bullish" else "#f85149" if bias == "bearish" else "#484f58"
            bias_bg = "rgba(35,134,54,0.1)" if bias == "bullish" else "rgba(248,81,73,0.1)" if bias == "bearish" else "rgba(72,79,88,0.1)"
            st.markdown(f'<div style="text-align:center;padding:10px;background:{bias_bg};border:1px solid {bias_color}33;border-radius:6px;margin-bottom:12px;"><div style="font-size:9px;color:#484f58;font-family:JetBrains Mono,monospace;letter-spacing:1px;">DAILY BIAS</div><div style="font-size:15px;font-weight:700;color:{bias_color};font-family:Rajdhani,sans-serif;letter-spacing:2px;">{bias.upper()}</div></div>', unsafe_allow_html=True)
            min_score = st.session_state.config.strategy.confluence_min
            bar_color = "#3fb950" if score >= min_score else "#d29922"
            bar_pct = int((score / 6) * 100)
            st.markdown(f'<div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:9px;color:#484f58;font-family:JetBrains Mono,monospace;letter-spacing:1px;">CONFLUENCE</span><span style="font-size:11px;font-weight:600;color:{bar_color};font-family:JetBrains Mono,monospace;">{score}/6</span></div><div style="background:#21262d;border-radius:2px;height:3px;"><div style="background:{bar_color};width:{bar_pct}%;height:3px;border-radius:2px;"></div></div></div>', unsafe_allow_html=True)
            checks = smc_data.get("checklist", {}).get("checks", {})
            items = [("Bias","daily_bias"),("Sweep","liquidity_sweep"),("BoS","bos"),("Zone","price_zone"),("FVG","fvg"),("OB","order_block")]
            tooltips = {"daily_bias":"Bullish/bearish based on higher timeframe structure","liquidity_sweep":"Price grabbed stops then reversed","bos":"Break of structure confirmed new direction","price_zone":"Price in discount (buy) or premium (sell)","fvg":"Fair Value Gap — 3-candle imbalance zone","order_block":"Last opposing candle before the move"}
            for label, key in items:
                active = checks.get(key, {}).get("active", False)
                color = "#3fb950" if active else "#21262d"
                tip = tooltips.get(key, "")
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #21262d;" title="{tip}"><span style="color:{color};font-size:12px;font-family:JetBrains Mono,monospace;">{"●" if active else "○"} {label}</span><span style="color:{"#3fb950" if active else "#21262d"};font-size:10px;">{"✓" if active else "—"}</span></div>', unsafe_allow_html=True)
            fvgs = smc_data.get("fvgs", [])
            if fvgs:
                st.markdown("<div style='margin-top:10px;font-size:9px;color:#484f58;font-family:JetBrains Mono,monospace;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;'>FVG Zones</div>", unsafe_allow_html=True)
                for fvg in fvgs[:2]:
                    fc = "#3fb950" if "bullish" in fvg.get("type","") else "#f85149"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:{fc};padding:2px 0;'>{fvg['bottom']:.2f}–{fvg['top']:.2f}</div>", unsafe_allow_html=True)
            obs = smc_data.get("obs", [])
            if obs:
                st.markdown("<div style='margin-top:8px;font-size:9px;color:#484f58;font-family:JetBrains Mono,monospace;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;'>Order Blocks</div>", unsafe_allow_html=True)
                for ob in obs[:2]:
                    oc = "#58a6ff" if "bullish" in ob.get("type","") else "#f0883e"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:{oc};padding:2px 0;'>{ob['bottom']:.2f}–{ob['top']:.2f}</div>", unsafe_allow_html=True)
            signal_text = "WAIT"
            signal_color = "#484f58"
            signal_bg = "rgba(72,79,88,0.1)"
            if score >= min_score and bias != "neutral":
                signal_text = "BUY SETUP" if bias == "bullish" else "SELL SETUP"
                signal_color = "#3fb950" if bias == "bullish" else "#f85149"
                signal_bg = "rgba(35,134,54,0.1)" if bias == "bullish" else "rgba(248,81,73,0.1)"
            st.markdown(f'<div style="margin-top:14px;padding:10px;background:{signal_bg};border:1px solid {signal_color}33;border-radius:6px;text-align:center;"><div style="font-size:9px;color:#484f58;font-family:JetBrains Mono,monospace;letter-spacing:1px;">SIGNAL</div><div style="font-size:13px;font-weight:700;color:{signal_color};font-family:Rajdhani,sans-serif;letter-spacing:2px;">{signal_text}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center;padding:40px 0;color:#484f58;font-size:12px;font-family:JetBrains Mono,monospace;'>Connect API &<br>enable SMC<br>to see analysis</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ── DASHBOARD ──────────────────────────────────────────────────────────────────
elif page == "Dashboard":
    st.markdown("### Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("▶  Start Bot", use_container_width=True, type="primary"):
            if not st.session_state.connected or not st.session_state.bot:
                st.error("Connect API keys first.")
            elif st.session_state.bot.is_running:
                st.warning("Already running.")
            else:
                ok, msg = st.session_state.bot.start()
                st.success(msg) if ok else st.error(msg)
    with c2:
        if st.button("⏹  Stop", use_container_width=True):
            if st.session_state.bot and st.session_state.bot.is_running:
                st.session_state.bot.stop()
                st.warning("Bot stopped.")
    with c3:
        if st.button("⚡  Emergency Close", use_container_width=True):
            if st.session_state.bot:
                ok, msg = st.session_state.bot.emergency_close()
                st.warning(msg) if ok else st.error(msg)
    with c4:
        auto_refresh = st.toggle("Auto-refresh", value=False)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if st.session_state.bot and st.session_state.connected:
        data = st.session_state.bot.get_dashboard_data()
        account = data.get("account", {})
        stats = data.get("stats", {})
        positions = data.get("positions", [])
        dd = data.get("drawdown", {})
        balance = account.get("equity", 0)
        pnl = account.get("pnl_today", 0)
        pnl_pct = account.get("pnl_pct", 0)
        session = data.get("session", "—")
        last_cycle = data.get("last_cycle", "—")
        if balance > 0:
            st.session_state.equity_history.append({"time": datetime.now(timezone.utc).strftime("%H:%M"), "equity": balance})

        # Drawdown warning
        if dd.get("is_killed"):
            st.markdown(f'<div style="padding:12px;background:rgba(248,81,73,0.1);border:1px solid rgba(248,81,73,0.3);border-radius:6px;color:#f85149;font-size:13px;margin-bottom:12px;">⛔ BOT HALTED — {dd.get("kill_reason","")}</div>', unsafe_allow_html=True)
        elif dd.get("daily_drawdown_pct", 0) > dd.get("max_daily_pct", 3) * 0.7:
            st.markdown(f'<div style="padding:12px;background:rgba(210,153,34,0.1);border:1px solid rgba(210,153,34,0.3);border-radius:6px;color:#d29922;font-size:13px;margin-bottom:12px;">⚠ Daily drawdown at {dd.get("daily_drawdown_pct",0):.1f}% — limit is {dd.get("max_daily_pct",3):.1f}%</div>', unsafe_allow_html=True)
    else:
        balance = pnl = pnl_pct = 0
        stats = {}
        positions = []
        session = "—"
        last_cycle = "—"

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Equity", f"${balance:,.2f}" if balance else "—")
    with m2: st.metric("Day P&L", f"${pnl:+,.2f}" if pnl else "$0.00", delta=f"{pnl_pct:+.2f}%" if pnl_pct else None)
    with m3: st.metric("Open Trades", stats.get("open_trades", 0))
    with m4:
        total = stats.get("total_trades", 0)
        st.metric("Win Rate", f"{stats.get('win_rate',0):.1f}%" if total > 0 else "—")
    with m5: st.metric("Session", session)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    chart_col, pos_col = st.columns([3, 1], gap="medium")
    with chart_col:
        st.markdown('<div class="card"><div class="card-header">Equity Curve</div>', unsafe_allow_html=True)
        if len(st.session_state.equity_history) > 1:
            eq_df = pd.DataFrame(st.session_state.equity_history)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=eq_df["time"], y=eq_df["equity"], mode="lines", line=dict(color="#58a6ff", width=2), fill="tozeroy", fillcolor="rgba(88,166,255,0.05)"))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117", margin=dict(l=0,r=0,t=8,b=0), height=220, xaxis=dict(showgrid=False, color="#484f58", showline=False, zeroline=False), yaxis=dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, zeroline=False, tickformat="$,.0f"), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("<div style='height:220px;display:flex;align-items:center;justify-content:center;color:#484f58;font-size:13px;font-family:JetBrains Mono,monospace;'>Start bot to track equity</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with pos_col:
        st.markdown('<div class="card"><div class="card-header">Positions</div>', unsafe_allow_html=True)
        if positions:
            for p in positions:
                pc = "#3fb950" if p["pnl"] >= 0 else "#f85149"
                st.markdown(f"<div style='padding:10px 0;border-bottom:1px solid #21262d;'><div style='display:flex;justify-content:space-between;margin-bottom:4px;'><span style='font-weight:600;color:#e6edf3;'>{p['symbol']}</span><span style='color:{pc};font-family:JetBrains Mono,monospace;font-size:13px;'>${p['pnl']:+.2f}</span></div><div style='display:flex;justify-content:space-between;'><span style='color:{pc};font-size:11px;font-family:JetBrains Mono,monospace;'>{p['side'].upper()}</span><span style='color:#484f58;font-size:11px;font-family:JetBrains Mono,monospace;'>@ {p['entry_price']:.2f}</span></div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding:32px 0;text-align:center;color:#484f58;font-size:12px;font-family:JetBrains Mono,monospace;'>No open positions</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;color:#484f58;margin-top:4px;'>Last cycle: {last_cycle} | Watching: {', '.join(st.session_state.config.markets.symbols)}</div>", unsafe_allow_html=True)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

# ── STRATEGY ───────────────────────────────────────────────────────────────────
elif page == "Strategy":
    st.markdown("### Strategy Engine")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<div class="card"><div class="card-header">SMC Confluence Checklist</div>', unsafe_allow_html=True)
        checks = {"Daily Bias": False, "Liquidity Sweep": False, "Break of Structure": False, "Price in Correct Zone": False, "Fair Value Gap": False, "Order Block": False}
        score = 0
        bias_text = "—"
        if st.session_state.bot and st.session_state.connected:
            try:
                bot = st.session_state.bot
                if bot.data_feed and bot.smc_engine:
                    for symbol in bot.config.markets.symbols:
                        daily = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_bias, n=50)
                        h4 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_structure, n=50)
                        h1 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_confirmation, n=50)
                        m15 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_entry, n=50)
                        m5 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_precision, n=50)
                        if not any(df.empty for df in [daily, h4, h1, m15, m5]):
                            result = bot.smc_engine.get_checklist(symbol, daily, h4, h1, m15, m5)
                            c = result.get("checks", {})
                            checks["Daily Bias"] = c.get("daily_bias", {}).get("active", False)
                            checks["Liquidity Sweep"] = c.get("liquidity_sweep", {}).get("active", False)
                            checks["Break of Structure"] = c.get("bos", {}).get("active", False)
                            checks["Price in Correct Zone"] = c.get("price_zone", {}).get("active", False)
                            checks["Fair Value Gap"] = c.get("fvg", {}).get("active", False)
                            checks["Order Block"] = c.get("order_block", {}).get("active", False)
                            score = result.get("score", 0)
                            bias_text = result.get("bias", "neutral").upper()
                            break
            except Exception as e:
                st.warning(f"Error: {e}")
        for name, active in checks.items():
            cc = "c-on" if active else "c-off"
            st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #21262d;"><span style="color:{"#3fb950" if active else "#21262d"};font-size:13px;">{"●" if active else "○"} {name}</span><span style="color:{"#3fb950" if active else "#21262d"};font-family:JetBrains Mono,monospace;font-size:11px;">{"CONFIRMED" if active else "WAITING"}</span></div>', unsafe_allow_html=True)
        min_score = st.session_state.config.strategy.confluence_min
        bar_pct = int((score / 6) * 100)
        bar_color = "#3fb950" if score >= min_score else "#d29922"
        st.markdown(f'<div style="margin-top:16px;padding:14px;background:#0d1117;border-radius:6px;border:1px solid #21262d;"><div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#484f58;letter-spacing:1px;">CONFLUENCE SCORE</span><span style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:600;color:{bar_color};">{score} / 6</span></div><div style="background:#21262d;border-radius:2px;height:4px;"><div style="background:{bar_color};width:{bar_pct}%;height:4px;border-radius:2px;"></div></div><div style="display:flex;justify-content:space-between;margin-top:8px;"><span style="font-size:10px;color:#484f58;font-family:JetBrains Mono,monospace;">Bias: {bias_text}</span><span style="font-size:10px;color:#484f58;font-family:JetBrains Mono,monospace;">Min: {min_score}</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div class="card-header">Timeframe Cascade</div>', unsafe_allow_html=True)
        for tf, label, color in [("1D","Daily Bias","#58a6ff"),("4H","Structure","#bc8cff"),("1H","Confirmation","#d29922"),("15M","Entry Zone","#3fb950"),("5M","Precision","#3fb950")]:
            st.markdown(f"<div style='display:flex;align-items:center;gap:14px;padding:6px 0;'><span style='background:#0d1117;border:1px solid {color}33;border-radius:4px;padding:6px 14px;font-family:JetBrains Mono,monospace;font-size:14px;font-weight:600;min-width:52px;text-align:center;display:inline-block;color:{color};'>{tf}</span><span style='color:#8b949e;font-size:13px;'>{label}</span></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-header">Sessions (UTC)</div>', unsafe_allow_html=True)
        now_hour = datetime.now(timezone.utc).hour
        for name, start, end in [("Sydney",21,6),("Tokyo",0,9),("London",7,12),("New York",12,17)]:
            active = (now_hour >= start or now_hour < end) if start > end else (start <= now_hour < end)
            color = "#3fb950" if active else "#484f58"
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #21262d;font-size:13px;'><span style='color:{color};'>{'●' if active else '○'} &nbsp;{name}</span><span style='color:#484f58;font-family:JetBrains Mono,monospace;font-size:11px;'>{start:02d}:00–{end:02d}:00</span></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "Backtest":
    render_backtest_page(st.session_state.bot, st.session_state.config)

elif page == "History":
    render_trade_history(st.session_state.bot)

elif page == "Parameters":
    st.markdown("### Parameters")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Risk Management", "Trailing Stop", "Strategy", "Markets & Sessions", "Alerts"])
    with tab1:
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown('<div class="card"><div class="card-header">Position Sizing</div>', unsafe_allow_html=True)
            risk = st.session_state.config.risk
            nr = st.number_input("Risk Per Trade (%)", value=risk.risk_per_trade*100, min_value=0.1, max_value=5.0, step=0.1)
            nd = st.number_input("Max Daily Loss (%)", value=risk.max_daily_loss*100, min_value=0.5, max_value=10.0, step=0.5)
            ndr = st.number_input("Drawdown Limit (%)", value=risk.drawdown_limit*100, min_value=1.0, max_value=20.0, step=0.5)
            nt = st.number_input("Max Open Trades", value=float(risk.max_open_trades), min_value=1.0, max_value=5.0, step=1.0)
            if st.button("Save Risk", use_container_width=True, key="save_risk"):
                st.session_state.config.risk.risk_per_trade = nr/100
                st.session_state.config.risk.max_daily_loss = nd/100
                st.session_state.config.risk.drawdown_limit = ndr/100
                st.session_state.config.risk.max_open_trades = int(nt)
                st.success("Saved.")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="card"><div class="card-header">Take Profit</div>', unsafe_allow_html=True)
            ntp = st.number_input("Close at TP1 (%)", value=risk.tp1_close_pct*100, min_value=10.0, max_value=100.0, step=10.0)
            st.number_input("TP1 R-Multiple", value=1.5, min_value=0.5, max_value=5.0, step=0.5)
            st.number_input("TP2 R-Multiple", value=3.0, min_value=1.0, max_value=10.0, step=0.5)
            if st.button("Save TP", use_container_width=True, key="save_tp"):
                st.session_state.config.risk.tp1_close_pct = ntp/100
                st.success("Saved.")
            st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        st.markdown('<div class="card"><div class="card-header">Trailing Stop Loss</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;color:#8b949e;">Locks in profits as price moves in your favor. Only moves in the profitable direction — never backward.</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            trail_enabled = st.toggle("Enable Trailing Stop", value=False)
            trail_pct = st.number_input("Trail Distance (%)", value=1.0, min_value=0.1, max_value=5.0, step=0.1, help="How far behind price the SL trails")
        with col2:
            activate_r = st.number_input("Activate at R-Multiple", value=1.0, min_value=0.5, max_value=3.0, step=0.5, help="Only start trailing after reaching this profit level")
            st.markdown(f'<div style="padding:10px;background:#0d1117;border:1px solid #21262d;border-radius:6px;font-size:11px;color:#484f58;font-family:JetBrains Mono,monospace;">Activates at {activate_r}R profit<br>Trails {trail_pct:.1f}% below price<br>Example: $100 entry, $95 SL<br>Activates at ${100+5*activate_r:.0f}, trails {trail_pct:.1f}% behind</div>', unsafe_allow_html=True)
        if st.button("Save Trailing Stop", use_container_width=True, key="save_trail"):
            st.success(f"Trailing stop {'enabled' if trail_enabled else 'disabled'} — Trail: {trail_pct}% | Activates at: {activate_r}R")
        st.markdown('</div>', unsafe_allow_html=True)
    with tab3:
        st.markdown('<div class="card"><div class="card-header">SMC Detection</div>', unsafe_allow_html=True)
        strat = st.session_state.config.strategy
        nf = st.number_input("FVG Min Size (pts)", value=strat.fvg_min_size_pts, min_value=1.0, max_value=50.0, step=1.0, help="Minimum size of a Fair Value Gap to be considered valid")
        no = st.number_input("OB Lookback (candles)", value=float(strat.ob_lookback), min_value=5.0, max_value=50.0, step=1.0, help="How many candles back to look for Order Blocks")
        nc = st.number_input("Min Confluence Score (/6)", value=float(strat.confluence_min), min_value=1.0, max_value=6.0, step=1.0, help="Minimum signals required before taking a trade")
        if st.button("Save Strategy", use_container_width=True, key="save_strat"):
            st.session_state.config.strategy.fvg_min_size_pts = nf
            st.session_state.config.strategy.ob_lookback = int(no)
            st.session_state.config.strategy.confluence_min = int(nc)
            st.success("Saved.")
        st.markdown('</div>', unsafe_allow_html=True)
    with tab4:
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown('<div class="card"><div class="card-header">Symbols</div>', unsafe_allow_html=True)
            si = st.text_input("Symbols (comma separated)", value=", ".join(st.session_state.config.markets.symbols), help="Alpaca-supported symbols only e.g. SPY, QQQ, AAPL")
            if st.button("Save Symbols", use_container_width=True, key="save_sym"):
                syms = [s.strip().upper() for s in si.split(",") if s.strip()]
                st.session_state.config.markets.symbols = syms
                st.success(f"Saved: {syms}")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="card"><div class="card-header">Sessions</div>', unsafe_allow_html=True)
            strat = st.session_state.config.strategy
            lon = st.checkbox("London (07–12 UTC)", value="london" in strat.active_sessions)
            ny = st.checkbox("New York (12–17 UTC)", value="new_york" in strat.active_sessions)
            lo = st.checkbox("London Open (07–09 UTC)", value="london_open" in strat.active_sessions)
            nyo = st.checkbox("NY Open (13–15 UTC)", value="ny_open" in strat.active_sessions)
            if st.button("Save Sessions", use_container_width=True, key="save_sess"):
                active = []
                if lon: active.append("london")
                if ny: active.append("new_york")
                if lo: active.append("london_open")
                if nyo: active.append("ny_open")
                st.session_state.config.strategy.active_sessions = active
                st.success(f"Saved: {active}")
            st.markdown('</div>', unsafe_allow_html=True)
    with tab5:
        st.markdown('<div class="card"><div class="card-header">Telegram Alerts</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;color:#8b949e;">Get instant notifications when the bot trades, hits a loss limit, or encounters an error.</p>', unsafe_allow_html=True)
        st.markdown("""
        <div style='padding:12px;background:#0d1117;border:1px solid #21262d;border-radius:6px;font-size:12px;color:#484f58;font-family:JetBrains Mono,monospace;margin-bottom:12px;'>
            Setup: 1. Message @BotFather on Telegram → /newbot<br>
            2. Copy the token below<br>
            3. Message your bot → get your Chat ID from @userinfobot
        </div>
        """, unsafe_allow_html=True)
        tg_token = st.text_input("Telegram Bot Token", value=st.session_state.config.alerts.telegram_token, placeholder="1234567890:ABCdefGHI...")
        tg_chat = st.text_input("Telegram Chat ID", value=st.session_state.config.alerts.telegram_chat_id, placeholder="123456789")
        col1, col2 = st.columns(2)
        with col1:
            alert_entry = st.checkbox("Alert on Trade Entry", value=st.session_state.config.alerts.alert_on_entry)
            alert_exit = st.checkbox("Alert on Trade Exit", value=st.session_state.config.alerts.alert_on_exit)
        with col2:
            alert_loss = st.checkbox("Alert on Daily Loss Hit", value=st.session_state.config.alerts.alert_on_daily_loss)
            alert_err = st.checkbox("Alert on Error", value=st.session_state.config.alerts.alert_on_error)
        sa, sb = st.columns(2)
        with sa:
            if st.button("Save Alerts", use_container_width=True, key="save_alerts"):
                st.session_state.config.alerts.telegram_token = tg_token
                st.session_state.config.alerts.telegram_chat_id = tg_chat
                st.session_state.config.alerts.alert_on_entry = alert_entry
                st.session_state.config.alerts.alert_on_exit = alert_exit
                st.session_state.config.alerts.alert_on_daily_loss = alert_loss
                st.session_state.config.alerts.alert_on_error = alert_err
                if st.session_state.bot and st.session_state.bot.alerter:
                    st.session_state.bot.alerter.token = tg_token
                    st.session_state.bot.alerter.chat_id = tg_chat
                    st.session_state.bot.alerter.enabled = bool(tg_token and tg_chat)
                st.success("Alerts saved.")
        with sb:
            if st.button("Send Test Message", use_container_width=True, key="test_alert"):
                from execution.alerts import TelegramAlerter
                alerter = TelegramAlerter(tg_token, tg_chat)
                if alerter.test():
                    st.success("Test message sent!")
                else:
                    st.error("Failed. Check your token and chat ID.")
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "Logs":
    render_log_viewer()
    if st.session_state.bot and st.session_state.bot.risk_manager:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown("#### Performance")
        stats = st.session_state.bot.risk_manager.get_stats()
        s1, s2, s3, s4 = st.columns(4)
        with s1: st.metric("Total Trades", stats.get("total_trades", 0))
        with s2: st.metric("Wins", stats.get("wins", 0))
        with s3: st.metric("Win Rate", f"{stats.get('win_rate',0):.1f}%")
        with s4: st.metric("Total P&L", f"${stats.get('total_pnl',0):+,.2f}")