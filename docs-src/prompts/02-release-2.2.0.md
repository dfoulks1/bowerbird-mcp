# 02 — 2.2.0 release notes (the scope to build the release prompt from)

2026-11-18 · notes, not yet a prompt. Next step: run bbq on this to settle the open questions, then write the prompt.
2.1.3 shipped (tag `v2.1.3`, `main` at `d6a3102`).

## In 2.2.0 (decided)

### 1. Scrub the legacy `kb` / KnowledgeBaseMCP naming
The project's old name leaks into the code, docs and config. It confuses readers (`kb` reads like an object; it is the
`bowerbird_mcp` module). Breaking, so 2.2.0, with fallbacks.
- **Docs and prose:** drop every `alias kb=` and `kb <tool>` example (README, `sealing.md`, others). The commands are
  `bowerbird` and `bowerbird-mcp`. Leave CHANGELOG history as written.
- **Internal names:** the `kb` module variable (`bowerbird_serve.py`, hooks) becomes `bb`; `KB_ROOT` becomes `ROOT`;
  the test file's `k.` gets a real name. About 240 + 143 + 527 mechanical hits.
- **Config file:** `kbmcp.yaml` becomes `bowerbird.yaml`. The old name keeps loading with a one-line deprecation
  warning for a version or two. 221 hits in 26 files.
- **Env vars:** `KB_*` (`KB_ROLE`, `KB_USER`, `KB_SEMANTIC`, `KB_AI_PRODUCERS` and the rest) become `BOWERBIRD_*`; the old
  names are read as fallbacks for the same period.
- **Index marker:** `kb-index:start` and `:end` stay readable; new writes use the Bowerbird name, so no generated index
  goes stale. (The code comment says the old text was kept on purpose.)
- **Risk:** `kbmcp.yaml` and `KB_*` live in people's repos and MCP configs. The fallbacks are what make it safe.

### 2. Semantic search becomes an extra
`fastembed` (about 150 MB with its dependencies) leaves the base install: `semantic = ["fastembed"]` in
`[project.optional-dependencies]`. A draft was built and reverted on 2.1.3 (not committed); the touch points are:
- `pyproject.toml` (drop from `dependencies`, add the extra), `uv lock`
- `bowerbird_mcp.py`: the comment near line 119 and the `fastembed is missing` error near line 1735 (say
  `pip install 'bowerbird-mcp[semantic]'`)
- `bowerbird_serve.py` (the "meaning search is off" hint, near line 325)
- `README.md` (about line 605), `docs-src/getting-started.md` (about 208), `troubleshooting.md` (about 43), `serve.md` (about 70)
- CHANGELOG "Changed": a collection with `semantic: true` stops with `fastembed is missing` until the extra is installed.
- The code already imports `fastembed` lazily, so no logic change.

### 3. Derived state recorded in the ledger (replaces the glob-based version shipped in 2.1.3)
2.1.3 marks a file `derived` when a `!` glob in `seal.require` leaves it out (`kb.derived`, `kb.derived_files`). Two
problems: `!` means "no review needed", not "generated" (a hand-written exemption gets a wrong "derived from the code"
badge), and the banner hook cannot reuse the logic without importing `bowerbird_mcp` (which imports `mcp`).
Design agreed in this session:
- A derived file gets a ledger line in `.waxseals.yaml`: `{file, sha256, by: 'process:<tool>', at, kind: derived}`. A
  person never signs it; a generator writes it (for example `docs_tools.py` for `tools.md`), through a command such as
  `seal derived=true file=tools.md`.
- State is `derived` while the file's sha256 matches that entry. A hand edit breaks it: "edited since generated".
- `serve`, `seal check` and the banner hook all read the ledger. None evaluates globs. The `!` glob stays as the policy
  that says no human review is needed.
- Remove `kb.derived` and `derived_files()` (or reduce them to ledger lookups).
- Open: the command's exact shape; whether `seal check` reports a derived file whose hash drifted; migration for
  `docs-src` (`tools.md`).

### 4. `hooks/seal_banner.py` stops duplicating logic
It keeps its own `fnmatch` copy of the derived rule today. After item 3 it reads only the ledger with plain `yaml`. It must
not import `bowerbird_mcp` (the docs build runs in `uvx --with pymdown-extensions mkdocs build`, which has no `mcp`).

## Candidates (from TODO.md "Next", not yet decided)
- Search for a generated site: `reindex export=search-index.json`, client-side MiniSearch or lunr, badge by trust tier.
- Addressable resources: concepts and passages as `kb://{bundle}/{file}` MCP resources (rename the scheme in step 1? it is
  public, decide).
- MCP prompts (answer from the collection and cite; review a decision record).
- Progress notifications from `reindex` over MCP.
- A loader registry for `sync` (a seventh format is the time).
- SKOS: count links across files for `hubs`.
- Attested provenance badge for generators other than MkDocs.

## Loose ends and known gaps to settle
- **Ruff:** `ruff check .` reports 29 findings, the same with and without the 2.1.3 changes. `tools/QA.sh` has no `ruff`
  line, though the user believes it runs one. Decide: fix the 29, or add ruff to QA, or neither. mypy was never run.
- **`serve restart`** is untested end to end (the real path stops a server and forks a new one, which the in-process test
  cannot do). Add a subprocess test.
- **Seal modal wording** ("I reviewed this concept") for code files: decided fine as is.
- **`serve-verbs` local branch** is redundant (its commits are in `main`); delete it.
- **Untracked in the working tree:** `.kiro/` and `.mcp.json`; decide whether to ignore or commit them.
- **Version and docs:** bump to 2.2.0 in `pyproject.toml` and `VERSION` in `bowerbird_mcp.py`; `uv lock`; CHANGELOG; docs
  rebuild after the person seals; the person builds, runs `twine check` and uploads to PyPI. No `gh release`.
- **Breaking-change note:** a bare `serve` already only reports status (shipped in 2.1.3); repeat it in the 2.2.0 notes if
  scripts still call it.

## How the release runs (the recipe that worked for 2.1.3)
1. bbq on this file, then ratify. 2. A fresh Sonnet 5.5 subagent builds on `release-2.2.0` and opens the PR, stopping
there. 3. The person seals, reruns QA and the click-through, merges and tags (`releasing.md`). 4. The person publishes to PyPI.
