"""Bounded fake control plane and OpenAI-compatible inference serving."""

import hashlib
import hmac
import json
import os
import ssl
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

MAX_REQUEST_BYTES = 64 * 1024
MODEL = "z-ai/glm-5.3"
TEXT = "Hello from the bounded fake inference backend."
STOP_TEXT = "The bounded answer ends before the marker."
SEARCH_TEXT = "The review mountain is 2962 metres high [1]."
SEARCH_QUERY = "review mountain height"
SEARCH_TITLE = "Review mountain reference"
SEARCH_URL = "https://reference.invalid/review-mountain"
SEARCH_SNIPPET = "The review mountain has a surveyed height of 2962 metres."
SEARCH_CALL_ID = "call_review_search"
TOOL_CALL_ID = "call_review_weather"
TOOL_ARGUMENTS = '{"location":"Zurich","unit":"celsius"}'
STOP_MARKER = "REVIEW-STOP-MARKER"
USAGE = {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16}
MESSAGES = dict.fromkeys(
    ("plain", "tools", "search", "stop-string"),
    [{"role": "user", "content": "Produce one short deterministic greeting."}],
)
NORM_MESSAGES = [{"role": "user", "content": "Normalization probe request."}]
ARG_MESSAGES = [{"role": "user", "content": "Argument shape probe request."}]
SLOW_MESSAGES = [{"role": "user", "content": "Slow stream probe request."}]
INVALID_MESSAGES = [{"role": "user", "content": "Invalid stream probe request."}]
ERROR_PREFIX = "REVIEW-ERROR-MODE:"
ARGUMENT_SHAPES = {
    "probe_string": '"Zurich"',
    "probe_array": '["Zurich","celsius"]',
    "probe_object": '{"location":"Zurich"}',
}
SLOW_STREAM_GAP_S = 4.0
TIMEOUT_SLEEP_S = 120.0

_recording_lock = threading.Lock()
_recording = {"count": 0, "body": None}


def record_request(body):
    with _recording_lock:
        _recording["count"] += 1
        _recording["body"] = body


def recorded_request():
    with _recording_lock:
        return {"count": _recording["count"], "body": _recording["body"]}


def authorized(header, token):
    return hmac.compare_digest(header, "Bearer " + token)


def function_name(tool):
    if not isinstance(tool, dict) or not isinstance(tool.get("function"), dict):
        return None
    return tool["function"].get("name")


def tool_call(call_id, name, arguments):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def completion(message, finish_reason, usage=USAGE):
    return {
        "id": "runtime-completion",
        "object": "chat.completion",
        "created": 0,
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", **message},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        pass

    def respond(self, data, status=200):
        body = json.dumps(data, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        self.wfile.write(body)

    def refuse(self, status=403):
        self.respond({"error": "refused"}, status)

    def raw_response(self, body, status=200, content_type="application/json", headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        if body:
            self.wfile.write(body)

    def service_authorized(self):
        return authorized(self.headers.get("Authorization", ""), os.environ["SERVICE_TOKEN"])

    def endpoint_authorized(self):
        expected = hmac.new(
            os.environ["ENDPOINT_SECRET"].encode(), os.environ["DEPLOYMENT_ID"].encode(), hashlib.sha256
        ).hexdigest()
        return authorized(self.headers.get("Authorization", ""), expected)

    def caller_authorized(self):
        return authorized(self.headers.get("Authorization", ""), os.environ["CALLER_TOKEN"])

    def request_json(self):
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.refuse(400)
            return None
        if not 0 < size <= MAX_REQUEST_BYTES:
            self.refuse(413)
            return None
        try:
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError
            return body
        except (ValueError, TypeError, json.JSONDecodeError):
            self.refuse(400)
            return None

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/__review__/recorded":
            if not self.caller_authorized():
                self.refuse(401)
            else:
                self.respond(recorded_request())
        elif parsed.path == "/health":
            self.respond({"status": "ok"})
        elif parsed.path == "/auth/v1/user":
            if not self.caller_authorized() or self.headers.get("apikey") != os.environ["SUPABASE_KEY"]:
                self.refuse(401)
            else:
                self.respond({"id": "runtime-user"})
        elif parsed.path == "/internal/auth/org-context":
            if self.headers.get("X-Lyceum-Service-Token") != os.environ["SERVICE_TOKEN"]:
                self.send_response(401)
                self.send_header("X-Lyceum-Auth-Failure", "service-token")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif not self.caller_authorized():
                self.refuse(401)
            else:
                self.respond({"org_id": "runtime-org", "allowed_providers": ["iris"]})
        elif parsed.path == "/internal/inference/serverless/models":
            if not self.service_authorized():
                self.refuse(401)
            else:
                self.respond({"models": [{"hf_model_id": MODEL}]})
        elif parsed.path in ("/v1/models", "/openai/v1/models"):
            if not (self.endpoint_authorized() or self.caller_authorized()):
                self.refuse(401)
            else:
                self.respond({"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "iris"}]})
        elif parsed.path == "/internal/inference/serverless/resolve":
            query = parse_qs(parsed.query)
            if not self.service_authorized():
                self.refuse(401)
            elif query.get("model") == [MODEL]:
                self.respond({"deployment_id": os.environ["DEPLOYMENT_ID"]})
            else:
                self.refuse(404)
        elif parsed.path == "/external/inference/get":
            query = parse_qs(parsed.query)
            if not self.service_authorized():
                self.refuse(401)
            elif query.get("deployment_id") != [os.environ["DEPLOYMENT_ID"]]:
                self.refuse(404)
            else:
                self.respond(
                    {
                        "deployment_id": os.environ["DEPLOYMENT_ID"],
                        "hf_model_id": MODEL,
                        "serving_name": MODEL,
                        "org_id": "runtime-org",
                        "status": "created",
                        "replicas": [{"replica_id": "fake-replica", "status": "running"}],
                    }
                )
        else:
            self.refuse(404)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/v1/chat/completions", "/openai/v1/chat/completions", "/v1/search"):
            self.refuse(404)
            return
        if path == "/v1/search":
            if not authorized(self.headers.get("Authorization", ""), os.environ["LINKUP_API_KEY"]):
                self.refuse(401)
                return
        elif not (self.endpoint_authorized() or self.caller_authorized()):
            body = self.request_json()
            if body is not None:
                self.refuse(401)
            return
        body = self.request_json()
        if body is None:
            return
        if path == "/v1/search":
            self.search(body)
        else:
            self.chat(body)

    def search(self, body):
        if (
            body.get("q") != SEARCH_QUERY
            or not isinstance(body["q"], str)
            or body.get("depth") != "fast"
            or body.get("outputType") != "searchResults"
            or set(body) - {"q", "depth", "outputType", "maxResults", "includeDomains", "excludeDomains"}
        ):
            self.refuse(400)
            return
        self.respond(
            {
                "results": [
                    {
                        "type": "text",
                        "name": SEARCH_TITLE,
                        "url": SEARCH_URL,
                        "content": SEARCH_SNIPPET,
                        "favicon": "",
                    }
                ]
            }
        )

    def chat(self, body):
        if body.get("model") != MODEL or not isinstance(body.get("messages"), list):
            self.refuse(400)
            return
        messages = body["messages"]
        tools = body.get("tools", [])
        if not isinstance(tools, list):
            self.refuse(400)
            return
        names = {function_name(tool) for tool in tools}
        content = messages[0].get("content") if len(messages) == 1 and isinstance(messages[0], dict) else None
        if isinstance(content, str) and content.startswith(ERROR_PREFIX):
            self.error_mode(content[len(ERROR_PREFIX):])
        elif messages == NORM_MESSAGES:
            record_request(body)
            self.completion_response({"content": TEXT}, "stop", body)
        elif messages == SLOW_MESSAGES:
            self.completion_response({"content": TEXT}, "stop", body, gap=SLOW_STREAM_GAP_S)
        elif messages == INVALID_MESSAGES:
            self.invalid_stream_response()
        elif messages == ARG_MESSAGES and names & set(ARGUMENT_SHAPES):
            name = sorted(names & set(ARGUMENT_SHAPES))[0]
            call = tool_call("call_review_shape", name, ARGUMENT_SHAPES[name])
            self.completion_response(
                {"content": None, "tool_calls": [call]}, "tool_calls", body, gap=SLOW_STREAM_GAP_S
            )
        elif (
            messages[:1] == ARG_MESSAGES
            and isinstance(messages[-1], dict)
            and messages[-1].get("role") == "tool"
            and messages[-1].get("tool_call_id") == "call_review_shape"
        ):
            self.completion_response({"content": TEXT}, "stop", body, gap=SLOW_STREAM_GAP_S)
        elif messages == MESSAGES["stop-string"] and body.get("stop") == [STOP_MARKER]:
            self.completion_response({"content": STOP_TEXT}, "stop", body)
        elif messages == MESSAGES["tools"] and "lookup_weather" in names:
            call = tool_call(TOOL_CALL_ID, "lookup_weather", TOOL_ARGUMENTS)
            self.completion_response({"content": None, "tool_calls": [call]}, "tool_calls", body)
        elif messages == MESSAGES["search"] and "web_search" in names and "web_search_options" not in body:
            call = tool_call(SEARCH_CALL_ID, "web_search", json.dumps({"query": SEARCH_QUERY}))
            self.completion_response({"content": None, "tool_calls": [call]}, "tool_calls", body)
        elif messages == MESSAGES["plain"]:
            self.completion_response({"content": TEXT}, "stop", body)
        elif (
            messages[:1] == MESSAGES["search"]
            and isinstance(messages[-1], dict)
            and messages[-1].get("role") == "tool"
            and messages[-1].get("tool_call_id") == SEARCH_CALL_ID
            and isinstance(messages[-1].get("content"), str)
            and SEARCH_URL in messages[-1]["content"]
        ):
            self.completion_response({"content": SEARCH_TEXT}, "stop", body)
        else:
            self.refuse(400)

    def error_mode(self, directive):
        mode, _, canary = directive.partition(":")
        if not canary or len(canary) > 128:
            self.refuse(400)
        elif mode == "parse-error":
            self.raw_response(b'{"id":"runtime-completion","choices":[' + canary.encode())
        elif mode == "upstream-error":
            self.respond({"error": {"message": f"upstream failure {canary}"}}, 500)
        elif mode == "redirect":
            self.raw_response(
                b"", 307, headers=(("Location", f"/v1/chat/completions?signature={canary}"),)
            )
        elif mode == "timeout":
            time.sleep(TIMEOUT_SLEEP_S)
            self.close_connection = True
        else:
            self.refuse(400)

    def invalid_stream_response(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        chunk = {
            "id": "runtime-completion",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": MODEL,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": "partial"}, "finish_reason": None}],
            "usage": None,
        }
        self.wfile.write(b"data: " + json.dumps(chunk, separators=(",", ":")).encode() + b"\n\n")
        self.wfile.write(b"data: {not-json\n\n")
        self.wfile.flush()
        self.close_connection = True

    def completion_response(self, message, finish_reason, request_body, gap=0.0):
        if request_body.get("stream") is not True:
            self.respond(completion(message, finish_reason))
            return
        self.stream_response(message, finish_reason, gap)

    def stream_response(self, message, finish_reason, gap=0.0):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def event(choices, usage=None, include_model=True):
            data = {"id": "runtime-completion", "object": "chat.completion.chunk", "created": 0}
            if include_model:
                data["model"] = MODEL
            data.update(choices=choices, usage=usage)
            self.wfile.write(b"data: " + json.dumps(data, separators=(",", ":")).encode() + b"\n\n")
            self.wfile.flush()

        event([{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}])
        text = message.get("content")
        if text:
            midpoint = len(text) // 2
            for position, part in enumerate((text[:midpoint], text[midpoint:])):
                event([{"index": 0, "delta": {"content": part}, "finish_reason": None}])
                if position == 0 and gap:
                    time.sleep(gap)
        for index, call in enumerate(message.get("tool_calls", [])):
            first = {
                "index": index,
                "id": call["id"],
                "type": "function",
                "function": {"name": call["function"]["name"], "arguments": ""},
            }
            event([{"index": 0, "delta": {"tool_calls": [first]}, "finish_reason": None}])
            if gap:
                time.sleep(gap)
            arguments = call["function"]["arguments"]
            midpoint = len(arguments) // 2
            for part in (arguments[:midpoint], arguments[midpoint:]):
                fragment = {"index": index, "function": {"arguments": part}}
                event([{"index": 0, "delta": {"tool_calls": [fragment]}, "finish_reason": None}])
        if message.get("annotations"):
            delta = {"annotations": message["annotations"]}
            event([{"index": 0, "delta": delta, "finish_reason": None}])
        event([{"index": 0, "delta": {}, "finish_reason": finish_reason}], USAGE)
        event([], USAGE)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


def certificate_server():
    directory = Path(os.environ.get("CERTIFICATE_DIR", "/certificates"))
    certificate = directory / "linkup.crt"
    key = directory / "linkup.key"
    if not certificate.is_file() or not key.is_file():
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-subj", "/CN=api.linkup.so", "-addext", "subjectAltName=DNS:api.linkup.so",
                "-keyout", str(key), "-out", str(certificate),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=30,
        )
        key.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    server = ThreadingHTTPServer(("0.0.0.0", 443), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main():
    if os.getuid() == 0:
        raise RuntimeError("The fixture must not run as root")
    tls_server = certificate_server()
    inference_server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    auxiliary_servers = (tls_server, inference_server)
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in auxiliary_servers]
    for thread in threads:
        thread.start()
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        for auxiliary in auxiliary_servers:
            auxiliary.shutdown()
            auxiliary.server_close()
        for thread in threads:
            thread.join(5)


if __name__ == "__main__":
    main()
