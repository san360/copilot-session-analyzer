"""CSS constants for the Copilot Session Analyser dark theme."""

MAIN_CSS = """
<style>
    /* Global dark theme overrides */
    .stApp {
        background-color: #1a1a1a !important;
        color: #e8e6de !important;
    }

    /* Hide default Streamlit header/footer */
    header[data-testid="stHeader"] {
        background-color: #1a1a1a !important;
    }

    /* Card base */
    .card {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }

    /* Session header card */
    .session-header-card {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }
    .session-header-card .model-name {
        font-size: 28px;
        font-weight: 700;
        color: #e8e6de;
        margin: 0;
    }
    .session-header-card .mode-badge {
        display: inline-block;
        background-color: #1D9E75;
        color: #fff;
        font-size: 12px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        margin-left: 12px;
        vertical-align: middle;
    }
    .session-header-card .session-id {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        color: #888;
        margin-top: 4px;
    }
    .session-header-card .date-text {
        font-size: 16px;
        color: #e8e6de;
        text-align: right;
    }
    .session-header-card .account-text {
        font-size: 12px;
        color: #888;
        text-align: right;
        margin-top: 2px;
    }
    .session-header-card .divider {
        border-top: 1px solid #3a3a3a;
        margin: 16px 0;
    }
    .stat-value {
        font-size: 22px;
        font-weight: 700;
        color: #e8e6de;
        margin: 0;
    }
    .stat-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
    }

    /* Section headings */
    .section-heading {
        font-size: 12px;
        font-weight: 700;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 32px;
        margin-bottom: 16px;
    }

    /* Timeline */
    .timeline-container {
        position: relative;
        padding-left: 40px;
        margin-bottom: 8px;
    }
    .timeline-line {
        position: absolute;
        left: 18px;
        top: 0;
        bottom: 0;
        width: 1px;
        background-color: #3a3a3a;
    }
    .timeline-dot {
        position: absolute;
        left: 12px;
        top: 14px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 2px solid;
        background-color: #1a1a1a;
        z-index: 1;
    }
    .timeline-card {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 6px;
        border-left: 3px solid;
    }
    .timeline-title {
        font-size: 13px;
        font-weight: 600;
        color: #e8e6de;
        margin: 0;
    }
    .timeline-subtitle {
        font-size: 11px;
        color: #888;
        margin: 4px 0 0 0;
    }

    /* Round cards */
    .round-card {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .round-badge {
        display: inline-block;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 12px;
        color: #fff;
        margin-right: 12px;
    }
    .round-prompt {
        font-size: 14px;
        font-weight: 600;
        color: #e8e6de;
        display: inline;
    }
    .round-stat-value {
        font-size: 20px;
        font-weight: 700;
        color: #e8e6de;
        margin: 0;
    }
    .round-stat-label {
        font-size: 10px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
    }
    .round-meta {
        font-size: 11px;
        color: #888;
        font-family: 'Consolas', 'Monaco', monospace;
        margin-top: 10px;
    }

    /* Tool chips */
    .tool-chip {
        display: inline-block;
        font-size: 11px;
        color: #888;
        background-color: #1a1a1a;
        border: 1px solid #3a3a3a;
        padding: 2px 6px;
        border-radius: 4px;
        margin: 2px 3px;
    }

    /* Progress bars for completion tokens */
    .token-bar-row {
        display: flex;
        align-items: center;
        margin-bottom: 4px;
    }
    .token-bar-label {
        font-size: 11px;
        font-family: 'Consolas', 'Monaco', monospace;
        color: #888;
        min-width: 36px;
        text-align: right;
        margin-right: 8px;
    }
    .token-bar-track {
        flex: 1;
        background-color: #1a1a1a;
        border-radius: 3px;
        height: 8px;
        overflow: hidden;
    }
    .token-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }
    .token-bar-value {
        font-size: 11px;
        color: #e8e6de;
        min-width: 60px;
        text-align: right;
        margin-left: 8px;
    }

    /* Info boxes */
    .info-box {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 18px 20px;
        height: 100%;
    }
    .info-box-title {
        font-size: 14px;
        font-weight: 700;
        color: #e8e6de;
        margin-bottom: 8px;
    }
    .info-box-body {
        font-size: 13px;
        color: #aaa;
        line-height: 1.5;
    }

    /* Delta badge */
    .delta-badge {
        font-size: 11px;
        color: #888;
        margin-left: 6px;
    }

    /* Summary stats */
    .summary-big-number {
        font-size: 32px;
        font-weight: 700;
        color: #e8e6de;
    }
    .summary-label {
        font-size: 12px;
        color: #888;
    }
    .summary-sublabel {
        font-size: 11px;
        color: #666;
    }

    /* Key rules grid */
    .rules-box {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 12px;
        min-height: 140px;
    }
    .rules-box-title {
        font-size: 14px;
        font-weight: 700;
        color: #e8e6de;
        margin-bottom: 8px;
    }
    .rules-box-body {
        font-size: 13px;
        color: #aaa;
        line-height: 1.5;
    }

    /* Context note */
    .context-note {
        font-size: 12px;
        color: #EF9F27;
        background-color: rgba(239, 159, 39, 0.1);
        border: 1px solid rgba(239, 159, 39, 0.3);
        border-radius: 6px;
        padding: 8px 12px;
        margin-top: 12px;
    }

    /* Upload area styling */
    [data-testid="stFileUploader"] {
        max-width: 600px;
        margin: 0 auto;
    }
</style>
"""
