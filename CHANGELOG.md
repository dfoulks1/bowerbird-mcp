# Changelog

## Unreleased

### Changed
- `serve` takes a verb: `start`, `stop`, `restart` and `status`, each with an optional port (26937 when left out). A bare
  `serve` now only reports status, where it used to start a server, so scripts that ran `bowerbird serve` to start must run
  `bowerbird serve start`. `start` does nothing when ours is already on the port, and refuses a port something else holds.
  `stop` with nothing running exits 0. `restart` stops what it finds, waits for the port to clear, then starts.

## 2.1.3 (2026-11-18)

### Added
- `serve` shows seal-only collections: each file `seal.require` names is a read-only page, numbered, with its seal state
  and the Seal modal. A binary or over-512 KB file is not listed or shown (the command line still seals it).
- New extra `syntax` (`bowerbird-mcp[serve,syntax]`): pygments colours code by file name, with a light and a dark set.
  Without it a file shows as plain numbered text.
- A fourth seal state, `derived`: a file a `!` glob in `seal.require` leaves out (a page or a non-markdown file built from
  the code) is badged "derived from the code" in `serve`, with no Seal button, no stop for `n`/`p`, and a refusal if a seal
  is posted for it. New `derived(path)` and `derived_files()` in `bowerbird_mcp.py`; `seal check` is unchanged.
- `/` shows the shell (tree, search, empty panes) when the root has no `index.md`, not a directory listing.

### Fixed
- `serve` served any file under the collection, `.env`, `.git/` and `.waxseals.yaml` among them, and followed symbolic
  links. Now a path with a dot-prefixed part, or through a symlink, is a 404 for GET, HEAD and listings, and listings leave
  both out.

## 2.1.1 (2026-11-18)

### Added
- `bowerbird serve` is now a front end to the tools for a person, with no AI in it. A pencil and a gear (Move, Delete,
  Seal) in the right-hand pane; **+ New file** at the foot of every folder (a trailing `/` makes a folder); an editor with
  Save, Lint (the text as typed) and Cancel; a tags field on any page with frontmatter; Lint all and a Tags page that
  renames or merges a tag everywhere. A change shows its diff and applies on Confirm. Delete is refused while another
  page links to the file. Seal opens a modal that asks what the MCP prompt asks (confirm, and your id) and records
  `human:<id>` for exactly that text. Nothing it writes carries a `generated` stamp.
- `serve status` (exit 0 running, 1 not), and a Stop button in the top bar. A foreground `serve -f` now writes the pid
  file too, so `status` and `stop` see it.

- Search in `serve` has four modes, chosen beside the search box (and kept): **Passages** (ranked sections, by keyword),
  **Concepts** (whole pages, as `search`), **Meaning** (passages fused with meaning; on when `kbmcp.yaml` sets `semantic: true`,
  and says so when it is off), and **Tags** (pages with a tag containing your text). The tag list links into Tags search.

### Fixed
- `serve` searched only the bundle around the directory it was started from. It now works from the collection root, so
  search, lint and the tools see the whole collection wherever `serve` was run.

### Changed
- Writes need a per-run token and a `localhost` Host header (DNS rebinding); reads check the Host too.
- `serve stop` no longer signals a pid when nothing answers on the port (a stale pid file could name another process).
- `seal` and `serve` build the review prompt from one function (`review_target`, `review_message`).

## 2.1.0 (2026-11-17)

### Added
- `bowerbird serve`: a read-only view of the collection in your browser, on `127.0.0.1:26937` (BOWER on a phone
  keypad). It runs in the background (`serve -f` stays in the foreground, `serve stop` ends it, `serve 8080` picks a
  port). A folder tree, ranked search (`/`, the same passages the tools return, semantic when `kbmcp.yaml` turns it on),
  an outline and backlinks per page, and a badge on each page: sealed, unsealed, or seal broken by edit, checked by
  the same hash and ledger as `seal check=true`. Light, dark or system theme (`t`). It rereads the files on every
  request and never writes a seal. Needs the optional extra: `pip install 'bowerbird-mcp[serve]'`.

### Changed
- `bowerbird` is a second command for the same tool (`bowerbird serve`); `bowerbird-mcp` is unchanged. The package
  is still `bowerbird-mcp` on PyPI.

## 2.0.1 (2026-11-17)

The command-line ergonomics and mixed-format collections. **One behaviour changes for anyone who nests collections:** a
`kbmcp.yaml` in a subfolder is now an override of the one above it, not a separate collection (see Changed).

### Added
- Mixed formats: a `kbmcp.yaml` in a folder overrides the one above it for that folder and everything under it, the
  nearest winning (like an inherited ACL). One collection can hold OKF with a folder of ADRs, or markdown with ADRs, or
  any mix. `format`, `seal` (globs start at that folder), `about`, `hubs` and `min_similarity` may be overridden; a
  folder that sets a collection-wide key (`roles`, `passages`, `index`, `semantic`, `semantic_model`, `vector_index`,
  `build`) is refused. Each file is read, indexed and sealed in its own folder's format; `lint`, `fix`, `index`, `provenance`
  and `upgrade` skip files in other formats (a link from one still keeps a concept from being an orphan; `move` and
  `migrate` rewrite links in them); a server offers the tools of every format in use. One index, one ledger.
- The command line takes `--flags` and short flags (`init -t markdown -a "Docs" --apply`, `seal -cp`), with
  `-h` per command and `-O` (or `-F`) to choose the output. They are turned into the same `name=value` arguments,
  which still work everywhere, so CI and agents are unaffected. Flags are not abbreviated (`--app` is not
  `--apply`). The daily commands (`init`, `seal`, `lint`, `status`, `search`, `passages`, `list`, `get`, `links`) have
  fixed short flags, and `bundle` is `-B` in all of them; other commands take the first free letter, so use their
  long flags in scripts. `--attest` is unchanged.

### Changed
- **A `kbmcp.yaml` below the root is an override, not another collection.** Before, a folder holding its own
  `kbmcp.yaml` was skipped by the outer collection. Now it is part of it, and the collection's root is the outermost
  `kbmcp.yaml` inside the git work tree (a repository inside another stays its own collection). Nested files are found
  with `git ls-files` and read once, at startup.
- `help` is short and grouped (knowledge, retrieval, verification) and shows only the commands the collection's format
  has; `help all` lists every command. Examples print `bowerbird-mcp`, not `uv run bowerbird_mcp.py`.
- `<tool> -h` and `help <tool>` list each argument as its flags (`-p, --promote`, `-d, --decision DECISION`) and print
  the examples as flags; `tools.md` gains a Flag column. `lint -a` is a switch (`--no-all` is the other way), not
  `-a VALUE`. `seal check` hints end in `--attest`, the command a person runs. A new Command line page covers flags,
  output and exit codes.
- At a terminal the command line prints text by default; piped, in CI or in a script it still prints JSON.
  `output=json` or `output=text` overrides either.
- `--attest` now needs a terminal (stdin a TTY). A pipe or script is refused with exit 2. This stops headless runs; a
  hardware-backed seal is planned as the stronger gate.

## 2.0.0 (2026-11-16)

A major version: several things a 1.x user relied on changed.

### Breaking
- The MCP tool `verify` is now `seal` (one function for a human's review, in every format). `verify` and `ratify`
  remain command-line names for it, but an MCP client calling `verify` must call `seal`.
- `kbmcp.yaml` is the collection's committed, shared configuration (it was local and ignored by git). `config` no
  longer lists it in `.gitignore`. Personal overrides now go in a `.env` file or `KB_*` variables.
- Any folder holding a `kbmcp.yaml` is its own collection, so the outer one skips it and `lint` no longer reports
  `nested_config`.
- `init` writes more (a filled-in `kbmcp.yaml`, `env.example`, `.mcp.json`, and your id in `.env`) and is async.
- The `KB_ROOT` message no longer points at a `root:` key (there is none).

### Added
- `format: seal-only`: a collection of any text files (code, configuration) with nothing indexed or searched. The
  `seal.require` globs name the files, and `seal check=true` fails when one has no human review of its current version.
  `init holds=seal-only` writes only `about`, `format` and an empty `seal.require`.
- `seal` is its own role (`roles: [read, write, structure, lifecycle, seal]`), so a server can offer review without
  `write`. `fix` moved back to `write`; the four older roles stay within about 15% of each other.
- `seal` (command-line names `verify` for okf and `ratify` for ADRs): one function for a human's review, in every
  format, replacing `verify` as the tool. Over MCP it asks the human in a prompt, as `verify` did. okf records
  `verified: {by, at, sha256}` in the concept; the other formats keep one dense line per file (file, sha256, by, at,
  decision, and `bowerbird`, the version that wrote it) in a committed `.waxseals.yaml`, only the latest seal, which sealing again replaces (git has the earlier
  ones). The sha256 binds the review to the exact bytes: an edit breaks the seal and the hit shows `unverified` and
  `stale`, and the line still names the version that was reviewed. A ledger decision becomes the hit's `status`. 
- `seal check=true` (a pre-commit hook, CI; `since=` for pull requests) exits 1 on `unsigned`, `stale_signature`,
  `claims_accepted` and `orphan_signature` (a warning). The policy is the `seal` key in the committed `kbmcp.yaml`:
  `require` globs (default everything) and `exempt_status` (default proposed, draft); no override can loosen it.
- `format: skos` indexes SKOS thesauri (Turtle, RDF/XML, JSON-LD, N-Triples, N3; optional extra `bowerbird-mcp[skos]`, needs
  `rdflib`): one passage per `skos:Concept`, headed by its broader chain, with labels, notes and broader/narrower/
  related neighbours in the text. No hub boost, since a concept's links stay inside its file.
- `format: adr` (every markdown file but README.md and index.md is a decision record) and `format: markdown` in kbmcp.yaml
  index a folder with no OKF frontmatter, so `passages` works on
  ADR and MADR records. A numbered file name or a path through adr/decisions gets type `adr` and its `status`
  (MADR 3 frontmatter, a Nygard `## Status` section, or MADR 2's `* Status:` line). `index.md` and `log.md` are ordinary files, and a hit is
  `unverified` until a person seals it. A server offers a few tools outside OKF, by format: markdown `get`, `search`,
  `dirs`, `links`, `list`, `status`, `heatmap`, `init` and `config` on top of `passages`, `reindex` and `seal`; adr also
  `move`; skos `passages`, `reindex` and `seal`; asciidoc those three and `heatmap`; seal-only just `seal`.
- `vector_index` in kbmcp.yaml picks how semantic search finds neighbours: `scan` (default, exact, Python),
  `sqlite-vec` (exact, in C, same results as scan, faster from about 10K passages) or `hnsw` (approximate, a graph
  file beside the index, seeded and single-threaded so builds repeat). Both are optional extras
  (`bowerbird-mcp[sqlite-vec]`, `bowerbird-mcp[hnsw]`). `hnsw` keeps the top 500 before the type/tag/dir filters.

- `format: asciidoc` indexes `.adoc` and `.asciidoc` files: one passage per section, `:name: value` header attributes or
  YAML front matter as metadata, `xref:`, `link:` and `<<file.adoc#id>>` links. No new dependency.
- `list` and `status` work in markdown and adr. A decision record is stable, superseded, rejected or deprecated, and a
  person's seal is what makes a stable one accepted (`state`: accepted, proposed or superseded). `status` counts them
  (`by_state`) and the records edited since a review (`stale`); `list status=proposed` is the unreviewed worklist.
  `accepted` is a command-line name for `seal`, like `ratify`. `heatmap` counts each format's own files.
- `seal.require` takes `!` globs to leave files out (a generated page): `require: ["/*.md", "!/tools.md"]`.
- `move` carries a file's seal to the new path when its text does not change; a file whose own links had to be
  rewritten loses it, as any edit does.
- The site build renders each page's review badge from the ledger (`hooks/seal_banner.py`), so the page source never
  holds the seal data and rendering cannot stale a seal.

### Changed
- The command-line option that picks how a result is printed is now `output=` (`text`, `json`, `github` or `sarif`), so it
  no longer shares a name with a collection's `format`. `format=` still works as an alias.
- Releases are published to PyPI by hand (`uv publish`), not by a GitHub Actions workflow; the publish workflow is removed.
  See `CONTRIBUTING.md`.
- `init` also writes a `.mcp.json` (commit it): whoever clones the repository has the tools, with nothing to register
  on their own machine (Claude Code asks once to approve a project's server). The collection's settings, reviews and
  client configuration all travel with the repository.
- The roles are evened out by moving `fix` from `write` to `structure`: about 1,750, 1,900, 1,850 and 1,800 tokens.
- `kbmcp.yaml` is now the collection's committed, shared configuration, and any folder holding one is a
  collection. `config` no longer lists it in `.gitignore`; a folder inside a collection that has its own
  `kbmcp.yaml` is skipped by the outer one, and `lint` no longer reports `nested_config`.
- Personal and machine overrides: every key but `format` has a `KB_<KEY>` variable. `env.example` lists them; copy it to
  `.env` (not committed; `init` and `config` ignore it). Precedence: `kbmcp.yaml`, then `.env`, then real environment
  variables. `config` also writes `env.example`.
- `init` writes a mostly filled-in `kbmcp.yaml`: `format` is guessed from the folder, and `about`, `user` (into
  `.env`) and `holds` (okf, markdown, adr, skos, asciidoc or seal-only) are asked for in an MCP prompt or at a terminal, or passed as arguments.
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
