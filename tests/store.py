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
from contextlib import contextmanager

TERMINAL = ("succeeded", "failed", "cancelled", "expired", "quarantined")

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
  updated_at      REAL NOT NULL,
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_claimable ON jobs (state, claimed_at);
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

    def claim(self, worker):
        """Take one queued job exclusively. Two workers cannot claim the same job."""
        with self.tx() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE state='queued' ORDER BY updated_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            updated = db.execute(
                "UPDATE jobs SET state='running', claimed_by=?, claimed_at=?, updated_at=?"
                " WHERE id=? AND state='queued'",
                (worker, self.clock(), self.clock(), row["id"])).rowcount
            if updated != 1:
                return None                     # somebody else won the race
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

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

    def fail(self, job_id, code, attempt_ceiling=MAX_ATTEMPTS):
        """Retry by failure class, then quarantine (§18).

        A job that fails identically three times is poison: retrying it is a
        loop that costs money and never succeeds, which is the failure the
        class exists to prevent.
        """
        with self.tx() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["state"] in TERMINAL:
                return dict(row) if row else None
            retryable = RETRYABLE.get(code, False)
            attempts = row["attempt"]
            if retryable and attempts < attempt_ceiling:
                db.execute(
                    "UPDATE jobs SET state='queued', attempt=attempt+1, error=?,"
                    " claimed_by=NULL, updated_at=? WHERE id=?",
                    (code, self.clock(), job_id))
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
        """Terminal states are final: a finished job is never reopened."""
        with self.tx() as db:
            placeholders = ",".join("?" * len(TERMINAL))
            db.execute(
                f"UPDATE jobs SET state=?, error=?, claimed_by=NULL, updated_at=?"
                f" WHERE id=? AND state NOT IN ({placeholders})",
                (state, error, self.clock(), job_id, *TERMINAL))

    def requeue_orphans(self, older_than=0.0):
        """A worker that died leaves a running job; put it back."""
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
