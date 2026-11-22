# Commit discipline — the four failures that produced the rules

Each of these happened in a real project and each cost real time. They are listed in the order they were discovered, because the later ones only became visible once the earlier ones were fixed.

## 1. `git add <directory>` swallowed the next commit

```bash
git add tests && git commit -m "feat: the compiler fix"   # stages all of tests/
git add tests/service.py && git commit -m "feat: the service"   # nothing to stage
```

The second commit exits non-zero. If the steps are separate lines rather than an `&&` chain, **the script keeps going** — so the third and fourth commits succeed and the second is simply missing.

**Symptom:** `git log` has fewer commits than the plan, and a file appears in a commit whose message does not mention it.

**Fix:** explicit paths, and a commit function that exits the whole script on failure:

```bash
c() { git add "$@" && git commit -q -m "$1" || { echo "FAILED"; exit 1; }; }
```

## 2. `set -e` did not save it

`set -e` aborts on a failing command, but only within the same shell invocation and only for commands not in a condition. A commit inside `a && b && c` at the end of a line aborts that line — and the next line runs.

**Fix:** the commit helper above, which calls `exit 1` explicitly.

## 3. `--amend` and `reset --soft` were used to hide it

Amending the wrong commit to "fix" a missing one rewrites history that may already be pushed, and the mistake becomes invisible rather than corrected.

**Fix:** before pushing, `git reset --soft <good-commit>` and redo the sequence. After pushing, add a correcting commit and say so.

## 4. The verification was missing

Nothing in the sequence checked that the commit it just made *existed*.

**Fix:** after a multi-commit run, count them:

```bash
git log --oneline | head -n "$EXPECTED" | wc -l
```

and compare against the plan. A history that cannot be counted cannot be trusted.

---

## The rules, in one place

1. Stage explicit paths; never a directory that will be committed again.
2. One commit, one intent, one prefix (`feat:`, `fix:`, `test:`, `build:`, `docs:`, `ci:`).
3. Body explains *why*; the diff explains what.
4. Fail loudly: a commit that did not happen must stop the run.
5. Verify the count before pushing.
6. Redo with `reset --soft` before pushing; correct with a new commit after.
7. Never force-push a shared branch.
8. When two implementations of one thing exist, delete one — do not reconcile them.
