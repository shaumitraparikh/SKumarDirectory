#!/usr/bin/env bash
# Smoke test for the single entry point (update.sh).
# Rebuilds and runs the whole suite in --local mode, then checks that the
# catalog was fully generated and that the run left the Git history untouched.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output_file="$(mktemp)"
trap 'rm -f "$output_file"' EXIT

head_before="$(git rev-parse HEAD)"

# update.sh --local must never pull, commit, or restart the seller server.
CATALOG_NO_BROWSER=1 ./update.sh --local >"$output_file" 2>&1 || {
    echo "update.sh --local failed with exit code $?."
    cat "$output_file"
    exit 1
}
cat "$output_file"

if ! grep -qE '^[[:space:]]*Items: [1-9][0-9]*[[:space:]]*$' "$output_file"; then
    echo "The updater did not report a non-empty catalog build."
    exit 1
fi

if ! grep -q "rebuilt and tested locally" "$output_file"; then
    echo "The updater did not reach the expected local result."
    exit 1
fi

if ! grep -q "Ran 1 test" "$output_file" && ! grep -qE '^Ran [0-9]+ tests?' "$output_file"; then
    echo "The updater did not run the Python test suite."
    exit 1
fi

head_after="$(git rev-parse HEAD)"
if [ "$head_before" != "$head_after" ]; then
    echo "The local smoke test unexpectedly changed the Git commit."
    exit 1
fi

echo "One-click smoke test passed."
