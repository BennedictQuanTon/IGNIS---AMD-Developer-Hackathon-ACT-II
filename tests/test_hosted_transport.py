import unittest

from mock_chat_server import ScriptedServer, chat_reply, reply

from ignis_wo.hosted.pacing import RequestPacer, shared_pacer
from ignis_wo.hosted.transport import ChatClient, Gateway, ProviderError, parse_json_content

KEY = "rc-test-secret-key"
MESSAGES = [{"role": "user", "content": "hi"}]
NULL_LIMIT = reply({"error": {"message": "The requested max_tokens (4096) exceeds the maximum output tokens allowed "
                                         "for model Qwen3.8-27B (null)"}}, 400)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def client_for(server, **options) -> ChatClient:
    return ChatClient(server.base_url, KEY, sleep=options.pop("sleep", lambda seconds: None), **options)


class RequestTests(unittest.TestCase):
    def test_json_object_request_reads_content_and_keeps_reasoning_apart(self):
        rate = {"X-RateLimit-Remaining-User-RPM": "17"}
        usage = {"prompt_tokens": 3, "completion_tokens": 9, "completion_tokens_details": {"reasoning_tokens": 6}}
        script = [reply(chat_reply('{"ok": true}', reasoning="thinking about it", usage=usage), headers=rate)]
        with ScriptedServer(script) as server:
            result = client_for(server).complete("DeepSeek-V4-Flash", MESSAGES)
        body = server.requests[0]["body"]
        self.assertEqual(server.requests[0]["headers"]["Authorization"], f"Bearer {KEY}")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(result.content, '{"ok": true}')
        self.assertEqual(result.reasoning, "thinking about it")
        self.assertEqual(result.usage["completion_tokens_details"]["reasoning_tokens"], 6)
        self.assertEqual(result.rate_headers["x-ratelimit-remaining-user-rpm"], "17")
        self.assertNotIn("messages", result.request_parameters)

    def test_json_schema_request_carries_a_strict_named_schema(self):
        schema = {"type": "object"}
        with ScriptedServer([reply(chat_reply("{}"))]) as server:
            client_for(server).complete("MiMo-V2.6-Flash", MESSAGES, "json_schema", schema)
        response_format = server.requests[0]["body"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["schema"], schema)
        self.assertTrue(response_format["json_schema"]["strict"])

    def test_list_models_reads_the_data_array(self):
        with ScriptedServer([reply({"data": [{"id": "GLM-5.3-Flash", "json_output": True}]})]) as server:
            models = client_for(server).list_models()
        self.assertEqual(models[0]["id"], "GLM-5.3-Flash")
        self.assertEqual(server.requests[0]["method"], "GET")


class ErrorTests(unittest.TestCase):
    def assert_failure(self, script, kind, requests=1, **options) -> ProviderError:
        with ScriptedServer(script) as server, self.assertRaises(ProviderError) as caught:
            client_for(server, **options).complete("m", MESSAGES)
        self.assertEqual(caught.exception.kind, kind)
        self.assertEqual(len(server.requests), requests)
        self.assertNotIn(KEY, str(caught.exception))
        return caught.exception

    def test_gateway_error_envelope(self):
        body = {"error": {"message": "Unauthorized: No API key provided.", "code": "invalid_api_key"}}
        error = self.assert_failure([reply(body, 401)], "auth")
        self.assertEqual(error.code, "invalid_api_key")

    def test_platform_detail_string_envelope(self):
        error = self.assert_failure([reply({"detail": "Invalid bearer token"}, 401)], "auth")
        self.assertIn("Invalid bearer token", str(error))

    def test_platform_detail_error_envelope_with_concurrency_limit(self):
        body = {"detail": {"error": {"message": "too many in flight", "code": "token_concurrency_rate_limit_exceeded"}}}
        clock = FakeClock()
        error = self.assert_failure([reply(body, 429, {"Retry-After": "1"})], "concurrency_limited", requests=3,
                                    sleep=clock.sleep, clock=clock)
        self.assertEqual(error.retry_after, 1.0)
        self.assertTrue(all(1.0 <= seconds <= 1.25 for seconds in clock.sleeps))

    def test_rate_limit_is_retried_after_the_advertised_wait(self):
        limited = reply({"error": {"message": "Rate limit exceeded", "code": "rate_limit_exceeded"}}, 429,
                        {"Retry-After": "2"})
        clock = FakeClock()
        with ScriptedServer([limited, reply(chat_reply("{}"))]) as server:
            result = client_for(server, sleep=clock.sleep, clock=clock).complete("m", MESSAGES)
        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(clock.sleeps[0], 2.0)

    def test_rate_limit_wait_beyond_the_budget_fails_without_sleeping(self):
        limited = reply({"error": {"message": "Rate limit exceeded"}}, 429, {"Retry-After": "60"})
        clock = FakeClock()
        self.assert_failure([limited], "rate_limited", sleep=clock.sleep, clock=clock, max_wait_seconds=30)
        self.assertEqual(clock.sleeps, [])

    def test_transient_outage_gives_up_after_the_attempt_limit(self):
        self.assert_failure([reply({"detail": "bad gateway"}, 502)], "unavailable", requests=3)

    def test_low_credits_are_classified_and_not_retried(self):
        body = {"error": {"message": "Daily usage limit exceeded: maximum $10 per period"}}
        self.assert_failure([reply(body, 429)], "credits")

    def test_unknown_model_is_a_bad_request(self):
        self.assert_failure([reply({"error": {"message": "Requested model x not supported"}}, 400)], "bad_request")

    def test_timeout_is_not_retried(self):
        self.assert_failure([reply(chat_reply("{}"), delay=0.6)], "timeout", timeout_seconds=0.2)

    def test_dropped_connection_is_an_outage_and_retried(self):
        with ScriptedServer([reply(None, drop=True), reply(chat_reply("{}"))]) as server:
            result = client_for(server).complete("m", MESSAGES)
        self.assertEqual(result.attempts, 2)
        self.assert_failure([reply(None, drop=True)], "unavailable", requests=3)

    def test_reply_without_choices_is_invalid(self):
        self.assert_failure([reply({"object": "chat.completion"})], "invalid_response")


class OutputTests(unittest.TestCase):
    def test_empty_answer_cut_by_length_is_retried_once_with_double_budget(self):
        script = [reply(chat_reply("", "length", reasoning="long thoughts")), reply(chat_reply('{"a": 1}'))]
        with ScriptedServer(script) as server:
            result = client_for(server).complete("m", MESSAGES, max_tokens=100)
        self.assertEqual(result.content, '{"a": 1}')
        self.assertEqual([request["body"]["max_tokens"] for request in server.requests], [100, 200])

    def test_partial_answer_cut_by_length_is_truncated(self):
        with ScriptedServer([reply(chat_reply('{"entities": [', "length"))]) as server:
            with self.assertRaises(ProviderError) as caught:
                client_for(server).complete("m", MESSAGES)
        self.assertEqual(caught.exception.kind, "truncated")
        self.assertIsNotNone(caught.exception.result)

    def test_empty_final_answer_is_an_error_not_an_empty_success(self):
        with ScriptedServer([reply(chat_reply(None, reasoning='{"looks": "like json"}'))]) as server:
            with self.assertRaises(ProviderError) as caught:
                client_for(server).complete("m", MESSAGES)
        self.assertEqual(caught.exception.kind, "empty_output")

    def test_fenced_json_is_accepted_and_malformed_json_rejected(self):
        self.assertEqual(parse_json_content('```json\n{"a": 1}\n```'), {"a": 1})
        for content in ('{"a": ', "[1, 2]", "plain words"):
            with self.assertRaises(ProviderError) as caught:
                parse_json_content(content)
            self.assertEqual(caught.exception.kind, "invalid_response")


class BudgetTests(unittest.TestCase):
    def test_a_server_default_budget_is_left_out_and_truncation_is_not_retried(self):
        with ScriptedServer([reply(chat_reply("", "length"))]) as server, self.assertRaises(ProviderError) as caught:
            client_for(server).complete("m", MESSAGES, max_tokens=None)
        self.assertEqual(caught.exception.kind, "truncated")
        self.assertEqual(len(server.requests), 1)
        self.assertNotIn("max_tokens", server.requests[0]["body"])
        self.assertEqual(caught.exception.result.request_parameters["max_tokens_policy"], "server_default")

    def test_a_rejected_budget_stops_when_fallback_is_off(self):
        with ScriptedServer([NULL_LIMIT]) as server, self.assertRaises(ProviderError) as caught:
            client_for(server).complete("m", MESSAGES)
        self.assertEqual(caught.exception.kind, "budget_rejected")
        self.assertEqual(len(server.requests), 1)

    def test_fallback_retries_once_without_max_tokens_and_remembers_the_model(self):
        with ScriptedServer([NULL_LIMIT, reply(chat_reply("{}"))]) as server:
            client = client_for(server)
            first = client.complete("m", MESSAGES, budget_fallback=True)
            second = client.complete("m", MESSAGES, budget_fallback=True)
        self.assertEqual([request["body"].get("max_tokens") for request in server.requests], [4096, None, None])
        self.assertEqual(first.request_parameters["budget_fallback"]["rejected_max_tokens"], 4096)
        self.assertIsNone(first.request_parameters["effective_max_tokens"])
        self.assertEqual(second.request_parameters["max_tokens_policy"], "explicit_with_fallback")
        self.assertEqual(second.request_parameters["budget_fallback"], {"remembered": True})

    def test_other_bad_requests_never_trigger_the_fallback(self):
        unknown = reply({"error": {"message": "Unknown parameter: foo"}}, 400)
        with ScriptedServer([unknown]) as server, self.assertRaises(ProviderError) as caught:
            client_for(server).complete("m", MESSAGES, budget_fallback=True)
        self.assertEqual(caught.exception.kind, "bad_request")
        self.assertEqual(len(server.requests), 1)

    def test_an_oversized_body_is_refused_before_sending(self):
        with ScriptedServer([reply(chat_reply("{}"))]) as server, self.assertRaises(ProviderError) as caught:
            gateway = Gateway(server.base_url, KEY, max_body_bytes=100)
            ChatClient(gateway=gateway).complete("m", [{"role": "user", "content": "x" * 200}])
        self.assertEqual(caught.exception.kind, "bad_request")
        self.assertEqual(server.requests, [])


class PacerTests(unittest.TestCase):
    def test_a_pause_imposed_while_a_caller_sleeps_is_rechecked(self):
        clock = FakeClock()

        def sleep(seconds):
            if not clock.sleeps:
                pacer.pause(10.0)
            clock.sleep(seconds)

        pacer = RequestPacer(requests_per_minute=60, clock=clock, sleep=sleep)
        for _ in range(2):
            with pacer.slot():
                pass
        self.assertEqual(clock.sleeps, [1.0, 9.0])

    def test_the_allowance_reserve_stops_requests_before_the_limit(self):
        clock = FakeClock()
        pacer = RequestPacer(allowance_reserve=0.25, clock=clock, sleep=clock.sleep)
        with pacer.slot():
            pass
        pacer.observe({"x-ratelimit-limit-user-daily-usd": "1", "x-ratelimit-remaining-user-daily-usd": "0.2"})
        with self.assertRaises(ProviderError) as caught, pacer.slot():
            pass
        self.assertEqual(caught.exception.kind, "credits")

    def test_the_shared_pacer_is_one_object_and_refuses_other_settings(self):
        pacer = shared_pacer()
        self.assertIs(shared_pacer(), pacer)
        with self.assertRaises(ValueError):
            shared_pacer(requests_per_minute=5)

    def test_clients_sharing_a_gateway_share_its_pacer(self):
        clock = FakeClock()
        pacer = RequestPacer(requests_per_minute=60, clock=clock, sleep=clock.sleep)
        with ScriptedServer([reply(chat_reply("{}"))]) as server:
            gateway = Gateway(server.base_url, KEY, pacer=pacer)
            ChatClient(gateway=gateway).complete("m", MESSAGES)
            ChatClient(gateway=gateway).complete("m", MESSAGES)
        self.assertEqual(clock.sleeps, [1.0])

    def test_requests_are_spaced_by_the_rate_limit(self):
        clock = FakeClock()
        pacer = RequestPacer(requests_per_minute=30, max_in_flight=1, clock=clock, sleep=clock.sleep)
        for _ in range(3):
            with pacer.slot():
                pass
        self.assertEqual(clock.sleeps, [2.0, 2.0])

    def test_an_exhausted_shared_window_pauses_for_a_minute(self):
        clock = FakeClock()
        pacer = RequestPacer(requests_per_minute=60, clock=clock, sleep=clock.sleep)
        pacer.observe({"x-ratelimit-remaining-user-rpm": "1"})
        with pacer.slot():
            pass
        self.assertEqual(clock.sleeps, [60.0])

    def test_a_rate_limit_pauses_every_caller_of_the_pacer(self):
        clock = FakeClock()
        pacer = RequestPacer(requests_per_minute=60, clock=clock, sleep=clock.sleep)
        limited = reply({"error": {"message": "Rate limit exceeded"}}, 429, {"Retry-After": "5"})
        with ScriptedServer([limited]) as server, self.assertRaises(ProviderError):
            ChatClient(server.base_url, KEY, pacer=pacer, max_attempts=1).complete("m", MESSAGES)
        self.assertEqual(pacer.paused_until, 5.0)

    def test_pacer_is_used_by_the_client(self):
        clock = FakeClock()
        pacer = RequestPacer(requests_per_minute=60, clock=clock, sleep=clock.sleep)
        with ScriptedServer([reply(chat_reply("{}"))]) as server:
            client = ChatClient(server.base_url, KEY, pacer=pacer)
            client.complete("m", MESSAGES)
            client.complete("m", MESSAGES)
        self.assertEqual(clock.sleeps, [1.0])


if __name__ == "__main__":
    unittest.main()

