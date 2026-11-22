#!/usr/bin/env bash
# Run the suite in two batches.
#
# The full suite is over five minutes because Appendix A generates four
# 3000-frame fixtures for the split-rule test. Discovery in one process no
# longer fits a comfortable CI step, so the fast tests run first and the
# render tests second — a fast failure is worth more than a slow pass.
set -euo pipefail
cd "$(dirname "$0")"

FAST="test_compiler test_planner test_repair test_identity test_service test_store test_accuracy test_otio test_v22 test_conformance test_v25 test_v26 test_v27 test_v212"
RENDER="test_render test_compiler_extended test_packaging test_v28 test_v29 test_v210 test_v211"

echo "=== fast ==="
python3 -m unittest $FAST
echo "=== render ==="
python3 -m unittest $RENDER
echo "=== all green ==="
