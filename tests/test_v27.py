"""v2.7: a dispatcher that posts, shared state, and the quotas that cost money."""
import json
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import auth as A
import dispatcher as D
import store as St
import webhook as W


class TestDispatcher(unittest.TestCase):
    """§15.3 — at-least-once means something is sent."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.secret = "whsec_y"
        self.store.add_endpoint("tnt_a", "https://example.test/hook", self.secret)
        self.posted = []

    def _deliver(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        return self.store.pending_deliveries()[0]

    def test_a_delivery_is_posted_and_marked(self):
        delivery = self._deliver()
        sent = D.Dispatcher(self.store, transport=lambda u, b, h: (self.posted.append(b), 200)[1])
        delivered, failed = sent.run_once()
        self.assertEqual((delivered, failed), (1, 0))
        self.assertEqual(self.store.delivery(delivery["id"])["state"], "delivered")

    def test_the_posted_body_verifies(self):
        self._deliver()
        sent = D.Dispatcher(self.store, transport=lambda u, b, h: (
            self.posted.append((b, h)), 200)[1])
        sent.run_once()
        body, headers = self.posted[0]
        self.assertTrue(W.verify(self.secret, body,
                                 headers["X-Cutforge-Timestamp"],
                                 headers["X-Cutforge-Signature"]))
        self.assertEqual(json.loads(body)["event"], "job.succeeded")

    def test_a_failure_is_retried_and_then_delivered(self):
        # the receiver fails twice, then accepts — the retry path end to end
        delivery = self._deliver()
        attempts = {"n": 0}

        def flaky(url, body, headers):
            attempts["n"] += 1
            return 500 if attempts["n"] < 3 else 200

        sent = D.Dispatcher(self.store, transport=flaky)
        self.assertEqual(sent.run_once(), (0, 1))
        self.store.db.execute("UPDATE deliveries SET next_attempt_at=0")
        self.store.db.commit()
        self.assertEqual(sent.run_once(), (0, 1))
        self.store.db.execute("UPDATE deliveries SET next_attempt_at=0")
        self.store.db.commit()
        self.assertEqual(sent.run_once(), (1, 0))
        self.assertEqual(self.store.delivery(delivery["id"])["state"], "delivered")

    def test_a_transport_error_is_a_failure_not_a_crash(self):
        self._deliver()

        def broken(url, body, headers):
            raise OSError("connection refused")

        self.assertEqual(D.Dispatcher(self.store, transport=broken).run_once(), (0, 1))

    def test_five_failures_dead_letter(self):
        delivery = self._deliver()
        sent = D.Dispatcher(self.store, transport=lambda u, b, h: 500)
        for _ in range(5):
            self.store.db.execute("UPDATE deliveries SET next_attempt_at=0")
            self.store.db.commit()
            sent.run_once()
        self.assertEqual(self.store.delivery(delivery["id"])["state"], "dead")


class _Receiver(BaseHTTPRequestHandler):
    """A receiver that fails twice, then accepts — over a real socket."""
    attempts = 0
    verified = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        type(self).attempts += 1
        ok = W.verify("whsec_z", body, self.headers.get("X-Cutforge-Timestamp"),
                      self.headers.get("X-Cutforge-Signature"))
        type(self).verified.append(ok)
        self.send_response(200 if type(self).attempts >= 3 else 500)
        self.send_header("Content-Length", "0")
        self.end_headers()


class TestDeliveryOverTheWire(unittest.TestCase):
    """The retry path against a receiver, not against a lambda."""

    def setUp(self):
        self.store = St.Store(":memory:")
        _Receiver.attempts = 0
        _Receiver.verified = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Receiver)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self.httpd.server_address[1]}/hook"
        self.store.add_endpoint("tnt_a", url, "whsec_z")

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_a_receiver_that_fails_twice_still_gets_the_event(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        sent = D.Dispatcher(self.store)
        for _ in range(3):
            sent.run_once()
            self.store.db.execute("UPDATE deliveries SET next_attempt_at=0")
            self.store.db.commit()
        delivery = self.store.db.execute("SELECT * FROM deliveries").fetchone()
        self.assertEqual(dict(delivery)["state"], "delivered")
        self.assertEqual(_Receiver.attempts, 3)
        self.assertTrue(all(_Receiver.verified), "every attempt must carry a valid signature")


class TestSharedState(unittest.TestCase):
    """§16 — state that must outlive a process, in the store."""

    def setUp(self):
        self.store = St.Store(":memory:")

    def test_a_token_issued_in_one_process_is_visible_in_another(self):
        A.Tokens(store=self.store).issue("tok_a", "tnt_a")
        other = A.Tokens(store=self.store)
        self.assertIsNotNone(other.principal({"Authorization": "Bearer tok_a"}))

    def test_revocation_reaches_every_process(self):
        issuer = A.Tokens(store=self.store)
        issuer.issue("tok_a", "tnt_a")
        other = A.Tokens(store=self.store)
        issuer.revoke("tok_a")
        self.assertIsNone(other.principal({"Authorization": "Bearer tok_a"}))

    def test_revocation_survives_a_restart(self):
        issuer = A.Tokens(store=self.store)
        issuer.issue("tok_a", "tnt_a")
        issuer.revoke("tok_a")
        restarted = A.Tokens(store=self.store)
        self.assertIsNone(restarted.principal({"Authorization": "Bearer tok_a"}))

    def test_the_bucket_is_shared_between_workers(self):
        # two workers with private buckets would allow capacity x workers
        allowed = [self.store.take_token("tnt_a", capacity=2, refill_per_second=0)
                   for _ in range(3)]
        self.assertEqual(allowed, [True, True, False])


class TestCostQuotas(unittest.TestCase):
    """§16.1 — submissions per minute is not the quota that costs money."""

    def setUp(self):
        self.store = St.Store(":memory:")

    def test_render_minutes_are_counted_and_capped(self):
        self.assertEqual(self.store.consume_render_minutes("tnt_a", 30, limit=60),
                         (True, 30.0))
        self.assertEqual(self.store.consume_render_minutes("tnt_a", 40, limit=60)[0], False)

    def test_a_refused_request_does_not_consume(self):
        self.store.consume_render_minutes("tnt_a", 50, limit=60)
        ok, used = self.store.consume_render_minutes("tnt_a", 20, limit=60)
        self.assertFalse(ok)
        self.assertEqual(used, 50.0)

    def test_tenants_have_separate_quotas(self):
        self.store.consume_render_minutes("tnt_a", 60, limit=60)
        self.assertTrue(self.store.consume_render_minutes("tnt_b", 60, limit=60)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
