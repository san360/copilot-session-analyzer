"""Reusable render functions for each dashboard section."""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone
from parser import SessionData, TranscriptData, format_elapsed, format_span

ROUND_COLORS = ["#7F77DD", "#378ADD", "#1D9E75", "#EF9F27", "#DD77A0"]
ROUND_BAR_COLORS = ["#1D9E75", "#378ADD", "#1D9E75", "#EF9F27"]
ROUND_BAR_FINAL_COLORS = ["#085041", "#0C447C", "#085041", "#7A5000"]


def _fmt(n):
    if n is None or n == 0:
        return "N/A"
    return f"{n:,}"

def _fmt_or_zero(n):
    if n is None:
        return "N/A"
    return f"{n:,}"

def _round_color(idx):
    return ROUND_COLORS[idx % len(ROUND_COLORS)]

def _bar_color(idx):
    return ROUND_BAR_COLORS[idx % len(ROUND_BAR_COLORS)]

def _bar_final_color(idx):
    return ROUND_BAR_FINAL_COLORS[idx % len(ROUND_BAR_FINAL_COLORS)]


# ─── ChatSession Renderers ──────────────────────────────────────────────────

def render_session_header(session: SessionData):
    dt = datetime.fromtimestamp(session.creation_date / 1000, tz=timezone.utc) if session.creation_date else None
    date_str = dt.strftime("%B %d, %Y") if dt else "Unknown"
    num_rounds = len(session.requests)
    span_str = format_span(session.span_ms)
    ext_str = f"{session.extension_name} v{session.extension_version}" if session.extension_version else session.extension_name

    # Capabilities badges
    caps_html = ""
    if session.capabilities:
        cap_items = []
        for cap_name, cap_val in session.capabilities.items():
            if cap_val:
                cap_items.append(f'<span style="display:inline-block;background:#333;color:#aaa;font-size:10px;padding:2px 6px;border-radius:4px;margin-right:4px;">{cap_name}</span>')
        if cap_items:
            caps_html = f'<div style="margin-top:6px;">{"".join(cap_items)}</div>'

    # Pricing line
    pricing_html = ""
    if session.pricing_display:
        pricing_html = f'<p class="account-text">pricing: {session.pricing_display}</p>'

    # Top section: model + date — use st.columns to avoid nested div issues
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(
            f'<p class="model-name" style="display:inline;">{session.model_name}</p>'
            f'<span class="mode-badge">{session.mode} mode</span>'
            f'<p class="session-id">{session.session_id}</p>'
            f'{caps_html}',
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown(
            f'<div style="text-align:right;">'
            f'<p class="date-text">{date_str}</p>'
            f'<p class="account-text">account: {session.account_label} · multiplier: {session.multiplier}</p>'
            f'{pricing_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Stats grid using st.columns
    stat_cols = st.columns(6)
    stats = [
        (_fmt(session.max_input_tokens), "max input tokens"),
        (_fmt(session.max_output_tokens), "max output tokens"),
        (str(num_rounds), "rounds"),
        (_fmt_or_zero(session.total_lines), "JSONL lines"),
        (span_str, "session span"),
        (ext_str, "extension"),
    ]
    for col, (val, label) in zip(stat_cols, stats):
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:8px 0;">'
                f'<p class="stat-value">{val}</p>'
                f'<p class="stat-label">{label}</p></div>',
                unsafe_allow_html=True,
            )


def render_timeline(session: SessionData):
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

        # Credits display
        credits_html = ""
        if rd.credits:
            credits_html = f'<p style="font-size:11px;color:#EF9F27;margin-top:4px;">💰 {rd.credits}</p>'

        # Tool chips — use tool_ids if available, fallback to tool_names
        tool_list = rd.tool_ids if rd.tool_ids else rd.tool_names
        tool_chips_html = ""
        if tool_list:
            chips = "".join(f'<span class="tool-chip">{name}</span>' for name in tool_list)
            tool_chips_html = f'<div style="margin-top: 10px;">{chips}</div>'

        # Response kind counts
        kind_chips_html = ""
        if rd.response_kind_counts:
            kc_items = []
            for rk, cnt in sorted(rd.response_kind_counts.items()):
                kc_items.append(f'<span class="tool-chip">{rk}: {cnt}</span>')
            kind_chips_html = f'<div style="margin-top:6px;">{"".join(kc_items)}</div>'

        # Model state
        state_str = ""
        if rd.model_state_value == 1:
            state_str = "  ·  ✓ completed"
        elif rd.model_state_value > 0:
            state_str = f"  ·  state: {rd.model_state_value}"

        context_note_html = ""
        if i > 0 and rd.prompt_tokens > 0:
            prev_rd = session.requests[i - 1]
            if prev_rd.prompt_tokens > 0:
                delta = rd.prompt_tokens - prev_rd.prompt_tokens
                if delta > 0:
                    context_note_html = f'<div class="context-note">Context grew by +{delta:,} prompt tokens from R{i} — full R{i} history carried forward</div>'

        html_top = f"""
        <div class="round-card">
            <div style="margin-bottom: 14px;">
                <span class="round-badge" style="background-color: {color};">Round {round_num}</span>
                <span class="round-prompt">{prompt_trunc}</span>
            </div>
        </div>
        """
        with col:
            st.markdown(html_top, unsafe_allow_html=True)

            # Stats row 1
            scols1 = st.columns(3)
            for sc, (sv, sl) in zip(scols1, [
                (_fmt(rd.prompt_tokens), "prompt tokens"),
                (_fmt_or_zero(rd.completion_tokens), "completion tokens"),
                (_fmt_or_zero(total_tokens), "total tokens"),
            ]):
                with sc:
                    st.markdown(f'<p class="round-stat-value">{sv}</p><p class="round-stat-label">{sl}</p>', unsafe_allow_html=True)

            # Stats row 2
            scols2 = st.columns(3)
            for sc, (sv, sl) in zip(scols2, [
                (_fmt(rd.output_tokens_result), "outputTokens (result)"),
                (str(rd.tool_call_rounds_count), "tool call rounds"),
                (elapsed_str, "elapsed"),
            ]):
                with sc:
                    st.markdown(f'<p class="round-stat-value">{sv}</p><p class="round-stat-label">{sl}</p>', unsafe_allow_html=True)

            if credits_html:
                st.markdown(credits_html, unsafe_allow_html=True)

            st.markdown(
                f'<p class="round-meta">request_{short_id}  ·  T+{t_offset:.1f}min  ·  result: line {rd.result_line}{state_str}</p>',
                unsafe_allow_html=True,
            )
            if tool_chips_html:
                st.markdown(tool_chips_html, unsafe_allow_html=True)
            if kind_chips_html:
                st.markdown(kind_chips_html, unsafe_allow_html=True)
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
                        f'<div style="height:100%;border-radius:3px;width:{pct}%;background-color:{fill_color};"></div></div>'
                        f'<span style="font-size:11px;color:#e8e6de;min-width:60px;text-align:right;margin-left:8px;">{val:,}</span></div>',
                        unsafe_allow_html=True,
                    )
            if context_note_html:
                st.markdown(context_note_html, unsafe_allow_html=True)


def render_token_chart(session: SessionData):
    st.markdown('<p class="section-heading">TOKEN BREAKDOWN COMPARISON</p>', unsafe_allow_html=True)
    round_labels = [f"Round {i + 1}" for i in range(len(session.requests))]
    prompt_tokens = [rd.prompt_tokens for rd in session.requests]
    completion_tokens = [rd.completion_tokens for rd in session.requests]
    output_tokens = [rd.output_tokens_result for rd in session.requests]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Prompt tokens", x=round_labels, y=prompt_tokens, marker_color="#7F77DD",
                         hovertemplate="%{x}<br>Prompt tokens: %{y:,}<extra></extra>"))
    fig.add_trace(go.Bar(name="Completion tokens", x=round_labels, y=completion_tokens, marker_color="#1D9E75",
                         hovertemplate="%{x}<br>Completion tokens: %{y:,}<extra></extra>"))
    fig.add_trace(go.Bar(name="outputTokens (result record)", x=round_labels, y=output_tokens, marker_color="#EF9F27",
                         hovertemplate="%{x}<br>outputTokens (result): %{y:,}<extra></extra>"))
    fig.update_layout(
        barmode="group", plot_bgcolor="#1e1e1e", paper_bgcolor="#1a1a1a",
        font=dict(color="#e8e6de", size=12), height=280,
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        yaxis=dict(gridcolor="#333", gridwidth=0.5, tickformat=",.0f"),
        xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_output_tokens_explainer(session: SessionData):
    st.markdown('<p class="section-heading">WHAT ROLE DOES OUTPUTTOKENS PLAY?</p>', unsafe_allow_html=True)
    multiplier_text = f"{session.model_name} carries a {session.multiplier} multiplier"
    cols = st.columns(3)
    boxes = [
        ("Billing event anchor", f"Copilot uses this to log a billing-ready event. {multiplier_text}, so these tokens cost {session.multiplier} more than base. It captures the output of the call that 'closed' the result."),
        ("Snapshot in time", "The result record is written mid-stream. For heavy agent rounds it captures only the last batch after all tool rounds finish. For lighter rounds it may capture an early checkpoint before generation ends."),
        ("Not the authoritative total", "Always use the final completionTokens streaming value for the true output count. outputTokens will be lower — sometimes dramatically lower — in agent-mode sessions with many tool rounds."),
    ]
    for col, (title, body) in zip(cols, boxes):
        with col:
            st.markdown(f'<div class="info-box"><p class="info-box-title">{title}</p><p class="info-box-body">{body}</p></div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    num_rounds = len(session.requests)
    total_tool_rounds = sum(rd.tool_call_rounds_count for rd in session.requests)
    total_prompt = sum(rd.prompt_tokens for rd in session.requests)
    total_completion = sum(rd.completion_tokens for rd in session.requests)
    grand_total = total_prompt + total_completion

    summary_cols = st.columns(num_rounds + 1)
    for i, rd in enumerate(session.requests):
        sub_label = ""
        if rd.completion_token_history and len(rd.completion_token_history) >= 2:
            prev_val = rd.completion_token_history[-2][1]
            sub_label = f"= {rd.completion_tokens:,} − {prev_val:,} (last batch only)"
        with summary_cols[i]:
            st.markdown(f"""
            <div class="card" style="text-align: center; padding: 16px;">
                <p style="font-size: 32px; font-weight: 700; color: #e8e6de; margin: 0;">{_fmt_or_zero(rd.output_tokens_result)}</p>
                <p style="font-size: 12px; color: #888; margin: 4px 0 0 0;">R{i + 1} outputTokens</p>
                <p style="font-size: 11px; color: #666; margin: 2px 0 0 0;">{sub_label}</p>
            </div>""", unsafe_allow_html=True)
    with summary_cols[-1]:
        st.markdown(f"""
        <div class="card" style="padding: 16px;">
            <p style="font-size: 13px; color: #aaa; line-height: 1.6; margin: 0;">
                <strong style="color: #e8e6de;">Session total (true counts):</strong><br>
                Prompt: {total_prompt:,} tokens in<br>Completion: {total_completion:,} tokens out<br>
                Grand total: {grand_total:,} tokens across {num_rounds} rounds</p>
            <p style="font-size: 11px; color: #666; margin-top: 8px; font-style: italic;">
                Note: prompt token counts reflect only the final model call per round.
                Actual input across all {total_tool_rounds} tool call rounds is higher.</p>
        </div>""", unsafe_allow_html=True)


def render_key_rules(session: SessionData):
    st.markdown('<p class="section-heading">KEY RULES TO REMEMBER</p>', unsafe_allow_html=True)
    rules = [
        ("completionTokens is a running total, not a delta", "Each write replaces the prior value with the new cumulative total. Updates are progress snapshots, not additive increments."),
        ("Counter resets per request", "Each new request starts a fresh completionTokens counter from 0. Sum the final values across requests for session totals."),
        ("No promptTokens in streaming", "The JSONL only streams completionTokens live. Prompt/input tokens are written once inside requests.N.result at the end of processing."),
        ("Multiple JSONL entries per request", "One round produces many kind:1 and kind:2 entries as streaming progresses. The last completionTokens entry for a request index is the final count."),
    ]
    row1 = st.columns(2)
    row2 = st.columns(2)
    all_cols = [row1[0], row1[1], row2[0], row2[1]]
    for col, (title, body) in zip(all_cols, rules):
        with col:
            st.markdown(f'<div class="rules-box"><p class="rules-box-title">{title}</p><p class="rules-box-body">{body}</p></div>', unsafe_allow_html=True)


# ─── Transcript Renderers ───────────────────────────────────────────────────

def render_transcript_header(session: SessionData):
    td = session.transcript

    # Top section using st.columns
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(
            f'<p class="model-name" style="display:inline;">Transcript</p>'
            f'<span class="mode-badge" style="background-color:#378ADD;">event stream</span>'
            f'<p class="session-id">{td.session_id}</p>',
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown(
            f'<div style="text-align:right;">'
            f'<p class="date-text">{td.start_time[:10] if td.start_time else "Unknown"}</p>'
            f'<p class="account-text">producer: {td.producer}  ·  version: {td.version}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Stats grid using st.columns
    stat_cols = st.columns(6)
    failure_color = '#E54D42' if td.total_tool_failures > 0 else '#e8e6de'
    stats = [
        (str(td.total_lines), "JSONL lines", None),
        (str(len(td.user_messages)), "user messages", None),
        (str(len(td.turns)), "assistant turns", None),
        (str(td.total_tool_calls), "tool executions", None),
        (str(td.total_tool_successes), "successes", None),
        (str(td.total_tool_failures), "failures", failure_color),
    ]
    for col, (val, label, color) in zip(stat_cols, stats):
        color_style = f'color:{color};' if color else ''
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:8px 0;">'
                f'<p class="stat-value" style="{color_style}">{val}</p>'
                f'<p class="stat-label">{label}</p></div>',
                unsafe_allow_html=True,
            )


def render_transcript_timeline(session: SessionData):
    td = session.transcript
    st.markdown(f'<p class="section-heading">TRANSCRIPT TIMELINE — {td.total_lines} EVENTS</p>', unsafe_allow_html=True)

    for event in td.timeline:
        ts_display = ""
        if event.timestamp:
            ts_display = f' <span style="color:#666;font-size:10px;margin-left:8px;">{event.timestamp}</span>'
        html = f"""
        <div class="timeline-container">
            <div class="timeline-line"></div>
            <div class="timeline-dot" style="border-color: {event.dot_color};"></div>
            <div class="timeline-card" style="border-left-color: {event.dot_color};">
                <p class="timeline-title">{event.title}{ts_display}</p>
                <p class="timeline-subtitle">{event.subtitle}</p>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def render_transcript_turns(session: SessionData):
    td = session.transcript
    if not td.turns:
        return

    st.markdown('<p class="section-heading">ASSISTANT TURNS</p>', unsafe_allow_html=True)

    for turn in td.turns:
        color = _round_color(turn.turn_index)
        total_msgs = len(turn.messages)
        total_tools = len(turn.tool_executions)
        reasoning_badge = ' <span style="display:inline-block;background:#7F77DD;color:#fff;font-size:10px;padding:1px 6px;border-radius:4px;margin-left:6px;">reasoning</span>' if turn.has_reasoning else ""

        tool_chips = ""
        if turn.tool_executions:
            tool_names = {}
            for te in turn.tool_executions:
                tool_names[te.tool_name] = tool_names.get(te.tool_name, 0) + 1
            chips = "".join(f'<span class="tool-chip">{name} ×{cnt}</span>' if cnt > 1 else f'<span class="tool-chip">{name}</span>' for name, cnt in tool_names.items())
            tool_chips = f'<div style="margin-top:8px;">{chips}</div>'

        st.markdown(f"""
        <div class="round-card">
            <div style="margin-bottom: 10px;">
                <span class="round-badge" style="background-color: {color};">Turn {turn.turn_index + 1}</span>
                <span style="font-size:13px;color:#888;">{total_msgs} messages  ·  {total_tools} tool calls{reasoning_badge}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div><p class="round-stat-value">{turn.total_content_length:,}</p><p class="round-stat-label">content chars</p></div>
                <div><p class="round-stat-value">{total_tools}</p><p class="round-stat-label">tool executions</p></div>
                <div><p class="round-stat-value">{total_msgs}</p><p class="round-stat-label">messages</p></div>
            </div>
            {tool_chips}
        </div>
        """, unsafe_allow_html=True)


def render_transcript_tool_chart(session: SessionData):
    td = session.transcript
    if not td.tool_usage_counts:
        return

    st.markdown('<p class="section-heading">TOOL USAGE BREAKDOWN</p>', unsafe_allow_html=True)

    sorted_tools = sorted(td.tool_usage_counts.items(), key=lambda x: x[1], reverse=True)
    names = [t[0] for t in sorted_tools]
    counts = [t[1] for t in sorted_tools]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts, y=names, orientation="h",
        marker_color="#378ADD",
        hovertemplate="%{y}: %{x} calls<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="#1e1e1e", paper_bgcolor="#1a1a1a",
        font=dict(color="#e8e6de", size=11),
        height=max(200, len(names) * 28),
        margin=dict(l=200, r=20, t=10, b=30),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(gridcolor="#333", gridwidth=0.5, title="Executions"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_transcript_messages(session: SessionData):
    td = session.transcript
    if not td.user_messages:
        return

    st.markdown('<p class="section-heading">USER MESSAGES</p>', unsafe_allow_html=True)

    for i, msg in enumerate(td.user_messages):
        content = msg["content"]
        trunc = content[:300] + ("..." if len(content) > 300 else "")
        ts = msg.get("timestamp", "")
        attach_count = len(msg.get("attachments", []))
        attach_str = f"  ·  {attach_count} attachments" if attach_count else ""

        st.markdown(f"""
        <div class="card" style="margin-bottom: 8px; padding: 14px;">
            <p style="font-size:12px;color:#888;margin:0 0 6px 0;">Message {i + 1}  ·  {ts}{attach_str}</p>
            <p style="font-size:13px;color:#e8e6de;margin:0;line-height:1.5;white-space:pre-wrap;">{trunc}</p>
        </div>
        """, unsafe_allow_html=True)


# ─── Format Comparison Info ─────────────────────────────────────────────────

def render_format_info():
    st.markdown('<p class="section-heading">CHATSESSIONS VS TRANSCRIPTS — FORMAT COMPARISON</p>', unsafe_allow_html=True)

    cols = st.columns(2)
    with cols[0]:
        st.markdown("""
        <div class="info-box">
            <p class="info-box-title">chatSessions (CRDT Patch Log)</p>
            <p class="info-box-body">
                <strong>Owner:</strong> VS Code core (workbench)<br>
                <strong>Purpose:</strong> UI state persistence & session restore<br>
                <strong>Format:</strong> kind:0 snapshots + kind:1/2 diff patches<br>
                <strong>Location:</strong> <code>chatSessions/{id}.jsonl</code><br><br>
                <strong>Unique data:</strong> Token counts (prompt/completion), timing data, content references,
                tool confirmation states, full response rendering, editor state, model configuration,
                cost/multiplier metadata, streaming progress
            </p>
        </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown("""
        <div class="info-box">
            <p class="info-box-title">Transcripts (Event Stream)</p>
            <p class="info-box-body">
                <strong>Owner:</strong> Copilot extension (SessionTranscriptService)<br>
                <strong>Purpose:</strong> Conversation event log for hooks & replay<br>
                <strong>Format:</strong> Linked list of typed events (parentId chain)<br>
                <strong>Location:</strong> <code>GitHub.copilot-chat/transcripts/{id}.jsonl</code><br><br>
                <strong>Unique data:</strong> Clean event ordering, explicit tool arguments at execution time,
                separate start/complete events per tool, reasoning text as first-class field,
                producer identity, tool success/failure tracking
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="margin-top: 12px; padding: 16px;">
        <p style="font-size: 13px; color: #aaa; line-height: 1.6; margin: 0;">
            <strong style="color: #e8e6de;">Key insight:</strong> These are complementary, not replacements.
            chatSessions is VS Code's authoritative state store (for session restore after reload).
            Transcripts are the Copilot extension's event log (exposed to hooks and external tools).
            Both use the same session ID for correlation. A third format — <strong>debug-logs</strong>
            (OpenTelemetry spans) — exists for developer diagnostics with per-LLM-call token counts and system prompts.
        </p>
    </div>
    """, unsafe_allow_html=True)
