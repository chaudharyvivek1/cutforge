"""Prometheus text exposition for the signals §17 specifies.

No dependency: the format is text, and the store already knows the numbers.
v2.4 specified nine signals and emitted none, which made three of the
document's strongest claims unobservable.
"""


def render(store, now=None):
    """The signals the store can produce, in the format a scraper expects."""
    import time
    now = time.time() if now is None else now
    rows = store.db.execute("SELECT state, COUNT(*) n FROM jobs GROUP BY state").fetchall()
    counts = {r["state"]: r["n"] for r in rows}

    oldest = store.db.execute(
        "SELECT MIN(updated_at) t FROM jobs WHERE state='queued'").fetchone()["t"]
    retries = store.db.execute(
        "SELECT COUNT(*) n FROM jobs WHERE attempt > 1").fetchone()["n"]
    attempts = store.db.execute(
        "SELECT attempt, COUNT(*) n FROM jobs GROUP BY attempt").fetchall()

    out = [
        "# HELP cutforge_jobs_total Jobs by state.",
        "# TYPE cutforge_jobs_total gauge",
    ]
    for state in sorted(counts):
        out.append(f'cutforge_jobs_total{{state="{state}"}} {counts[state]}')

    out += ["# HELP cutforge_queue_depth Jobs waiting to be claimed.",
            "# TYPE cutforge_queue_depth gauge",
            f"cutforge_queue_depth {counts.get('queued', 0)}",
            "# HELP cutforge_oldest_job_age_seconds Age of the oldest queued job.",
            "# TYPE cutforge_oldest_job_age_seconds gauge",
            f"cutforge_oldest_job_age_seconds {round(max(0.0, now - oldest), 3) if oldest else 0.0}",
            "# HELP cutforge_retries_total Jobs that have been retried.",
            "# TYPE cutforge_retries_total counter",
            f"cutforge_retries_total {retries}",
            "# HELP cutforge_attempts_total Jobs by attempt count.",
            "# TYPE cutforge_attempts_total gauge"]
    for row in attempts:
        out.append(f'cutforge_attempts_total{{attempt="{row["attempt"]}"}} {row["n"]}')
    return "\n".join(out) + "\n"
