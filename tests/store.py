"""A persistent job store and a worker loop, so a job can survive its process.

v2.1's service kept jobs in a dictionary: a restart lost everything, and a
worker that died mid-render took the job with it. §18 specifies checkpointing
at segment granularity, cooperative cancellation within thirty seconds, and a
retry that must not double-charge. Those are claims about *state surviving*,
and a dictionary cannot keep them.

SQLite here for one reason: it is a file, it has transactions, and it needs no
server. The invariants it carries are the ones in §13.3 that matter at this
size — a terminal state is final, an idempotency key returns one job, and a
claim on a job is exclusive.
"""
import json
import sqlite3
import time
import uuid

import webhook
from contextlib import contextmanager

# The states no transition leaves. `expired` was in this tuple from v2.2 and
# nothing ever set it — §8.5 says an unanswered hold expires *as failed*, so a
# seventh terminal state was a state with no path to it.
TERMINAL = ("succeeded", "failed", "cancelled", "quarantined")

# §18: the retry policy is keyed to the failure class, not to a counter alone.
RETRYABLE = {
    "TRANSIENT": True,        # network reset, 5xx from storage, worker eviction
    "RESOURCE": True,         # GPU OOM, disk full — retry once on a larger worker
    "PERMANENT": False,       # corrupt source, schema violation, missing asset
    "BUDGET": False,          # a ceiling was hit; retrying spends more of it
    "HOLD_EXPIRED": False,    # a timeout is not consent
    "POISON": False,          # identical failure three times
}
MAX_ATTEMPTS = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  kind            TEXT NOT NULL,
  state           TEXT NOT NULL,
  idempotency_key TEXT,
  attempt         INTEGER NOT NULL DEFAULT 1,
  segments_done   INTEGER NOT NULL DEFAULT 0,
  segments_total  INTEGER NOT NULL DEFAULT 0,
  payload         TEXT NOT NULL DEFAULT '{}',
  degraded        INTEGER NOT NULL DEFAULT 0,
  error           TEXT,
  hold_deadline   REAL,
  claimed_by      TEXT,
  claimed_at      REAL,
  retry_after     REAL NOT NULL DEFAULT 0,
  updated_at      REAL NOT NULL,
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_claimable ON jobs (state, claimed_at);

CREATE TABLE IF NOT EXISTS webhook_endpoints (
  id         TEXT PRIMARY KEY,
  tenant_id  TEXT NOT NULL,
  url        TEXT NOT NULL,
  secret     TEXT NOT NULL,
  UNIQUE (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS tokens (
  token      TEXT PRIMARY KEY,
  tenant_id  TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'tenant',
  subject    TEXT NOT NULL DEFAULT '',
  issued_at  REAL NOT NULL,
  expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS revocations (
  token      TEXT PRIMARY KEY,
  tenant_id  TEXT NOT NULL,
  revoked_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS buckets (
  tenant_id  TEXT PRIMARY KEY,
  tokens     REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS usage (
  tenant_id      TEXT NOT NULL,
  period         TEXT NOT NULL,
  render_minutes REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, period)
);

CREATE TABLE IF NOT EXISTS deliveries (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  endpoint_id     TEXT NOT NULL,
  job_id          TEXT,
  event           TEXT NOT NULL,
  body            TEXT NOT NULL,
  state           TEXT NOT NULL DEFAULT 'pending',
  attempts        INTEGER NOT NULL DEFAULT 0,
  next_attempt_at REAL NOT NULL DEFAULT 0,
  created_at      REAL NOT NULL,
  UNIQUE (tenant_id, job_id, event)
);
"""


class Store:
    def __init__(self, path=":memory:", clock=time.time):
        self.path = path
        self.clock = clock
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    @contextmanager
    def tx(self):
        try:
            yield self.db
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------ write
    def submit(self, tenant, kind, idempotency_key=None, payload=None):
        """The same key from the same tenant returns the original job (§15.1)."""
        with self.tx() as db:
            if idempotency_key:
                row = db.execute(
                    "SELECT * FROM jobs WHERE tenant_id=? AND idempotency_key=?",
                    (tenant, idempotency_key)).fetchone()
                if row:
                    return dict(row), False
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            db.execute(
                "INSERT INTO jobs (id, tenant_id, kind, state, idempotency_key,"
                " payload, updated_at) VALUES (?,?,?,?,?,?,?)",
                (job_id, tenant, kind, "queued", idempotency_key,
                 json.dumps(payload or {}), self.clock()))
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()), True

    def claim(self, worker, max_per_tenant=2):
        """Take one due job, fairly.

        Two rules, both of which v2.3 lacked. A job is not claimable before its
        `retry_after` — that is backoff — and a tenant may not hold more than
        `max_per_tenant` running jobs, which is what stops one tenant's fifty
        submissions starving another's one. Without the second rule the queue
        is first-in-first-out and a bulk uploader owns it.
        """
        with self.tx() as db:
            busy = {r["tenant_id"]: r["n"] for r in db.execute(
                "SELECT tenant_id, COUNT(*) AS n FROM jobs WHERE state='running'"
                " GROUP BY tenant_id")}
            rows = db.execute(
                "SELECT * FROM jobs WHERE state='queued' AND retry_after<=?"
                " ORDER BY updated_at LIMIT 200", (self.clock(),)).fetchall()
            for row in rows:
                if busy.get(row["tenant_id"], 0) >= max_per_tenant:
                    continue
                updated = db.execute(
                    "UPDATE jobs SET state='running', claimed_by=?, claimed_at=?,"
                    " updated_at=? WHERE id=? AND state='queued'",
                    (worker, self.clock(), self.clock(), row["id"])).rowcount
                if updated == 1:
                    return dict(db.execute("SELECT * FROM jobs WHERE id=?",
                                           (row["id"],)).fetchone())
            return None

    def transition(self, job_id, state, **fields):
        """Move a job, unless it is terminal — terminal states are final."""
        with self.tx() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["state"] in TERMINAL:
                return dict(row) if row else None
            sets = ["state=?", "updated_at=?"]
            values = [state, self.clock()]
            if "degraded" in fields:
                sets.append("degraded=?")
                values.append(1 if fields["degraded"] else 0)
            if state == "awaiting_input" and "hold_deadline" in fields:
                sets.append("hold_deadline=?")
                values.append(fields["hold_deadline"])
            values.append(job_id)
            db.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", values)
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def checkpoint(self, job_id, segments_done):
        """§18: a long render checkpoints per segment, so a resume starts there."""
        with self.tx() as db:
            db.execute("UPDATE jobs SET segments_done=?, updated_at=? WHERE id=?",
                       (segments_done, self.clock(), job_id))

    def fail(self, job_id, code, attempt_ceiling=MAX_ATTEMPTS, base_delay=1.0):
        """Retry by failure class, with backoff, then quarantine (§18).

        A job that fails identically three times is poison: retrying it is a
        loop that costs money and never succeeds, which is the class exists to
        prevent. A retryable failure is scheduled at `base_delay * 2^(n-1)`
        plus a jitter derived from the job id, so two jobs that failed at the
        same moment do not retry at the same moment and knock over a
        dependency that was just recovering.
        """
        with self.tx() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["state"] in TERMINAL:
                return dict(row) if row else None
            retryable = RETRYABLE.get(code, False)
            attempts = row["attempt"]
            if retryable and attempts < attempt_ceiling:
                delay = base_delay * (2 ** (attempts - 1))
                jitter = (hash(row["id"]) % 1000) / 1000.0 * delay * 0.5
                db.execute(
                    "UPDATE jobs SET state='queued', attempt=attempt+1, error=?,"
                    " retry_after=?, claimed_by=NULL, updated_at=? WHERE id=?",
                    (code, self.clock() + delay + jitter, self.clock(), job_id))
            elif retryable:
                db.execute(
                    "UPDATE jobs SET state='quarantined', error='POISON',"
                    " claimed_by=NULL, updated_at=? WHERE id=?", (self.clock(), job_id))
            else:
                db.execute(
                    "UPDATE jobs SET state='failed', error=?, claimed_by=NULL,"
                    " updated_at=? WHERE id=?", (code, self.clock(), job_id))
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def finish(self, job_id, state, error=None):
        """Terminal states are final: a finished job is never reopened.

        A terminal state also emits an event, and the UNIQUE (tenant, job,
        event) makes the emission idempotent — a job finished twice does not
        deliver twice, which is what §15.3's at-least-once promise requires
        of the sender.
        """
        with self.tx() as db:
            placeholders = ",".join("?" * len(TERMINAL))
            changed = db.execute(
                f"UPDATE jobs SET state=?, error=?, claimed_by=NULL, updated_at=?"
                f" WHERE id=? AND state NOT IN ({placeholders})",
                (state, error, self.clock(), job_id, *TERMINAL)).rowcount
            if changed:
                self._emit(db, job_id, state)
            return changed

    def _emit(self, db, job_id, state):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return
        event = f"job.{state}"
        for endpoint in db.execute(
                "SELECT * FROM webhook_endpoints WHERE tenant_id=?",
                (row["tenant_id"],)).fetchall():
            body = json.dumps({"event": event, "job_id": job_id,
                               "tenant_id": row["tenant_id"],
                               "state": state, "error": row["error"]}).encode()
            try:
                db.execute(
                    "INSERT INTO deliveries (id, tenant_id, endpoint_id, job_id, event,"
                    " body, created_at) VALUES (?,?,?,?,?,?,?)",
                    (f"dlv_{uuid.uuid4().hex[:8]}", row["tenant_id"], endpoint["id"],
                     job_id, event, body.decode(), self.clock()))
            except sqlite3.IntegrityError:
                pass                      # already emitted: idempotent by design

    # ------------------------------------------------------- shared state
    def store_token(self, token, tenant, role, subject, issued_at, expires_at):
        with self.tx() as db:
            db.execute("INSERT OR REPLACE INTO tokens (token, tenant_id, role, subject,"
                       " issued_at, expires_at) VALUES (?,?,?,?,?,?)",
                       (token, tenant, role, subject, issued_at, expires_at))

    def token_record(self, token):
        row = self.db.execute("SELECT * FROM tokens WHERE token=?", (token,)).fetchone()
        return dict(row) if row else None

    def revoke_token(self, token, tenant):
        """Revocation must survive a restart and reach every process."""
        with self.tx() as db:
            db.execute("INSERT OR REPLACE INTO revocations (token, tenant_id, revoked_at)"
                       " VALUES (?,?,?)", (token, tenant, self.clock()))

    def is_revoked(self, token):
        return self.db.execute("SELECT 1 FROM revocations WHERE token=?",
                               (token,)).fetchone() is not None

    def take_token(self, tenant, capacity, refill_per_second, now=None):
        """A shared token bucket: one row per tenant, refilled on read.

        Two workers behind a load balancer each keeping their own bucket would
        allow capacity × workers, which is not the limit anyone configured.
        """
        now = self.clock() if now is None else now
        with self.tx() as db:
            row = db.execute("SELECT tokens, updated_at FROM buckets WHERE tenant_id=?",
                             (tenant,)).fetchone()
            if row is None:
                tokens, last = float(capacity), now
            else:
                tokens = min(float(capacity),
                             row["tokens"] + (now - row["updated_at"]) * refill_per_second)
                last = now
            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0
            db.execute("INSERT OR REPLACE INTO buckets (tenant_id, tokens, updated_at)"
                       " VALUES (?,?,?)", (tenant, tokens, last))
            return allowed

    def consume_render_minutes(self, tenant, minutes, limit, period=None):
        """The quota that costs money, unlike submissions per minute (§16.1)."""
        period = period or time.strftime("%Y-%m")
        with self.tx() as db:
            row = db.execute("SELECT render_minutes FROM usage WHERE tenant_id=? AND period=?",
                             (tenant, period)).fetchone()
            used = row["render_minutes"] if row else 0.0
            if used + minutes > limit:
                return False, used
            db.execute("INSERT OR REPLACE INTO usage (tenant_id, period, render_minutes)"
                       " VALUES (?,?,?)", (tenant, period, used + minutes))
            return True, used + minutes

    # ------------------------------------------------------------- delivery
    def add_endpoint(self, tenant, url, secret):
        endpoint_id = f"wh_{uuid.uuid4().hex[:8]}"
        with self.tx() as db:
            db.execute("INSERT INTO webhook_endpoints (id, tenant_id, url, secret)"
                       " VALUES (?,?,?,?)", (endpoint_id, tenant, url, secret))
        return endpoint_id

    def pending_deliveries(self, now=None):
        now = self.clock() if now is None else now
        rows = self.db.execute(
            "SELECT * FROM deliveries WHERE state='pending' AND next_attempt_at<=?"
            " ORDER BY created_at", (now,)).fetchall()
        return [dict(r) for r in rows]

    def delivery_delivered(self, delivery_id):
        with self.tx() as db:
            db.execute("UPDATE deliveries SET state='delivered', attempts=attempts+1"
                       " WHERE id=?", (delivery_id,))
        return self.delivery(delivery_id)

    def delivery(self, delivery_id):
        row = self.db.execute("SELECT * FROM deliveries WHERE id=?",
                              (delivery_id,)).fetchone()
        return dict(row) if row else None

    def delivery_failed(self, delivery_id, base_delay=1.0, ceiling=5):
        """Retry with the same backoff shape §18 uses; dead-letter after five."""
        with self.tx() as db:
            row = db.execute("SELECT * FROM deliveries WHERE id=?",
                             (delivery_id,)).fetchone()
            if row is None:
                return None
            attempts = row["attempts"] + 1
            if attempts >= ceiling:
                db.execute("UPDATE deliveries SET state='dead', attempts=? WHERE id=?",
                           (attempts, delivery_id))
            else:
                delay = base_delay * (2 ** (attempts - 1))
                db.execute("UPDATE deliveries SET attempts=?, next_attempt_at=? WHERE id=?",
                           (attempts, self.clock() + delay, delivery_id))
            return self.delivery(delivery_id)

    def delivery_request(self, delivery_id):
        """The body and headers a sender posts, signed with the endpoint secret."""
        row = self.delivery(delivery_id)
        endpoint = self.db.execute("SELECT * FROM webhook_endpoints WHERE id=?",
                                   (row["endpoint_id"],)).fetchone()
        body = row["body"].encode()
        return body, webhook.headers(endpoint["secret"], body)

    def requeue_orphans(self, older_than=30.0):
        """A worker that died leaves a running job; put it back.

        The lease matters. v2.2 defaulted this to zero, which requeued every
        running job on every sweep — including the ones a live worker was
        rendering, so two workers could render the same job and both write.
        Thirty seconds is the lease a heartbeat is expected to renew.
        """
        with self.tx() as db:
            cutoff = self.clock() - older_than
            return db.execute(
                "UPDATE jobs SET state='queued', claimed_by=NULL, attempt=attempt+1,"
                " updated_at=? WHERE state='running' AND claimed_at<=?",
                (self.clock(), cutoff)).rowcount

    def cancel(self, tenant, job_id):
        with self.tx() as db:
            placeholders = ",".join("?" * len(TERMINAL))
            db.execute(
                f"UPDATE jobs SET state='cancelled', updated_at=?"
                f" WHERE id=? AND tenant_id=? AND state NOT IN ({placeholders})",
                (self.clock(), job_id, tenant, *TERMINAL))
            row = db.execute("SELECT * FROM jobs WHERE id=? AND tenant_id=?",
                             (job_id, tenant)).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------- read
    def get(self, tenant, job_id):
        row = self.db.execute("SELECT * FROM jobs WHERE id=? AND tenant_id=?",
                              (job_id, tenant)).fetchone()
        return dict(row) if row else None

    def expire_holds(self):
        """§8.5: an unanswered hold expires to failed, never to delivered."""
        with self.tx() as db:
            return db.execute(
                "UPDATE jobs SET state='failed', error='HOLD_EXPIRED', hold_deadline=NULL,"
                " updated_at=? WHERE state='awaiting_input' AND hold_deadline IS NOT NULL"
                " AND hold_deadline<=?", (self.clock(), self.clock())).rowcount


class Worker:
    """One loop, one job at a time, resumable from its checkpoint."""

    def __init__(self, store, name="w1", segments=4):
        self.store = store
        self.name = name
        self.segments = segments

    def run_once(self):
        job = self.store.claim(self.name)
        if job is None:
            return None
        start = job["segments_done"]
        for segment in range(start, self.segments):
            current = self.store.get(job["tenant_id"], job["id"])
            if current["state"] == "cancelled":
                return current                    # cooperative: stop at a boundary
            self.store.checkpoint(job["id"], segment + 1)
        self.store.finish(job["id"], "succeeded")
        return self.store.get(job["tenant_id"], job["id"])
