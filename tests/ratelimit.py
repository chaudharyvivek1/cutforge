"""Per-tenant token buckets (§16.1).

The two-job concurrency cap in the store *delays* work; a rate limit
*refuses* it. v2.5 had the first and not the second, so a tenant could submit
ten thousand jobs and the only back-pressure was a queue that grew.

A token bucket is the right shape because it allows a burst and bounds the
sustained rate, which is what a render API actually needs: a user uploads
forty clips at once and then works for an hour.
"""
import time


class Buckets:
    def __init__(self, capacity=60, refill_per_second=1.0, clock=None):
        self.capacity = float(capacity)
        self.refill = float(refill_per_second)
        self.clock = clock or time.time
        self.state = {}          # tenant -> (tokens, last_refill)

    def take(self, tenant, cost=1.0):
        """True when the request may proceed; False when it must be refused."""
        now = self.clock()
        tokens, last = self.state.get(tenant, (self.capacity, now))
        tokens = min(self.capacity, tokens + (now - last) * self.refill)
        if tokens < cost:
            self.state[tenant] = (tokens, now)
            return False
        self.state[tenant] = (tokens - cost, now)
        return True

    def retry_after(self, tenant, cost=1.0):
        """Seconds until the bucket holds enough for the request (§16.1)."""
        tokens, last = self.state.get(tenant, (self.capacity, self.clock()))
        missing = cost - tokens
        if missing <= 0:
            return 0
        return max(1, int(-(-missing // self.refill)))       # ceil, in seconds
