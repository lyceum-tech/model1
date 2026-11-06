"""Bounded fake control plane and OpenAI-compatible inference serving."""

import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_REQUEST_BYTES = 64 * 1024
MODEL = "z-ai/glm-5.3"
TEXT = "Hello from the bounded fake inference backend."
USAGE = {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16}


def authorized(header, token):
    return hmac.compare_digest(header, "Bearer " + token)


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

    def service_authorized(self):
        return authorized(self.headers.get("Authorization", ""), os.environ["SERVICE_TOKEN"])

    def endpoint_authorized(self):
        expected = hmac.new(
            os.environ["ENDPOINT_SECRET"].encode(), os.environ["DEPLOYMENT_ID"].encode(), hashlib.sha256
        ).hexdigest()
        return authorized(self.headers.get("Authorization", ""), expected)

    def caller_authorized(self):
        return authorized(self.headers.get("Authorization", ""), os.environ["CALLER_TOKEN"])

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/health":
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
        if urlsplit(self.path).path not in ("/v1/chat/completions", "/openai/v1/chat/completions"):
            self.refuse(404)
            return
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.refuse(400)
            return
        if not 0 < size <= MAX_REQUEST_BYTES:
            self.refuse(413)
            return
        raw_body = self.rfile.read(size)
        if not (self.endpoint_authorized() or self.caller_authorized()):
            self.refuse(401)
            return
        try:
            body = json.loads(raw_body)
            if body["model"] != MODEL or body["messages"] != [
                {"role": "user", "content": "Produce one short deterministic greeting."}
            ]:
                raise ValueError
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.refuse(400)
            return
        if body.get("stream") is not True:
            self.respond(
                {
                    "id": "runtime-completion",
                    "object": "chat.completion",
                    "created": 0,
                    "model": MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": TEXT},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": USAGE,
                }
            )
            return
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
        event([{"index": 0, "delta": {"content": TEXT[:21]}, "finish_reason": None}])
        event([{"index": 0, "delta": {"content": TEXT[21:]}, "finish_reason": None}])
        event([{"index": 0, "delta": {}, "finish_reason": "stop"}], USAGE)
        event([], USAGE)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


def main():
    if os.getuid() == 0:
        raise RuntimeError("The fixture must not run as root")
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.timeout = 5
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
