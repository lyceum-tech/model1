"""Exercise the candidate proxy and emit comparison facts, never response bodies."""

import argparse
import contextlib
import http.client
import json
import os
import re
import threading
import time
from urllib.parse import urlsplit

from .fake_backend import ARG_MESSAGES, ERROR_PREFIX, INVALID_MESSAGES, MODEL, NORM_MESSAGES, SLOW_MESSAGES

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
FIELDS = ("text", "model", "usage", "finish_reason")
REQUEST = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Produce one short deterministic greeting."}],
    "max_tokens": 64,
}
SCENARIOS = {
    "plain": REQUEST,
    "tools": {
        "model": MODEL,
        "messages": REQUEST["messages"],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_weather",
                    "description": "Look up the weather for one place.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location", "unit"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "max_tokens": 64,
    },
    "search": {
        "model": MODEL,
        "messages": REQUEST["messages"],
        "web_search_options": {},
        "max_tokens": 96,
    },
    "stop-string": {
        "model": MODEL,
        "messages": REQUEST["messages"],
        "stop": ["REVIEW-STOP-MARKER"],
        "max_tokens": 64,
    },
}


def connection(host="inference-proxy", port=8080, timeout=20):
    if not isinstance(host, str) or urlsplit("//" + host).hostname != host or not 0 < port < 65536:
        raise ValueError("Invalid candidate endpoint")
    return http.client.HTTPConnection(host, port, timeout=timeout)


def assistant_text(content, calls, annotations):
    if content is not None and not isinstance(content, str):
        raise ValueError("Invalid assistant content")
    if not isinstance(calls, list) or not isinstance(annotations, list):
        raise ValueError("Invalid assistant payload")
    normalized_calls = []
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise ValueError("Invalid tool call")
        function = call["function"]
        if (
            not isinstance(call.get("id"), str)
            or not call["id"]
            or call.get("type") != "function"
            or not isinstance(function.get("name"), str)
            or not function["name"]
            or not isinstance(function.get("arguments"), str)
        ):
            raise ValueError("Invalid tool call fields")
        normalized_calls.append(
            {
                "id": call["id"],
                "type": "function",
                "function": {"name": function["name"], "arguments": function["arguments"]},
            }
        )
    if not normalized_calls and not annotations:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Completion has no assistant content")
        return content
    return json.dumps(
        {"content": content or "", "tool_calls": normalized_calls, "annotations": annotations},
        sort_keys=True,
        separators=(",", ":"),
    )


def response(conn, timeout):
    if time.monotonic() > timeout:
        raise ValueError("Response deadline exceeded")
    raw = conn.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Response exceeds the byte limit")
    if conn.status != 200 or conn.getheader("Content-Type", "").split(";")[0].strip() != "application/json":
        raise ValueError("Candidate returned an unexpected response")
    document = json.loads(raw)
    if document.get("object") != "chat.completion" or len(document["choices"]) != 1:
        raise ValueError("Completion does not have one choice")
    choice = document["choices"][0]
    if choice["index"] != 0:
        raise ValueError("Unexpected choice index")
    message = choice["message"]
    if message["role"] != "assistant":
        raise ValueError("Completion has no assistant message")
    if choice["finish_reason"] not in ("stop", "tool_calls"):
        raise ValueError("Completion did not terminate normally")
    if not isinstance(document["model"], str) or not document["model"] or not isinstance(document["usage"], dict):
        raise ValueError("Completion has no model or usage")
    return {
        "text": assistant_text(message.get("content"), message.get("tool_calls", []), message.get("annotations", [])),
        "model": document["model"],
        "usage": document["usage"],
        "finish_reason": choice["finish_reason"],
    }


def extend_tool_call(calls, fragment):
    if not isinstance(fragment, dict) or type(fragment.get("index")) is not int or not 0 <= fragment["index"] <= 32:
        raise ValueError("Invalid streamed tool-call index")
    if len(calls) >= 32 and fragment["index"] not in calls:
        raise ValueError("Too many streamed tool calls")
    call = calls.setdefault(
        fragment["index"], {"id": "", "type": "", "function": {"name": "", "arguments": ""}}
    )
    for field in ("id", "type"):
        value = fragment.get(field, "")
        if not isinstance(value, str):
            raise ValueError("Invalid streamed tool call")
        call[field] += value
    function = fragment.get("function", {})
    if not isinstance(function, dict):
        raise ValueError("Invalid streamed tool function")
    for field in ("name", "arguments"):
        value = function.get(field, "")
        if not isinstance(value, str):
            raise ValueError("Invalid streamed tool function")
        call["function"][field] += value


def stream(conn, timeout):
    if conn.status != 200 or conn.getheader("Content-Type", "").split(";")[0].strip() != "text/event-stream":
        raise ValueError("Candidate did not return an event stream")
    started = time.monotonic()
    size = 0
    text = []
    calls = {}
    annotations = []
    model = None
    usage = None
    finish_reason = None
    done = False
    event_lines = []
    while True:
        if time.monotonic() - started > timeout:
            raise ValueError("Stream deadline exceeded")
        line = conn.readline(MAX_RESPONSE_BYTES + 1)
        if not line:
            break
        size += len(line)
        if size > MAX_RESPONSE_BYTES:
            raise ValueError("Stream exceeds the byte limit")
        line = line.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            if len(event_lines) >= 64:
                raise ValueError("Event exceeds the line limit")
            event_lines.append(line[5:].removeprefix(" "))
        elif not line:
            if not event_lines:
                continue
            payload = "\n".join(event_lines)
            event_lines = []
            if payload == "[DONE]":
                done = True
                break
            chunk = json.loads(payload)
            if "error" in chunk:
                raise ValueError("Stream contains an error")
            if chunk.get("object") != "chat.completion.chunk":
                raise ValueError("Unexpected chunk type")
            if "model" in chunk:
                if (
                    not isinstance(chunk["model"], str)
                    or not chunk["model"]
                    or (model is not None and model != chunk["model"])
                ):
                    raise ValueError("Inconsistent model")
                model = chunk["model"]
            if chunk.get("usage") is not None:
                if not isinstance(chunk["usage"], dict):
                    raise ValueError("Invalid usage")
                usage = chunk["usage"]
            choices = chunk.get("choices")
            if not isinstance(choices, list):
                raise ValueError("Invalid choices")
            for choice in choices:
                if choice["index"] != 0:
                    raise ValueError("Unexpected choice index")
                delta = choice.get("delta", {})
                if not isinstance(delta, dict):
                    raise ValueError("Invalid delta")
                if isinstance(delta.get("content"), str):
                    text.append(delta["content"])
                elif delta.get("content") is not None:
                    raise ValueError("Invalid streamed content")
                delta_calls = delta.get("tool_calls", [])
                if not isinstance(delta_calls, list):
                    raise ValueError("Invalid streamed tool calls")
                for fragment in delta_calls:
                    extend_tool_call(calls, fragment)
                delta_annotations = delta.get("annotations", [])
                if not isinstance(delta_annotations, list):
                    raise ValueError("Invalid streamed annotations")
                annotations.extend(delta_annotations)
                reason = choice.get("finish_reason")
                if reason is not None:
                    if finish_reason is not None:
                        raise ValueError("Multiple terminal choices")
                    finish_reason = reason
    remainder = conn.read(MAX_RESPONSE_BYTES + 1)
    if remainder.strip() or len(remainder) > MAX_RESPONSE_BYTES or event_lines:
        raise ValueError("Stream has trailing data")
    if not done or finish_reason not in ("stop", "tool_calls") or model is None or usage is None:
        raise ValueError("Stream lacks usage, normal finish, or DONE")
    return {
        "text": assistant_text("".join(text), [calls[index] for index in sorted(calls)], annotations),
        "model": model,
        "usage": usage,
        "finish_reason": finish_reason,
    }


def request(conn, payload):
    conn.request(
        "POST",
        "/openai/v1/chat/completions",
        json.dumps(payload).encode(),
        {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["CALLER_TOKEN"],
        },
    )
    return conn.getresponse()


def compare(scenario="plain", timeout=90):
    body = SCENARIOS[scenario]
    deadline = time.monotonic() + timeout
    with contextlib.closing(connection()) as conn:
        complete = response(request(conn, {**body, "stream": False}), deadline)
    with contextlib.closing(connection()) as conn:
        assembled = stream(
            request(conn, {**body, "stream": True, "stream_options": {"include_usage": True}}),
            min(30, max(0, deadline - time.monotonic())),
        )
    if any(type(assembled[field]) is not type(complete[field]) for field in FIELDS):
        raise ValueError("Response field types differ")
    expected_reason = "tool_calls" if scenario == "tools" else "stop"
    if complete["finish_reason"] != expected_reason or assembled["finish_reason"] != expected_reason:
        raise ValueError("Scenario returned the wrong terminal reason")
    if scenario in ("tools", "search"):
        payload = json.loads(complete["text"])
        required = "tool_calls" if scenario == "tools" else "annotations"
        if not payload[required]:
            raise ValueError("Scenario lacks its required assistant payload")
    if scenario == "stop-string" and "REVIEW-STOP-MARKER" in complete["text"]:
        raise ValueError("Stop marker leaked into the response")
    return {"scenario": scenario, "comparisons": {field: assembled[field] == complete[field] for field in FIELDS}}


_PROBE_ERRORS = (
    AssertionError,
    AttributeError,
    ConnectionError,
    IndexError,
    KeyError,
    TimeoutError,
    TypeError,
    ValueError,
    UnicodeError,
    http.client.HTTPException,
    OSError,
    json.JSONDecodeError,
)


def guarded(scenario, collect):
    """One scenario's transport or contract failure stays inconclusive, never a pass."""
    try:
        return collect(scenario)
    except _PROBE_ERRORS:
        return {"scenario": scenario, "error": "response-contract-inconclusive"}


def plain_observation(scenario="plain", timeout=90):
    return guarded(scenario, lambda name: compare(name, timeout))


def observations(timeout=90):
    return [plain_observation(scenario, timeout) for scenario in SCENARIOS]


CHAT_PATH = "/openai/v1/chat/completions"
MODELS_PATH = "/openai/v1/models"
# Production heartbeats every 10s against a 30s idle limit. The harness runs
# the candidate with a 1s heartbeat and keeps the same 3x ratio.
IDLE_LIMIT_MS = 3000
INVALID_VALUE = "<invalid>"
RULE_4_SCENARIOS = ("sdk", "public-routing", "response-schema")
RULE_7_SCENARIOS = ("parse-error", "timeout", "redirect", "upstream-error")
RULE_10_SCENARIOS = (
    "string-argument",
    "array-argument",
    "object-argument",
    "cancellation",
    "invalid-message",
    "queue-pressure",
)
NORM_SCENARIOS = {
    "absent": {},
    "null": {"max_tokens": None},
    "empty": {"max_tokens": ""},
    "wrong-type": {"max_tokens": [64]},
    "zero": {"max_tokens": 0},
    "negative": {"max_tokens": -5},
    "conflicting-aliases": {"max_tokens": 64, "max_completion_tokens": 32},
}
CONTRACT_FIELDS = {
    "sdk": ["id", "object", "model", "choices", "usage", "message", "finish_reason", "role", "content"],
    "public-routing": ["object", "data", "id"],
    "response-schema": [
        "id", "object", "model", "choices", "usage", "message", "finish_reason", "role", "tool_calls",
    ],
}


def http_call(method, path, payload=None, timeout=20):
    """One bounded request through the candidate; any HTTP status is an observation."""
    with contextlib.closing(connection(timeout=timeout)) as conn:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": "Bearer " + os.environ["CALLER_TOKEN"]}
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body, headers)
        result = conn.getresponse()
        raw = result.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeds the byte limit")
        return result.status, raw


def recorded():
    """Read the fixture's last normalization-probe request, as forwarded upstream."""
    with contextlib.closing(connection(host="127.0.0.1", port=8080, timeout=10)) as conn:
        conn.request(
            "GET", "/__review__/recorded", headers={"Authorization": "Bearer " + os.environ["CALLER_TOKEN"]}
        )
        result = conn.getresponse()
        raw = result.read(MAX_RESPONSE_BYTES + 1)
        if result.status != 200 or len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Fixture recording is unavailable")
        document = json.loads(raw)
        if not isinstance(document.get("count"), int) or not (
            document.get("body") is None or isinstance(document.get("body"), dict)
        ):
            raise ValueError("Fixture recording is malformed")
        return document["count"], document["body"]


def _response_fields(raw):
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError):
        return []
    if not isinstance(document, dict):
        return []
    fields = set(document)
    choices = document.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        fields |= set(choices[0])
        if isinstance(choices[0].get("message"), dict):
            fields |= set(choices[0]["message"])
    data = document.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        fields |= set(data[0])
    return sorted(fields)


def contract_fact(scenario):
    """Rule 4: status and response fields against fixed trusted contract fixtures."""
    if scenario == "public-routing":
        status, raw = http_call("GET", MODELS_PATH)
    elif scenario == "response-schema":
        status, raw = http_call("POST", CHAT_PATH, {**SCENARIOS["tools"], "stream": False})
    else:
        status, raw = http_call("POST", CHAT_PATH, {**REQUEST, "stream": False})
    return {
        "scenario": scenario,
        "actual_status": status,
        "contract_status": 200,
        "required_fields": CONTRACT_FIELDS[scenario],
        "response_fields": _response_fields(raw),
    }


def canonical(value):
    """The collector's canonical form of one sent token-limit value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return INVALID_VALUE
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else INVALID_VALUE
    if isinstance(value, str):
        text = value.strip()
        return int(text) if re.fullmatch(r"[+-]?\d+", text) else INVALID_VALUE
    return INVALID_VALUE


def _effective(body):
    """The token-limit value an upstream reads: the newer alias wins if present."""
    if not isinstance(body, dict):
        return None
    for key in ("max_completion_tokens", "max_tokens"):
        if key in body:
            return body[key]
    return None


def normalization_fact(scenario):
    """Rule 5: rejection before forwarding, or forwarding of the canonical value."""
    payload = {"model": MODEL, "messages": NORM_MESSAGES, **NORM_SCENARIOS[scenario], "stream": False}
    before, _ = recorded()
    status, _raw = http_call("POST", CHAT_PATH, payload, timeout=30)
    after, upstream = recorded()
    forwarded = after > before
    upstream_value = _effective(upstream) if forwarded else None
    normalized = canonical(_effective(payload))
    ambiguous = bool(
        forwarded
        and isinstance(upstream, dict)
        and "max_tokens" in upstream
        and "max_completion_tokens" in upstream
        and canonical(upstream["max_tokens"]) != canonical(upstream["max_completion_tokens"])
    )
    return {
        "scenario": scenario,
        "forwarded": forwarded,
        "accepted": status == 200,
        "status": status,
        "normalized": normalized,
        "validated": upstream_value if forwarded else normalized,
        "upstream_value": upstream_value,
        "ambiguous_aliases": ambiguous,
    }


def error_leak_fact(scenario):
    """Rule 7 probe half: the runtime agent adds the captured-logs search result."""
    canary = f"{os.environ['REVIEW_CANARY']}-{scenario}"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"{ERROR_PREFIX}{scenario}:{canary}"}],
        "max_tokens": 64,
        "stream": False,
    }
    status, raw = http_call("POST", CHAT_PATH, payload, timeout=100)
    leaked = canary in raw.decode("utf-8", "replace")
    return {"scenario": scenario, "canaries": [canary], "client_error": canary if leaked else f"http-{status}"}


def _record(events, turn, kind, start):
    events.append({"turn": turn, "kind": kind, "time_ms": int((time.monotonic() - start) * 1000)})


def record_stream(result, turn, start, events, cancel_after_content=False):
    """Record one streamed turn's progress kinds; also assemble its tool calls."""
    assembled = {"text": [], "tool_calls": {}}
    if result.status != 200:
        result.read(MAX_RESPONSE_BYTES + 1)
        _record(events, turn, "error", start)
        return assembled
    event_lines = []
    size = 0
    try:
        while True:
            line = result.readline(MAX_RESPONSE_BYTES + 1)
            if not line:
                _record(events, turn, "closed", start)
                return assembled
            size += len(line)
            if size > MAX_RESPONSE_BYTES:
                _record(events, turn, "error", start)
                return assembled
            line = line.decode("utf-8").rstrip("\r\n")
            if line.startswith(":"):
                _record(events, turn, "heartbeat", start)
            elif line.startswith("data:"):
                event_lines.append(line[5:].removeprefix(" "))
            elif not line and event_lines:
                payload = "\n".join(event_lines)
                event_lines = []
                if payload == "[DONE]":
                    _record(events, turn, "done", start)
                    return assembled
                try:
                    chunk = json.loads(payload)
                except (ValueError, UnicodeError):
                    _record(events, turn, "error", start)
                    return assembled
                if not isinstance(chunk, dict) or "error" in chunk:
                    _record(events, turn, "error", start)
                    return assembled
                progress = False
                for choice in chunk.get("choices") or []:
                    if not isinstance(choice, dict):
                        continue
                    delta = choice.get("delta") or {}
                    if not isinstance(delta, dict):
                        continue
                    if isinstance(delta.get("content"), str) and delta["content"]:
                        assembled["text"].append(delta["content"])
                        progress = True
                    for fragment in delta.get("tool_calls") or []:
                        try:
                            extend_tool_call(assembled["tool_calls"], fragment)
                            progress = True
                        except (ValueError, TypeError, KeyError):
                            _record(events, turn, "error", start)
                            return assembled
                if progress:
                    _record(events, turn, "content", start)
                    if cancel_after_content:
                        _record(events, turn, "closed", start)
                        return assembled
    except (TimeoutError, ConnectionError, http.client.HTTPException, OSError, UnicodeError):
        _record(events, turn, "closed", start)
    return assembled


def _stream_turn(payload, turn, start, events, cancel_after_content=False):
    conn = connection(timeout=IDLE_LIMIT_MS / 1000 + 10)
    try:
        result = request(conn, {**payload, "stream": True, "stream_options": {"include_usage": True}})
        return record_stream(result, turn, start, events, cancel_after_content)
    finally:
        conn.close()


def _shape_tool(name):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "Echo one value.",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _argument_fact(scenario):
    name = {
        "string-argument": "probe_string",
        "array-argument": "probe_array",
        "object-argument": "probe_object",
    }[scenario]
    start = time.monotonic()
    events = []
    payload = {"model": MODEL, "messages": ARG_MESSAGES, "tools": [_shape_tool(name)], "max_tokens": 64}
    assembled = _stream_turn(payload, 1, start, events)
    calls = [assembled["tool_calls"][index] for index in sorted(assembled["tool_calls"])]
    if not calls or not calls[0].get("id"):
        raise ValueError("Argument scenario produced no tool call")
    call = calls[0]
    messages = [
        *ARG_MESSAGES,
        {"role": "assistant", "content": None, "tool_calls": [call]},
        {"role": "tool", "tool_call_id": call["id"], "content": "ok"},
    ]
    _stream_turn({**payload, "messages": messages}, 2, start, events)
    return {"scenario": scenario, "events": events, "idle_limit_ms": IDLE_LIMIT_MS}


def _cancellation_fact():
    start = time.monotonic()
    events = []
    _stream_turn(
        {"model": MODEL, "messages": SLOW_MESSAGES, "max_tokens": 64},
        1,
        start,
        events,
        cancel_after_content=True,
    )
    status, _raw = http_call("GET", MODELS_PATH, timeout=15)
    if status != 200:
        raise ValueError("Candidate did not recover after cancellation")
    return {"scenario": "cancellation", "events": events, "idle_limit_ms": IDLE_LIMIT_MS}


def _queue_pressure_fact():
    payload = {"model": MODEL, "messages": SLOW_MESSAGES, "max_tokens": 64}
    ready = [threading.Event(), threading.Event()]
    occupiers = []

    def occupy(index):
        try:
            conn = connection(timeout=30)
            occupiers.append(conn)
            result = request(conn, {**payload, "stream": True, "stream_options": {"include_usage": True}})
            while True:
                line = result.readline(MAX_RESPONSE_BYTES + 1)
                if not line:
                    break
                if b"content" in line:
                    ready[index].set()
        except (TimeoutError, ConnectionError, http.client.HTTPException, OSError):
            pass
        finally:
            ready[index].set()

    threads = [threading.Thread(target=occupy, args=(index,), daemon=True) for index in range(2)]
    for thread in threads:
        thread.start()
    for signal_ready in ready:
        signal_ready.wait(timeout=20)
    start = time.monotonic()
    events = []
    try:
        _stream_turn(payload, 1, start, events)
    finally:
        for conn in occupiers:
            with contextlib.suppress(OSError):
                conn.close()
        for thread in threads:
            thread.join(timeout=5)
    if not events:
        raise ValueError("Queue pressure produced no events")
    return {"scenario": "queue-pressure", "events": events, "idle_limit_ms": IDLE_LIMIT_MS}


def stream_progress_fact(scenario):
    """Rule 10: every turn progresses within the idle limit and terminates once."""
    if scenario in ("string-argument", "array-argument", "object-argument"):
        return _argument_fact(scenario)
    if scenario == "cancellation":
        return _cancellation_fact()
    if scenario == "queue-pressure":
        return _queue_pressure_fact()
    start = time.monotonic()
    events = []
    _stream_turn({"model": MODEL, "messages": INVALID_MESSAGES, "max_tokens": 64}, 1, start, events)
    if not events:
        raise ValueError("Invalid-message scenario produced no events")
    return {"scenario": scenario, "events": events, "idle_limit_ms": IDLE_LIMIT_MS}


def all_observations(timeout=90):
    """Collect candidate-bound facts for every probe-served rule."""
    return {
        "4": [guarded(scenario, contract_fact) for scenario in RULE_4_SCENARIOS],
        "5": [guarded(scenario, normalization_fact) for scenario in NORM_SCENARIOS],
        "7": [guarded(scenario, error_leak_fact) for scenario in RULE_7_SCENARIOS],
        "9": observations(timeout),
        "10": [guarded(scenario, stream_progress_fact) for scenario in RULE_10_SCENARIOS],
    }


def wait_ready(timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with contextlib.closing(connection(timeout=5)) as conn:
                conn.request(
                    "GET", "/openai/v1/models", headers={"Authorization": "Bearer " + os.environ["CALLER_TOKEN"]}
                )
                result = conn.getresponse()
                raw = result.read(MAX_RESPONSE_BYTES + 1)
                if result.status != 200:
                    raise ValueError("Candidate readiness failed")
                data = json.loads(raw)
                if MODEL not in {entry["id"] for entry in data["data"]}:
                    raise ValueError("Candidate has no fake model")
                return
        except (TimeoutError, ConnectionRefusedError, ConnectionResetError, http.client.HTTPException, OSError):
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    try:
        wait_ready()
    except (TimeoutError, OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        pass
    result = all_observations() if args.all else plain_observation()
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
