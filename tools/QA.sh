#!/usr/bin/env bash
# QA.sh: every check this repository asks for before a release, in one command. Run it from anywhere.
#   tools/QA.sh                      all checks, on Python 3.10 to 3.14
#   PYTHONS="3.12" tools/QA.sh       the same, on the Pythons you name (space separated)
# Needs uv. Changes nothing in the working tree; stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONS="${PYTHONS:-3.10 3.11 3.12 3.13 3.14}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
step() { printf '\n== %s\n' "$*"; }
fail() { printf '\nQA FAILED: %s\n' "$*" >&2; exit 1; }

step "tests, with every optional backend (rdflib, sqlite-vec, hnswlib), on: $PYTHONS"
for v in $PYTHONS; do
  printf 'python %s: ' "$v"
  uv run --python "$v" --with rdflib --with sqlite-vec --with hnswlib test_bowerbird_mcp.py | tail -n 1
done

step "docs-src/tools.md is what the tools' own docstrings produce"
cp docs-src/tools.md "$TMP/tools.md"
uv run --python 3.12 docs_tools.py
if ! cmp -s docs-src/tools.md "$TMP/tools.md"; then
  cp "$TMP/tools.md" docs-src/tools.md
  fail "docs-src/tools.md is stale | fix: uv run --python 3.12 docs_tools.py"
fi

step "the docs build with no warnings, and docs/ is the committed build of docs-src/"
uvx --with pymdown-extensions mkdocs build --strict -d "$TMP/site" >/dev/null
diff -r -x 'sitemap.xml*' "$TMP/site" docs >/dev/null || fail "docs/ is stale | fix: uvx --with pymdown-extensions mkdocs build"

step "uv.lock matches pyproject.toml"
uv lock --check

printf '\nQA ok (%s)\n' "$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
