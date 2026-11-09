import http.client
import io
import json
import os
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

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


def chunk(delta, reason=None, usage=None):
    return {
        "object": "chat.completion.chunk",
        "model": fake_backend.MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": reason}],
        "usage": usage,
    }


def sse(chunks):
    return b"".join(b"data: " + json.dumps(item).encode() + b"\n\n" for item in chunks) + b"data: [DONE]\n\n"


def citation():
    return {
        "type": "url_citation",
        "url_citation": {
            "url": fake_backend.SEARCH_URL,
            "title": fake_backend.SEARCH_TITLE,
            "start_index": 38,
            "end_index": 41,
        },
    }


class ContractsTest(unittest.TestCase):
    def test_valid_response_is_normalized(self):
        raw = fake_backend.completion({"content": "answer"}, "stop")
        result = probe.response(HTTPResult(json.dumps(raw).encode()), float("inf"))
        self.assertEqual(result, completion())

    def test_tool_calls_and_annotations_have_matching_stream_semantics(self):
        call = fake_backend.tool_call(fake_backend.TOOL_CALL_ID, "lookup_weather", fake_backend.TOOL_ARGUMENTS)
        message = {"content": None, "tool_calls": [call], "annotations": [citation()]}
        raw = fake_backend.completion(message, "tool_calls")
        complete = probe.response(HTTPResult(json.dumps(raw).encode()), float("inf"))
        pieces = fake_backend.TOOL_ARGUMENTS[:12], fake_backend.TOOL_ARGUMENTS[12:]
        chunks = [
            chunk({"role": "assistant", "content": ""}),
            chunk({
                "tool_calls": [{
                    "index": 0,
                    "id": call["id"],
                    "type": "function",
                    "function": {"name": "lookup_weather", "arguments": ""},
                }]
            }),
            chunk({"tool_calls": [{"index": 0, "function": {"arguments": pieces[0]}}]}),
            chunk({"tool_calls": [{"index": 0, "function": {"arguments": pieces[1]}}]}),
            chunk({"annotations": [citation()]}),
            chunk({}, "tool_calls", completion()["usage"]),
        ]
        assembled = probe.stream(HTTPResult(sse(chunks), content_type="text/event-stream"), 5)
        self.assertEqual(assembled, complete)
        self.assertEqual(json.loads(complete["text"])["tool_calls"], [call])
        self.assertEqual(json.loads(complete["text"])["annotations"], [citation()])
        self.assertEqual(complete["finish_reason"], "tool_calls")

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
            chunk({"role": "assistant", "content": "ans"}),
            chunk({}, "stop", completion()["usage"]),
        ]
        events = b"".join(b"data: " + json.dumps(item).encode() + b"\n\n" for item in chunks)
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

    def test_independent_scenario_failures_do_not_hide_other_results(self):
        facts = [{"scenario": name, "comparisons": {field: True for field in probe.FIELDS}} for name in probe.SCENARIOS]
        effects = [facts[0], ValueError("malformed tools"), facts[2], facts[3]]
        with patch.object(probe, "compare", side_effect=effects):
            observed = probe.observations()
        self.assertEqual(observed[0], facts[0])
        self.assertEqual(observed[1], {"scenario": "tools", "error": "response-contract-inconclusive"})
        self.assertEqual(observed[2:], facts[2:])
        self.assertEqual(rule_09.evaluate(observed)["status"], "yellow")

    def test_partial_plain_result_is_explicitly_not_the_full_rule(self):
        result = rule_09.evaluate([{"scenario": "plain", "comparisons": {key: True for key in probe.FIELDS}}])
        self.assertEqual(result["status"], "yellow")
        self.assertIn("plain passed", result["reason"])
        self.assertIn("tools", result["reason"])
        self.assertIn("search", result["reason"])
        self.assertIn("stop-string", result["reason"])

    def test_all_four_passing_scenarios_complete_the_rule(self):
        facts = [{"scenario": name, "comparisons": {field: True for field in probe.FIELDS}} for name in probe.SCENARIOS]
        self.assertEqual(tuple(probe.SCENARIOS), rule_09.REQUIRED)
        self.assertEqual(rule_09.evaluate(facts)["status"], "green")

    def test_malformed_comparisons_are_inconclusive(self):
        for comparisons in (None, [], {"text": True}, {key: 1 for key in probe.FIELDS}):
            with self.subTest(comparisons=comparisons):
                self.assertIsNone(rule_09.evaluate_one({"comparisons": comparisons}))
                self.assertEqual(
                    rule_09.evaluate([{"scenario": "plain", "comparisons": comparisons}])["status"], "yellow"
                )

    def test_search_uses_hosted_options_not_a_client_search_function(self):
        self.assertEqual(probe.SCENARIOS["search"]["web_search_options"], {})
        self.assertNotIn("tools", probe.SCENARIOS["search"])
        self.assertEqual(probe.SCENARIOS["stop-string"]["stop"], [fake_backend.STOP_MARKER])

    def test_scenarios_share_the_bounded_routing_session(self):
        prefixes = {json.dumps(body["messages"], sort_keys=True) for body in probe.SCENARIOS.values()}
        self.assertEqual(len(prefixes), 1)

    def test_endpoint_does_not_accept_host_injection(self):
        for host in ("example.invalid/path", "example.invalid@other.invalid", "user:pass@example.invalid"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    probe.connection(host)


class RuntimeTopologyTest(unittest.TestCase):
    def setUp(self):
        self.compose = yaml.safe_load((Path(__file__).parents[1] / "src" / "runtime_assets" / "compose.yaml").read_text())

    def test_candidate_has_valid_bounded_routing_limits(self):
        limits = json.loads(self.compose["services"]["inference-proxy"]["environment"]["ROUTING_LIMITS"])
        self.assertEqual(
            limits,
            {
                "iris": {
                    "*": {
                        "max_pinned_sessions": 1,
                        "max_global_in_flight_request_slots": 2,
                        "global_in_flight_request_slots_reserved_for_pinned_sessions": 1,
                        "max_per_session_in_flight_request_slots": 1,
                    }
                }
            },
        )

    def test_search_is_internal_and_candidate_gets_only_the_public_certificate(self):
        candidate = self.compose["services"]["inference-proxy"]
        fixture = self.compose["services"]["fixture"]
        self.assertTrue(self.compose["networks"]["runtime"]["internal"])
        self.assertIn("api.linkup.so", fixture["networks"]["runtime"]["aliases"])
        self.assertEqual(candidate["environment"]["LINKUP_API_KEY"], "${LINKUP_API_KEY}")
        self.assertEqual(candidate["environment"]["SSL_CERT_FILE"], "/certificates/linkup.crt")
        self.assertIn("certificates:/certificates:ro", candidate["volumes"])
        self.assertIn("certificates:/certificates", fixture["volumes"])
        self.assertIn("certificates", self.compose["volumes"])


class FakeBackendTest(unittest.TestCase):
    def setUp(self):
        self.values = {
            "CALLER_TOKEN": "test-caller-token",
            "SERVICE_TOKEN": "test-service-token",
            "SUPABASE_KEY": "test-supabase-key",
            "ENDPOINT_SECRET": "test-endpoint-secret",
            "LINKUP_API_KEY": "test-linkup-key",
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

    def connection(self):
        return http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)

    def post(self, path, body, token):
        connection = self.connection()
        connection.request("POST", path, json.dumps(body).encode(), {"Authorization": "Bearer " + token})
        response = connection.getresponse()
        try:
            return response.status, response.read()
        finally:
            connection.close()

    def candidate_request(self, original_request, connection, payload):
        def upstream_request(body):
            upstream = connection()
            try:
                return original_request(upstream, body).read()
            finally:
                upstream.close()

        if "web_search_options" not in payload:
            return original_request(connection(), payload)
        search_tool = {
            "type": "function",
            "function": {
                "name": "web_search",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
        initial = {key: value for key, value in payload.items() if key not in ("web_search_options", "stream", "stream_options")}
        initial["tools"] = [search_tool]
        document = json.loads(upstream_request(initial))
        message = document["choices"][0]["message"]
        search = {"q": fake_backend.SEARCH_QUERY, "depth": "fast", "outputType": "searchResults"}
        status, raw = self.post("/v1/search", search, "test-linkup-key")
        self.assertEqual(status, 200)
        tool_result = {"role": "tool", "tool_call_id": fake_backend.SEARCH_CALL_ID, "content": raw.decode()}
        replay = {
            key: value for key, value in payload.items() if key != "web_search_options"
        }
        replay["messages"] = [*payload["messages"], message, tool_result]
        raw = upstream_request(replay)
        if not payload.get("stream"):
            document = json.loads(raw)
            document["choices"][0]["message"]["annotations"] = [citation()]
            return HTTPResult(json.dumps(document).encode())
        annotation = chunk({"annotations": [citation()]})
        frame = b"data: " + json.dumps(annotation).encode() + b"\n\n"
        return HTTPResult(raw.replace(b"data: [DONE]\n\n", frame + b"data: [DONE]\n\n"), content_type="text/event-stream")

    def test_all_scenarios_match_without_disclosing_bodies(self):
        def test_connection(host="inference-proxy", port=8080, timeout=20):
            return self.connection()

        def request(connection, payload):
            return self.candidate_request(original_request, test_connection, payload)

        original_request = probe.request
        with (
            patch.object(probe, "connection", test_connection),
            patch.object(probe, "request", side_effect=request),
        ):
            probe.wait_ready()
            facts = probe.observations()
        expected = [{"scenario": name, "comparisons": {field: True for field in probe.FIELDS}} for name in probe.SCENARIOS]
        self.assertEqual(facts, expected)
        self.assertEqual(rule_09.evaluate(facts)["status"], "green")
        serialized = json.dumps(facts)
        for secret in (
            fake_backend.TEXT,
            fake_backend.TOOL_ARGUMENTS,
            fake_backend.SEARCH_QUERY,
            fake_backend.SEARCH_TEXT,
            fake_backend.SEARCH_URL,
            fake_backend.STOP_MARKER,
            *self.values.values(),
            *(body["messages"][0]["content"] for body in probe.SCENARIOS.values()),
        ):
            self.assertNotIn(secret, serialized)

    def test_control_plane_requires_synthetic_credentials_and_bound_upstream_token(self):
        search = {"q": fake_backend.SEARCH_QUERY, "depth": "fast", "outputType": "searchResults"}
        self.assertEqual(self.post("/v1/search", search, "wrong")[0], 401)
        status, raw = self.post("/v1/search", search, "test-linkup-key")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["results"][0]["url"], fake_backend.SEARCH_URL)
        body = probe.REQUEST
        self.assertEqual(self.post("/v1/chat/completions", body, "wrong")[0], 401)

    def test_search_request_contract_is_bounded(self):
        for body in (
            {"q": "unexpected query"},
            {"q": fake_backend.SEARCH_QUERY, "depth": "deep", "outputType": "searchResults"},
            {"q": fake_backend.SEARCH_QUERY, "depth": "fast", "outputType": "searchResults", "extra": True},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.post("/v1/search", body, "test-linkup-key")[0], 400)

    def test_control_plane_and_inference_listeners_are_started(self):
        with (
            patch.object(os, "getuid", return_value=1000),
            patch.object(fake_backend, "certificate_server"),
            patch.object(fake_backend, "ThreadingHTTPServer") as server,
        ):
            fake_backend.main()
        listeners = [call.args[0] for call in server.call_args_list]
        self.assertEqual(listeners, [("0.0.0.0", 8000), ("0.0.0.0", 8080)])

    def test_fixture_refuses_to_start_as_root(self):
        with patch.object(os, "getuid", return_value=0):
            with self.assertRaises(RuntimeError):
                fake_backend.main()


if __name__ == "__main__":
    unittest.main()
