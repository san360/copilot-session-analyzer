# Copilot Session Analyser

A Streamlit web application that parses GitHub Copilot chat session JSONL files and renders a visual dashboard for understanding token usage, tool calls, timelines, credits, and session structure.

Supports **two JSONL formats** — chatSessions (CRDT patch log) and transcripts (event stream) — with auto-detection. Upload one or both files for the same session to get the complete picture.

## What It Does

Upload one or both Copilot session `.jsonl` files and get an instant visual breakdown. A **radio selector** switches between Chat Session, Transcript, and Format Info views.

### Chat Session View (tabbed)
The chatSession CRDT patch log is presented in tabs:
- **Overview** — Model name, mode, account, token limits, capabilities, pricing, session span
- **Timeline** — Chronological view of all JSONL events: session init, user prompts, request submissions, completion token streaming, agent tool calls, result records
- **Rounds** — Side-by-side cards per request showing prompt/completion/output tokens, tool call rounds, elapsed time, credits, tool IDs, response kind breakdown, and streaming progress bars
- **Tokens** — Grouped bar chart comparing prompt, completion, and outputTokens across rounds + outputTokens explainer
- **Cost & Credits** — Total tokens, model multiplier, total credits from `result.details`, per-round breakdown with credit values, and pricing explainer

### Transcript View (single scrollable page)
The transcript event stream is rendered as a continuous dashboard:
- **Header** — Session metadata, user message count, assistant turns, tool execution stats (success/failure)
- **Timeline** — Chronological event stream: session.start, user.message, assistant turns, tool execution start/complete
- **Tools** — Horizontal bar chart of tool usage by frequency
- **Turns** — Assistant turn cards showing message count, content length, tool executions, reasoning indicators
- **Messages** — Full user message content with timestamps and attachment counts

### Format Info View
A detailed comparison page with:
- Side-by-side format cards with unique data per format
- Feature comparison table (12 aspects)
- Event type reference for both formats
- File locations for Windows, macOS, and Linux
- Related documentation links (GitHub Copilot docs, VS Code API, premium request usage)

## JSONL File Formats

### chatSessions — VS Code Core (CRDT)
Written by VS Code's workbench for **session persistence and restore**. Uses diff-based patches.

```
%APPDATA%\Code\User\workspaceStorage\<id>\chatSessions\<session-id>.jsonl
```

| Kind | Purpose |
|------|---------|
| `0` | Full session snapshot (model metadata, mode, account, capabilities, pricing) |
| `1` | Patch update (completionTokens, result, elapsedMs, modelState, contentReferences) |
| `2` | Array replace (requests, response items with tool invocations, thinking, text edits) |

### Transcripts — Copilot Extension (Event Stream)
Written by the Copilot extension's `SessionTranscriptService` as a **conversation event log**.

```
%APPDATA%\Code\User\workspaceStorage\<id>\GitHub.copilot-chat\transcripts\<session-id>.jsonl
```

| Event Type | Purpose |
|------------|---------|
| `session.start` | Session metadata (producer, versions) |
| `user.message` | User prompts with attachments |
| `assistant.turn_start/end` | Turn boundaries |
| `assistant.message` | Model responses with reasoning text and tool requests |
| `tool.execution_start/complete` | Tool calls with arguments and success/failure |

### Key Differences

| Aspect | chatSessions | Transcripts |
|--------|-------------|-------------|
| **Owner** | VS Code core | Copilot extension |
| **Purpose** | Session restore after reload | Event log for hooks & replay |
| **Token data** | ✅ Full streaming counts | ❌ Not included |
| **Tool arguments** | Serialized in response | ✅ Explicit at execution time |
| **Tool success/fail** | ❌ Not tracked | ✅ Per-tool tracking |
| **Reasoning text** | In response items | ✅ First-class field |
| **Pricing/cost** | ✅ Credits per round | ❌ Not included |

Both formats share the same **session ID** for correlation.

## Project Structure

```
app.py              # Main Streamlit entry — radio selector + tabbed/scrollable views
parser.py           # JSONL parsing — chatSession & transcript parsers
components.py       # Render functions for all dashboard sections
styles.py           # CSS constants for the dark theme
requirements.txt    # Python dependencies
```

## Prerequisites

- Python 3.10+

## Setup & Run

```bash
# Clone the repository
git clone https://github.com/san360/copilot-session-analyzer.git
cd copilot-session-analyzer

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Finding Your Session Files

### Windows
```
%APPDATA%\Code\User\workspaceStorage\<workspace-id>\chatSessions\*.jsonl
%APPDATA%\Code\User\workspaceStorage\<workspace-id>\GitHub.copilot-chat\transcripts\*.jsonl
```

### macOS
```
~/Library/Application Support/Code/User/workspaceStorage/<workspace-id>/chatSessions/*.jsonl
~/Library/Application Support/Code/User/workspaceStorage/<workspace-id>/GitHub.copilot-chat/transcripts/*.jsonl
```

### Linux
```
~/.config/Code/User/workspaceStorage/<workspace-id>/chatSessions/*.jsonl
~/.config/Code/User/workspaceStorage/<workspace-id>/GitHub.copilot-chat/transcripts/*.jsonl
```

Sort by date to find the most recent sessions.

## Usage

1. Open `http://localhost:8501` in your browser
2. Upload a chatSession file, a transcript file, or both — the format is auto-detected
3. Use the radio selector to switch between Chat Session, Transcript, and Format Info views
4. Within Chat Session, navigate tabs (Overview, Timeline, Rounds, Tokens, Cost & Credits)
5. The Transcript view is a single scrollable dashboard — no sub-tabs needed

## Edge Cases Handled

- Single-round sessions
- 3+ round sessions (cards wrap into columns)
- Missing `promptTokens` or `result` records (shows N/A / "in progress")
- Empty tool call rounds
- Large files (line-by-line streaming parse)
- Non-string field values in tool invocations
- Files with unknown format (clear error message)

## Tech Stack

- **Streamlit** — UI framework with radio selector and tabbed/scrollable layouts
- **Plotly** — Charts and visualisations
- **pandas** — Data manipulation
- All processing is local; no external API calls
