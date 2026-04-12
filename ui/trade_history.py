"""
SMCBot — Trade History Page
Full trade log with stats, streaks, and per-trade details.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime


def render_trade_history(bot):
    """Render the full trade history page."""
    st.markdown("### Trade History")

    if not bot or not bot.risk_manager:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:24px;text-align:center;color:#484f58;font-size:13px;font-family:JetBrains Mono,monospace;">Connect API and start trading to see history.</div>', unsafe_allow_html=True)
        return

    trades = bot.risk_manager.trade_history

    if not trades:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:24px;text-align:center;color:#484f58;font-size:13px;font-family:JetBrains Mono,monospace;">No trades yet. Start the bot to begin trading.</div>', unsafe_allow_html=True)
        return

    # ── Summary Stats ──────────────────────────────────────────────────────
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    total_profit = sum(t.get("pnl", 0) for t in wins)
    total_loss = abs(sum(t.get("pnl", 0) for t in losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    best_trade = max(trades, key=lambda t: t.get("pnl", 0))
    worst_trade = min(trades, key=lambda t: t.get("pnl", 0))
    avg_win = total_profit / len(wins) if wins else 0
    avg_loss = total_loss / len(losses) if losses else 0

    # Current streak
    streak = 0
    streak_type = ""
    if trades:
        last_result = "win" if trades[-1].get("pnl", 0) > 0 else "loss"
        streak_type = last_result
        for t in reversed(trades):
            r = "win" if t.get("pnl", 0) > 0 else "loss"
            if r == last_result:
                streak += 1
            else:
                break

    # Stats row
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("Total Trades", len(trades))
    with m2: st.metric("Win Rate", f"{win_rate:.1f}%", delta=f"{len(wins)}W / {len(losses)}L")
    with m3:
        pnl_delta = f"+{total_pnl/abs(total_pnl)*100:.1f}%" if total_pnl != 0 else None
        st.metric("Total P&L", f"${total_pnl:+,.2f}")
    with m4: st.metric("Profit Factor", f"{profit_factor:.2f}")
    with m5: st.metric("Best Trade", f"${best_trade.get('pnl',0):+,.2f}")
    with m6:
        streak_color = "🟢" if streak_type == "win" else "🔴"
        st.metric("Current Streak", f"{streak_color} {streak} {streak_type.upper()}S")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:1.5px;font-family:JetBrains Mono,monospace;margin-bottom:12px;">Cumulative P&L</div>', unsafe_allow_html=True)
        cumulative = []
        running = 0
        for t in trades:
            running += t.get("pnl", 0)
            cumulative.append(running)
        fig = go.Figure()
        color = "#3fb950" if cumulative[-1] >= 0 else "#f85149"
        fig.add_trace(go.Scatter(y=cumulative, mode="lines", line=dict(color=color, width=2), fill="tozeroy", fillcolor=f"rgba{'(63,185,80' if color == '#3fb950' else '(248,81,73'},0.05)"))
        fig.add_hline(y=0, line_color="#30363d", line_width=1)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117", margin=dict(l=0,r=0,t=0,b=0), height=160, xaxis=dict(showgrid=False, color="#484f58", showline=False, zeroline=False), yaxis=dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, zeroline=False, tickformat="$,.0f"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:1.5px;font-family:JetBrains Mono,monospace;margin-bottom:12px;">Win / Loss Distribution</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        pnls = [t.get("pnl", 0) for t in trades]
        colors = ["#3fb950" if p > 0 else "#f85149" for p in pnls]
        fig2.add_trace(go.Bar(y=pnls, marker_color=colors, hovertemplate="$%{y:,.2f}<extra></extra>"))
        fig2.add_hline(y=0, line_color="#30363d", line_width=1)
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117", margin=dict(l=0,r=0,t=0,b=0), height=160, xaxis=dict(showgrid=False, color="#484f58", showline=False), yaxis=dict(showgrid=True, gridcolor="#161b22", color="#484f58", showline=False, tickformat="$,.0f"), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:1.5px;font-family:JetBrains Mono,monospace;margin-bottom:12px;">Performance Breakdown</div>', unsafe_allow_html=True)

        rows = [
            ("Avg Win", f"${avg_win:,.2f}", "#3fb950"),
            ("Avg Loss", f"-${avg_loss:,.2f}", "#f85149"),
            ("Best Trade", f"${best_trade.get('pnl',0):+,.2f}", "#3fb950"),
            ("Worst Trade", f"${worst_trade.get('pnl',0):+,.2f}", "#f85149"),
            ("Total Profit", f"${total_profit:,.2f}", "#3fb950"),
            ("Total Loss", f"-${total_loss:,.2f}", "#f85149"),
        ]
        for label, value, color in rows:
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #21262d;'><span style='color:#484f58;font-size:12px;'>{label}</span><span style='color:{color};font-family:JetBrains Mono,monospace;font-size:12px;'>{value}</span></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Symbol Breakdown ───────────────────────────────────────────────────
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    sym_col, filter_col = st.columns([3, 1])
    with filter_col:
        filter_result = st.selectbox("Filter", ["All", "Wins Only", "Losses Only"], label_visibility="collapsed")
        sort_by = st.selectbox("Sort", ["Newest First", "Biggest Win", "Biggest Loss"], label_visibility="collapsed")

    # Filter trades
    if filter_result == "Wins Only":
        filtered = [t for t in trades if t.get("pnl", 0) > 0]
    elif filter_result == "Losses Only":
        filtered = [t for t in trades if t.get("pnl", 0) <= 0]
    else:
        filtered = trades

    if sort_by == "Biggest Win":
        filtered = sorted(filtered, key=lambda t: t.get("pnl", 0), reverse=True)
    elif sort_by == "Biggest Loss":
        filtered = sorted(filtered, key=lambda t: t.get("pnl", 0))
    else:
        filtered = list(reversed(filtered))

    # Trade table
    if filtered:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:1.5px;font-family:JetBrains Mono,monospace;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #21262d;">Trade Log</div>', unsafe_allow_html=True)

        # Header
        st.markdown("""
        <div style='display:grid;grid-template-columns:80px 60px 90px 90px 90px 90px 90px 80px;gap:8px;padding:6px 0;border-bottom:1px solid #21262d;'>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>SYMBOL</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>SIDE</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>ENTRY</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>SL</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>TP1</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>TP2</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>P&L</span>
            <span style='color:#484f58;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:1px;'>SCORE</span>
        </div>
        """, unsafe_allow_html=True)

        for t in filtered[:50]:
            pnl = t.get("pnl", 0)
            pnl_color = "#3fb950" if pnl >= 0 else "#f85149"
            side_color = "#3fb950" if t.get("side") == "buy" else "#f85149"
            score = t.get("confluence", t.get("confluence_score", 0))
            bar = "█" * score + "░" * (6 - score)

            st.markdown(f"""
            <div style='display:grid;grid-template-columns:80px 60px 90px 90px 90px 90px 90px 80px;gap:8px;padding:8px 0;border-bottom:1px solid #21262d0d;font-family:JetBrains Mono,monospace;font-size:12px;'>
                <span style='color:#e6edf3;font-weight:600;'>{t.get('symbol','—')}</span>
                <span style='color:{side_color};'>{t.get('side','—').upper()}</span>
                <span style='color:#8b949e;'>${t.get('entry',0):.2f}</span>
                <span style='color:#f85149;'>${t.get('sl',0):.2f}</span>
                <span style='color:#3fb950;'>${t.get('tp1',0):.2f}</span>
                <span style='color:#58a6ff;'>${t.get('tp2',0):.2f}</span>
                <span style='color:{pnl_color};font-weight:600;'>${pnl:+.2f}</span>
                <span style='color:#484f58;font-size:10px;'>{bar}</span>
            </div>
            """, unsafe_allow_html=True)

        # Export
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        export_data = [{
            "Symbol": t.get("symbol",""),
            "Side": t.get("side","").upper(),
            "Entry": t.get("entry", 0),
            "SL": t.get("sl", 0),
            "TP1": t.get("tp1", 0),
            "TP2": t.get("tp2", 0),
            "P&L ($)": round(t.get("pnl", 0), 2),
            "Confluence": t.get("confluence", 0),
        } for t in filtered]

        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False)
        st.download_button(
            "📥 Export Trade History CSV",
            data=csv,
            file_name=f"janustech_trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
        st.markdown('</div>', unsafe_allow_html=True)