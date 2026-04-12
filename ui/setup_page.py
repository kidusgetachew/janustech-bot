"""
PROJECT JANUSTECH — Setup Page
Glassmorphism aesthetic, KPI cards, animated status, mini terminal.
"""

import streamlit as st
from datetime import datetime, timezone


def render_setup_page():
    """Render the full glassmorphism setup page."""

    # Inject setup-specific CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Rajdhani:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    /* ── Background grid pattern ── */
    .stApp {
        background:
            linear-gradient(rgba(0,229,255,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,229,255,0.015) 1px, transparent 1px),
            #0d1117 !important;
        background-size: 40px 40px !important;
    }

    /* ── Glassmorphism cards ── */
    .glass-card {
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(0,229,255,0.12);
        border-radius: 12px;
        padding: 28px;
        position: relative;
        overflow: hidden;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,229,255,0.4), transparent);
    }

    .glass-card-sm {
        background: rgba(255,255,255,0.02);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(0,229,255,0.08);
        border-radius: 10px;
        padding: 16px 20px;
        position: relative;
    }

    /* ── KPI cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }

    .kpi-card {
        background: rgba(0,229,255,0.03);
        border: 1px solid rgba(0,229,255,0.1);
        border-radius: 10px;
        padding: 14px 18px;
        position: relative;
        overflow: hidden;
    }

    .kpi-card::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(0,229,255,0.4), transparent);
    }

    .kpi-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #484f58;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 16px;
        font-weight: 600;
        color: #00e5ff;
    }

    .kpi-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: #484f58;
        margin-top: 2px;
    }

    /* ── Input glow effects ── */
    .stTextInput > div > div > input {
        background: rgba(0,0,0,0.4) !important;
        border: 1px solid rgba(0,229,255,0.15) !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s !important;
        padding: 10px 14px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: rgba(0,229,255,0.6) !important;
        box-shadow: 0 0 0 3px rgba(0,229,255,0.08), 0 0 20px rgba(0,229,255,0.05) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #30363d !important;
        letter-spacing: 1px !important;
    }

    .stNumberInput > div > div > input {
        background: rgba(0,0,0,0.4) !important;
        border: 1px solid rgba(0,229,255,0.15) !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }

    .stNumberInput > div > div > input:focus {
        border-color: rgba(0,229,255,0.6) !important;
        box-shadow: 0 0 0 3px rgba(0,229,255,0.08) !important;
    }

    /* ── Connect button ── */
    .connect-btn > button {
        background: rgba(0,229,255,0.08) !important;
        border: 1px solid rgba(0,229,255,0.4) !important;
        color: #00e5ff !important;
        border-radius: 8px !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        transition: all 0.2s !important;
        padding: 10px !important;
    }

    .connect-btn > button:hover {
        background: rgba(0,229,255,0.15) !important;
        border-color: rgba(0,229,255,0.8) !important;
        box-shadow: 0 0 20px rgba(0,229,255,0.15) !important;
        color: #ffffff !important;
    }

    /* ── Animated status dots ── */
    @keyframes pulse-cyan {
        0%, 100% { opacity: 1; box-shadow: 0 0 4px #00e5ff; }
        50% { opacity: 0.4; box-shadow: 0 0 12px #00e5ff; }
    }
    @keyframes pulse-green {
        0%, 100% { opacity: 1; box-shadow: 0 0 4px #3fb950; }
        50% { opacity: 0.4; box-shadow: 0 0 12px #3fb950; }
    }
    @keyframes pulse-red {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .dot-offline {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #f85149;
        animation: pulse-red 2s infinite;
        margin-right: 6px;
    }
    .dot-paper {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #00e5ff;
        animation: pulse-cyan 2s infinite;
        margin-right: 6px;
    }
    .dot-live {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #3fb950;
        animation: pulse-green 1.5s infinite;
        margin-right: 6px;
    }

    /* ── Terminal feed ── */
    .terminal-feed {
        background: rgba(0,0,0,0.6);
        border: 1px solid rgba(0,229,255,0.1);
        border-radius: 8px;
        padding: 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        line-height: 1.9;
        height: 140px;
        overflow-y: auto;
    }

    .terminal-feed::-webkit-scrollbar { width: 3px; }
    .terminal-feed::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.2); border-radius: 2px; }

    /* ── Section header ── */
    .section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #00e5ff;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(0,229,255,0.1);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .section-label::before {
        content: '';
        display: inline-block;
        width: 4px; height: 4px;
        background: #00e5ff;
        border-radius: 50%;
    }

    /* ── Radio buttons ── */
    .stRadio > div {
        flex-direction: row !important;
        gap: 16px !important;
    }
    .stRadio label {
        color: #8b949e !important;
        font-size: 13px !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ── Warning box ── */
    .live-warning {
        padding: 14px;
        background: rgba(248,81,73,0.06);
        border: 1px solid rgba(248,81,73,0.25);
        border-radius: 8px;
        margin-bottom: 16px;
        font-size: 12px;
        color: #f85149;
        font-family: 'DM Sans', sans-serif;
        line-height: 1.6;
    }

    /* ── Glossary items ── */
    .glossary-item {
        display: flex;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid rgba(0,229,255,0.05);
        font-size: 12px;
        align-items: flex-start;
    }

    .glossary-term {
        font-family: 'JetBrains Mono', monospace;
        color: #00e5ff;
        min-width: 60px;
        font-size: 11px;
        font-weight: 600;
        padding-top: 1px;
    }

    .glossary-desc {
        color: #8b949e;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    connected = st.session_state.get("connected", False)
    bot = st.session_state.get("bot", None)
    config = st.session_state.get("config", None)

    # ── KPI Cards ──────────────────────────────────────────────────────────
    balance_str = "$0.00"
    equity_str = "$0.00"
    if bot and connected:
        acc = bot.get_dashboard_data().get("account", {})
        balance_str = f"${acc.get('equity', 0):,.2f}"

    status_dot = "dot-offline"
    status_text = "OFFLINE"
    mode_text = "NONE"
    strategy_text = "SMC v1.0"

    if connected and bot and bot.is_running:
        status_dot = "dot-live"
        status_text = "LIVE"
        mode_text = "PAPER" if config and config.api.paper_trading else "LIVE"
    elif connected:
        status_dot = "dot-paper"
        status_text = "CONNECTED"
        mode_text = "PAPER" if config and config.api.paper_trading else "LIVE"

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">System Status</div>
            <div class="kpi-value" style="display:flex;align-items:center;">
                <span class="{status_dot}"></span>
                {status_text}
            </div>
            <div class="kpi-sub">{'Bot active' if status_text == 'LIVE' else 'Awaiting connection'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Account Balance</div>
            <div class="kpi-value">{balance_str}</div>
            <div class="kpi-sub">{'Live equity' if connected else 'Not connected'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Trading Mode</div>
            <div class="kpi-value">{mode_text}</div>
            <div class="kpi-sub">{'Real funds' if mode_text == 'LIVE' else 'Simulated funds'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Active Strategy</div>
            <div class="kpi-value" style="font-size:14px;">{strategy_text}</div>
            <div class="kpi-sub">Smart Money Concepts</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Main layout ─────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 2], gap="large")

    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">API Configuration</div>', unsafe_allow_html=True)

        trading_mode = st.radio("Account Type", ["Paper Trading", "Live Trading"], horizontal=True)
        paper = trading_mode == "Paper Trading"

        if not paper:
            st.markdown("""
            <div class="live-warning">
                ⚠️ <strong>LIVE TRADING WARNING</strong><br>
                This mode uses real money. Losses can exceed your deposit.
                Ensure you have thoroughly tested on Paper Trading first.
                You are solely responsible for any financial losses.
            </div>
            """, unsafe_allow_html=True)
            confirm_live = st.checkbox("I understand this uses real money and accept all risks")
        else:
            confirm_live = True

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        api_key = st.text_input(
            "API Key ID",
            placeholder="PK••••••••••••••••••••••••",
            help="Your Alpaca API Key ID starting with PK"
        )
        secret_key = st.text_input(
            "Secret Key",
            placeholder="••••••••••••••••••••••••••••••••",
            type="password",
            help="Your Alpaca Secret Key — never share this"
        )

        ca, cb = st.columns(2)
        with ca:
            risk_pct = st.number_input(
                "Risk Per Trade (%)",
                min_value=0.1, max_value=5.0, value=1.0, step=0.1,
                help="% of account risked per trade. 1% recommended."
            )
        with cb:
            max_loss = st.number_input(
                "Max Daily Loss (%)",
                min_value=0.5, max_value=10.0, value=3.0, step=0.5,
                help="Bot halts for the day after this loss."
            )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        st.markdown('<div class="connect-btn">', unsafe_allow_html=True)
        connect_clicked = st.button("CONNECT & VERIFY", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

        if connect_clicked:
            if not api_key or not secret_key:
                st.error("Both API Key and Secret Key are required.")
            elif not paper and not confirm_live:
                st.error("You must confirm you accept the risks of live trading.")
            else:
                with st.spinner("Verifying credentials with Alpaca..."):
                    from config.config import BotConfig
                    from bot import SMCBot
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
                        st.error(f"Connection failed: {msg}")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Mini Terminal Feed ─────────────────────────────────────────────
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card-sm">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">System Console</div>', unsafe_allow_html=True)

        from config.logger import get_recent_logs
        logs = get_recent_logs(20)

        now = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if logs:
            log_lines = ""
            color_map = {"ok": "#3fb950", "warn": "#d29922", "err": "#f85149", "neu": "#484f58"}
            for log in reversed(logs[-8:]):
                c = color_map.get(log.get("type", "neu"), "#484f58")
                log_lines += f"<div><span style='color:#30363d;'>{log['time']}</span> <span style='color:{c};'>{log['msg']}</span></div>"
        else:
            log_lines = f"""
            <div><span style='color:#30363d;'>{now}</span> <span style='color:#00e5ff;'>PROJECT JANUSTECH v1.0 initialized</span></div>
            <div><span style='color:#30363d;'>{now}</span> <span style='color:#484f58;'>SMC strategy engine loaded</span></div>
            <div><span style='color:#30363d;'>{now}</span> <span style='color:#484f58;'>Risk manager ready — 1% per trade</span></div>
            <div><span style='color:#30363d;'>{now}</span> <span style='color:#d29922;'>Awaiting API connection...</span></div>
            <div><span style='color:#30363d;'>{now}</span> <span style='color:#484f58;'>Enter credentials above to connect ▲</span></div>
            """

        st.markdown(f'<div class="terminal-feed">{log_lines}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # ── How to get keys ────────────────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Get API Keys</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:13px;color:#8b949e;line-height:2;'>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>01</span>
                <span>Go to <span style='color:#00e5ff;'>alpaca.markets</span></span>
            </div>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>02</span>
                <span>Create a free account</span>
            </div>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>03</span>
                <span>Navigate to Paper Trading</span>
            </div>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>04</span>
                <span>Click <span style='color:#e6edf3;'>Your API Keys</span></span>
            </div>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>05</span>
                <span>Generate a new key pair</span>
            </div>
            <div style='display:flex;gap:12px;align-items:center;padding:4px 0;'>
                <span style='color:#00e5ff;font-family:JetBrains Mono,monospace;font-size:11px;min-width:20px;'>06</span>
                <span>Paste both keys in the form</span>
            </div>
        </div>
        <div style='margin-top:14px;padding:12px;background:rgba(210,153,34,0.06);border:1px solid rgba(210,153,34,0.2);border-radius:8px;font-size:12px;color:#d29922;line-height:1.6;'>
            ⚠ Always start on Paper Trading.<br>
            Run for 2–4 weeks before going live.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── SMC Glossary ───────────────────────────────────────────────────
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">SMC Glossary</div>', unsafe_allow_html=True)

        glossary = [
            ("Bias", "Bullish or bearish direction based on higher timeframe structure"),
            ("Sweep", "Price grabs liquidity (stops) then immediately reverses"),
            ("BoS", "Break of Structure — confirms the new direction is real"),
            ("FVG", "Fair Value Gap — 3-candle imbalance where price often returns"),
            ("OB", "Order Block — last opposing candle before a strong move"),
            ("Score", "Confluence score out of 6 — higher means stronger signal"),
        ]

        for term, desc in glossary:
            st.markdown(f"""
            <div class="glossary-item">
                <span class="glossary-term">{term}</span>
                <span class="glossary-desc">{desc}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Getting started ────────────────────────────────────────────────
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Quick Start</div>', unsafe_allow_html=True)
        steps = [
            ("Terminal", "Browse stocks and view live SMC analysis"),
            ("Backtest", "Test strategy on historical data first"),
            ("Dashboard", "Start bot and monitor live trades"),
            ("History", "Review every trade the bot has taken"),
            ("Parameters", "Tune risk, strategy, and alerts"),
        ]
        for page, desc in steps:
            st.markdown(f"""
            <div style='display:flex;gap:12px;padding:7px 0;border-bottom:1px solid rgba(0,229,255,0.05);align-items:center;'>
                <span style='font-family:JetBrains Mono,monospace;font-size:11px;color:#00e5ff;min-width:80px;font-weight:600;'>{page}</span>
                <span style='font-size:12px;color:#8b949e;'>{desc}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)