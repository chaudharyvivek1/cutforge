"""Signed webhook delivery (§15.3), with the replay window it needs.

A webhook without a signature is an unauthenticated instruction to somebody
else's system; a signature without a timestamp is replayable forever. Both
are cheap to get right and expensive to retrofit.
"""
import hashlib
import hmac
import time

WINDOW_SECONDS = 300


def sign(secret, body, timestamp):
    """HMAC-SHA256 over `timestamp.body`, so the timestamp is authenticated."""
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify(secret, body, timestamp, signature, now=None, window=WINDOW_SECONDS):
    """True only for a correct signature inside the replay window."""
    now = time.time() if now is None else now
    try:
        age = now - float(timestamp)
    except (TypeError, ValueError):
        return False
    if age < -60 or age > window:
        return False
    expected = sign(secret, body, timestamp)
    return hmac.compare_digest(expected, signature or "")


def headers(secret, body, timestamp=None):
    """The three headers a receiver needs."""
    ts = str(int(time.time() if timestamp is None else timestamp))
    return {
        "Content-Type": "application/json",
        "X-Cutforge-Timestamp": ts,
        "X-Cutforge-Signature": sign(secret, body, ts),
    }
