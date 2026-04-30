"""JSONL parsing logic for Copilot Session Analyser."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RequestData:
    """Parsed data for a single request/round."""
    index: int = 0
    request_id: str = ""
    timestamp: int = 0  # Unix ms
    model_id: str = ""
    prompt_text: str = ""
    mode: str = ""
    extension_version: str = ""

    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0  # final streaming value
    output_tokens_result: int = 0  # from result record snapshot
    completion_token_history: list = field(default_factory=list)  # [(line_num, value)]

    # Timing
    first_progress_ms: float = 0
    total_elapsed_ms: float = 0

    # Tool calls
    tool_call_rounds_count: int = 0
    tool_names: list = field(default_factory=list)
    tool_call_rounds_raw: list = field(default_factory=list)

    # Content references
    content_references: list = field(default_factory=list)

    # Response items
    response_items: list = field(default_factory=list)

    # Result line number
    result_line: int = 0

    # Request submitted line number
    request_line: int = 0

    # Has result?
    has_result: bool = False

    # Thinking tokens
    thinking_tokens: int = 0


@dataclass
class TimelineEvent:
    """A single event in the session timeline."""
    line_number: int = 0
    line_end: int = 0  # for range events
    kind: int = 0
    event_type: str = ""  # session_init, user_typing, request_submitted, completion_update, tools_fire, result_written, pending_edits
    dot_color: str = "#888"
    title: str = ""
    subtitle: str = ""
    request_index: int = -1
    value: object = None


@dataclass
class SessionData:
    """Fully parsed session data."""
    # Session metadata
    session_id: str = ""
    creation_date: int = 0  # Unix ms
    model_name: str = ""
    model_id: str = ""
    multiplier: str = ""
    multiplier_numeric: float = 1.0
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    account_label: str = ""
    mode: str = ""
    extension_name: str = ""
    extension_version: str = ""

    # Requests
    requests: list = field(default_factory=list)  # list of RequestData

    # Timeline
    timeline: list = field(default_factory=list)  # list of TimelineEvent

    # File stats
    total_lines: int = 0
    custom_title: str = ""

    # Session span
    span_ms: float = 0


def _safe_get(obj, *keys, default=None):
    """Safely navigate nested dicts/lists."""
    current = obj
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        elif isinstance(current, list) and isinstance(k, int) and 0 <= k < len(current):
            current = current[k]
        else:
            return default
    return current


def _format_number(n):
    """Format number with commas."""
    if n is None:
        return "N/A"
    return f"{n:,}"


def parse_session(file_bytes: bytes) -> SessionData:
    """Parse a JSONL file into a SessionData object."""
    text = file_bytes.decode("utf-8", errors="replace")
    lines = text.strip().split("\n")

    session = SessionData()
    session.total_lines = len(lines)

    # Tracking structures
    requests_dict: dict[int, RequestData] = {}
    input_text_drafts: list = []  # [(line_num, text)]
    input_text_first_line = None
    input_text_last_line = None
    completion_update_counters: dict[int, int] = {}  # request_idx -> update count
    tool_fire_ranges: dict = {}  # key -> {first, last, tools, request_idx}
    pending_edits_events: list = []

    for line_idx, line_text in enumerate(lines):
        line_num = line_idx + 1
        line_text = line_text.strip()
        if not line_text:
            continue

        try:
            obj = json.loads(line_text)
        except json.JSONDecodeError:
            continue

        kind = obj.get("kind")

        if kind == 0:
            # Session init
            v = obj.get("v", {})
            session.session_id = v.get("sessionId", "")
            session.creation_date = v.get("creationDate", 0)

            model_meta = _safe_get(v, "inputState", "selectedModel", "metadata", default={})
            session.model_name = model_meta.get("name", "Unknown Model")
            session.model_id = model_meta.get("id", "")
            session.multiplier = model_meta.get("multiplier", "1x")
            session.multiplier_numeric = model_meta.get("multiplierNumeric", 1.0)
            session.max_input_tokens = model_meta.get("maxInputTokens", 0)
            session.max_output_tokens = model_meta.get("maxOutputTokens", 0)

            auth = model_meta.get("auth", {})
            session.account_label = auth.get("accountLabel", "")

            mode_info = _safe_get(v, "inputState", "mode", default={})
            session.mode = mode_info.get("id", "") if isinstance(mode_info, dict) else ""

            # Timeline: session init
            subtitle_parts = [
                f"Model: {session.model_name}",
                f"Mode: {session.mode}",
                f"Account: {session.account_label}",
                f"Max input: {_format_number(session.max_input_tokens)} tok",
                f"Max output: {_format_number(session.max_output_tokens)} tok",
            ]
            session.timeline.append(TimelineEvent(
                line_number=line_num,
                kind=0,
                event_type="session_init",
                dot_color="#7F77DD",
                title=f"Line {line_num} — kind:0  Session created",
                subtitle="  ·  ".join(subtitle_parts),
            ))

        elif kind == 1:
            # Patch update
            k_path = obj.get("k", [])
            v = obj.get("v")

            if k_path == ["inputState", "inputText"]:
                if v and isinstance(v, str) and v.strip():
                    input_text_drafts.append((line_num, v))
                    if input_text_first_line is None:
                        input_text_first_line = line_num
                    input_text_last_line = line_num

            elif k_path == ["customTitle"]:
                session.custom_title = v if isinstance(v, str) else ""

            elif k_path == ["hasPendingEdits"]:
                pending_edits_events.append((line_num, v))
                session.timeline.append(TimelineEvent(
                    line_number=line_num,
                    kind=1,
                    event_type="pending_edits",
                    dot_color="#888",
                    title=f"Line {line_num} — hasPendingEdits → {v}",
                    subtitle="Editor edits in progress",
                ))

            elif (len(k_path) == 3 and k_path[0] == "requests"
                  and isinstance(k_path[1], int)
                  and k_path[2] == "completionTokens"):
                req_idx = k_path[1]
                token_val = v if isinstance(v, (int, float)) else 0

                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]
                rd.completion_token_history.append((line_num, int(token_val)))
                rd.completion_tokens = int(token_val)

                # Track update counter
                if req_idx not in completion_update_counters:
                    completion_update_counters[req_idx] = 0
                completion_update_counters[req_idx] += 1
                update_num = completion_update_counters[req_idx]

                # Compute delta
                history = rd.completion_token_history
                prev_val = history[-2][1] if len(history) >= 2 else 0
                delta = int(token_val) - prev_val
                delta_str = f"+{_format_number(delta)}" if delta > 0 else ""

                # Contextual description
                is_final = False  # We'll mark final later
                ctx_desc = _get_completion_context_desc(update_num, req_idx + 1, is_final, session.custom_title)

                title = f"Line {line_num} — completionTokens update #{update_num}  →  {_format_number(int(token_val))}"
                if delta_str:
                    title += f'  <span class="delta-badge">{delta_str}</span>'

                session.timeline.append(TimelineEvent(
                    line_number=line_num,
                    kind=1,
                    event_type="completion_update",
                    dot_color="#EF9F27",
                    title=title,
                    subtitle=ctx_desc,
                    request_index=req_idx,
                    value=int(token_val),
                ))

            elif (len(k_path) == 3 and k_path[0] == "requests"
                  and isinstance(k_path[1], int)
                  and k_path[2] == "contentReferences"):
                req_idx = k_path[1]
                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]
                if isinstance(v, list):
                    for ref in v:
                        if not isinstance(ref, dict):
                            continue
                        path = _safe_get(ref, "reference", "path", default=None)
                        if path and isinstance(path, str):
                            rd.content_references.append(path)

            elif (len(k_path) == 3 and k_path[0] == "requests"
                  and isinstance(k_path[1], int)
                  and k_path[2] == "result"):
                req_idx = k_path[1]
                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]
                rd.has_result = True
                rd.result_line = line_num

                if isinstance(v, dict):
                    timings = v.get("timings", {})
                    rd.first_progress_ms = timings.get("firstProgress", 0)
                    rd.total_elapsed_ms = timings.get("totalElapsed", 0)

                    metadata = v.get("metadata", {})
                    rd.prompt_tokens = metadata.get("promptTokens", 0) or 0
                    rd.output_tokens_result = metadata.get("outputTokens", 0) or 0

                    tool_rounds = metadata.get("toolCallRounds", [])
                    if isinstance(tool_rounds, list):
                        rd.tool_call_rounds_count = len(tool_rounds)
                        rd.tool_call_rounds_raw = tool_rounds
                        for tr in tool_rounds:
                            if isinstance(tr, dict):
                                calls = tr.get("toolCalls", [])
                                if isinstance(calls, list):
                                    for tc in calls:
                                        name = tc.get("name", "")
                                        if name and name not in rd.tool_names:
                                            rd.tool_names.append(name)
                                thinking = tr.get("thinking", {})
                                if isinstance(thinking, dict):
                                    rd.thinking_tokens += thinking.get("tokens", 0)

                # Mark last completion_update for this request as final
                _mark_final_completion(session.timeline, req_idx)

        elif kind == 2:
            # Array replace
            k_path = obj.get("k", [])
            v = obj.get("v", [])

            if k_path == ["requests"] and isinstance(v, list):
                # New request(s) being added
                for item in v:
                    if not isinstance(item, dict):
                        continue
                    # Figure out the index
                    req_idx = len(requests_dict)
                    # Check if this is an existing request being updated
                    req_id = item.get("requestId", "")
                    found_idx = None
                    for idx, rd in requests_dict.items():
                        if rd.request_id == req_id and req_id:
                            found_idx = idx
                            break
                    if found_idx is not None:
                        req_idx = found_idx
                    else:
                        # Check based on count
                        req_idx = len(requests_dict)

                    if req_idx not in requests_dict:
                        requests_dict[req_idx] = RequestData(index=req_idx)

                    rd = requests_dict[req_idx]
                    rd.request_id = item.get("requestId", rd.request_id)
                    rd.timestamp = item.get("timestamp", rd.timestamp)
                    rd.model_id = item.get("modelId", rd.model_id)
                    rd.request_line = line_num

                    msg = item.get("message", {})
                    if isinstance(msg, dict) and msg.get("text"):
                        rd.prompt_text = msg["text"]

                    agent = item.get("agent", {})
                    if isinstance(agent, dict):
                        rd.extension_version = agent.get("extensionVersion", "")
                        if not session.extension_version:
                            session.extension_version = rd.extension_version

                    mode_info = item.get("modeInfo", {})
                    if isinstance(mode_info, dict):
                        rd.mode = mode_info.get("kind", "")

                    # Flush user typing events if pending
                    if input_text_drafts and input_text_first_line:
                        final_text = input_text_drafts[-1][1] if input_text_drafts else ""
                        trunc = final_text[:120] + ("..." if len(final_text) > 120 else "")
                        title_part = f' · Title auto-set: "{session.custom_title}"' if session.custom_title else ""
                        session.timeline.append(TimelineEvent(
                            line_number=input_text_first_line,
                            line_end=input_text_last_line or input_text_first_line,
                            kind=1,
                            event_type="user_typing",
                            dot_color="#888",
                            title=f"Lines {input_text_first_line}–{input_text_last_line} — kind:1  User types their prompt ({len(input_text_drafts)} drafts)",
                            subtitle=f'{trunc}{title_part}',
                        ))
                        input_text_drafts.clear()
                        input_text_first_line = None
                        input_text_last_line = None

                    # Context refs subtitle
                    ref_str = ""
                    if rd.content_references:
                        ref_str = f"  ·  context ref: {rd.content_references[0].split('/')[-1] if '/' in rd.content_references[0] else rd.content_references[0]}"

                    round_num = req_idx + 1
                    short_id = rd.request_id[:8] if rd.request_id else "unknown"
                    ts_str = datetime.fromtimestamp(rd.timestamp / 1000, tz=timezone.utc).strftime("%H:%M:%S") if rd.timestamp else ""

                    session.timeline.append(TimelineEvent(
                        line_number=line_num,
                        kind=2,
                        event_type="request_submitted",
                        dot_color="#1D9E75",
                        title=f"Line {line_num} — kind:2  Round {round_num} submitted",
                        subtitle=f"request_{short_id}  ·  ts {ts_str}  ·  {rd.mode or session.mode} mode{ref_str}",
                        request_index=req_idx,
                    ))

            elif (len(k_path) == 3 and k_path[0] == "requests"
                  and isinstance(k_path[1], int)
                  and k_path[2] == "response"):
                req_idx = k_path[1]
                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]

                if isinstance(v, list):
                    tool_calls_in_batch = []
                    for item in v:
                        if isinstance(item, dict):
                            rd.response_items.append(item)
                            if item.get("kind") == "toolInvocationSerialized":
                                inv_msg = item.get("invocationMessage", "")
                                if not isinstance(inv_msg, str):
                                    inv_msg = str(inv_msg) if inv_msg else ""
                                tool_kind = _safe_get(item, "toolSpecificData", "kind", default="")
                                if not isinstance(tool_kind, str):
                                    tool_kind = str(tool_kind) if tool_kind else ""
                                tool_calls_in_batch.append(inv_msg or tool_kind or "tool")

                    if tool_calls_in_batch:
                        # Group tool fire events
                        key = f"tools_{req_idx}"
                        if key not in tool_fire_ranges:
                            tool_fire_ranges[key] = {
                                "first": line_num, "last": line_num,
                                "tools": set(), "request_idx": req_idx, "count": 0,
                            }
                        tf = tool_fire_ranges[key]
                        tf["last"] = line_num
                        tf["tools"].update(tool_calls_in_batch)
                        tf["count"] += len(tool_calls_in_batch)

    # Flush any remaining user typing events
    if input_text_drafts and input_text_first_line:
        final_text = input_text_drafts[-1][1] if input_text_drafts else ""
        trunc = final_text[:120] + ("..." if len(final_text) > 120 else "")
        title_part = f' · Title auto-set: "{session.custom_title}"' if session.custom_title else ""
        session.timeline.append(TimelineEvent(
            line_number=input_text_first_line,
            line_end=input_text_last_line or input_text_first_line,
            kind=1,
            event_type="user_typing",
            dot_color="#888",
            title=f"Lines {input_text_first_line}–{input_text_last_line} — kind:1  User types their prompt ({len(input_text_drafts)} drafts)",
            subtitle=f'{trunc}{title_part}',
        ))

    # Add tool fire events to timeline
    for key, tf in tool_fire_ranges.items():
        tools_str = ", ".join(sorted(tf["tools"]))
        if len(tools_str) > 100:
            tools_str = tools_str[:100] + "..."
        session.timeline.append(TimelineEvent(
            line_number=tf["first"],
            line_end=tf["last"],
            kind=2,
            event_type="tools_fire",
            dot_color="#378ADD",
            title=f"Lines {tf['first']}–{tf['last']} — kind:2  Agent tools fire ({tf['count']} tool calls)",
            subtitle=tools_str,
            request_index=tf["request_idx"],
        ))

    # Sort timeline by line number
    session.timeline.sort(key=lambda e: e.line_number)

    # Build requests list in order
    for idx in sorted(requests_dict.keys()):
        session.requests.append(requests_dict[idx])

    # Compute session span
    if session.requests:
        last_event_ts = 0
        for rd in session.requests:
            end_ts = rd.timestamp + rd.total_elapsed_ms
            if end_ts > last_event_ts:
                last_event_ts = end_ts
        session.span_ms = last_event_ts - session.creation_date if session.creation_date else 0

    # Extension info
    if session.requests and session.requests[0].extension_version:
        session.extension_version = session.requests[0].extension_version
    session.extension_name = "GitHub Copilot Chat"

    return session


def _get_completion_context_desc(update_num: int, round_num: int, is_final: bool, title: str) -> str:
    """Get contextual description for a completionTokens update."""
    if is_final:
        return f"Round {round_num} complete. This is the total output tokens for this prompt → response."
    if update_num == 1:
        return "Model emitted initial thinking blocks. Running total so far."
    elif update_num == 2:
        return "Post sub-agent synthesis. More output generated."
    elif update_num == 3:
        hint = f" — {title}" if title else ""
        return f"Large batch of output tokens{hint} being generated."
    else:
        return f"Streaming update #{update_num}. Running total continues."


def _mark_final_completion(timeline: list, req_idx: int):
    """Mark the last completion_update event for a request index as final."""
    last_event = None
    for event in timeline:
        if event.event_type == "completion_update" and event.request_index == req_idx:
            last_event = event
    if last_event:
        round_num = req_idx + 1
        # Update subtitle to final message
        last_event.subtitle = f"Round {round_num} complete. This is the total output tokens for this prompt → response."
        # Update title to include "final" label
        if "final" not in last_event.title:
            last_event.title = last_event.title.replace("completionTokens update", "completionTokens update (final)")


def format_elapsed(ms: float) -> str:
    """Format milliseconds as human-readable elapsed time."""
    if ms <= 0:
        return "in progress"
    seconds = ms / 1000
    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    return f"{seconds:.1f}s"


def format_span(ms: float) -> str:
    """Format span in ms to ~Xm or ~Xh Xm."""
    if ms <= 0:
        return "N/A"
    minutes = ms / 60000
    if minutes >= 60:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"~{hours}h {mins}m"
    return f"~{int(minutes)}m"
