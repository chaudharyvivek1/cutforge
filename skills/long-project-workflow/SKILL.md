---
name: long-project-workflow
description: Run a long project as a sequence of small, verified, committed steps — a spec or a codebase that will be worked on across many sessions, where every change must be reviewable, reversible and provable. Use when the user works in versions or milestones ("do v2.9", "next phase", "update the repo"), asks for step-by-step commits, wants documentation files (README, RELEASES, ROADMAP, CHANGELOG, worklog), or says they will come back to the work repeatedly. Covers the verify-then-change loop, commit discipline, the documentation set a long project needs, and how to hand over so the next session starts where the last one stopped.
---

# Long-project workflow

A project that will be worked on for months is not a big task; it is a hundred small ones with a memory. This skill is that memory: the order of work, the commit discipline, the documents that keep a stranger (or you, in three weeks) oriented, and the checks that make "done" mean something.

## The loop, for every session

**Verify, then change.** Never start editing on an unverified tree.

1. **Orient** — read the state, not the history:
   ```bash
   git log --oneline | head -3 && git status --short
   ```
   Then run the project's checks. If anything is red, fix that first; a change made on a red tree cannot be attributed.
2. **Re-establish the tooling.** A fresh pod/session often lacks what the last one installed. Re-run the install line and confirm nothing is *skipping* — a skipped test is not a pass.
3. **Read the open list** (findings, TODOs, backlog). It is the only honest statement of what is wrong.
4. **Do the smallest complete unit.** One version, one finding, one subsystem — never two.
5. **Check it four ways**: static analysis, unit tests, the project's own checkers, and a look at the actual artefact.
6. **Commit in steps**, each one reviewable alone.
7. **Write the next open list before closing.**

## Commit discipline

This is where long projects quietly rot. The rule:

> **Stage explicit paths. Verify every commit landed. Never let a commit be a no-op.**

A sequence that looks correct and silently produces three commits instead of seven is worse than one long commit, because the history now lies about what changed together.

```bash
set -e
c() { git add "$@" && git commit -q -m "$MSG" -m "$BODY" || { echo "COMMIT FAILED: $MSG"; exit 1; }; }

c path/a.py path/a_test.py    # not: git add tests
c docs/spec.md
```

**The failure this prevents** (measured: five times in one project): `git add tests` stages the whole directory, so the next commit's `git add tests/other.py` has nothing left to stage, `git commit` exits non-zero, and — because the steps were separate lines rather than one `&&` chain — the remaining commits still run. The result is a history where a subsystem appears inside an unrelated fix.

Rules that follow:

- **One commit = one intent.** `fix:`, `feat:`, `test:`, `build:`, `docs:`, `ci:`, `chore:`.
- **Body explains why**, not what. The diff says what.
- **Verify, don't assume**: after the sequence, `git log --oneline | head -n <expected>` and count. If the count is wrong, `git reset --soft` and redo — never `--amend` your way out of a conflated history.
- **Never force-push** a branch someone else may have read.
- **Delete duplicates rather than reconciling them.** Two implementations of one contract, each correct, is the most expensive state to be in.

See `references/commit-discipline.md` for the four failures that produced these rules.

## The documentation set

A long project needs seven documents, and they answer different questions. Adding one late is cheap; reconstructing one is not.

| File | Answers | Written when |
|---|---|---|
| `README.md` | What is this, what does it refuse to be, how do I read it | First commit |
| `CHANGELOG.md` | What changed in each version and why | Every version |
| `RELEASES.md` | What shipped, when, and what "release" means here | Second version |
| `ROADMAP.md` | Where it stands, what is left, how long | Once, then after each version |
| `docs/worklog.md` | How it was built, step by step, and what each step found | Every session |
| `docs/reviews/vX-candidates.md` | What is still wrong, with severity and a proposed fix | Every version, before shipping |
| `docs/repo/description.md` + `ABOUT.md` | The repository's own metadata, as text | When it goes public |

Two of these are routinely skipped and are the two that matter most for a long project: the **worklog** (so the next session knows what was tried and why) and the **open list** (so "done" has a definition).

## Prove the artefact, not the source

If the deliverable is a document, build it from a source file and then **extract it back and re-run every check on the extracted text**. If it is a binary or a render, hash it. A source that passes its own tests while the artefact differs is the most common silent failure in long projects.

Then **look at it**: render and read the page. Split table rows, collapsed builds and stale captions are invisible to text checks.

## Handing over

Every session should end with a tree that a stranger can pick up:

- `git status` clean, checks green, open list written.
- The worklog's last section says what was done, what was found, and what is next.
- Any decision you made on the user's behalf is stated in one line, so it can be reversed.

## Which skill to load

Load one format skill for the artefact and this one for the process:

| Deliverable | Skill |
|---|---|
| Word document | `sarvam-docx` (docx-js) — or a project builder if the repo already has one |
| PDF | `sarvam-pdf` |
| Spreadsheet | `sarvam-xlsx` |
| Slides | `sarvam-slides` |
| Single HTML page, diagram, dashboard | `sarvam-html-skill` |
| Application code, a bug fix, a build error | `sarvam-coding` |
| A specification through review cycles | `technical-spec-versioning` |
| Creating or improving a skill | `skill-creator` |

When a repository already has its own builder (a script that generates the document from markdown), **use it** rather than the platform skill: the project's builder is what keeps the artefact and its source in sync, and replacing it breaks the round-trip check.
