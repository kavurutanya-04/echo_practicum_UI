"""Process-wide request spacing for profiles sharing an endpoint and credential."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import math
import threading
import time

from .execution_log import record


class RequestPacer:
    def __init__(self, interval):
        self.interval = interval
        self.next_request = 0.0
        self.lock = threading.Lock()

    def acquire(self):
        # Reserve actual starts, not future slots: slow requests cannot create bursts.
        with self.lock:
            wait = self.next_request - time.monotonic()
            if wait > 0:
                record("request_pacing_wait", seconds=round(wait, 3))
            while wait > 0:
                time.sleep(min(wait, 30))
                wait = self.next_request - time.monotonic()
            self.next_request = time.monotonic() + self.interval

    def defer(self, seconds):
        with self.lock:
            self.next_request = max(self.next_request, time.monotonic() + seconds)


_pacers = {}
_pool_lock = threading.Lock()


def shared_pacer(endpoint, key, interval):
    # No credentials are logged or used as plain-text dictionary identifiers.
    identity = (endpoint.rstrip("/"), hashlib.sha256(key.encode()).digest())
    with _pool_lock:
        pacer = _pacers.setdefault(identity, RequestPacer(interval))
        # A second profile cannot weaken the spacing of the same credential.
        with pacer.lock:
            previous = pacer.interval
            pacer.interval = max(previous, interval)
            if pacer.next_request:
                pacer.next_request += pacer.interval - previous
        return pacer


def retry_after_seconds(error, fallback):
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {}) or {}
    value = headers.get("retry-after") or headers.get("Retry-After")
    if value is not None:
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            try:
                moment = parsedate_to_datetime(value)
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                seconds = (moment - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                return fallback
        if math.isfinite(seconds) and seconds >= 0:
            return max(seconds, fallback)
    return fallback
