"""
SMCBot — Categorized Log Viewer
Filters logs by Error, Trade, System categories.
"""

import streamlit as st
from config.logger import get_recent_logs


def render_log_viewer():
    """Render the full log viewer with category filters."""

    st.markdown("### System Logs")

    # Controls row
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])

    with c1:
        search_term = st.text_input("Search logs", placeholder="Filter by keyword...", label_visibility="collapsed")

    with c2:
        show_errors = st.toggle("Errors", value=True)

    with c3:
        show_trades = st.toggle("Trades", value=True)

    with c4:
        show_system = st.toggle("System", value=True)

    with c5:
        if st.button("Clear", use_container_width=True):
            from config.logger import log_buffer
            log_buffer.clear()
            st.success("Cleared.")

    logs = get_recent_logs(200)

    # Categorize logs
    def categorize(log):
        msg = log.get("msg", "").lower()
        t = log.get("type", "neu")

        if t == "err" or "error" in msg or "failed" in msg or "exception" in msg:
            return "error"
        elif any(word in msg for word in ["order", "trade", "buy", "sell", "position", "closed", "opened", "signal", "pnl", "sl:", "tp:"]):
            return "trade"
        else:
            return "system"

    # Filter
    filtered = []
    for log in logs:
        cat = categorize(log)
        if cat == "error" and not show_errors:
            continue
        if cat == "trade" and not show_trades:
            continue
        if cat == "system" and not show_system:
            continue
        if search_term and search_term.lower() not in log.get("msg", "").lower():
            continue
        filtered.append((log, cat))

    # Stats row
    total = len(logs)
    errors = sum(1 for l in logs if categorize(l) == "error")
    trades = sum(1 for l in logs if categorize(l) == "trade")
    system = sum(1 for l in logs if categorize(l) == "system")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f'<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;">TOTAL</div><div style="font-size:18px;font-weight:600;color:#d1d4dc;font-family:JetBrains Mono,monospace;">{total}</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div style="background:#1e222d;border:1px solid rgba(239,83,80,0.3);border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;">ERRORS</div><div style="font-size:18px;font-weight:600;color:#ef5350;font-family:JetBrains Mono,monospace;">{errors}</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div style="background:#1e222d;border:1px solid rgba(41,98,255,0.3);border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;">TRADES</div><div style="font-size:18px;font-weight:600;color:#2962ff;font-family:JetBrains Mono,monospace;">{trades}</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div style="background:#1e222d;border:1px solid rgba(120,123,134,0.3);border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#787b86;font-family:JetBrains Mono,monospace;">SYSTEM</div><div style="font-size:18px;font-weight:600;color:#787b86;font-family:JetBrains Mono,monospace;">{system}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Log display
    cat_colors = {
        "error": "#ef5350",
        "trade": "#2962ff",
        "system": "#787b86",
    }
    cat_labels = {
        "error": "ERR",
        "trade": "TRD",
        "system": "SYS",
    }
    type_colors = {
        "ok": "#26a69a",
        "warn": "#ffa000",
        "err": "#ef5350",
        "neu": "#787b86",
    }

    if filtered:
        lines = []
        for log, cat in reversed(filtered):
            msg_color = type_colors.get(log.get("type", "neu"), "#787b86")
            cat_color = cat_colors.get(cat, "#787b86")
            cat_label = cat_labels.get(cat, "SYS")
            t = log["time"]
            m = log["msg"]
            lines.append(
                f"<div style='display:flex;gap:10px;padding:2px 0;align-items:baseline;'>"
                f"<span style='color:#434651;min-width:65px;font-family:JetBrains Mono,monospace;font-size:11px;'>{t}</span>"
                f"<span style='color:{cat_color};min-width:32px;font-family:JetBrains Mono,monospace;font-size:10px;font-weight:600;'>{cat_label}</span>"
                f"<span style='color:{msg_color};font-family:JetBrains Mono,monospace;font-size:11px;'>{m}</span>"
                f"</div>"
            )
        log_html = "".join(lines)
        st.markdown(
            f'<div style="background:#131722;border:1px solid #2a2e39;border-radius:6px;padding:12px;height:360px;overflow-y:auto;font-size:11px;line-height:1.8;">{log_html}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:#131722;border:1px solid #2a2e39;border-radius:6px;padding:12px;height:360px;display:flex;align-items:center;justify-content:center;color:#434651;font-family:JetBrains Mono,monospace;font-size:13px;">No logs match the current filters.</div>',
            unsafe_allow_html=True
        )