"""
SMCBot — Backtest Page v2
With progress bar, Buy & Hold comparison, CSV export.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io
from datetime import datetime


def render_backtest_page(bot, config):
    """Render the full backtest page."""
    st.markdown("### Backtester")
    st.markdown("<p style='font-size:13px;color:#787b86;'>Test the SMC strategy against historical data before going live.</p>", unsafe_allow_html=True)

    if not bot or not bot.client or not bot.client.connected:
        st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:24px;text-align:center;color:#787b86;font-size:13px;">Connect your API keys in Setup to run backtests.</div>', unsafe_allow_html=True)
        return

    # ── Config ──────────────────────────────────────────────────────────────
    st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:16px;margin-bottom:16px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #2a2e39;">Configuration</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        symbol = st.selectbox("Symbol", options=config.markets.symbols + ["SPY","QQQ","AAPL","TSLA","NVDA","MSFT"], index=0)
    with col2:
        lookback = st.selectbox("Period", ["1 Month","3 Months","6 Months","1 Year"], index=2)
    with col3:
        init_balance = st.number_input("Balance ($)", value=100000, min_value=1000, step=1000)
    with col4:
        min_conf = st.number_input("Min Confluence", value=float(config.strategy.confluence_min), min_value=1.0, max_value=6.0, step=1.0)
    with col5:
        compare_bh = st.toggle("vs Buy & Hold", value=True)

    run_col, _ = st.columns([1, 4])
    with run_col:
        run_clicked = st.button("▶ Run Backtest", use_container_width=True, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Run ─────────────────────────────────────────────────────────────────
    if run_clicked:
        lookback_days = {"1 Month":30,"3 Months":90,"6 Months":180,"1 Year":365}[lookback]

        # Progress bar
        progress = st.progress(0, text="Loading market data...")
        status = st.empty()

        try:
            status.markdown('<div style="font-size:12px;color:#787b86;font-family:JetBrains Mono,monospace;">📡 Fetching historical data...</div>', unsafe_allow_html=True)
            progress.progress(10, text="Fetching data...")

            daily = bot.client.get_bars(symbol, "1Day", lookback_days=lookback_days)
            progress.progress(25, text="Loading 4H data...")
            h4 = bot.client.get_bars(symbol, "4Hour", lookback_days=lookback_days)
            progress.progress(40, text="Loading 1H data...")
            h1 = bot.client.get_bars(symbol, "1Hour", lookback_days=lookback_days)
            progress.progress(55, text="Loading 15M data...")
            m15 = bot.client.get_bars(symbol, "15Min", lookback_days=lookback_days)
            progress.progress(70, text="Running SMC strategy...")

            if any(df.empty for df in [daily, h4, h1, m15]):
                st.error("Failed to load data.")
                progress.empty()
                status.empty()
                return

            status.markdown(f'<div style="font-size:12px;color:#26a69a;font-family:JetBrains Mono,monospace;">✓ Loaded {len(m15)} M15 bars. Running strategy on {symbol}...</div>', unsafe_allow_html=True)

            from backtesting.backtester import Backtester
            from config.config import RiskConfig

            bt_config = config.strategy
            bt_config.confluence_min = int(min_conf)
            backtester = Backtester(bt_config, RiskConfig(), initial_balance=init_balance)

            progress.progress(80, text="Analyzing signals...")
            result = backtester.run(symbol, daily, h4, h1, m15)

            progress.progress(95, text="Calculating metrics...")

            # Buy & Hold comparison
            bh_return = 0.0
            bh_equity = []
            if compare_bh and not daily.empty:
                bh_start = daily["close"].iloc[0]
                bh_end = daily["close"].iloc[-1]
                bh_return = ((bh_end - bh_start) / bh_start) * 100
                bh_equity = [init_balance * (p / bh_start) for p in daily["close"]]

            progress.progress(100, text="Done!")
            progress.empty()
            status.empty()

            st.session_state["bt_result"] = result
            st.session_state["bt_bh_return"] = bh_return
            st.session_state["bt_bh_equity"] = bh_equity
            st.session_state["bt_symbol"] = symbol

        except Exception as e:
            st.error(f"Backtest error: {e}")
            progress.empty()
            status.empty()
            return

    # ── Results ─────────────────────────────────────────────────────────────
    if "bt_result" in st.session_state:
        result = st.session_state["bt_result"]
        bh_return = st.session_state.get("bt_bh_return", 0)
        bh_equity = st.session_state.get("bt_bh_equity", [])
        bt_symbol = st.session_state.get("bt_symbol", symbol)

        if result.total_trades == 0:
            st.markdown('<div style="background:#1e222d;border:1px solid #ffa00033;border-radius:6px;padding:24px;text-align:center;color:#ffa000;font-size:13px;">No trades found. Try lowering confluence minimum or extending lookback.</div>', unsafe_allow_html=True)
            return

        # Alpha vs Buy & Hold
        alpha = result.total_pnl_pct - bh_return
        alpha_color = "#26a69a" if alpha >= 0 else "#ef5350"

        # Metrics
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        with m1:
            st.metric("Trades", result.total_trades)
        with m2:
            st.metric("Win Rate", f"{result.win_rate:.1f}%", delta=f"{result.wins}W/{result.losses}L")
        with m3:
            st.metric("Net P&L", f"${result.total_pnl:+,.2f}", delta=f"{result.total_pnl_pct:+.1f}%")
        with m4:
            st.metric("Profit Factor", f"{result.profit_factor:.2f}")
        with m5:
            st.metric("Max Drawdown", f"-{result.max_drawdown_pct:.1f}%")
        with m6:
            st.metric("Sharpe", f"{result.sharpe_ratio:.2f}")
        with m7:
            st.metric("Alpha vs B&H", f"{alpha:+.1f}%", delta=f"B&H: {bh_return:+.1f}%")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # Charts
        chart1, chart2 = st.columns([2, 1], gap="medium")

        with chart1:
            st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:16px;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:12px;">Equity Curve vs Buy & Hold</div>', unsafe_allow_html=True)

            eq = result.equity_curve
            fig = go.Figure()

            # Bot equity
            bot_color = "#26a69a" if result.total_pnl >= 0 else "#ef5350"
            bot_fill = "rgba(38,166,154,0.05)" if result.total_pnl >= 0 else "rgba(239,83,80,0.05)"
            fig.add_trace(go.Scatter(
                y=eq, mode="lines",
                name="SMCBot",
                line=dict(color=bot_color, width=2),
                fill="tozeroy", fillcolor=bot_fill,
                hovertemplate="SMCBot: $%{y:,.2f}<extra></extra>",
            ))

            # Buy & Hold overlay
            if bh_equity and compare_bh:
                # Normalize to same length as equity curve
                import numpy as np
                if len(bh_equity) > 1:
                    bh_resampled = np.interp(
                        np.linspace(0, 1, len(eq)),
                        np.linspace(0, 1, len(bh_equity)),
                        bh_equity
                    )
                    fig.add_trace(go.Scatter(
                        y=bh_resampled, mode="lines",
                        name="Buy & Hold",
                        line=dict(color="#787b86", width=1.5, dash="dash"),
                        hovertemplate="Buy & Hold: $%{y:,.2f}<extra></extra>",
                    ))

            # Initial balance line
            fig.add_hline(y=result.initial_balance, line_dash="dot", line_color="#434651", line_width=1)

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=8, b=0), height=240,
                xaxis=dict(showgrid=False, color="#434651", showline=False, zeroline=False, title="Trade #"),
                yaxis=dict(showgrid=True, gridcolor="#2a2e39", color="#434651", showline=False, zeroline=False, tickformat="$,.0f"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#787b86", size=11)),
                hoverlabel=dict(bgcolor="#2a2e39", bordercolor="#434651", font=dict(color="#d1d4dc", family="JetBrains Mono")),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with chart2:
            st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:16px;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:12px;">Trade P&L Distribution</div>', unsafe_allow_html=True)

            if result.trades:
                pnls = [t.pnl for t in result.trades]
                colors = ["#26a69a" if p > 0 else "#ef5350" for p in pnls]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    y=pnls, marker_color=colors,
                    hovertemplate="$%{y:,.2f}<extra></extra>",
                ))
                fig2.add_hline(y=0, line_color="#434651", line_width=1)
                fig2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=8, b=0), height=240,
                    xaxis=dict(showgrid=False, color="#434651", showline=False),
                    yaxis=dict(showgrid=True, gridcolor="#2a2e39", color="#434651", showline=False, tickformat="$,.0f"),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Stats + Trade log
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        s1, s2 = st.columns(2, gap="medium")

        with s1:
            st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:16px;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #2a2e39;">Performance Summary</div>', unsafe_allow_html=True)

            rows = [
                ("Period", f"{result.start_date} → {result.end_date}"),
                ("Starting Balance", f"${result.initial_balance:,.2f}"),
                ("Final Balance", f"${result.final_balance:,.2f}"),
                ("Net P&L", f"${result.total_pnl:+,.2f} ({result.total_pnl_pct:+.1f}%)"),
                ("Buy & Hold Return", f"{bh_return:+.1f}%"),
                ("Alpha Generated", f"{alpha:+.1f}%"),
                ("Avg Win", f"${result.avg_win:,.2f}"),
                ("Avg Loss", f"-${result.avg_loss:,.2f}"),
                ("Avg R:R", f"{result.avg_rr:.2f}"),
                ("Max Drawdown", f"-${result.max_drawdown:,.2f} (-{result.max_drawdown_pct:.1f}%)"),
                ("Sharpe Ratio", f"{result.sharpe_ratio:.2f}"),
            ]

            for label, value in rows:
                val_color = "#d1d4dc"
                if label == "Alpha Generated":
                    val_color = "#26a69a" if alpha >= 0 else "#ef5350"
                elif label == "Net P&L":
                    val_color = "#26a69a" if result.total_pnl >= 0 else "#ef5350"

                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #2a2e39;font-size:13px;'>"
                    f"<span style='color:#787b86;'>{label}</span>"
                    f"<span style='color:{val_color};font-family:JetBrains Mono,monospace;font-size:12px;'>{value}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with s2:
            st.markdown('<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:16px;">', unsafe_allow_html=True)

            # Export buttons
            export1, export2 = st.columns(2)
            with export1:
                if result.trades:
                    trade_data = [{
                        "Symbol": t.symbol,
                        "Side": t.side.upper(),
                        "Entry": t.entry_price,
                        "Exit": t.exit_price,
                        "SL": t.stop_loss,
                        "TP": t.take_profit_1,
                        "PnL ($)": round(t.pnl, 2),
                        "PnL (%)": round(t.pnl_pct, 2),
                        "Result": t.result.upper(),
                        "Exit Reason": t.exit_reason.upper(),
                        "Bars Held": t.bars_held,
                    } for t in result.trades]
                    df_export = pd.DataFrame(trade_data)
                    csv = df_export.to_csv(index=False)
                    st.download_button(
                        "📥 Export Trades CSV",
                        data=csv,
                        file_name=f"smcbot_backtest_{bt_symbol}_{result.start_date}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            with export2:
                # Summary export
                summary = {
                    "Metric": ["Symbol","Period","Total Trades","Win Rate","Net P&L","P&L %","Buy & Hold %","Alpha %","Profit Factor","Max Drawdown %","Sharpe Ratio","Avg Win","Avg Loss","Avg R:R"],
                    "Value": [
                        bt_symbol,
                        f"{result.start_date} to {result.end_date}",
                        result.total_trades,
                        f"{result.win_rate:.1f}%",
                        f"${result.total_pnl:+,.2f}",
                        f"{result.total_pnl_pct:+.1f}%",
                        f"{bh_return:+.1f}%",
                        f"{alpha:+.1f}%",
                        f"{result.profit_factor:.2f}",
                        f"-{result.max_drawdown_pct:.1f}%",
                        f"{result.sharpe_ratio:.2f}",
                        f"${result.avg_win:,.2f}",
                        f"${result.avg_loss:,.2f}",
                        f"{result.avg_rr:.2f}",
                    ]
                }
                df_summary = pd.DataFrame(summary)
                csv_summary = df_summary.to_csv(index=False)
                st.download_button(
                    "📥 Export Summary CSV",
                    data=csv_summary,
                    file_name=f"smcbot_summary_{bt_symbol}_{result.start_date}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            st.markdown('<div style="font-size:11px;color:#787b86;text-transform:uppercase;letter-spacing:1px;font-family:JetBrains Mono,monospace;margin:12px 0 8px;padding-top:8px;border-top:1px solid #2a2e39;">Trade Log (Last 20)</div>', unsafe_allow_html=True)

            if result.trades:
                trade_rows = []
                for t in result.trades[-20:]:
                    trade_rows.append({
                        "Side": t.side.upper(),
                        "Entry": f"${t.entry_price:.2f}",
                        "Exit": f"${t.exit_price:.2f}",
                        "P&L": f"${t.pnl:+.2f}",
                        "Reason": t.exit_reason.upper(),
                    })
                df_trades = pd.DataFrame(trade_rows)
                st.dataframe(df_trades, use_container_width=True, height=260, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)