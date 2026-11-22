"""A minimal job service: the runtime contracts of §15, §17 and §18, executed.

Nothing here needs a GPU, media or a framework. What it tests is what a
library call cannot: idempotency across a retry, the state machine surviving a
restart of the request, a hold with a deadline, and cancellation reaching a
terminal state.

It is a reference, not a product. One process, one dictionary, one thread.
"""
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TERMINAL = {"succeeded", "failed", "cancelled", "expired"}


class JobStore:
    """§13.3's jobs table, in memory, with the invariants that matter here."""

    def __init__(self, hold_seconds=5, clock=time.monotonic):
        self.jobs = {}
        self.by_key = {}
        self.lock = threading.Lock()
        self.hold_seconds = hold_seconds
        self.clock = clock

    def submit(self, tenant, kind, idempotency_key, payload=None):
        """§15.1: the same key from the same tenant returns the original job."""
        with self.lock:
            key = (tenant, idempotency_key)
            if idempotency_key and key in self.by_key:
                return self.by_key[key], False
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            job = {"id": job_id, "tenant_id": tenant, "kind": kind,
                   "state": "queued", "attempt": 1, "payload": payload or {},
                   "hold_deadline": None, "error": None}
            self.jobs[job_id] = job
            if idempotency_key:
                self.by_key[key] = job
            return job, True

    def get(self, tenant, job_id):
        """A job from another tenant is a 404, not a 403 (§14.5)."""
        job = self.jobs.get(job_id)
        if not job or job["tenant_id"] != tenant:
            return None
        self._expire(job)
        return job

    def transition(self, tenant, job_id, state, **fields):
        job = self.get(tenant, job_id)
        if job is None:
            return None
        if job["state"] in TERMINAL:
            return job                                  # terminal states are final
        job.update(fields)
        job["state"] = state
        if state == "awaiting_input" and job.get("hold_deadline") is None:
            job["hold_deadline"] = self.clock() + self.hold_seconds
        return job

    def answer(self, tenant, job_id, answer):
        job = self.get(tenant, job_id)
        if job is None or job["state"] != "awaiting_input":
            return None
        if answer == "accept_degraded":
            job["degraded"] = True
            job["state"] = "running"
        elif answer == "confirm":
            job["state"] = "running"
        else:
            job["error"] = "UNKNOWN_ANSWER"
            return job
        job["hold_deadline"] = None
        return job

    def cancel(self, tenant, job_id):
        job = self.get(tenant, job_id)
        if job is None or job["state"] in TERMINAL:
            return job
        job["state"] = "cancelled"
        return job

    def _expire(self, job):
        """§8.5: a timeout is not consent. An unanswered hold expires to failed."""
        if job["state"] == "awaiting_input" and job["hold_deadline"] is not None:
            if self.clock() >= job["hold_deadline"]:
                job["state"] = "failed"
                job["error"] = "HOLD_EXPIRED"
                job["hold_deadline"] = None


def make_handler(store, tenant="tnt_test"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body):
            payload = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _tenant(self):
            return self.headers.get("X-Tenant", tenant)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            parts = [p for p in self.path.strip("/").split("/") if p]

            if parts == ["v1", "jobs"]:
                job, created = store.submit(self._tenant(), body.get("kind", "plan"),
                                            self.headers.get("Idempotency-Key"),
                                            body.get("payload"))
                return self._send(202 if created else 200, {"job_id": job["id"],
                                                            "state": job["state"]})
            if len(parts) == 4 and parts[1] == "jobs" and parts[3] == "answer":
                return self._answer(parts, body)
            return self._send(404, {"error": "not found"})

        def _answer(self, parts, body):
            job_id = parts[2]
            job = store.answer(self._tenant(), job_id, body.get("answer"))
            if job is None:
                return self._send(404, {"error": "not found"})
            return self._send(200, job)

        def do_GET(self):
            parts = [p for p in self.path.strip("/").split("/") if p]
            if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
                job = store.get(self._tenant(), parts[2])
                if job is None:
                    return self._send(404, {"error": "not found"})
                return self._send(200, job)
            return self._send(404, {"error": "not found"})

        def do_DELETE(self):
            parts = [p for p in self.path.strip("/").split("/") if p]
            if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
                job = store.cancel(self._tenant(), parts[2])
                if job is None:
                    return self._send(404, {"error": "not found"})
                return self._send(200, job)
            return self._send(404, {"error": "not found"})

    return Handler


class Server:
    """A context manager, so a test cannot leak a listening socket."""

    def __init__(self, store, tenant="tnt_test"):
        self.store = store
        self.tenant = tenant
        self.httpd = None

    def __enter__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.tenant))
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        return False
