"""Exercise the candidate proxy and emit comparison facts, never response bodies."""

import argparse
import contextlib
import http.client
import json
import os
import time
from urllib.parse import urlsplit

from .fake_backend import MODEL

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


def plain_observation(scenario="plain", timeout=90):
    try:
        return compare(scenario, timeout)
    except (
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
    ):
        return {"scenario": scenario, "error": "response-contract-inconclusive"}


def observations(timeout=90):
    return [plain_observation(scenario, timeout) for scenario in SCENARIOS]


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
    result = observations() if args.all else plain_observation()
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
