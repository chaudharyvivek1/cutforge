#!/usr/bin/env bash
# Verify a project's state before changing anything.
# Usage: bash scripts/verify.sh "<test command>" "<checker command>..."
set -u
fail=0

echo "=== state ==="
git log --oneline | head -3
git status --short || true
[ -z "$(git status --porcelain)" ] || { echo "!! tree is dirty — commit or stash first"; fail=1; }

echo "=== tests ==="
if [ -n "${1:-}" ]; then
  if eval "$1" 2>&1 | tail -5 | tee /tmp/_tests.txt | grep -qi "skipped"; then
    echo "!! a test skipped — a skip is not a pass"
    fail=1
  fi
  grep -qE "\bOK\b|passed" /tmp/_tests.txt || { echo "!! tests did not pass"; fail=1; }
else
  echo "(no test command given)"
fi

echo "=== checkers ==="
shift || true
for cmd in "$@"; do
  if ! eval "$cmd" >/dev/null 2>&1; then
    echo "!! checker failed: $cmd"
    fail=1
  else
    echo "ok  $cmd"
  fi
done

[ "$fail" -eq 0 ] && echo "=== ready ===" || echo "=== NOT ready ==="
exit "$fail"
