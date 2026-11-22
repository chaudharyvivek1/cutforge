"""A minimal job service: the runtime contracts of §15, §17 and §18, executed.

Nothing here needs a GPU, media or a framework. What it tests is what a
library call cannot: idempotency across a retry, the state machine surviving a
restart of the request, a hold with a deadline, and cancellation reaching a
terminal state.

It is a reference, not a product. One process, one dictionary, one thread.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import auth as A
import metrics as M
import ratelimit as RL


def job_view(row):
    """The API's view of a job row — derived fields only, never stored twice."""
    if row is None:
        return None
    return {
        "id": row["id"], "tenant_id": row["tenant_id"], "kind": row["kind"],
        "state": row["state"], "attempt": row["attempt"],
        "segments_done": row["segments_done"],
        "hold_deadline": row["hold_deadline"], "error": row["error"],
        "degraded": bool(row["degraded"]),
    }


def make_handler(store, tokens=None):
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
            """§14.5: the tenant comes from the token; a header may only narrow."""
            try:
                return A.resolve(self.headers, self.server.tokens,
                                 self.headers.get("X-Tenant"))
            except A.AuthError as error:
                self._send(error.status, {"error": {"code": error.code}})
                return None

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            parts = [p for p in self.path.strip("/").split("/") if p]

            if parts == ["v1", "jobs"]:
                tenant = self._tenant()
                if tenant is None:
                    return
                if not self.server.buckets.take(tenant):
                    return self._send(429, {"error": {"code": "RATE_LIMITED",
                                                      "retry_after": self.server.buckets.retry_after(tenant)}})
                try:
                    payload, quality = self._quality_gate(body)
                except QualityRefused as refusal:
                    return self._send(422, {"error": {
                        "code": "PLAN_UNREPAIRABLE",
                        "message": "the plan could not be brought to an acceptable score",
                        "details": refusal.gate}})
                job, created = store.submit(tenant, body.get("kind", "plan"),
                                            self.headers.get("Idempotency-Key"),
                                            payload)
                return self._send(202 if created else 200,
                                  {"job_id": job["id"], "state": job["state"],
                                   "quality": quality})
            if len(parts) == 4 and parts[1] == "jobs" and parts[3] == "answer":
                return self._answer(parts, body)
            return self._send(404, {"error": "not found"})

        def _quality_gate(self, body):
            """§7.5: a plan that validates and scores badly must not ship.

            v2.13 built the repair and nothing called it. The gate runs it on
            submission, records what it changed, and refuses a plan it cannot
            bring to an acceptable score rather than rendering it silently.
            """
            payload = body.get("payload")
            if body.get("kind", "plan") != "plan" or not isinstance(payload, dict):
                return payload, None
            plan = payload.get("plan")
            if not plan:
                return payload, None
            import distribution as Ds
            import repair as Rp
            import rubric as Rb
            request = payload.get("request") or {}

            def verdict(candidate):
                # Both judges must accept. v2.17's labelled set contains a plan
                # that passes every threshold and is fifteen identical shots —
                # the threshold judge cannot see it and the shape judge can.
                return ("acceptable" if Rb.score(candidate, request)["verdict"] == "acceptable"
                        and Ds.judge(candidate, request)["label"] == "good"
                        else "below bar")

            before = {"verdict": verdict(plan), "total": Rb.score(plan, request)["total"]}
            repaired = Rp.apply_quality_repair(plan, request)
            after = {"verdict": verdict(repaired),
                     "total": Rb.score(repaired, request)["total"]}
            gate = {"before": before["verdict"], "after": after["verdict"],
                    "total": after["total"],
                    "repairs": Rp.quality_diff(plan, payload.get("request") or {})["repairs"]}
            if after["verdict"] not in ("acceptable",):
                # v2.14 repaired and reported, and queued the job anyway. A plan
                # the repair cannot lift fails later in the renderer, where the
                # error is more expensive and less legible — so it is refused
                # here, naming the criterion that would not move.
                gate["unrepairable"] = [r["criterion"] for r in gate["repairs"]]
                raise QualityRefused(gate)
            return dict(payload, plan=repaired), gate

        def _answer(self, parts, body):
            job_id = parts[2]
            job = store.get(self._tenant(), job_id)
            if job is None or job["state"] != "awaiting_input":
                return self._send(404, {"error": "not found"})
            answer = body.get("answer")
            if answer == "accept_degraded":
                store.transition(job_id, "running", degraded=True)
            elif answer == "confirm":
                store.transition(job_id, "running")
            else:
                return self._send(422, {"error": {"code": "UNKNOWN_ANSWER"}})
            return self._send(200, job_view(store.get(self._tenant(), job_id)))

        def do_GET(self):
            parts = [p for p in self.path.strip("/").split("/") if p]
            if parts == ["metrics"]:
                pass
            if parts == ["metrics"]:
                body = M.render(store).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
                store.expire_holds()
                job = store.get(self._tenant(), parts[2])
                if job is None:
                    return self._send(404, {"error": "not found"})
                return self._send(200, job_view(job))
            return self._send(404, {"error": "not found"})

        def do_DELETE(self):
            parts = [p for p in self.path.strip("/").split("/") if p]
            if parts == ["metrics"]:
                pass
            if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
                job = store.cancel(self._tenant(), parts[2])
                if job is None:
                    return self._send(404, {"error": "not found"})
                return self._send(200, job_view(job))
            return self._send(404, {"error": "not found"})

    return Handler


class QualityRefused(Exception):
    """§7.5: a plan the repair cannot lift is refused, not queued."""

    def __init__(self, gate):
        super().__init__("PLAN_UNREPAIRABLE")
        self.gate = gate


class Server:
    """A context manager, so a test cannot leak a listening socket."""

    def __init__(self, store, tokens, buckets=None):
        self.store = store
        self.tokens = tokens
        self.buckets = buckets or RL.Buckets()
        self.httpd = None

    def __enter__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.tokens))
        self.httpd.tokens = self.tokens
        self.httpd.buckets = self.buckets
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        return False
