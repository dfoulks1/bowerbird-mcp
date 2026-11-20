#!/usr/bin/env bash
# QA.sh: every check this repository asks for before a release, in one command. Run it from anywhere.
#   tools/QA.sh                      all checks, on Python 3.10 to 3.14
#   PYTHONS="3.12" tools/QA.sh       the same, on the Pythons you name (space separated)
#   tools/QA.sh --rebuild            first regenerate docs-src/tools.md and rebuild docs/ (the only thing that writes to the tree)
# Needs uv. Without --rebuild it changes nothing in the working tree (but docs_tools.py records docs-src/tools.md as derived in
# .waxseals.yaml the first time, and only then). It stops at the first failure, except ruff and mypy, which both run (last).
set -euo pipefail
cd "$(dirname "$0")/.."

REBUILD=0
[ "${1:-}" = "--rebuild" ] && REBUILD=1

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
  if [ "$REBUILD" = 1 ]; then
    echo "regenerated docs-src/tools.md"
  else
    cp "$TMP/tools.md" docs-src/tools.md
    fail "docs-src/tools.md is stale | fix: uv run --python 3.12 docs_tools.py (or tools/QA.sh --rebuild)"
  fi
fi

if [ "$REBUILD" = 1 ]; then
  step "rebuild docs/ from docs-src/ (seal the pages a person reviewed first: a build made before a seal is stale)"
  uvx --with pymdown-extensions mkdocs build --strict >/dev/null
fi

step "the docs build with no warnings, and docs/ is the committed build of docs-src/"
uvx --with pymdown-extensions mkdocs build --strict -d "$TMP/site" >/dev/null
diff -r -x 'sitemap.xml*' "$TMP/site" docs >/dev/null || fail "docs/ is stale | fix: tools/QA.sh --rebuild (or uvx --with pymdown-extensions mkdocs build)"

step "uv.lock matches pyproject.toml"
uv lock --check

step "ruff (the [tool.ruff] settings in pyproject.toml) and mypy: both run, then both are reported"
lint=0
uvx ruff check . || lint=1
uv run --with mypy --with types-PyYAML --with types-Markdown --with types-Pygments mypy bowerbird_mcp.py bowerbird_serve.py bowerbird_facts.py bowerbird_seal.py bowerbird_okf.py docs_tools.py || lint=1
[ "$lint" = 0 ] || fail "ruff or mypy reported findings (above) | fix: see TODO.md; uvx ruff check . --fix clears the safe ruff ones"

printf '\nQA ok (%s)\n' "$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
