"""Exercise the candidate proxy and emit comparison facts, never response bodies."""

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


def connection(host="inference-proxy", port=8080, timeout=20):
    if not isinstance(host, str) or urlsplit("//" + host).hostname != host or not 0 < port < 65536:
        raise ValueError("Invalid candidate endpoint")
    return http.client.HTTPConnection(host, port, timeout=timeout)


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
    if message["role"] != "assistant" or not message["content"].strip():
        raise ValueError("Completion has no assistant content")
    if choice["finish_reason"] != "stop":
        raise ValueError("Completion did not terminate normally")
    if not isinstance(document["usage"], dict):
        raise ValueError("Completion has no usage")
    return {
        "text": message["content"],
        "model": document["model"],
        "usage": document["usage"],
        "finish_reason": choice["finish_reason"],
    }


def stream(conn, timeout):
    if conn.status != 200 or conn.getheader("Content-Type", "").split(";")[0].strip() != "text/event-stream":
        raise ValueError("Candidate did not return an event stream")
    started = time.monotonic()
    size = 0
    text = []
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
                if isinstance(delta.get("content"), str):
                    text.append(delta["content"])
                reason = choice.get("finish_reason")
                if reason is not None:
                    if finish_reason is not None:
                        raise ValueError("Multiple terminal choices")
                    finish_reason = reason
    remainder = conn.read(MAX_RESPONSE_BYTES + 1)
    if remainder.strip() or len(remainder) > MAX_RESPONSE_BYTES or event_lines:
        raise ValueError("Stream has trailing data")
    if not done or finish_reason != "stop" or not "".join(text).strip() or model is None or usage is None:
        raise ValueError("Stream lacks content, usage, normal finish, or DONE")
    return {"text": "".join(text), "model": model, "usage": usage, "finish_reason": finish_reason}


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


def compare(timeout=90):
    deadline = time.monotonic() + timeout
    with contextlib.closing(connection()) as conn:
        complete = response(request(conn, {**REQUEST, "stream": False}), deadline)
    with contextlib.closing(connection()) as conn:
        assembled = stream(request(conn, {**REQUEST, "stream": True, "stream_options": {"include_usage": True}}), 30)
    if any(type(assembled[field]) is not type(complete[field]) for field in FIELDS):
        raise ValueError("Response field types differ")
    return {"scenario": "plain", "comparisons": {field: assembled[field] == complete[field] for field in FIELDS}}


def plain_observation(timeout=90):
    try:
        return compare(timeout)
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
        return {"scenario": "plain", "error": "response-contract-inconclusive"}


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
    try:
        wait_ready()
    except (TimeoutError, OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        pass
    print(json.dumps(plain_observation(), separators=(",", ":")))


if __name__ == "__main__":
    main()
