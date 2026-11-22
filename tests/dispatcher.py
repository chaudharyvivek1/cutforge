"""The loop that actually posts a webhook (§15.3).

v2.6 wrote delivery rows and nothing consumed them, so at-least-once was
at-least-once *bookkeeping*. This drains them, posts the signed body, and
feeds the result back into the store's retry policy.
"""
import urllib.error
import urllib.request


class Dispatcher:
    def __init__(self, store, timeout=5.0, transport=None):
        self.store = store
        self.timeout = timeout
        # injectable, so a test can watch the call without a socket
        self.transport = transport or self._post

    def _post(self, url, body, headers):
        request = urllib.request.Request(url, data=body, method="POST",
                                         headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.status

    def run_once(self):
        """Deliver everything that is due. Returns (delivered, failed)."""
        delivered = failed = 0
        for delivery in self.store.pending_deliveries():
            endpoint = self.store.db.execute(
                "SELECT url FROM webhook_endpoints WHERE id=?",
                (delivery["endpoint_id"],)).fetchone()
            if endpoint is None:
                self.store.delivery_failed(delivery["id"], base_delay=0)
                failed += 1
                continue
            body, headers = self.store.delivery_request(delivery["id"])
            try:
                status = self.transport(endpoint["url"], body, headers)
            except (urllib.error.URLError, OSError, TimeoutError):
                status = 0
            if 200 <= int(status) < 300:
                self.store.delivery_delivered(delivery["id"])
                delivered += 1
            else:
                self.store.delivery_failed(delivery["id"])
                failed += 1
        return delivered, failed
