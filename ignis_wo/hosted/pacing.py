"""Keeps one process under a request-rate and in-flight cap shared by every caller.

The team shares one key across three machines, so the pacer also backs off for a full minute
whenever the gateway reports that at most one request remains in the current window. It can also
hold back a reserve of the daily allowance, read from the gateway's daily-usd headers.
"""

import threading
import time
from contextlib import contextmanager

from ignis_wo.hosted.transport import ProviderError

shared = {"pacer": None, "settings": None}
shared_lock = threading.Lock()


def header_number(rate_headers: dict, name: str) -> float | None:
    try:
        return float(rate_headers[name])
    except (KeyError, TypeError, ValueError):
        return None


class RequestPacer:
    def __init__(self, requests_per_minute: float = 20, max_in_flight: int = 2, allowance_reserve: float = 0.0,
                 clock=time.monotonic, sleep=time.sleep):
        self.interval = 60.0 / requests_per_minute
        self.in_flight = threading.BoundedSemaphore(max_in_flight)
        self.allowance_reserve = allowance_reserve
        self.lock = threading.Lock()
        self.next_start = 0.0
        self.paused_until = 0.0
        self.allowance = None
        self.clock = clock
        self.sleep = sleep

    @contextmanager
    def slot(self):
        with self.in_flight:
            delay = self.reserve()
            while delay > 0:
                self.sleep(delay)
                delay = self.recheck_pause()
            self.check_allowance()
            yield

    def reserve(self) -> float:
        with self.lock:
            return self.reserve_locked()

    def reserve_locked(self) -> float:
        now = self.clock()
        start = max(now, self.next_start, self.paused_until)
        self.next_start = start + self.interval
        return start - now

    def recheck_pause(self) -> float:
        """A pause imposed while this caller slept sends it back into the queue, keeping the spacing."""
        with self.lock:
            if self.clock() >= self.paused_until:
                return 0.0
            return self.reserve_locked()

    def check_allowance(self) -> None:
        with self.lock:
            allowance = self.allowance
        if not self.allowance_reserve or allowance is None:
            return
        remaining, limit = allowance
        if remaining < self.allowance_reserve * limit:
            message = f"allowance reserve reached: {remaining:.4f} of {limit:g} left, reserve {self.allowance_reserve:.0%}"
            raise ProviderError("credits", message)

    def observe(self, rate_headers: dict) -> None:
        remaining_requests = header_number(rate_headers, "x-ratelimit-remaining-user-rpm")
        if remaining_requests is not None and remaining_requests <= 1:
            self.pause(60.0)
        remaining = header_number(rate_headers, "x-ratelimit-remaining-user-daily-usd")
        limit = header_number(rate_headers, "x-ratelimit-limit-user-daily-usd")
        if remaining is not None and limit:
            with self.lock:
                self.allowance = (remaining, limit)

    def pause(self, seconds: float) -> None:
        """Holds every caller of this pacer, e.g. after a 429 from the shared key."""
        with self.lock:
            self.paused_until = max(self.paused_until, self.clock() + seconds)


def shared_pacer(requests_per_minute: float = 20, max_in_flight: int = 2, allowance_reserve: float = 0.0):
    """One pacer per process, so extraction, explanation and OCR draw on the same budget."""
    settings = (requests_per_minute, max_in_flight, allowance_reserve)
    with shared_lock:
        if shared["pacer"] is None:
            shared["pacer"] = RequestPacer(*settings)
            shared["settings"] = settings
        elif shared["settings"] != settings:
            raise ValueError(f"the shared pacer already runs with {shared['settings']}, not {settings}")
        return shared["pacer"]
