"""Copilot Session Analyser — main Streamlit entry point."""

import streamlit as st
from parser import parse_session
from styles import MAIN_CSS
from components import (
    render_session_header,
    render_timeline,
    render_round_cards,
    render_token_chart,
    render_output_tokens_explainer,
    render_key_rules,
    render_cost_summary,
    render_transcript_header,
    render_transcript_timeline,
    render_transcript_turns,
    render_transcript_tool_chart,
    render_transcript_messages,
    render_format_info,
)

st.set_page_config(
    page_title="Copilot Session Analyser",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(MAIN_CSS, unsafe_allow_html=True)

st.markdown(
    '<h1 style="text-align: center; color: #e8e6de; font-size: 28px; margin-bottom: 4px;">'
    '🔍 Copilot Session Analyser</h1>'
    '<p style="text-align: center; color: #888; font-size: 14px; margin-bottom: 24px;">'
    'Upload GitHub Copilot session files — chatSession and/or transcript JSONL.</p>',
    unsafe_allow_html=True,
)

# ─── Two file uploaders side by side ───
up_col1, up_col2 = st.columns(2)
with up_col1:
    cs_file = st.file_uploader(
        "📁 Chat Session file (chatSessions/*.jsonl)",
        type=["jsonl", "json"],
        key="cs_upload",
        help="CRDT patch log from workspaceStorage/<id>/chatSessions/",
    )
with up_col2:
    tr_file = st.file_uploader(
        "📁 Transcript file (transcripts/*.jsonl)",
        type=["jsonl", "json"],
        key="tr_upload",
        help="Event stream from workspaceStorage/<id>/GitHub.copilot-chat/transcripts/",
    )


def _parse_and_cache(uploaded, cache_key):
    """Parse an uploaded file and store in session_state."""
    if uploaded is None:
        st.session_state.pop(cache_key, None)
        st.session_state.pop(cache_key + "_name", None)
        return None
    if st.session_state.get(cache_key + "_name") != uploaded.name:
        with st.spinner("Parsing..."):
            try:
                data = parse_session(uploaded.read())
                st.session_state[cache_key] = data
                st.session_state[cache_key + "_name"] = uploaded.name
            except Exception as e:
                st.error(f"Failed to parse {uploaded.name}: {e}")
                return None
    return st.session_state.get(cache_key)


cs_data = _parse_and_cache(cs_file, "cs_data")
tr_data = _parse_and_cache(tr_file, "tr_data")

has_cs = cs_data is not None
has_tr = tr_data is not None

if not has_cs and not has_tr:
    st.markdown(
        '<div style="text-align: center; padding: 60px 20px; color: #888;">'
        '<p style="font-size: 48px; margin-bottom: 12px;">📂</p>'
        '<p style="font-size: 16px;">Upload one or both <code>.jsonl</code> files above to get started</p>'
        '<p style="font-size: 13px; margin-top: 12px; max-width: 600px; margin-left: auto; margin-right: auto;">'
        'The <strong>Chat Session</strong> file (CRDT patch log) has token counts, streaming progress, and cost data.<br>'
        'The <strong>Transcript</strong> file (event stream) has tool execution details, user messages, and reasoning text.<br>'
        'Upload both for the same session ID to see the complete picture.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Build top-level tab list based on what was uploaded ───
top_tab_names = []
if has_cs:
    top_tab_names.append("📊 Chat Session")
if has_tr:
    top_tab_names.append("📜 Transcript")
top_tab_names.append("ℹ️ Format Info")

top_tabs = st.tabs(top_tab_names)
tab_idx = 0

# ─── Chat Session top-level tab ───
if has_cs:
    with top_tabs[tab_idx]:
        fmt_label = "chatSession (CRDT)" if cs_data.file_format == "chatSession" else cs_data.file_format
        st.markdown(
            f'<p style="margin-bottom:8px;">'
            f'<span style="display:inline-block;background:#7F77DD;color:#fff;font-size:11px;font-weight:600;'
            f'padding:3px 12px;border-radius:10px;">{fmt_label}</span></p>',
            unsafe_allow_html=True,
        )

        sub_overview, sub_timeline, sub_rounds, sub_tokens, sub_cost = st.tabs([
            "Overview", "Timeline", "Rounds", "Tokens", "Cost & Credits"
        ])

        with sub_overview:
            render_session_header(cs_data)
            render_key_rules(cs_data)

        with sub_timeline:
            render_timeline(cs_data)

        with sub_rounds:
            render_round_cards(cs_data)

        with sub_tokens:
            render_token_chart(cs_data)
            render_output_tokens_explainer(cs_data)

        with sub_cost:
            render_cost_summary(cs_data)

    tab_idx += 1

# ─── Transcript top-level tab ───
if has_tr:
    with top_tabs[tab_idx]:
        st.markdown(
            '<p style="margin-bottom:8px;">'
            '<span style="display:inline-block;background:#378ADD;color:#fff;font-size:11px;font-weight:600;'
            'padding:3px 12px;border-radius:10px;">transcript (event stream)</span></p>',
            unsafe_allow_html=True,
        )

        sub_overview, sub_timeline, sub_turns, sub_tools, sub_messages = st.tabs([
            "Overview", "Timeline", "Turns", "Tools", "Messages"
        ])

        with sub_overview:
            render_transcript_header(tr_data)

        with sub_timeline:
            render_transcript_timeline(tr_data)

        with sub_turns:
            render_transcript_turns(tr_data)

        with sub_tools:
            render_transcript_tool_chart(tr_data)

        with sub_messages:
            render_transcript_messages(tr_data)

    tab_idx += 1

# ─── Format Info tab (always last) ───
with top_tabs[tab_idx]:
    render_format_info()
