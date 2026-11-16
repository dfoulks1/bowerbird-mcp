# Changelog

## Unreleased

### Added
- `seal` (command-line names `verify` for okf and `ratify` for ADRs): one function for a human's review, in every
  format, replacing `verify` as the tool. Over MCP it asks the human in a prompt, as `verify` did. okf records
  `verified: {by, at, sha256}` in the concept; markdown and skos add an entry (file, sha256, by, at, decision) to a
  committed `verifications.yaml`. The sha256 binds the review to the exact bytes: an edit breaks the seal and the
  hit shows `unverified` and `stale`. A ledger decision becomes the hit's `status`.
- `seal check=true` (a pre-commit hook, CI; `since=` for pull requests) exits 1 on `unsigned`, `stale_signature`,
  `claims_accepted` and `orphan_signature` (a warning). The policy is the `seal` key in the committed `kbmcp.yaml`:
  `require` globs (default everything) and `exempt_status` (default proposed, draft); no override can loosen it.
- `format: skos` indexes SKOS thesauri (Turtle, RDF/XML, JSON-LD, N-Triples, N3; optional extra `bowerbird-mcp[skos]`, needs
  `rdflib`): one passage per `skos:Concept`, headed by its broader chain, with labels, notes and broader/narrower/
  related neighbours in the text. No hub boost, since a concept's links stay inside its file.
- `format: adr` (every markdown file but README.md and index.md is a decision record) and `format: markdown` in kbmcp.yaml
  index a folder with no OKF frontmatter, so `passages` works on
  ADR and MADR records. A numbered file name or a path through adr/decisions gets type `adr` and its `status`
  (MADR 3 frontmatter, a Nygard `## Status` section, or MADR 2's `* Status:` line). Only `passages`, `reindex` and `seal` are
  offered, `index.md` and `log.md` are ordinary files, and every hit is `unverified`.
- `vector_index` in kbmcp.yaml picks how semantic search finds neighbours: `scan` (default, exact, Python),
  `sqlite-vec` (exact, in C, same results as scan, faster from about 10K passages) or `hnsw` (approximate, a graph
  file beside the index, seeded and single-threaded so builds repeat). Both are optional extras
  (`bowerbird-mcp[sqlite-vec]`, `bowerbird-mcp[hnsw]`). `hnsw` keeps the top 500 before the type/tag/dir filters.

### Changed
- `kbmcp.yaml` is now the knowledgebase's committed, shared configuration, and any folder holding one is a
  knowledgebase. `config` no longer lists it in `.gitignore`; a folder inside a knowledgebase that has its own
  `kbmcp.yaml` is skipped by the outer one, and `lint` no longer reports `nested_config`.
- Personal and machine overrides: every key but `format` has a `KB_<KEY>` variable. `env.example` lists them; copy it to
  `.env` (not committed; `init` and `config` ignore it). Precedence: `kbmcp.yaml`, then `.env`, then real environment
  variables. `config` also writes `env.example`.
- `init` writes a mostly filled-in `kbmcp.yaml`: `format` is guessed from the folder, and `about`, `user` (into
  `.env`) and `holds` (okf, markdown or skos) are asked for in an MCP prompt or at a terminal, or passed as arguments.
  `markdown` and `skos` start no bundle. `init` is now async.
- The `KB_ROOT` refusal message no longer tells you to set a `root:` key (there is none).
- The server instructions are built from the settings: they follow `format` (OKF workflow, or read-only search for
  `markdown` and `skos`), mention semantic search when it is on, and point at `kbmcp.yaml`.
- `reindex` prints `embedding n/total` to stderr on the command line during a long first semantic build. Over MCP
  there is no progress yet (`reindex` is not async).
- Docs: README, guide, home page and getting-started cover `format`, `vector_index` and the new loaders; the guide has
  headings for settings, formats, the index and where tools look; `tools.md` is regenerated.
- Passages cut from a long section now overlap: a cut repeats the last paragraph (if short) at the head of the next
  piece, so an answer split at the seam is still found whole. Existing indexes rebuild once on first use; with
  `semantic: true` that re-embeds everything.

## 1.0.1 (2026-11-13)

### Renamed
- The project is now **Bowerbird**. The PyPI package and the command are `bowerbird-mcp` (was
  `knowledgebasemcp`), the script is `bowerbird_mcp.py` (was `KnowledgeBaseMCP.py`), and the repository is
  `dfoulks1/bowerbird-mcp`. The settings files stay `kbmcp.yaml` and `kbmcp.nolint`. The model cache moved to
  `~/.cache/bowerbird-mcp/models`. The 1.0.0 release keeps its old names.
- The generated-index marker in `index.md` files still says "KnowledgeBaseMCP", so existing knowledgebases are
  not rewritten.
- A new logo (a bower of sticks rising from an open book), on the site, in the README and as the favicon, with a
  social-preview image for link cards.
- The install lines use the PyPI name (`uvx bowerbird-mcp`); the repository form is kept for unreleased code.
- The website moved to <https://bowerbird.voltpop.com/>.

### Changed
- `fastembed` is declared once, as a dependency of the package. It is no longer in the script's own header, so
  `uv run KnowledgeBaseMCP.py` (and a lint-only hook that runs the script) no longer installs it. `uvx
  knowledgebasemcp` still has semantic search out of the box; the bare script needs `--with fastembed` for
  `semantic: true`, and says so.

## 1.0.0 (2026-11-13)

The first release. It collects everything built since the project started (2026-10-27) and adds the
following in the last stretch.

### Added
- **Install in one line:** `uvx --from git+https://github.com/dfoulks1/KnowledgeBaseMCP knowledgebasemcp`.
  One command, `knowledgebasemcp`; the file still runs as a script (`uv run KnowledgeBaseMCP.py`).
- **`kbmcp.yaml`:** local settings at the root of a knowledgebase. It marks the base, tells any server where
  the knowledgebase and its assets are, and is kept out of git. `--config` names one elsewhere, and `config`
  writes a commented example (and ignores it in git). `lint` flags a second one below the root (`nested_config`).
- **`passages`:** the best sections of the knowledgebase for a question, ranked by BM25 (SQLite FTS5) in one index
  file, with file, line, a percent `match`, trust tier and staleness on each hit, and `gap: true` when
  nothing fits. Concepts many others link to rank a little higher. Optional semantic matching by meaning
  (`semantic: true`, fastembed; the model, about 65 MB, downloads once). `reindex` builds, inspects (`info`) or
  drops the index, so a hook can keep it current (`build: manual`).
- **Roles:** `read`, `write`, `structure` and `lifecycle` (`--role` or `KB_ROLE`, `roles:` in `kbmcp.yaml`)
  split the 35 tools into four servers of about 2,300 to 2,500 tokens each, instead of about 9,500 for all.
- **`lint` always ends with a verdict line** (and a GitHub notice), so a hook shows it ran.
- **`about:`** in `kbmcp.yaml` tells an agent what a knowledgebase holds, for when several are loaded.
- **Docs:** Getting started and Understanding OKF pages, the site at https://knowledgebasemcp.voltpop.com/,
  `NOTICE` (credits the copied OKF specification) and `SECURITY.md`.

### Changed
- **`KB_ROOT` is no longer read** (the server exits with a message). Use `kbmcp.yaml`, found from the
  working directory upward or named with `--config`.
- `init` and `create` print the "land it via a branch and PR" hint only inside a git work tree.

### Fixed
- `lint` raised a `KeyError` when a file with no frontmatter linked to a concept.

### Known limits
- `passages` has no stemming ("rolling" does not match "roll"), and with `build: manual` it does not notice
  files changed since the last `reindex`.
- `fastembed` and its dependencies add about 150 MB to the install even with semantic search off (1.0.0; from
  1.0.1 only the installed package carries it, not the bare script).
- A human `verify` over MCP needs a client that supports confirmation prompts.
