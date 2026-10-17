"""Bounded live jobs: every HTTP attempt, retries included, is counted, timed and written to a ledger.

A job stops before its attempt or time cap is passed. Quota snapshots come from the daily-usd
headers on successful replies; they may lag and can include teammates' calls on the shared key,
so they are reported beside per-response usage, never instead of it.
"""

import datetime
import json
import threading
import time
from collections import Counter
from pathlib import Path

from ignis_wo.hosted.transport import ProviderError

QUOTA_HEADERS = ("x-ratelimit-limit-user-daily-usd", "x-ratelimit-used-user-daily-usd",
                 "x-ratelimit-remaining-user-daily-usd", "x-ratelimit-remaining-user-rpm")


class JobBudget:
    def __init__(self, name: str, max_attempts: int = 40, max_seconds: float = 1800, clock=time.monotonic):
        self.name = name
        self.max_attempts = max_attempts
        self.max_seconds = max_seconds
        self.clock = clock
        self.started = clock()
        self.attempts = []
        self.lock = threading.Lock()

    def spend(self, method: str, path: str) -> int:
        with self.lock:
            elapsed = self.clock() - self.started
            if len(self.attempts) >= self.max_attempts:
                raise ProviderError("job_budget", f"job {self.name} reached its cap of {self.max_attempts} attempts")
            if elapsed > self.max_seconds:
                raise ProviderError("job_budget", f"job {self.name} reached its {self.max_seconds:g} s time cap")
            moment = datetime.datetime.now(datetime.UTC).isoformat()
            self.attempts.append({"attempt": len(self.attempts) + 1, "at": moment, "method": method, "path": path,
                                  "outcome": None, "quota": None})
            return len(self.attempts) - 1

    def settle(self, ticket: int, outcome: str, headers: dict | None = None) -> None:
        """A failed attempt has unknown usage, not zero, so it gets no quota snapshot."""
        quota = {name: headers[name] for name in QUOTA_HEADERS if headers and name in headers} or None
        with self.lock:
            self.attempts[ticket].update({"outcome": outcome, "quota": quota})

    def summary(self) -> dict:
        with self.lock:
            attempts = list(self.attempts)
        quotas = [attempt["quota"] for attempt in attempts if attempt["quota"]]
        return {"job": self.name, "attempts": len(attempts), "max_attempts": self.max_attempts,
                "elapsed_seconds": round(self.clock() - self.started, 1), "max_seconds": self.max_seconds,
                "outcomes": dict(Counter(attempt["outcome"] for attempt in attempts)),
                "quota_first": quotas[0] if quotas else None, "quota_last": quotas[-1] if quotas else None}

    def write(self, directory: Path) -> dict:
        directory.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(attempt, sort_keys=True) for attempt in self.attempts]
        (directory / "attempts.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        summary = self.summary()
        (directory / "job.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return summary
