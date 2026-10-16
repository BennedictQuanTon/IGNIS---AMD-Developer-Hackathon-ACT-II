"""Keeps one process under a request-rate and in-flight cap shared by every caller.

The team shares one key across three machines, so the pacer also backs off for a full minute
whenever the gateway reports that at most one request remains in the current window.
"""

import threading
import time
from contextlib import contextmanager


class RequestPacer:
    def __init__(self, requests_per_minute: float = 20, max_in_flight: int = 2, clock=time.monotonic,
                 sleep=time.sleep):
        self.interval = 60.0 / requests_per_minute
        self.in_flight = threading.BoundedSemaphore(max_in_flight)
        self.lock = threading.Lock()
        self.next_start = 0.0
        self.clock = clock
        self.sleep = sleep

    @contextmanager
    def slot(self):
        with self.in_flight:
            delay = self.reserve()
            if delay > 0:
                self.sleep(delay)
            yield

    def reserve(self) -> float:
        with self.lock:
            now = self.clock()
            start = max(now, self.next_start)
            self.next_start = start + self.interval
            return start - now

    def observe(self, rate_headers: dict) -> None:
        remaining = rate_headers.get("x-ratelimit-remaining-user-rpm")
        try:
            exhausted = remaining is not None and float(remaining) <= 1
        except ValueError:
            exhausted = False
        if exhausted:
            self.pause(60.0)

    def pause(self, seconds: float) -> None:
        """Holds every caller of this pacer, e.g. after a 429 from the shared key."""
        with self.lock:
            self.next_start = max(self.next_start, self.clock() + seconds)
