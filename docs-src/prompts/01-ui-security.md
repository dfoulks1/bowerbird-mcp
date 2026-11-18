# 01 — Seal-only viewer and hidden-file fix (2.1.3)

2026-11-18 · type PR · lead Sonnet 5.5, medium effort. Source: `TODO.md`, section 2.1.3.

## Task

`bowerbird serve` cannot show or seal a seal-only collection, and it serves hidden files. Fix both on a new branch
`release-2.1.3`, cut from `release-2.1.2`.

Today, in `bowerbird_serve.py`:
- `scan()` globs `*.md` only, so code, YAML and config files get no page and no Seal button.
- `/` with no root `index.md` falls through to a plain directory listing.
- `do_GET` ends in `SimpleHTTPRequestHandler.do_GET`, and `do_HEAD` is inherited. Both go through `send_head()`, which
  serves anything under the root (`.env`, `.git/`, `.waxseals.yaml`) and follows symlinks. Listings go through
  `list_directory()`.

`kb` in `bowerbird_serve.py` is the `bowerbird_mcp` module, passed into `run(kb, ...)`. Add a one-line comment saying so
at the top of `run()`.

## Rules

- **Q3 Lead.** Sonnet 5.5, medium. A session on another model or effort stops and says so before doing anything.
- **Q4 Scope.** The full TODO plan:
  1. `/` renders the shell with empty reading and details panes when there is no `index.md`.
  2. `scan()` also lists `kb.sealonly_files()`, with state from `kb.reviews()` (pass `{}` for the frontmatter).
  3. The reading pane shows a seal-only file read-only as `<pre>` with line numbers and the existing Seal modal.
  4. New extra `syntax = ["pygments"]` in `pyproject.toml` (`bowerbird-mcp[serve,syntax]`). No per-language extras.
- **Q5 Hidden files.** Any request path with a dot-prefixed part is 404: `.env`, `.git/…`, `sub/.hidden`. Decode the
  path first, then check. Fix it in `send_head()` and `list_directory()` so GET, HEAD and listings are all covered, not
  only `do_GET`. Reuse `kb.confined` and `kb.inside` for path checks. Do not hand-roll them.
- **Q6 Limits.** A binary (not UTF-8) or oversized file is not listed and not shown. It is not sealable from the viewer;
  the CLI and `seal check` still cover it.
- **Q7 Tests.** Asserts in `test_bowerbird_mcp.py` that start the real handler on an ephemeral port in a temp
  collection. The fixture is a `kbmcp.yaml` with `format: seal-only` and a `seal: {require: [...]}` that matches a
  `.py` file. Cover:
  - `/.env`, `/sub/.hidden`, `//.env`, `/.%65nv` and `/%2e%2e/…` are 404, for GET and HEAD
  - a symlinked file and a symlinked directory are 404
  - `/` is 200 with no `index.md`
  - a seal-only `.py` is listed and renders with line numbers
  - a binary and an oversized file are absent
  - with pygments absent, the page renders plain
- **Q8 Ledger.** `.waxseals.yaml` is 404 in the browser like any dotfile. No exception.
- **Q9 Version.** Check what `pyproject.toml` says (2.1.1 at last look) and bump it to 2.1.3. Add a CHANGELOG entry.
- **Q10 Docs.** Update `docs-src/serve.md`, `docs-src/sealing.md` and `CHANGELOG.md`: the seal-only viewer, the
  hidden-file rule, the `syntax` extra, and that a listed file now renders as a page, not raw text. Never run `seal`,
  `ratify` or `verify --attest` (human-only). List in the PR body which seals broke so the user re-seals.
- **Q11 Highlight.** pygments picks the lexer by filename. Inline CSS has a light set and a dark set under the page's
  existing `prefers-color-scheme` query. Pygments missing means plain numbered `<pre>`.
- **Q12 Landing.** Two commits, so the highlighting can be dropped alone:
  1. the hidden-file and symlink fix, plus the shell at `/`
  2. the seal-only viewer and the pygments extra

  Docs, version and CHANGELOG go in the second, or a third. Open a PR from `release-2.1.3` and stop. Never merge, tag,
  push to `main`, seal, or publish to PyPI. Ask the user for the exact commit trailer before the first commit.
- **Q13 Protect/avoid.**
  - No MCP tool signature or CLI flag changes.
  - Stop and report on surprises (a failing test outside serve, a seal-only edge case) rather than widen scope.
  - Keep the `sealonly_files()` exclusions (ledger, `kbmcp.yaml`, `.env`, gitignored). No new bypass.
  - Hidden files are excluded everywhere (list, serve, scan). `sealonly_files()` can return files in dot-directories
    such as `.github/`; `scan()` filters them out. They stay sealable from the CLI.
  - Never follow symlinks: not in `scan()`, listings or serving. A path with any symlinked component is 404.

## Done when

`pytest` (the whole suite) and `ruff` pass. The user runs `QA.sh` and the manual click-through, so do not run or edit
them. State in the PR body what was run and what was not.

## Defaulted

- Size cap is 512 KB. veto: name another number.
- Binary test is "fails UTF-8 decode". veto: say if you want a NUL-byte sniff instead.
- Files touched: `bowerbird_serve.py`, `pyproject.toml`, `uv.lock` (regenerate if `uv` is present, else say so),
  `test_bowerbird_mcp.py`, the three doc files, `TODO.md` (tick the 2.1.3 item). veto: name any file to leave alone.
- The Seal modal's wording ("I reviewed this concept") is left as is for code files. Report it in the PR body if it
  reads wrong. veto: say if you want the copy changed here.

## Kickoff

You are Sonnet 5.5 at medium effort. On any other model or effort, stop and say so before doing anything. In
`/home/dfoulks/local/bowerbird-mcp`, read `docs-src/prompts/01-ui-security.md` and build exactly it: branch
`release-2.1.3` from `release-2.1.2`, the fix in `bowerbird_serve.py`, tests, docs, then open a PR and stop. Do not
merge, tag, seal or publish. Ask the user for the commit trailer before the first commit.
