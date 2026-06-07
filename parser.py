"""JSONL parsing logic for Copilot Session Analyser.

Supports two JSONL formats:
- chatSessions (CRDT patch log, kind:0/1/2) — VS Code core session persistence
- transcripts (event stream, type-based) — Copilot extension conversation log
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ToolExecution:
    """A single tool execution event (from transcripts)."""
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    success: bool = False
    start_timestamp: str = ""
    end_timestamp: str = ""


@dataclass
class TranscriptTurn:
    """A single assistant turn (from transcripts)."""
    turn_id: str = ""
    turn_index: int = 0
    start_timestamp: str = ""
    end_timestamp: str = ""
    messages: list = field(default_factory=list)
    tool_executions: list = field(default_factory=list)
    total_content_length: int = 0
    has_reasoning: bool = False


@dataclass
class TranscriptData:
    """Parsed transcript data."""
    session_id: str = ""
    start_time: str = ""
    version: int = 0
    producer: str = ""
    copilot_version: str = ""
    vscode_version: str = ""

    user_messages: list = field(default_factory=list)
    turns: list = field(default_factory=list)
    tool_executions: list = field(default_factory=list)

    timeline: list = field(default_factory=list)

    total_lines: int = 0
    total_tool_calls: int = 0
    total_tool_successes: int = 0
    total_tool_failures: int = 0
    unique_tools: list = field(default_factory=list)
    tool_usage_counts: dict = field(default_factory=dict)


@dataclass
class RequestData:
    """Parsed data for a single request/round."""
    index: int = 0
    request_id: str = ""
    response_id: str = ""
    timestamp: int = 0
    model_id: str = ""
    prompt_text: str = ""
    mode: str = ""
    mode_name: str = ""
    extension_version: str = ""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    output_tokens_result: int = 0
    completion_token_history: list = field(default_factory=list)

    first_progress_ms: float = 0
    total_elapsed_ms: float = 0
    elapsed_ms: int = 0

    credits: str = ""

    model_state_value: int = 0
    completed_at: int = 0

    tool_call_rounds_count: int = 0
    tool_names: list = field(default_factory=list)
    tool_ids: list = field(default_factory=list)
    tool_call_rounds_raw: list = field(default_factory=list)

    content_references: list = field(default_factory=list)
    response_items: list = field(default_factory=list)
    response_kind_counts: dict = field(default_factory=dict)

    result_line: int = 0
    request_line: int = 0
    has_result: bool = False
    thinking_tokens: int = 0

    variable_files: list = field(default_factory=list)
    followups: list = field(default_factory=list)


@dataclass
class TimelineEvent:
    """A single event in the session timeline."""
    line_number: int = 0
    line_end: int = 0
    kind: int = 0
    event_type: str = ""
    dot_color: str = "#888"
    title: str = ""
    subtitle: str = ""
    request_index: int = -1
    value: object = None
    timestamp: str = ""


@dataclass
class SessionData:
    """Fully parsed session data."""
    file_format: str = ""

    session_id: str = ""
    creation_date: int = 0
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
    initial_location: str = ""
    version: int = 0

    capabilities: dict = field(default_factory=dict)

    input_cost: int = 0
    output_cost: int = 0
    cache_cost: int = 0
    price_category: str = ""
    pricing_display: str = ""

    requests: list = field(default_factory=list)
    timeline: list = field(default_factory=list)

    total_lines: int = 0
    custom_title: str = ""
    span_ms: float = 0

    transcript: TranscriptData = field(default_factory=TranscriptData)


def _safe_get(obj, *keys, default=None):
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
    if n is None:
        return "N/A"
    return f"{n:,}"


def detect_format(first_line: str) -> str:
    try:
        obj = json.loads(first_line)
        if "kind" in obj:
            return "chatSession"
        elif "type" in obj:
            return "transcript"
    except json.JSONDecodeError:
        pass
    return "unknown"


def parse_session(file_bytes: bytes) -> SessionData:
    text = file_bytes.decode("utf-8", errors="replace")
    lines = text.strip().split("\n")
    if not lines:
        session = SessionData()
        session.file_format = "unknown"
        return session

    fmt = detect_format(lines[0])
    if fmt == "transcript":
        return _parse_transcript(lines)
    else:
        return _parse_chat_session(lines)


# ─── Transcript Parser ──────────────────────────────────────────────────────

def _parse_transcript(lines: list[str]) -> SessionData:
    session = SessionData()
    session.file_format = "transcript"
    session.total_lines = len(lines)
    td = TranscriptData()
    td.total_lines = len(lines)

    current_turn = None
    turn_index = 0
    tool_starts = {}

    for line_idx, line_text in enumerate(lines):
        line_num = line_idx + 1
        line_text = line_text.strip()
        if not line_text:
            continue
        try:
            obj = json.loads(line_text)
        except json.JSONDecodeError:
            continue

        event_type = obj.get("type", "")
        data = obj.get("data", {})
        if not isinstance(data, dict):
            data = {}
        timestamp = obj.get("timestamp", "")
        event_id = obj.get("id", "")

        if event_type == "session.start":
            td.session_id = data.get("sessionId", "")
            td.start_time = data.get("startTime", timestamp)
            td.version = data.get("version", 0)
            td.producer = data.get("producer", "")
            td.copilot_version = data.get("copilotVersion", "")
            td.vscode_version = data.get("vscodeVersion", "")
            session.session_id = td.session_id
            session.extension_version = td.copilot_version

            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="session_start", dot_color="#7F77DD",
                title=f"Line {line_num} — session.start",
                subtitle=f"Producer: {td.producer}  ·  Copilot: {td.copilot_version}  ·  VS Code: {td.vscode_version}",
                timestamp=timestamp,
            ))

        elif event_type == "user.message":
            content = data.get("content", "")
            attachments = data.get("attachments", [])
            td.user_messages.append({"content": content, "attachments": attachments, "timestamp": timestamp, "id": event_id})
            trunc = content[:120] + ("..." if len(content) > 120 else "")
            attach_str = f"  ·  {len(attachments)} attachments" if attachments else ""
            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="user_message", dot_color="#1D9E75",
                title=f"Line {line_num} — user.message",
                subtitle=f"{trunc}{attach_str}", timestamp=timestamp,
            ))

        elif event_type == "assistant.turn_start":
            turn_id = data.get("turnId", "")
            current_turn = TranscriptTurn(turn_id=turn_id, turn_index=turn_index, start_timestamp=timestamp)
            turn_index += 1
            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="turn_start", dot_color="#378ADD",
                title=f"Line {line_num} — assistant.turn_start (Turn {turn_index})",
                subtitle=f"turnId: {turn_id[:12]}...", timestamp=timestamp,
            ))

        elif event_type == "assistant.message":
            content = data.get("content", "")
            reasoning = data.get("reasoningText", "")
            tool_requests = data.get("toolRequests", [])
            msg_data = {"messageId": data.get("messageId", ""), "content": content, "reasoningText": reasoning, "toolRequests": tool_requests}

            if current_turn:
                current_turn.messages.append(msg_data)
                current_turn.total_content_length += len(content)
                if reasoning:
                    current_turn.has_reasoning = True

            tool_req_names = [tr.get("name", "") for tr in tool_requests if isinstance(tr, dict)]
            tool_str = f"  ·  tools: {', '.join(tool_req_names)}" if tool_req_names else ""
            content_trunc = content[:80] + ("..." if len(content) > 80 else "") if content else "(no content)"
            reasoning_str = f"  ·  reasoning ({len(reasoning)} chars)" if reasoning else ""

            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="assistant_message", dot_color="#378ADD",
                title=f"Line {line_num} — assistant.message",
                subtitle=f"{content_trunc}{reasoning_str}{tool_str}", timestamp=timestamp,
            ))

        elif event_type == "assistant.turn_end":
            if current_turn:
                current_turn.end_timestamp = timestamp
                td.turns.append(current_turn)
                current_turn = None
            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="turn_end", dot_color="#888",
                title=f"Line {line_num} — assistant.turn_end",
                subtitle=f"Turn {turn_index} completed", timestamp=timestamp,
            ))

        elif event_type == "tool.execution_start":
            tool_call_id = data.get("toolCallId", "")
            tool_name = data.get("toolName", "")
            arguments = data.get("arguments", {})
            te = ToolExecution(tool_call_id=tool_call_id, tool_name=tool_name,
                               arguments=arguments if isinstance(arguments, dict) else {},
                               start_timestamp=timestamp)
            tool_starts[tool_call_id] = te
            if tool_name:
                td.tool_usage_counts[tool_name] = td.tool_usage_counts.get(tool_name, 0) + 1
                if tool_name not in td.unique_tools:
                    td.unique_tools.append(tool_name)

            arg_keys = list(arguments.keys())[:3] if isinstance(arguments, dict) else []
            arg_summary = f"  ·  args: {', '.join(arg_keys)}" if arg_keys else ""
            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="tool_start", dot_color="#EF9F27",
                title=f"Line {line_num} — tool.execution_start: {tool_name}",
                subtitle=f"callId: {tool_call_id[:12]}...{arg_summary}", timestamp=timestamp,
            ))

        elif event_type == "tool.execution_complete":
            tool_call_id = data.get("toolCallId", "")
            success = data.get("success", False)
            td.total_tool_calls += 1
            if success:
                td.total_tool_successes += 1
            else:
                td.total_tool_failures += 1

            if tool_call_id in tool_starts:
                te = tool_starts[tool_call_id]
                te.success = success
                te.end_timestamp = timestamp
                td.tool_executions.append(te)
                if current_turn:
                    current_turn.tool_executions.append(te)

            tool_name = tool_starts.get(tool_call_id, ToolExecution()).tool_name
            status_str = "✓ success" if success else "✗ failed"
            td.timeline.append(TimelineEvent(
                line_number=line_num, event_type="tool_complete",
                dot_color="#1D9E75" if success else "#E54D42",
                title=f"Line {line_num} — tool.execution_complete: {tool_name}",
                subtitle=f"{status_str}  ·  callId: {tool_call_id[:12]}...", timestamp=timestamp,
            ))

    session.transcript = td
    session.total_lines = td.total_lines
    return session


# ─── ChatSession Parser ─────────────────────────────────────────────────────

def _parse_chat_session(lines: list[str]) -> SessionData:
    session = SessionData()
    session.file_format = "chatSession"
    session.total_lines = len(lines)

    requests_dict: dict[int, RequestData] = {}
    input_text_drafts = []
    input_text_first_line = None
    input_text_last_line = None
    completion_update_counters: dict[int, int] = {}
    tool_fire_ranges = {}

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
            v = obj.get("v", {})
            session.session_id = v.get("sessionId", "")
            session.creation_date = v.get("creationDate", 0)
            session.version = v.get("version", 0)
            session.initial_location = v.get("initialLocation", "")

            model_meta = _safe_get(v, "inputState", "selectedModel", "metadata", default={})
            session.model_name = model_meta.get("name", "Unknown Model")
            session.model_id = model_meta.get("id", "")
            session.multiplier = model_meta.get("multiplier", "1x")
            session.multiplier_numeric = model_meta.get("multiplierNumeric", 1.0)
            session.max_input_tokens = model_meta.get("maxInputTokens", 0)
            session.max_output_tokens = model_meta.get("maxOutputTokens", 0)
            session.input_cost = model_meta.get("inputCost", 0)
            session.output_cost = model_meta.get("outputCost", 0)
            session.cache_cost = model_meta.get("cacheCost", 0)
            session.price_category = model_meta.get("priceCategory", "")
            session.pricing_display = model_meta.get("pricing", "")
            caps = model_meta.get("capabilities", {})
            if isinstance(caps, dict):
                session.capabilities = caps
            auth = model_meta.get("auth", {})
            session.account_label = auth.get("accountLabel", "")
            mode_info = _safe_get(v, "inputState", "mode", default={})
            session.mode = mode_info.get("id", "") if isinstance(mode_info, dict) else ""

            subtitle_parts = [
                f"Model: {session.model_name}", f"Mode: {session.mode}",
                f"Account: {session.account_label}",
                f"Max input: {_format_number(session.max_input_tokens)} tok",
                f"Max output: {_format_number(session.max_output_tokens)} tok",
            ]
            if session.pricing_display:
                subtitle_parts.append(f"Pricing: {session.pricing_display}")
            session.timeline.append(TimelineEvent(
                line_number=line_num, kind=0, event_type="session_init", dot_color="#7F77DD",
                title=f"Line {line_num} — kind:0  Session created",
                subtitle="  ·  ".join(subtitle_parts),
            ))

        elif kind == 1:
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
                session.timeline.append(TimelineEvent(
                    line_number=line_num, kind=1, event_type="pending_edits", dot_color="#888",
                    title=f"Line {line_num} — hasPendingEdits → {v}",
                    subtitle="Editor edits in progress",
                ))

            elif len(k_path) == 3 and k_path[0] == "requests" and isinstance(k_path[1], int):
                req_idx = k_path[1]
                field_name = k_path[2]
                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]

                if field_name == "completionTokens":
                    token_val = v if isinstance(v, (int, float)) else 0
                    rd.completion_token_history.append((line_num, int(token_val)))
                    rd.completion_tokens = int(token_val)
                    if req_idx not in completion_update_counters:
                        completion_update_counters[req_idx] = 0
                    completion_update_counters[req_idx] += 1
                    update_num = completion_update_counters[req_idx]
                    history = rd.completion_token_history
                    prev_val = history[-2][1] if len(history) >= 2 else 0
                    delta = int(token_val) - prev_val
                    delta_str = f"+{_format_number(delta)}" if delta > 0 else ""
                    ctx_desc = _get_completion_context_desc(update_num, req_idx + 1, False, session.custom_title)
                    title = f"Line {line_num} — completionTokens update #{update_num}  →  {_format_number(int(token_val))}"
                    if delta_str:
                        title += f'  <span class="delta-badge">{delta_str}</span>'
                    session.timeline.append(TimelineEvent(
                        line_number=line_num, kind=1, event_type="completion_update", dot_color="#EF9F27",
                        title=title, subtitle=ctx_desc, request_index=req_idx, value=int(token_val),
                    ))

                elif field_name == "elapsedMs":
                    rd.elapsed_ms = v if isinstance(v, (int, float)) else 0

                elif field_name == "modelState":
                    if isinstance(v, dict):
                        rd.model_state_value = v.get("value", 0)
                        rd.completed_at = v.get("completedAt", 0)

                elif field_name == "followups":
                    if isinstance(v, list):
                        rd.followups = v

                elif field_name == "contentReferences":
                    if isinstance(v, list):
                        for ref in v:
                            if not isinstance(ref, dict):
                                continue
                            path = _safe_get(ref, "reference", "path", default=None)
                            if path and isinstance(path, str):
                                rd.content_references.append(path)

                elif field_name == "result":
                    rd.has_result = True
                    rd.result_line = line_num
                    if isinstance(v, dict):
                        details = v.get("details", "")
                        if isinstance(details, str) and details:
                            rd.credits = details
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
                    _mark_final_completion(session.timeline, req_idx)

        elif kind == 2:
            k_path = obj.get("k", [])
            v = obj.get("v", [])

            if k_path == ["requests"] and isinstance(v, list):
                for item in v:
                    if not isinstance(item, dict):
                        continue
                    req_idx = len(requests_dict)
                    req_id = item.get("requestId", "")
                    for idx, existing in requests_dict.items():
                        if existing.request_id == req_id and req_id:
                            req_idx = idx
                            break
                    else:
                        req_idx = len(requests_dict)

                    if req_idx not in requests_dict:
                        requests_dict[req_idx] = RequestData(index=req_idx)
                    rd = requests_dict[req_idx]
                    rd.request_id = item.get("requestId", rd.request_id)
                    rd.response_id = item.get("responseId", rd.response_id)
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
                        rd.mode_name = mode_info.get("modeName", "")
                    var_data = item.get("variableData", {})
                    if isinstance(var_data, dict):
                        for vr in var_data.get("variables", []):
                            if isinstance(vr, dict):
                                rd.variable_files.append({"kind": vr.get("kind", ""), "name": vr.get("name", ""), "value": vr.get("value", "")})

                    # Extract result from the request item (credits, tokens, timings)
                    result = item.get("result")
                    if isinstance(result, dict):
                        rd.has_result = True
                        rd.result_line = line_num
                        details = result.get("details", "")
                        if isinstance(details, str) and details:
                            rd.credits = details
                        timings = result.get("timings", {})
                        if isinstance(timings, dict):
                            rd.first_progress_ms = timings.get("firstProgress", 0) or 0
                            rd.total_elapsed_ms = timings.get("totalElapsed", 0) or 0
                        metadata = result.get("metadata", {})
                        if isinstance(metadata, dict):
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

                    if input_text_drafts and input_text_first_line:
                        final_text = input_text_drafts[-1][1]
                        trunc = final_text[:120] + ("..." if len(final_text) > 120 else "")
                        title_part = f' · Title auto-set: "{session.custom_title}"' if session.custom_title else ""
                        session.timeline.append(TimelineEvent(
                            line_number=input_text_first_line, line_end=input_text_last_line or input_text_first_line,
                            kind=1, event_type="user_typing", dot_color="#888",
                            title=f"Lines {input_text_first_line}–{input_text_last_line} — kind:1  User types their prompt ({len(input_text_drafts)} drafts)",
                            subtitle=f'{trunc}{title_part}',
                        ))
                        input_text_drafts.clear()
                        input_text_first_line = None
                        input_text_last_line = None

                    ref_str = ""
                    if rd.content_references:
                        first_ref = rd.content_references[0]
                        ref_str = f"  ·  context ref: {first_ref.split('/')[-1] if '/' in first_ref else first_ref}"
                    round_num = req_idx + 1
                    short_id = rd.request_id[:8] if rd.request_id else "unknown"
                    ts_str = datetime.fromtimestamp(rd.timestamp / 1000, tz=timezone.utc).strftime("%H:%M:%S") if rd.timestamp else ""
                    session.timeline.append(TimelineEvent(
                        line_number=line_num, kind=2, event_type="request_submitted", dot_color="#1D9E75",
                        title=f"Line {line_num} — kind:2  Round {round_num} submitted",
                        subtitle=f"request_{short_id}  ·  ts {ts_str}  ·  {rd.mode or session.mode} mode{ref_str}",
                        request_index=req_idx,
                    ))

            elif (len(k_path) == 3 and k_path[0] == "requests"
                  and isinstance(k_path[1], int) and k_path[2] == "response"):
                req_idx = k_path[1]
                if req_idx not in requests_dict:
                    requests_dict[req_idx] = RequestData(index=req_idx)
                rd = requests_dict[req_idx]
                if isinstance(v, list):
                    tool_calls_in_batch = []
                    for item in v:
                        if isinstance(item, dict):
                            rd.response_items.append(item)
                            item_kind = item.get("kind", "")
                            if isinstance(item_kind, str) and item_kind:
                                rd.response_kind_counts[item_kind] = rd.response_kind_counts.get(item_kind, 0) + 1
                            if item_kind == "toolInvocationSerialized":
                                tool_id = item.get("toolId", "")
                                if isinstance(tool_id, str) and tool_id and tool_id not in rd.tool_ids:
                                    rd.tool_ids.append(tool_id)
                                inv_msg = item.get("invocationMessage", "")
                                if not isinstance(inv_msg, str):
                                    inv_msg = str(inv_msg) if inv_msg else ""
                                tool_kind = _safe_get(item, "toolSpecificData", "kind", default="")
                                if not isinstance(tool_kind, str):
                                    tool_kind = str(tool_kind) if tool_kind else ""
                                tool_calls_in_batch.append(inv_msg or tool_kind or "tool")
                    if tool_calls_in_batch:
                        key = f"tools_{req_idx}"
                        if key not in tool_fire_ranges:
                            tool_fire_ranges[key] = {"first": line_num, "last": line_num, "tools": set(), "request_idx": req_idx, "count": 0}
                        tf = tool_fire_ranges[key]
                        tf["last"] = line_num
                        tf["tools"].update(tool_calls_in_batch)
                        tf["count"] += len(tool_calls_in_batch)

    # Flush remaining
    if input_text_drafts and input_text_first_line:
        final_text = input_text_drafts[-1][1]
        trunc = final_text[:120] + ("..." if len(final_text) > 120 else "")
        title_part = f' · Title auto-set: "{session.custom_title}"' if session.custom_title else ""
        session.timeline.append(TimelineEvent(
            line_number=input_text_first_line, line_end=input_text_last_line or input_text_first_line,
            kind=1, event_type="user_typing", dot_color="#888",
            title=f"Lines {input_text_first_line}–{input_text_last_line} — kind:1  User types their prompt ({len(input_text_drafts)} drafts)",
            subtitle=f'{trunc}{title_part}',
        ))

    for key, tf in tool_fire_ranges.items():
        tools_str = ", ".join(sorted(tf["tools"]))
        if len(tools_str) > 100:
            tools_str = tools_str[:100] + "..."
        session.timeline.append(TimelineEvent(
            line_number=tf["first"], line_end=tf["last"], kind=2,
            event_type="tools_fire", dot_color="#378ADD",
            title=f"Lines {tf['first']}–{tf['last']} — kind:2  Agent tools fire ({tf['count']} tool calls)",
            subtitle=tools_str, request_index=tf["request_idx"],
        ))

    session.timeline.sort(key=lambda e: e.line_number)
    for idx in sorted(requests_dict.keys()):
        session.requests.append(requests_dict[idx])

    if session.requests:
        last_event_ts = 0
        for rd in session.requests:
            end_ts = rd.timestamp + rd.total_elapsed_ms
            if end_ts > last_event_ts:
                last_event_ts = end_ts
        session.span_ms = last_event_ts - session.creation_date if session.creation_date else 0

    if session.requests and session.requests[0].extension_version:
        session.extension_version = session.requests[0].extension_version
    session.extension_name = "GitHub Copilot Chat"
    return session


def _get_completion_context_desc(update_num, round_num, is_final, title):
    if is_final:
        return f"Round {round_num} complete. This is the total output tokens for this prompt → response."
    if update_num == 1:
        return "Model emitted initial thinking blocks. Running total so far."
    elif update_num == 2:
        return "Post sub-agent synthesis. More output generated."
    elif update_num == 3:
        hint = f" — {title}" if title else ""
        return f"Large batch of output tokens{hint} being generated."
    return f"Streaming update #{update_num}. Running total continues."


def _mark_final_completion(timeline, req_idx):
    last_event = None
    for event in timeline:
        if event.event_type == "completion_update" and event.request_index == req_idx:
            last_event = event
    if last_event:
        last_event.subtitle = f"Round {req_idx + 1} complete. This is the total output tokens for this prompt → response."
        if "final" not in last_event.title:
            last_event.title = last_event.title.replace("completionTokens update", "completionTokens update (final)")


def format_elapsed(ms):
    if ms <= 0:
        return "in progress"
    seconds = ms / 1000
    if seconds >= 60:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    return f"{seconds:.1f}s"


def format_span(ms):
    if ms <= 0:
        return "N/A"
    minutes = ms / 60000
    if minutes >= 60:
        return f"~{int(minutes // 60)}h {int(minutes % 60)}m"
    return f"~{int(minutes)}m"
