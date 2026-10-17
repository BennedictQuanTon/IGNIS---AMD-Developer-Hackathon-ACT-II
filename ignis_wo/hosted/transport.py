"""Client for the AMD Token Factory chat API (OpenAI-compatible), with typed failures.

Documented behaviour this client relies on: https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/
and https://amd-aim.github.io/radeon-cloud-docs/api/errors/. The final answer is read from
`message.content` only; `message.reasoning` is kept separately and never parsed as output.

`Gateway` owns what every role shares: pacing, the allowance guard, retries and error parsing.
`ChatClient` adds chat semantics on top, so a future OCR client can share one Gateway without
sending chat-only parameters.
"""

import http.client
import json
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "https://developer.amd.com.cn/radeon/api/v1"
OUTPUT_MODES = ("json_object", "json_schema", "text")
RETRYABLE_KINDS = frozenset({"rate_limited", "concurrency_limited", "unavailable"})
TRANSIENT_KINDS = RETRYABLE_KINDS | {"timeout"}
RECORD_LEVEL_KINDS = frozenset({"invalid_response", "empty_output", "truncated"})
STOP_KINDS = frozenset({"auth", "credits", "budget_rejected"})
FENCED_JSON = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
BUDGET_REJECTED = re.compile(r"max_tokens.*exceeds the maximum output tokens allowed", re.IGNORECASE)


class ProviderError(Exception):
    """A failed call, classified so callers can retry, skip the record, or stop."""

    def __init__(self, kind: str, message: str, status: int | None = None, code: str | None = None,
                 retry_after: float | None = None, result=None):
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.status = status
        self.code = code
        self.retry_after = retry_after
        self.result = result

    @property
    def transient(self) -> bool:
        return self.kind in TRANSIENT_KINDS

    @property
    def record_level(self) -> bool:
        return self.kind in RECORD_LEVEL_KINDS


@dataclass(frozen=True)
class ChatResult:
    content: str
    reasoning: str | None
    finish_reason: str | None
    usage: dict
    rate_headers: dict
    latency_seconds: float
    attempts: int
    request_parameters: dict = field(default_factory=dict)


def parse_json_content(content: str) -> dict:
    text = content.strip()
    fenced = FENCED_JSON.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProviderError("invalid_response", f"final answer is not JSON ({error.msg})") from None
    if not isinstance(value, dict):
        raise ProviderError("invalid_response", "final answer is not a JSON object")
    return value


def budget_policy(max_tokens: int | None, budget_fallback: bool) -> str:
    if max_tokens is None:
        return "server_default"
    return "explicit_with_fallback" if budget_fallback else "explicit"


def budget_label(max_tokens: int | None, budget_fallback: bool) -> str:
    """Short form of the output-length policy, used inside model and replay identities."""
    if max_tokens is None:
        return "server-default"
    return f"max{max_tokens}-fallback" if budget_fallback else f"max{max_tokens}"


def chat_parameters(model: str, messages: list[dict], output_mode: str, schema: dict | None,
                    reasoning_effort: str | None, max_tokens: int | None, temperature: float) -> dict:
    """A max_tokens of None is left out of the request, so the server's default limit applies."""
    if output_mode not in OUTPUT_MODES:
        raise ValueError(f"output_mode must be one of {OUTPUT_MODES}")
    parameters = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:
        parameters["max_tokens"] = max_tokens
    if reasoning_effort:
        parameters["reasoning_effort"] = reasoning_effort
    if output_mode == "json_object":
        parameters["response_format"] = {"type": "json_object"}
    if output_mode == "json_schema":
        json_schema = {"name": "ignis_output", "strict": True, "schema": schema}
        parameters["response_format"] = {"type": "json_schema", "json_schema": json_schema}
    return parameters


def error_details(body: bytes) -> tuple[str, str | None]:
    """Reads the three documented envelopes: error{...}, detail{error{...}} and detail "text"."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body.decode("utf-8", "replace")[:300], None
    if not isinstance(payload, dict):
        return str(payload)[:300], None
    error = payload.get("error")
    detail = payload.get("detail")
    if error is None and isinstance(detail, dict):
        error = detail.get("error")
    if isinstance(error, dict):
        return str(error.get("message", "")), error.get("code")
    if error is not None:
        return str(error), None
    return str(detail if detail is not None else payload)[:300], None


def classify(status: int, message: str, code: str | None) -> str:
    lowered = f"{message} {code or ''}".lower()
    if status == 400 and BUDGET_REJECTED.search(message):
        return "budget_rejected"
    if status in (401, 403):
        return "auth"
    if "credit" in lowered or "usage limit" in lowered or "balance" in lowered:
        return "credits"
    if status == 429:
        return "concurrency_limited" if "concurrency" in lowered else "rate_limited"
    if status >= 500:
        return "unavailable"
    return "bad_request"


def retry_after_seconds(headers) -> float | None:
    value = headers.get("Retry-After") if headers else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rate_headers(headers) -> dict:
    return {name.lower(): value for name, value in headers.items() if name.lower().startswith("x-ratelimit-")}


class Gateway:
    """HTTP access to the AMD API shared by every role in a process."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None, timeout_seconds: float = 180,
                 max_attempts: int = 3, max_wait_seconds: float = 90, pacer=None, sleep=time.sleep,
                 clock=time.monotonic, max_body_bytes: int = 1_000_000):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_wait_seconds = max_wait_seconds
        self.pacer = pacer
        self.sleep = sleep
        self.clock = clock
        self.max_body_bytes = max_body_bytes

    def send(self, method: str, path: str, body: dict | None = None, timeout_seconds: float | None = None,
             max_body_bytes: int | None = None):
        """Per-call limits override the gateway defaults, e.g. for long OCR requests with large bodies."""
        limits = (timeout_seconds or self.timeout_seconds, max_body_bytes or self.max_body_bytes)
        started = self.clock()
        attempt = 0
        while True:
            attempt += 1
            try:
                reply, headers, latency = self.request_once(method, path, body, limits)
                return reply, headers, latency, attempt
            except ProviderError as error:
                wait = self.retry_wait(error, attempt)
                if wait is None or self.clock() - started + wait > self.max_wait_seconds:
                    raise
                self.sleep(wait)

    def retry_wait(self, error: ProviderError, attempt: int) -> float | None:
        if error.kind not in RETRYABLE_KINDS or attempt >= self.max_attempts:
            return None
        base = error.retry_after if error.retry_after is not None else 2.0 ** attempt
        return base + random.uniform(0, 0.25 * max(base, 1.0))

    def request_once(self, method: str, path: str, body: dict | None, limits: tuple[float, int]):
        timeout_seconds, max_body_bytes = limits
        data = json.dumps(body).encode("utf-8") if body is not None else None
        if data is not None and len(data) > max_body_bytes:
            raise ProviderError("bad_request", f"request body is {len(data)} bytes, over the {max_body_bytes} limit")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        if self.pacer is None:
            return self.timed_open(request, timeout_seconds)
        with self.pacer.slot():
            try:
                reply, response_headers, latency = self.timed_open(request, timeout_seconds)
            except ProviderError as error:
                if error.kind == "rate_limited":
                    self.pacer.pause(error.retry_after or 60.0)
                raise
        self.pacer.observe(response_headers)
        return reply, response_headers, latency

    def timed_open(self, request, timeout_seconds: float):
        """Times only the successful request itself, not pacing waits or earlier failed attempts."""
        began = self.clock()
        reply, headers = self.open(request, timeout_seconds)
        return reply, headers, self.clock() - began

    def open(self, request, timeout_seconds: float):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
                headers = rate_headers(response.headers)
        except urllib.error.HTTPError as error:
            message, code = error_details(error.read())
            kind = classify(error.code, message, code)
            raise ProviderError(kind, message, error.code, code, retry_after_seconds(error.headers)) from None
        except TimeoutError:
            raise ProviderError("timeout", f"no reply within {timeout_seconds}s") from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderError("timeout", f"no reply within {timeout_seconds}s") from None
            raise ProviderError("unavailable", f"connection failed ({error.reason})") from None
        except (http.client.HTTPException, ConnectionError) as error:
            raise ProviderError("unavailable", f"connection dropped ({type(error).__name__})") from None
        try:
            return json.loads(raw), headers
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderError("invalid_response", "reply body is not JSON") from None


class ChatClient:
    """Chat completions over a Gateway. Builds its own Gateway when none is shared with it."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None, timeout_seconds: float = 180,
                 max_attempts: int = 3, max_wait_seconds: float = 90, pacer=None, sleep=time.sleep,
                 clock=time.monotonic, gateway: Gateway | None = None):
        self.gateway = gateway or Gateway(base_url, api_key, timeout_seconds, max_attempts, max_wait_seconds, pacer,
                                          sleep, clock)
        self.server_default_models = set()

    @property
    def base_url(self) -> str:
        return self.gateway.base_url

    def complete(self, model: str, messages: list[dict], output_mode: str = "json_object", schema: dict | None = None,
                 reasoning_effort: str | None = "low", max_tokens: int | None = 4096, temperature: float = 0,
                 budget_fallback: bool = False) -> ChatResult:
        """`budget_fallback` opts in to one retry without max_tokens when the model rejects the budget.
        Once a model has needed it, later calls for that model leave max_tokens out from the start."""
        uses_default = max_tokens is None or (budget_fallback and model in self.server_default_models)
        effective_tokens = None if uses_default else max_tokens
        parameters = chat_parameters(model, messages, output_mode, schema, reasoning_effort, effective_tokens,
                                     temperature)
        policy = {"max_tokens_policy": budget_policy(max_tokens, budget_fallback),
                  "effective_max_tokens": effective_tokens}
        if uses_default and max_tokens is not None:
            policy["budget_fallback"] = {"remembered": True}
        try:
            result = self.post_chat(parameters, policy)
        except ProviderError as error:
            if error.kind != "budget_rejected" or not budget_fallback or effective_tokens is None:
                raise
            self.server_default_models.add(model)
            parameters = {key: value for key, value in parameters.items() if key != "max_tokens"}
            rejected = {"rejected_max_tokens": effective_tokens, "message": str(error)}
            policy = {**policy, "effective_max_tokens": None, "budget_fallback": rejected}
            effective_tokens = None
            result = self.post_chat(parameters, policy)
        if result.finish_reason == "length" and not result.content.strip() and effective_tokens is not None:
            result = self.retry_with_double_budget(parameters, policy, result)
        if result.finish_reason == "length":
            limit = result.request_parameters.get("effective_max_tokens")
            stopped_at = f"max_tokens={limit}" if limit is not None else "the server's default output limit"
            raise ProviderError("truncated", f"output stopped at {stopped_at}", result=result)
        if not result.content.strip():
            raise ProviderError("empty_output", "the final answer was empty", result=result)
        return result

    def retry_with_double_budget(self, parameters: dict, policy: dict, first: ChatResult) -> ChatResult:
        doubled = parameters["max_tokens"] * 2
        try:
            return self.post_chat({**parameters, "max_tokens": doubled}, {**policy, "effective_max_tokens": doubled})
        except ProviderError as error:
            if error.kind != "budget_rejected":
                raise
            message = f"output stopped at max_tokens={parameters['max_tokens']}; a larger budget was rejected"
            raise ProviderError("truncated", message, result=first) from None

    def list_models(self) -> list[dict]:
        reply, _, _, _ = self.gateway.send("GET", "/models")
        return reply.get("data", []) if isinstance(reply, dict) else []

    def post_chat(self, parameters: dict, policy: dict | None = None) -> ChatResult:
        reply, headers, latency, attempts = self.gateway.send("POST", "/chat/completions", parameters)
        try:
            choice = reply["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("invalid_response", "reply has no choices[0].message") from None
        recorded_parameters = {key: value for key, value in parameters.items() if key != "messages"}
        return ChatResult(
            content=message.get("content") or "",
            reasoning=message.get("reasoning"),
            finish_reason=choice.get("finish_reason"),
            usage=reply.get("usage") or {},
            rate_headers=headers,
            latency_seconds=round(latency, 3),
            attempts=attempts,
            request_parameters={**recorded_parameters, **(policy or {})},
        )
