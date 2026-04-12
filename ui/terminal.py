"""
SMCBot — Trading Terminal Dashboard
Full TradingView-style terminal with candlestick charts,
stock catalog, and live SMC analysis overlay.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Popular stocks catalog
STOCK_CATALOG = {
    "Indices & ETFs": ["SPY", "QQQ", "DIA", "IWM", "VTI", "GLD", "SLV"],
    "Tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "INTC", "NFLX"],
    "Finance": ["JPM", "BAC", "GS", "MS", "WFC", "BRK-B", "V", "MA"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "OXY", "BP"],
    "Health": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY"],
    "Consumer": ["WMT", "COST", "TGT", "NKE", "MCD", "SBUX"],
    "Crypto ETFs": ["IBIT", "FBTC", "GBTC", "ETHA"],
}

ALL_SYMBOLS = [s for group in STOCK_CATALOG.values() for s in group]


def get_stock_data(client, symbol: str, timeframe: str = "1Day", days: int = 90) -> pd.DataFrame:
    """Fetch OHLCV data using Alpaca client."""
    try:
        df = client.get_bars(symbol, timeframe, lookback_days=days)
        return df
    except Exception as e:
        return pd.DataFrame()


def get_quick_stats(df: pd.DataFrame) -> dict:
    """Calculate quick stats from OHLCV data."""
    if df.empty or len(df) < 2:
        return {}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    change = last["close"] - prev["close"]
    change_pct = (change / prev["close"]) * 100
    return {
        "price": last["close"],
        "change": change,
        "change_pct": change_pct,
        "high": last["high"],
        "low": last["low"],
        "volume": last["volume"],
        "avg_volume": df["volume"].tail(20).mean(),
    }


def render_candlestick_chart(df: pd.DataFrame, symbol: str, smc_levels: dict = None) -> go.Figure:
    """Render a full candlestick chart with SMC overlays."""
    if df.empty:
        return None

    fig = go.Figure()

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name=symbol,
        increasing=dict(line=dict(color="#26a69a", width=1), fillcolor="#26a69a"),
        decreasing=dict(line=dict(color="#ef5350", width=1), fillcolor="#ef5350"),
    ))

    # Volume bars at bottom
    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["close"], df["open"])]

    fig.add_trace(go.Bar(
        x=df.index,
        y=df["volume"],
        name="Volume",
        marker_color=colors,
        opacity=0.3,
        yaxis="y2",
    ))

    # SMC overlays
    if smc_levels:
        # FVG zones
        for fvg in smc_levels.get("fvgs", []):
            color = "rgba(38,166,154,0.08)" if fvg.get("type") == "bullish_fvg" else "rgba(239,83,80,0.08)"
            border = "#26a69a" if fvg.get("type") == "bullish_fvg" else "#ef5350"
            fig.add_hrect(
                y0=fvg["bottom"], y1=fvg["top"],
                fillcolor=color,
                line=dict(color=border, width=1, dash="dot"),
                annotation_text="FVG",
                annotation_position="right",
                annotation_font=dict(size=10, color=border),
            )

        # Order blocks
        for ob in smc_levels.get("obs", []):
            color = "rgba(41,98,255,0.08)" if ob.get("type") == "bullish_ob" else "rgba(255,152,0,0.08)"
            border = "#2962ff" if ob.get("type") == "bullish_ob" else "#ff9800"
            fig.add_hrect(
                y0=ob["bottom"], y1=ob["top"],
                fillcolor=color,
                line=dict(color=border, width=1, dash="dash"),
                annotation_text="OB",
                annotation_position="right",
                annotation_font=dict(size=10, color=border),
            )

        # Equilibrium line
        if smc_levels.get("equilibrium"):
            fig.add_hline(
                y=smc_levels["equilibrium"],
                line_color="#787b86",
                line_dash="dot",
                line_width=1,
                annotation_text="EQ",
                annotation_font=dict(size=10, color="#787b86"),
            )

        # Bias line
        bias = smc_levels.get("bias", "neutral")
        bias_color = "#26a69a" if bias == "bullish" else "#ef5350" if bias == "bearish" else "#787b86"

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#131722",
        margin=dict(l=0, r=60, t=8, b=0),
        height=420,
        xaxis=dict(
            showgrid=True,
            gridcolor="#1e222d",
            color="#787b86",
            showline=False,
            zeroline=False,
            rangeslider=dict(visible=False),
            type="date",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1e222d",
            color="#787b86",
            showline=False,
            zeroline=False,
            side="right",
            tickformat="$.2f",
        ),
        yaxis2=dict(
            overlaying="y",
            side="left",
            showgrid=False,
            showticklabels=False,
            range=[0, df["volume"].max() * 5],
        ),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2e39",
            bordercolor="#434651",
            font=dict(color="#d1d4dc", family="JetBrains Mono", size=12),
        ),
        xaxis_rangeslider_visible=False,
    )

    return fig


def get_smc_analysis(bot, symbol: str) -> dict:
    """Run full SMC analysis on a symbol and return levels + checklist."""
    if not bot or not bot.data_feed or not bot.smc_engine:
        return {}

    try:
        daily = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_bias, n=50)
        h4 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_structure, n=50)
        h1 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_confirmation, n=50)
        m15 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_entry, n=50)
        m5 = bot.data_feed.get_candles(symbol, bot.config.strategy.tf_precision, n=50)

        if any(df.empty for df in [daily, h4, h1, m15, m5]):
            return {}

        # Get checklist
        checklist = bot.smc_engine.get_checklist(symbol, daily, h4, h1, m15, m5)

        # Get FVGs and OBs from M15
        from strategy.imbalance import IMBDetector
        imb = IMBDetector(
            fvg_min_size=bot.config.strategy.fvg_min_size_pts,
            ob_lookback=bot.config.strategy.ob_lookback,
        )

        bias = checklist.get("bias", "neutral")
        fvgs = imb.find_fvgs(m15, bias) if bias != "neutral" else []
        obs = imb.find_order_blocks(m15, bias) if bias != "neutral" else []

        # Equilibrium
        range_high = h1["high"].tail(20).max() if not h1.empty else 0
        range_low = h1["low"].tail(20).min() if not h1.empty else 0
        eq = (range_high + range_low) / 2 if range_high and range_low else 0

        return {
            "checklist": checklist,
            "fvgs": fvgs[:3],   # Top 3 most recent
            "obs": obs[:3],
            "equilibrium": eq,
            "bias": bias,
            "score": checklist.get("score", 0),
        }

    except Exception as e:
        return {}


def render_terminal(bot, config):
    """Render the full trading terminal."""

    # ── Top search bar ─────────────────────────────────────────────────────
    search_col, tf_col, mode_col = st.columns([3, 2, 1])

    with search_col:
        search = st.text_input(
            "Search",
            placeholder="Search symbol e.g. AAPL, TSLA, NVDA...",
            label_visibility="collapsed",
            key="symbol_search"
        )

    with tf_col:
        timeframe = st.selectbox(
            "Timeframe",
            ["5Min", "15Min", "1Hour", "4Hour", "1Day"],
            index=4,
            label_visibility="collapsed",
        )

    with mode_col:
        show_smc = st.toggle("SMC", value=True)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    # ── Layout: Catalog | Chart | Analysis ─────────────────────────────────
    catalog_col, chart_col, analysis_col = st.columns([1, 3, 1], gap="small")

    # ── CATALOG ────────────────────────────────────────────────────────────
    with catalog_col:
        st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:12px;height:520px;overflow-y:auto;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:10px;">Watchlist</div>', unsafe_allow_html=True)

        # Filter by search
        search_term = search.upper() if search else ""
        selected = st.session_state.get("selected_symbol", "SPY")

        for group, symbols in STOCK_CATALOG.items():
            filtered = [s for s in symbols if search_term in s] if search_term else symbols
            if not filtered:
                continue

            st.markdown(f'<div style="font-size:10px;color:#434651;letter-spacing:1px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin:10px 0 4px;">{group}</div>', unsafe_allow_html=True)

            for sym in filtered:
                is_active = sym == selected
                bg = "background:rgba(41,98,255,0.1);border:1px solid rgba(41,98,255,0.2);" if is_active else "background:transparent;border:1px solid transparent;"
                color = "#2962ff" if is_active else "#b2b5be"

                if st.button(
                    sym,
                    key=f"sym_{sym}",
                    use_container_width=True,
                ):
                    st.session_state["selected_symbol"] = sym
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── CHART ──────────────────────────────────────────────────────────────
    with chart_col:
        symbol = st.session_state.get("selected_symbol", "SPY")

        # If search matches a symbol directly
        if search and search.upper() in ALL_SYMBOLS:
            symbol = search.upper()
            st.session_state["selected_symbol"] = symbol

        # Get data
        tf_days = {"5Min": 7, "15Min": 14, "1Hour": 30, "4Hour": 60, "1Day": 90}
        days = tf_days.get(timeframe, 90)

        if bot and bot.client and bot.client.connected:
            df = get_stock_data(bot.client, symbol, timeframe, days)
            stats = get_quick_stats(df)
            smc_data = get_smc_analysis(bot, symbol) if show_smc else {}
        else:
            df = pd.DataFrame()
            stats = {}
            smc_data = {}

        # Symbol header
        price = stats.get("price", 0)
        change = stats.get("change", 0)
        change_pct = stats.get("change_pct", 0)
        change_color = "#26a69a" if change >= 0 else "#ef5350"
        change_arrow = "▲" if change >= 0 else "▼"

        st.markdown(f"""
        <div style='display:flex;align-items:baseline;gap:16px;margin-bottom:8px;'>
            <span style='font-family:JetBrains Mono,monospace;font-size:22px;font-weight:600;color:#d1d4dc;'>{symbol}</span>
            <span style='font-family:JetBrains Mono,monospace;font-size:20px;font-weight:600;color:#d1d4dc;'>${price:,.2f}</span>
            <span style='font-family:JetBrains Mono,monospace;font-size:14px;color:{change_color};'>{change_arrow} ${abs(change):.2f} ({change_pct:+.2f}%)</span>
            <span style='font-size:11px;color:#434651;font-family:JetBrains Mono,monospace;margin-left:auto;'>{timeframe} · {len(df)} bars</span>
        </div>
        """, unsafe_allow_html=True)

        # Chart
        st.markdown('<div style="background:#131722;border:1px solid #2a2e39;border-radius:6px;padding:8px;">', unsafe_allow_html=True)

        if not df.empty:
            fig = render_candlestick_chart(df.tail(120), symbol, smc_data if show_smc else None)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            if not bot or not bot.client or not bot.client.connected:
                st.markdown("<div style='height:420px;display:flex;align-items:center;justify-content:center;color:#434651;font-family:JetBrains Mono,monospace;font-size:13px;'>Connect API keys to view charts</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='height:420px;display:flex;align-items:center;justify-content:center;color:#434651;font-family:JetBrains Mono,monospace;font-size:13px;'>No data for {symbol}</div>", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Stats bar
        if stats:
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#787b86;'>HIGH &nbsp;</span><span style='color:#26a69a;'>${stats.get('high',0):,.2f}</span></div>", unsafe_allow_html=True)
            with s2:
                st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#787b86;'>LOW &nbsp;</span><span style='color:#ef5350;'>${stats.get('low',0):,.2f}</span></div>", unsafe_allow_html=True)
            with s3:
                vol = stats.get("volume", 0)
                vol_str = f"{vol/1e6:.1f}M" if vol > 1e6 else f"{vol/1e3:.0f}K"
                st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#787b86;'>VOL &nbsp;</span><span style='color:#d1d4dc;'>{vol_str}</span></div>", unsafe_allow_html=True)
            with s4:
                avg_vol = stats.get("avg_volume", 0)
                avg_str = f"{avg_vol/1e6:.1f}M" if avg_vol > 1e6 else f"{avg_vol/1e3:.0f}K"
                st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;'><span style='color:#787b86;'>AVG VOL &nbsp;</span><span style='color:#d1d4dc;'>{avg_str}</span></div>", unsafe_allow_html=True)

    # ── SMC ANALYSIS PANEL ─────────────────────────────────────────────────
    with analysis_col:
        st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:12px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #2a2e39;">SMC Analysis</div>', unsafe_allow_html=True)

        if smc_data and show_smc:
            checklist = smc_data.get("checklist", {})
            bias = smc_data.get("bias", "neutral")
            score = smc_data.get("score", 0)

            # Bias badge
            bias_color = "#26a69a" if bias == "bullish" else "#ef5350" if bias == "bearish" else "#787b86"
            bias_bg = "rgba(38,166,154,0.1)" if bias == "bullish" else "rgba(239,83,80,0.1)" if bias == "bearish" else "rgba(120,123,134,0.1)"
            st.markdown(f"""
            <div style='text-align:center;padding:10px;background:{bias_bg};border:1px solid {bias_color}33;border-radius:4px;margin-bottom:12px;'>
                <div style='font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;'>DAILY BIAS</div>
                <div style='font-size:16px;font-weight:700;color:{bias_color};font-family:JetBrains Mono,monospace;'>{bias.upper()}</div>
            </div>
            """, unsafe_allow_html=True)

            # Score bar
            min_score = config.strategy.confluence_min
            bar_color = "#26a69a" if score >= min_score else "#ffa000"
            bar_pct = int((score / 6) * 100)
            st.markdown(f"""
            <div style='margin-bottom:12px;'>
                <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
                    <span style='font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;'>CONFLUENCE</span>
                    <span style='font-size:11px;font-weight:600;color:{bar_color};font-family:JetBrains Mono,monospace;'>{score}/6</span>
                </div>
                <div style='background:#2a2e39;border-radius:2px;height:3px;'>
                    <div style='background:{bar_color};width:{bar_pct}%;height:3px;border-radius:2px;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Checks
            checks = checklist.get("checks", {})
            check_items = [
                ("Bias", "daily_bias"),
                ("Sweep", "liquidity_sweep"),
                ("BoS", "bos"),
                ("Zone", "price_zone"),
                ("FVG", "fvg"),
                ("OB", "order_block"),
            ]

            for label, key in check_items:
                active = checks.get(key, {}).get("active", False)
                detail = checks.get(key, {}).get("detail", "")
                color = "#26a69a" if active else "#434651"
                dot = "●" if active else "○"
                st.markdown(f"""
                <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #2a2e391a;'>
                    <span style='color:{color};font-size:12px;font-family:JetBrains Mono,monospace;'>{dot} {label}</span>
                    <span style='color:{"#26a69a" if active else "#2a2e39"};font-size:10px;font-family:JetBrains Mono,monospace;'>{"✓" if active else "—"}</span>
                </div>
                """, unsafe_allow_html=True)

            # FVG levels
            fvgs = smc_data.get("fvgs", [])
            if fvgs:
                st.markdown("<div style='margin-top:12px;font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>FVG Zones</div>", unsafe_allow_html=True)
                for fvg in fvgs[:2]:
                    fcolor = "#26a69a" if "bullish" in fvg.get("type","") else "#ef5350"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:{fcolor};padding:3px 0;'>{fvg['bottom']:.2f} – {fvg['top']:.2f}</div>", unsafe_allow_html=True)

            # OB levels
            obs = smc_data.get("obs", [])
            if obs:
                st.markdown("<div style='margin-top:8px;font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Order Blocks</div>", unsafe_allow_html=True)
                for ob in obs[:2]:
                    ocolor = "#2962ff" if "bullish" in ob.get("type","") else "#ff9800"
                    st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:{ocolor};padding:3px 0;'>{ob['bottom']:.2f} – {ob['top']:.2f}</div>", unsafe_allow_html=True)

            # Trade signal
            signal_text = "WAIT"
            signal_color = "#787b86"
            signal_bg = "rgba(120,123,134,0.1)"
            if score >= min_score and bias != "neutral":
                signal_text = "BUY SETUP" if bias == "bullish" else "SELL SETUP"
                signal_color = "#26a69a" if bias == "bullish" else "#ef5350"
                signal_bg = "rgba(38,166,154,0.1)" if bias == "bullish" else "rgba(239,83,80,0.1)"

            st.markdown(f"""
            <div style='margin-top:14px;padding:10px;background:{signal_bg};border:1px solid {signal_color}33;border-radius:4px;text-align:center;'>
                <div style='font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;'>SIGNAL</div>
                <div style='font-size:14px;font-weight:700;color:{signal_color};font-family:JetBrains Mono,monospace;'>{signal_text}</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div style='text-align:center;padding:40px 0;color:#434651;font-size:12px;font-family:JetBrains Mono,monospace;'>
                Connect API &<br>enable SMC toggle<br>to see analysis
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)