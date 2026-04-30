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
)

st.set_page_config(
    page_title="Copilot Session Analyser",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject custom CSS
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# Title
st.markdown(
    '<h1 style="text-align: center; color: #e8e6de; font-size: 28px; margin-bottom: 4px;">'
    '🔍 Copilot Session Analyser</h1>'
    '<p style="text-align: center; color: #888; font-size: 14px; margin-bottom: 32px;">'
    'Upload a GitHub Copilot chat session JSONL file to visualise the full session breakdown.</p>',
    unsafe_allow_html=True,
)

# File upload
uploaded_file = st.file_uploader(
    "Upload a Copilot session JSONL file",
    type=["jsonl", "json"],
    help="Export your Copilot chat session as JSONL and upload it here.",
)

if uploaded_file is not None:
    # Parse only if new file or first upload
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

    # Section 2 — Session Header
    render_session_header(session_data)

    # Section 3 — Timeline
    render_timeline(session_data)

    # Section 4 — Round Cards
    render_round_cards(session_data)

    # Section 5 — Token Chart
    render_token_chart(session_data)

    # Section 6 — outputTokens Explainer
    render_output_tokens_explainer(session_data)

    # Section 7 — Key Rules
    render_key_rules(session_data)

else:
    # No file uploaded — show placeholder
    st.markdown(
        '<div style="text-align: center; padding: 60px 20px; color: #888;">'
        '<p style="font-size: 48px; margin-bottom: 12px;">📂</p>'
        '<p style="font-size: 16px;">Drop a <code>.jsonl</code> session file above to get started</p>'
        '</div>',
        unsafe_allow_html=True,
    )
