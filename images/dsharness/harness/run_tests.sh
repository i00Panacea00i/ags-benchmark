#!/usr/bin/env bash
# Unified test entrypoint (DATA_CONTRACT.md §4).
#
# Usage:
#   run_tests.sh <instance_id> [--reset] [--apply-tests] [--apply-golden] [--list]
#
#   --reset        restore repo to pristine base_commit state first
#   --apply-tests  apply the instance's test patch after reset/current state
#   --apply-golden apply the instance's golden patch (implies tests already applied)
#   --list         print F2P/P2P test ids and exit
#
# Runs the instance's FAIL_TO_PASS + PASS_TO_PASS suites against the CURRENT
# repo state, writes JSON summary to /benchmark/results/<instance_id>.json,
# exits 0 iff every selected test passes.
set -uo pipefail

ROOT="${BENCHMARK_ROOT:-/benchmark}"
INSTANCE_ID="${1:?usage: run_tests.sh <instance_id> [--reset] [--apply-tests] [--apply-golden] [--list]}"
shift || true

RESET=0; APPLY_TESTS=0; APPLY_GOLDEN=0; LIST=0
for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    --apply-tests) APPLY_TESTS=1 ;;
    --apply-golden) APPLY_GOLDEN=1 ;;
    --list) LIST=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# --- load instance record from manifest ---
mapfile -t RECORDS < <(jq -c "select(.instance_id == \"$INSTANCE_ID\")" "$ROOT/manifest.jsonl")
[ "${#RECORDS[@]}" -ge 1 ] || { echo "instance $INSTANCE_ID not found in manifest" >&2; exit 2; }
REC="${RECORDS[0]}"

REPO_NAME=$(jq -r '.repo' <<<"$REC" | sed 's|/|__|g')
BASE_COMMIT=$(jq -r '.base_commit' <<<"$REC")
REPO_DIR="$ROOT/repos/$REPO_NAME"
# 兼容相对（DATA_CONTRACT 布局）与绝对（内容注入布局）两种补丁路径
TEST_PATCH=$(jq -r '.test_patch' <<<"$REC");  [[ "$TEST_PATCH"  = /* ]] || TEST_PATCH="$ROOT/$TEST_PATCH"
GOLDEN_PATCH=$(jq -r '.golden_patch' <<<"$REC"); [[ "$GOLDEN_PATCH" = /* ]] || GOLDEN_PATCH="$ROOT/$GOLDEN_PATCH"

mapfile -t ALL_IDS < <(jq -r '.FAIL_TO_PASS[], .PASS_TO_PASS[]' <<<"$REC")
mapfile -t F2P_IDS < <(jq -r '.FAIL_TO_PASS[]' <<<"$REC")

if [ "$LIST" -eq 1 ]; then
  printf 'F2P:\n'; printf '  %s\n' "${F2P_IDS[@]}"
  printf 'P2P:\n'; jq -r '.PASS_TO_PASS[]' <<<"$REC" | sed 's/^/  /'
  exit 0
fi

cd "$REPO_DIR" || exit 2

# --- state transitions ---
if [ "$RESET" -eq 1 ]; then
  git checkout --quiet -- . || true
  git clean -qfd || true
  git checkout --quiet "$BASE_COMMIT"
fi
[ "$APPLY_TESTS" -eq 1 ]  && git apply "$TEST_PATCH"
[ "$APPLY_GOLDEN" -eq 1 ] && git apply "$GOLDEN_PATCH"

# --- run suite ---
mkdir -p "$ROOT/results"
OUT="$ROOT/results/${INSTANCE_ID}.json"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pytest "${ALL_IDS[@]}" -q --tb=no \
  --json-report --json-report-file="$OUT" 2>/dev/null || \
"$PYTHON" -m pytest "${ALL_IDS[@]}" -q --tb=no | tee "$OUT.txt"

# --- summarize (works with or without pytest-json-report) ---
"$PYTHON" - "$OUT" "$INSTANCE_ID" "${F2P_IDS[@]}" <<'PYEOF'
import json, sys, pathlib
out_path, instance = sys.argv[1], sys.argv[2]
f2p = set(sys.argv[3:])
try:
    data = json.loads(pathlib.Path(out_path).read_text())
    tests = {t["nodeid"]: t["outcome"] for t in data.get("tests", [])}
except Exception:
    tests = {}
summary = {"instance_id": instance, "total": len(tests),
           "fail_to_pass": {k: tests.get(k, "missing") for k in sorted(f2p)},
           "all_passed": bool(tests) and all(v == "passed" for v in tests.values())}
pathlib.Path(out_path).write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
sys.exit(0 if summary["all_passed"] else 1)
PYEOF
exit $?
