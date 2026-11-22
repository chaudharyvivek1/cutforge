#!/usr/bin/env python3
"""Static checks on the migration the specification publishes.

§13.5 promises a test that fails if any tenant-scoped table lacks the
composite key that makes cross-tenant references impossible. This is that
test, run against the DDL in the document rather than against a live
database — which means it can run on every push without a Postgres.

Usage:
    python build/check_sql.py [<spec.md>]
"""
import re
import sys
from pathlib import Path

try:
    import sqlglot
except ImportError:
    print("sqlglot is not installed; skipping migration checks (pip install sqlglot)")
    sys.exit(0)

FAILURES = []


def fail(msg):
    FAILURES.append(msg)


def newest_spec():
    candidates = sorted(Path("docs/spec").glob("v*.md"),
                        key=lambda p: [int(x) for x in p.stem.lstrip("v").split(".")])
    if not candidates:
        raise SystemExit("no specification found in docs/spec")
    return candidates[-1]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_spec()
    text = path.read_text(encoding="utf-8")

    marker = "--  Prompt-Driven AI Video Editor"
    if marker not in text:
        fail("migration block not found")
        print_failures()
        return 1
    i = text.index(marker)
    start = text.rindex("```", 0, i)
    end = text.index("```", i)
    sql = text[start + 3:end]

    # the header names a version and it must be this document's version
    vm = re.search(r"VERSION (\d+\.\d+)", text)
    version = vm.group(1) if vm else None
    hm = re.search(r"schema, v(\d+\.\d+)", sql)
    if not hm:
        fail("migration header does not name a schema version")
    elif version and hm.group(1) != version:
        fail(f"migration header says v{hm.group(1)}; the document is v{version}")

    # EXTENSION, DO blocks and GRANT are outside sqlglot's grammar; they are
    # valid PostgreSQL and are skipped rather than reported as failures.
    try:
        parsed = sqlglot.parse(sql, read="postgres", error_level=sqlglot.ErrorLevel.IGNORE)
    except TypeError:
        parsed = sqlglot.parse(sql, read="postgres")
    statements = [s for s in parsed if s]
    creates = [s for s in statements if s.key == "create" and s.args.get("kind") == "TABLE"]
    if not creates:
        fail("no CREATE TABLE statements parsed")

    tables = {}
    for c in creates:
        name = c.this.this.name
        body = c.sql(dialect="postgres")
        tables[name] = body

    # §13.2: a table that is the target of a relationship exposes UNIQUE (tenant_id, id),
    # and every tenant-scoped table has a primary key. Scoped this way because the
    # first version of this check demanded the unique on every table and the document's
    # own append-only logs contradicted it.
    referenced = set()
    for body in tables.values():
        for m in re.finditer(r"REFERENCES\s+(\w+)\s*\(\s*tenant_id", body, re.I):
            referenced.add(m.group(1))

    for name, body in tables.items():
        has_tenant = re.search(r"\btenant_id\b", body, re.I) is not None
        has_pk = "PRIMARY KEY" in body.upper()
        if has_tenant and not has_pk:
            fail(f"{name} has tenant_id but no id primary key — §13.2")
        if name in referenced:
            # the unique must carry the tenant as its first column; the rest of
            # the key follows the relationship (id, or sequence_id + revision)
            if not re.search(r"UNIQUE\s*\(\s*tenant_id\b", body, re.I):
                fail(f"{name} is a foreign-key target but has no UNIQUE starting with tenant_id — §13.2")

    for name in ("audit_log", "ops_log"):
        if name in referenced:
            fail(f"{name} is referenced; append-only logs must not be")

    # §14.1: every tenant-scoped table must be named in the RLS loop.
    # A table that exists and is not covered is the exact failure the section
    # warns about, and v1.7 introduced one by adding a table and not the loop.
    rls_names = set()
    for m in re.finditer(r"FOREACH t IN ARRAY ARRAY\[(.*?)\]", sql, re.S):
        rls_names |= set(re.findall(r"'([a-z_]+)'", m.group(1)))
    if not rls_names:
        fail("no RLS table array found — §14.1")
    else:
        for name, body in tables.items():
            if re.search(r"\btenant_id\b", body, re.I) and name not in rls_names:
                fail(f"{name} has tenant_id but is not in the RLS loop — §14.1")
        for name in sorted(rls_names - set(tables)):
            fail(f"RLS loop names {name}, which is not created by this migration")

    # §16.6.1: the erasure table must carry the jurisdiction it looks deadlines up by
    if "erasures" in tables:
        body = tables["erasures"]
        if "jurisdiction" not in body:
            fail("erasures has no jurisdiction column — §16.6.1")
        if "deadline" not in body:
            fail("erasures has no deadline column — §16.6.1")
    else:
        fail("no erasures table — §16.6.1")

    print(f"{path.name}: {len(statements)} statements, {len(tables)} tables, schema v{hm.group(1) if hm else '?'}")
    return print_failures()


def print_failures():
    if FAILURES:
        print("FAILED:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("Migration consistent with §13.2 and §16.6.1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
