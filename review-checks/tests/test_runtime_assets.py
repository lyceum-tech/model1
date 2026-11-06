import http.client
import io
import json
import os
import threading
import unittest
from unittest.mock import patch

from review_rules import rule_09
from runtime_assets import fake_backend, probe


class HTTPResult(io.BytesIO):
    def __init__(self, body, status=200, content_type="application/json"):
        super().__init__(body)
        self.status = status
        self.content_type = content_type

    def getheader(self, name, default=None):
        return self.content_type if name == "Content-Type" else default


def completion(**changes):
    data = {
        "text": "answer",
        "model": fake_backend.MODEL,
        "usage": {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16},
        "finish_reason": "stop",
    }
    data.update(changes)
    return data


class ContractsTest(unittest.TestCase):
    def test_valid_response_is_normalized(self):
        raw = {
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "answer"},
                    "finish_reason": "stop",
                }
            ],
            "model": fake_backend.MODEL,
            "usage": completion()["usage"],
        }
        result = probe.response(HTTPResult(json.dumps(raw).encode()), float("inf"))
        self.assertEqual(result, completion())

    def test_malformed_or_unsuccessful_completions_are_rejected(self):
        for raw in (
            b"not-json",
            b"{}",
            json.dumps({"object": "chat.completion", "choices": []}).encode(),
            b"0123456789" * (probe.MAX_RESPONSE_BYTES // 10),
        ):
            with self.subTest(raw=raw[:30]):
                with self.assertRaises((ValueError, KeyError, IndexError, json.JSONDecodeError)):
                    probe.response(HTTPResult(raw), float("inf"))
        with self.assertRaises(ValueError):
            probe.response(HTTPResult(b'{"token": "private"}', status=401), float("inf"))

    def test_stream_requires_content_usage_finish_and_done(self):
        chunks = [
            {
                "object": "chat.completion.chunk",
                "model": fake_backend.MODEL,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ans"}, "finish_reason": None}],
            },
            {
                "object": "chat.completion.chunk",
                "model": fake_backend.MODEL,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": completion()["usage"],
            },
        ]
        events = b"".join(b"data: " + json.dumps(chunk).encode() + b"\n\n" for chunk in chunks)
        self.assertEqual(
            probe.stream(HTTPResult(events + b"data: [DONE]\n\n", content_type="text/event-stream"), 5),
            completion(text="ans"),
        )
        for body in (
            events,
            b"data: not-json\n\ndata: [DONE]\n\n",
            events + b"data: [DONE]\n\ndata: {}\n\n",
            b'data: {"error": "upstream failure"}\n\ndata: [DONE]\n\n',
            events + b"data: [DONE]\n\ntrailing",
        ):
            with self.subTest(body=body[:60]):
                with self.assertRaises((ValueError, KeyError, json.JSONDecodeError)):
                    probe.stream(HTTPResult(body, content_type="text/event-stream"), 5)

    def test_stream_disagreement_is_a_real_counterexample(self):
        with (
            patch.object(probe, "response", return_value=completion()),
            patch.object(probe, "stream", return_value=completion(text="different")),
            patch.object(probe, "request"),
            patch.object(probe, "connection", return_value=http.client.HTTPConnection("fixture.invalid")),
        ):
            fact = probe.compare()
        self.assertEqual(fact["comparisons"]["text"], False)
        self.assertTrue(all(fact["comparisons"][field] for field in ("model", "usage", "finish_reason")))
        self.assertEqual(rule_09.evaluate([fact])["status"], "red")

    def test_partial_plain_result_is_explicitly_not_the_full_rule(self):
        result = rule_09.evaluate([{"scenario": "plain", "comparisons": {key: True for key in probe.FIELDS}}])
        self.assertEqual(result["status"], "yellow")
        self.assertIn("plain passed", result["reason"])
        self.assertIn("tools", result["reason"])
        self.assertIn("search", result["reason"])
        self.assertIn("stop-string", result["reason"])

    def test_malformed_comparisons_are_inconclusive(self):
        for comparisons in (None, [], {"text": True}, {key: 1 for key in probe.FIELDS}):
            with self.subTest(comparisons=comparisons):
                self.assertIsNone(rule_09.evaluate_one({"comparisons": comparisons}))
                self.assertEqual(
                    rule_09.evaluate([{"scenario": "plain", "comparisons": comparisons}])["status"], "yellow"
                )

    def test_endpoint_does_not_accept_host_injection(self):
        for host in ("example.invalid/path", "example.invalid@other.invalid", "user:pass@example.invalid"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    probe.connection(host)


class FakeBackendTest(unittest.TestCase):
    def setUp(self):
        self.values = {
            "CALLER_TOKEN": "test-caller-token",
            "SERVICE_TOKEN": "test-service-token",
            "SUPABASE_KEY": "test-supabase-key",
            "ENDPOINT_SECRET": "test-endpoint-secret",
            "DEPLOYMENT_ID": "runtime-fake-dep",
        }
        self.scope = patch.dict(os.environ, self.values)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.server = fake_backend.ThreadingHTTPServer(("127.0.0.1", 0), fake_backend.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 5)
        self.addCleanup(self.server.server_close)

    def get(self, path, token=""):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(
            "GET", path, headers={"Authorization": "Bearer " + token, "apikey": self.values["SUPABASE_KEY"]}
        )
        response = connection.getresponse()
        try:
            return response.status, response.read()
        finally:
            connection.close()

    def test_streamed_and_complete_fake_responses_match_without_disclosing_bodies(self):
        def test_connection(host="inference-proxy", port=8080, timeout=20):
            return http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=timeout)

        with patch.object(probe, "connection", test_connection):
            probe.wait_ready()
            fact = probe.plain_observation()
        self.assertEqual(fact, {"scenario": "plain", "comparisons": {field: True for field in probe.FIELDS}})
        self.assertNotIn(fake_backend.TEXT, json.dumps(fact))

    def test_control_plane_requires_synthetic_credentials_and_bound_upstream_token(self):
        self.assertEqual(self.get("/auth/v1/user")[0], 401)
        self.assertEqual(self.get("/auth/v1/user", "test-caller-token")[0], 200)
        self.assertEqual(self.get("/internal/auth/org-context", "test-caller-token")[0], 401)
        self.assertEqual(self.get("/internal/inference/serverless/models", "wrong")[0], 401)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        body = json.dumps(probe.REQUEST).encode()
        connection.request("POST", "/v1/chat/completions", body, {"Authorization": "Bearer wrong"})
        self.assertEqual(connection.getresponse().status, 401)
        connection.close()

    def test_fixture_refuses_to_start_as_root(self):
        with patch.object(os, "getuid", return_value=0):
            with self.assertRaises(RuntimeError):
                fake_backend.main()


if __name__ == "__main__":
    unittest.main()
