# Copilot Session Analyser

A Streamlit web application that parses GitHub Copilot chat session JSONL files and renders a rich, tabbed visual dashboard for understanding token usage, tool calls, timelines, and session structure.

Supports **two JSONL formats** — chatSessions (CRDT patch log) and transcripts (event stream) — with auto-detection and format-specific tabs.

## What It Does

Upload a Copilot session `.jsonl` file and get an instant visual breakdown:

### chatSession Format (CRDT Patch Log)
- **Overview** — Model name, mode, account, token limits, capabilities, pricing, session span
- **Timeline** — Chronological view of all JSONL events: session init, user prompts, request submissions, completion token streaming, agent tool calls, result records
- **Rounds** — Side-by-side cards per request showing prompt/completion/output tokens, tool call rounds, elapsed time, credits, tool IDs, response kind breakdown, and streaming progress bars
- **Tokens** — Grouped bar chart comparing prompt, completion, and outputTokens across rounds + outputTokens explainer

### Transcript Format (Event Stream)
- **Overview** — Session metadata, user message count, assistant turns, tool execution stats (success/failure)
- **Timeline** — Chronological event stream: session.start, user.message, assistant turns, tool execution start/complete
- **Turns** — Assistant turn cards showing message count, content length, tool executions, reasoning indicators
- **Tools** — Horizontal bar chart of tool usage by frequency
- **Messages** — Full user message content with timestamps and attachment counts

### Format Comparison
Both formats include a **Format Info** tab explaining the differences between chatSessions and transcripts.

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
app.py              # Main Streamlit entry — tabbed layout with format auto-detection
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
2. Upload a `.jsonl` file — the format is auto-detected
3. Navigate between tabs for different views of the session data
4. Upload a different file to analyse another session (state is cleared automatically)

## Edge Cases Handled

- Single-round sessions
- 3+ round sessions (cards wrap into columns)
- Missing `promptTokens` or `result` records (shows N/A / "in progress")
- Empty tool call rounds
- Large files (line-by-line streaming parse)
- Non-string field values in tool invocations
- Files with unknown format (clear error message)

## Tech Stack

- **Streamlit** — UI framework with tabbed layout
- **Plotly** — Charts and visualisations
- **pandas** — Data manipulation
- All processing is local; no external API calls
