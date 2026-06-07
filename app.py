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
    '<p style="text-align: center; color: #888; font-size: 14px; margin-bottom: 32px;">'
    'Upload a GitHub Copilot chat session JSONL file (chatSession or transcript format).</p>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a Copilot session JSONL file",
    type=["jsonl", "json"],
    help="Supports both chatSession (CRDT) and transcript (event stream) JSONL formats.",
)

if uploaded_file is not None:
    if st.session_state.get("last_file") != uploaded_file.name:
        with st.spinner("Parsing session file..."):
            try:
                file_bytes = uploaded_file.read()
                session_data = parse_session(file_bytes)
                st.session_state["session_data"] = session_data
                st.session_state["last_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"Failed to parse file: {e}")
                st.stop()

    session_data = st.session_state.get("session_data")
    if session_data is None:
        st.error("No session data available.")
        st.stop()

    # Show detected format badge
    fmt_label = "chatSession (CRDT)" if session_data.file_format == "chatSession" else "transcript (event stream)"
    fmt_color = "#7F77DD" if session_data.file_format == "chatSession" else "#378ADD"
    st.markdown(
        f'<p style="text-align:center;margin-bottom:16px;">'
        f'<span style="display:inline-block;background:{fmt_color};color:#fff;font-size:12px;font-weight:600;'
        f'padding:4px 14px;border-radius:12px;">Detected: {fmt_label}</span></p>',
        unsafe_allow_html=True,
    )

    if session_data.file_format == "chatSession":
        # ─── ChatSession tabs ───
        tab_overview, tab_timeline, tab_rounds, tab_tokens, tab_info = st.tabs([
            "📊 Overview", "📜 Timeline", "🔄 Rounds", "📈 Tokens", "ℹ️ Format Info"
        ])

        with tab_overview:
            render_session_header(session_data)
            render_key_rules(session_data)

        with tab_timeline:
            render_timeline(session_data)

        with tab_rounds:
            render_round_cards(session_data)

        with tab_tokens:
            render_token_chart(session_data)
            render_output_tokens_explainer(session_data)

        with tab_info:
            render_format_info()

    elif session_data.file_format == "transcript":
        # ─── Transcript tabs ───
        tab_overview, tab_timeline, tab_turns, tab_tools, tab_messages, tab_info = st.tabs([
            "📊 Overview", "📜 Timeline", "🔄 Turns", "🔧 Tools", "💬 Messages", "ℹ️ Format Info"
        ])

        with tab_overview:
            render_transcript_header(session_data)

        with tab_timeline:
            render_transcript_timeline(session_data)

        with tab_turns:
            render_transcript_turns(session_data)

        with tab_tools:
            render_transcript_tool_chart(session_data)

        with tab_messages:
            render_transcript_messages(session_data)

        with tab_info:
            render_format_info()

    else:
        st.error("Unknown file format. Expected chatSession (kind:0/1/2) or transcript (type-based events).")

else:
    st.markdown(
        '<div style="text-align: center; padding: 60px 20px; color: #888;">'
        '<p style="font-size: 48px; margin-bottom: 12px;">📂</p>'
        '<p style="font-size: 16px;">Drop a <code>.jsonl</code> session file above to get started</p>'
        '<p style="font-size: 13px; margin-top: 12px;">Supports both <strong>chatSession</strong> (CRDT patch log) '
        'and <strong>transcript</strong> (event stream) formats</p>'
        '</div>',
        unsafe_allow_html=True,
    )
