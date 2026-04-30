"""Reusable render functions for each dashboard section."""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone
from parser import SessionData, format_elapsed, format_span


# Round accent colours
ROUND_COLORS = ["#7F77DD", "#378ADD", "#1D9E75", "#EF9F27", "#DD77A0"]
ROUND_BAR_COLORS = ["#1D9E75", "#378ADD", "#1D9E75", "#EF9F27"]
ROUND_BAR_FINAL_COLORS = ["#085041", "#0C447C", "#085041", "#7A5000"]


def _fmt(n):
    """Format number with commas, or N/A."""
    if n is None or n == 0:
        return "N/A"
    return f"{n:,}"


def _fmt_or_zero(n):
    """Format number with commas, zero shows as 0."""
    if n is None:
        return "N/A"
    return f"{n:,}"


def _round_color(idx):
    return ROUND_COLORS[idx % len(ROUND_COLORS)]


def _bar_color(idx):
    return ROUND_BAR_COLORS[idx % len(ROUND_BAR_COLORS)]


def _bar_final_color(idx):
    return ROUND_BAR_FINAL_COLORS[idx % len(ROUND_BAR_FINAL_COLORS)]


def render_session_header(session: SessionData):
    """Section 2 — Session Header Card."""
    dt = datetime.fromtimestamp(session.creation_date / 1000, tz=timezone.utc) if session.creation_date else None
    date_str = dt.strftime("%B %d, %Y") if dt else "Unknown"

    num_rounds = len(session.requests)
    span_str = format_span(session.span_ms)
    ext_str = f"{session.extension_name} v{session.extension_version}" if session.extension_version else session.extension_name

    html = f"""
    <div class="session-header-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <p class="model-name" style="display: inline;">{session.model_name}</p>
                <span class="mode-badge">{session.mode} mode</span>
                <p class="session-id">{session.session_id}</p>
            </div>
            <div>
                <p class="date-text">{date_str}</p>
                <p class="account-text">account: {session.account_label} · multiplier: {session.multiplier}</p>
            </div>
        </div>
        <div class="divider"></div>
        <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; text-align: center;">
            <div>
                <p class="stat-value">{_fmt(session.max_input_tokens)}</p>
                <p class="stat-label">max input tokens</p>
            </div>
            <div>
                <p class="stat-value">{_fmt(session.max_output_tokens)}</p>
                <p class="stat-label">max output tokens</p>
            </div>
            <div>
                <p class="stat-value">{num_rounds}</p>
                <p class="stat-label">rounds</p>
            </div>
            <div>
                <p class="stat-value">{_fmt_or_zero(session.total_lines)}</p>
                <p class="stat-label">JSONL lines</p>
            </div>
            <div>
                <p class="stat-value">{span_str}</p>
                <p class="stat-label">session span</p>
            </div>
            <div>
                <p class="stat-value" style="font-size: 14px; margin-top: 6px;">{ext_str}</p>
                <p class="stat-label">extension</p>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_timeline(session: SessionData):
    """Section 3 — Session Timeline."""
    st.markdown(
        f'<p class="section-heading">SESSION TIMELINE — ALL {session.total_lines} LINES SUMMARISED</p>',
        unsafe_allow_html=True,
    )

    for event in session.timeline:
        html = f"""
        <div class="timeline-container">
            <div class="timeline-line"></div>
            <div class="timeline-dot" style="border-color: {event.dot_color};"></div>
            <div class="timeline-card" style="border-left-color: {event.dot_color};">
                <p class="timeline-title">{event.title}</p>
                <p class="timeline-subtitle">{event.subtitle}</p>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def render_round_cards(session: SessionData):
    """Section 4 — Round Cards side by side."""
    st.markdown('<p class="section-heading">ROUND DETAILS</p>', unsafe_allow_html=True)

    num_rounds = len(session.requests)
    if num_rounds == 0:
        st.info("No requests found in this session.")
        return

    cols = st.columns(min(num_rounds, 3))

    for i, rd in enumerate(session.requests):
        col = cols[i % len(cols)]
        color = _round_color(i)
        bar_col = _bar_color(i)
        bar_final = _bar_final_color(i)
        round_num = i + 1

        prompt_trunc = rd.prompt_text[:60] + ("..." if len(rd.prompt_text) > 60 else "") if rd.prompt_text else "(no prompt)"
        total_tokens = rd.prompt_tokens + rd.completion_tokens
        elapsed_str = format_elapsed(rd.total_elapsed_ms)
        short_id = rd.request_id[:8] if rd.request_id else "unknown"

        t_offset = (rd.timestamp - session.creation_date) / 60000 if session.creation_date and rd.timestamp else 0

        # Build tool chips HTML
        tool_chips_html = ""
        if rd.tool_names:
            chips = "".join(f'<span class="tool-chip">{name}</span>' for name in rd.tool_names)
            tool_chips_html = f'<div style="margin-top: 10px;">{chips}</div>'

        # Context note for R2+
        context_note_html = ""
        if i > 0 and rd.prompt_tokens > 0:
            prev_rd = session.requests[i - 1]
            if prev_rd.prompt_tokens > 0:
                delta = rd.prompt_tokens - prev_rd.prompt_tokens
                if delta > 0:
                    context_note_html = f"""
                    <div class="context-note">
                        Context grew by +{delta:,} prompt tokens from R{i} — full R{i} history carried forward
                    </div>
                    """

        html_top = f"""
        <div class="round-card">
            <div style="margin-bottom: 14px;">
                <span class="round-badge" style="background-color: {color};">Round {round_num}</span>
                <span class="round-prompt">{prompt_trunc}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
                <div>
                    <p class="round-stat-value">{_fmt(rd.prompt_tokens)}</p>
                    <p class="round-stat-label">prompt tokens</p>
                </div>
                <div>
                    <p class="round-stat-value">{_fmt_or_zero(rd.completion_tokens)}</p>
                    <p class="round-stat-label">completion tokens</p>
                </div>
                <div>
                    <p class="round-stat-value">{_fmt_or_zero(total_tokens)}</p>
                    <p class="round-stat-label">total tokens</p>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
                <div>
                    <p class="round-stat-value">{_fmt(rd.output_tokens_result)}</p>
                    <p class="round-stat-label">outputTokens (result)</p>
                </div>
                <div>
                    <p class="round-stat-value">{rd.tool_call_rounds_count}</p>
                    <p class="round-stat-label">tool call rounds</p>
                </div>
                <div>
                    <p class="round-stat-value">{elapsed_str}</p>
                    <p class="round-stat-label">elapsed</p>
                </div>
            </div>
            <p class="round-meta">request_{short_id}  ·  T+{t_offset:.1f}min  ·  result: line {rd.result_line}</p>
            {tool_chips_html}
        </div>
        """
        with col:
            st.markdown(html_top, unsafe_allow_html=True)

            # Render each progress bar individually to avoid deep nesting issues
            if rd.completion_token_history:
                max_val = max(v for _, v in rd.completion_token_history) or 1
                for j, (ln, val) in enumerate(rd.completion_token_history):
                    is_final = j == len(rd.completion_token_history) - 1
                    fill_color = bar_final if is_final else bar_col
                    pct = (val / max_val) * 100
                    st.markdown(
                        f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
                        f'<span style="font-size:11px;font-family:Consolas,Monaco,monospace;color:#888;min-width:36px;text-align:right;margin-right:8px;">L{ln}</span>'
                        f'<div style="flex:1;background-color:#1a1a1a;border-radius:3px;height:8px;overflow:hidden;">'
                        f'<div style="height:100%;border-radius:3px;width:{pct}%;background-color:{fill_color};"></div>'
                        f'</div>'
                        f'<span style="font-size:11px;color:#e8e6de;min-width:60px;text-align:right;margin-left:8px;">{val:,}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            if context_note_html:
                st.markdown(context_note_html, unsafe_allow_html=True)


def render_token_chart(session: SessionData):
    """Section 5 — Token Breakdown Comparison Chart."""
    st.markdown('<p class="section-heading">TOKEN BREAKDOWN COMPARISON</p>', unsafe_allow_html=True)

    round_labels = [f"Round {i + 1}" for i in range(len(session.requests))]
    prompt_tokens = [rd.prompt_tokens for rd in session.requests]
    completion_tokens = [rd.completion_tokens for rd in session.requests]
    output_tokens = [rd.output_tokens_result for rd in session.requests]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Prompt tokens",
        x=round_labels, y=prompt_tokens,
        marker_color="#7F77DD",
        hovertemplate="%{x}<br>Prompt tokens: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Completion tokens",
        x=round_labels, y=completion_tokens,
        marker_color="#1D9E75",
        hovertemplate="%{x}<br>Completion tokens: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="outputTokens (result record)",
        x=round_labels, y=output_tokens,
        marker_color="#EF9F27",
        hovertemplate="%{x}<br>outputTokens (result): %{y:,}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1a1a1a",
        font=dict(color="#e8e6de", size=12),
        height=280,
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        yaxis=dict(
            gridcolor="#333",
            gridwidth=0.5,
            tickformat=",.0f",
        ),
        xaxis=dict(
            showgrid=False,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_output_tokens_explainer(session: SessionData):
    """Section 6 — What Role Does outputTokens Play?"""
    st.markdown('<p class="section-heading">WHAT ROLE DOES OUTPUTTOKENS PLAY?</p>', unsafe_allow_html=True)

    multiplier_text = f"{session.model_name} carries a {session.multiplier} multiplier"

    cols = st.columns(3)
    boxes = [
        ("Billing event anchor",
         f"Copilot uses this to log a billing-ready event. {multiplier_text}, so these tokens cost {session.multiplier} more than base. It captures the output of the call that 'closed' the result."),
        ("Snapshot in time",
         "The result record is written mid-stream. For heavy agent rounds it captures only the last batch after all tool rounds finish. For lighter rounds it may capture an early checkpoint before generation ends."),
        ("Not the authoritative total",
         "Always use the final completionTokens streaming value for the true output count. outputTokens will be lower — sometimes dramatically lower — in agent-mode sessions with many tool rounds."),
    ]
    for col, (title, body) in zip(cols, boxes):
        with col:
            st.markdown(f"""
            <div class="info-box">
                <p class="info-box-title">{title}</p>
                <p class="info-box-body">{body}</p>
            </div>
            """, unsafe_allow_html=True)

    # Summary row using st.columns instead of nested HTML
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    num_rounds = len(session.requests)
    total_tool_rounds = sum(rd.tool_call_rounds_count for rd in session.requests)
    total_prompt = sum(rd.prompt_tokens for rd in session.requests)
    total_completion = sum(rd.completion_tokens for rd in session.requests)
    grand_total = total_prompt + total_completion

    summary_cols = st.columns(num_rounds + 1)

    for i, rd in enumerate(session.requests):
        if rd.completion_token_history and len(rd.completion_token_history) >= 2:
            prev_val = rd.completion_token_history[-2][1]
            sub_label = f"= {rd.completion_tokens:,} − {prev_val:,} (last batch only)"
        else:
            sub_label = ""

        with summary_cols[i]:
            st.markdown(f"""
            <div class="card" style="text-align: center; padding: 16px;">
                <p style="font-size: 32px; font-weight: 700; color: #e8e6de; margin: 0;">{_fmt_or_zero(rd.output_tokens_result)}</p>
                <p style="font-size: 12px; color: #888; margin: 4px 0 0 0;">R{i + 1} outputTokens</p>
                <p style="font-size: 11px; color: #666; margin: 2px 0 0 0;">{sub_label}</p>
            </div>
            """, unsafe_allow_html=True)

    with summary_cols[-1]:
        st.markdown(f"""
        <div class="card" style="padding: 16px;">
            <p style="font-size: 13px; color: #aaa; line-height: 1.6; margin: 0;">
                <strong style="color: #e8e6de;">Session total (true counts):</strong><br>
                Prompt: {total_prompt:,} tokens in<br>
                Completion: {total_completion:,} tokens out<br>
                Grand total: {grand_total:,} tokens across {num_rounds} rounds
            </p>
            <p style="font-size: 11px; color: #666; margin-top: 8px; font-style: italic;">
                Note: prompt token counts reflect only the final model call per round.
                Actual input across all {total_tool_rounds} tool call rounds is higher.
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_key_rules(session: SessionData):
    """Section 7 — Key Rules Reference."""
    st.markdown('<p class="section-heading">KEY RULES TO REMEMBER</p>', unsafe_allow_html=True)

    rules = [
        ("completionTokens is a running total, not a delta",
         "Each write replaces the prior value with the new cumulative total. Updates are progress snapshots, not additive increments."),
        ("Counter resets per request",
         "Each new request starts a fresh completionTokens counter from 0. Sum the final values across requests for session totals."),
        ("No promptTokens in streaming",
         "The JSONL only streams completionTokens live. Prompt/input tokens are written once inside requests.N.result at the end of processing."),
        ("Multiple JSONL entries per request",
         "One round produces many kind:1 and kind:2 entries as streaming progresses. The last completionTokens entry for a request index is the final count."),
    ]

    row1 = st.columns(2)
    row2 = st.columns(2)
    all_cols = [row1[0], row1[1], row2[0], row2[1]]

    for col, (title, body) in zip(all_cols, rules):
        with col:
            st.markdown(f"""
            <div class="rules-box">
                <p class="rules-box-title">{title}</p>
                <p class="rules-box-body">{body}</p>
            </div>
            """, unsafe_allow_html=True)
