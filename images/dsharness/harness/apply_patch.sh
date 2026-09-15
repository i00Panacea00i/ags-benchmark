#!/usr/bin/env bash
# Patch applicator (DATA_CONTRACT.md §4).
# The golden patch must apply strictly (git apply, no fuzzy fallback).
# Usage: apply_patch.sh <patch_file>
set -euo pipefail
PATCH="${1:?usage: apply_patch.sh <patch_file>}"
git apply --check "$PATCH" && git apply "$PATCH"
echo "applied: $PATCH"
