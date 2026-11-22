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
                job, created = store.submit(self._tenant(), body.get("kind", "plan"),
                                            self.headers.get("Idempotency-Key"),
                                            body.get("payload"))
                return self._send(202 if created else 200,
                                  {"job_id": job["id"], "state": job["state"]})
            if len(parts) == 4 and parts[1] == "jobs" and parts[3] == "answer":
                return self._answer(parts, body)
            return self._send(404, {"error": "not found"})

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


class Server:
    """A context manager, so a test cannot leak a listening socket."""

    def __init__(self, store, tokens):
        self.store = store
        self.tokens = tokens
        self.httpd = None

    def __enter__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.tokens))
        self.httpd.tokens = self.tokens
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        return False
