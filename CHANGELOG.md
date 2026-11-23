# Changelog

## 2.3.0 (unreleased)

### Removed
- **The old names.** `kbmcp.yaml`, `KB_*`, `kbmcp.nolint`, the `.kbmcp/` cache and the `kb-index` markers, read with a warning since 2.2.0, are gone. A `kbmcp.yaml` with no
  `bower.yaml` beside it stops the run with `git mv kbmcp.yaml bower.yaml`; the rest are ignored.

### Changed
- **`list` and `status` tell the truth about an edited OKF concept.** An OKF concept's reviews are in its frontmatter, bound to its text; `list` and `status` showed one edited since as `human-reviewed` (a search and `seal check`
  already said it was stale). They now say `unverified`.
- **`seal.count`: how many people hold a file** (a human signal: a machine check is never counted). With `seal: {extensions: true, count: true}`, `list` and `passages` show `seals: N` (the different people whose seal of the current version holds), a search
  ranks a file a little higher for each, and `seal check` returns the `most_sealed`.
- **Seal extensions are an add-on.** The code for several signers and a quorum moved out of core to `addons/seal-extensions` (`bowerbird-seal-extensions`, found through the `bowerbird.seal` entry point);
  `pip install 'bowerbird-mcp[seal-extensions]'` installs it. A collection that sets `seal.extensions: true` without it is told what to install, and a write that would lose seals is refused. A multi-seal ledger line
  now carries its `quorum`, so the docs badge says `by ann, bo (2 of 3 needed)`.
- **Distributed ledgers.** A seal goes into a `.waxseals.yaml` in the file's own folder, with the file's name relative to that folder, so seals live
  beside what they cover and move with the folder. A root `.waxseals.yaml` from before 2.3 is still read; a file's line leaves it when the file is sealed again.
  Reading merges every ledger (the nearest wins), `move` carries a seal into the new folder's ledger, and the docs hook looks for the nearest one.

- **A decision record's seal says what was decided.** Sealing an ADR or MADR (a person, in `serve` or by `seal`) now requires `decision=accepted|rejected`, and writes it into
  the file as its `status` before sealing, so the file, the ledger and `INDEX.md` agree. A record with the ADR+ header also gets `status-note`, `ratified-by`, `ratified-on`
  and a History line holding the old values. A machine's seal (`by=`) does not rule.

### Added
- **Fact badges and a bibliography.** A fact block is shown as its claim and a badge of its last check that links to an entry in a generated bibliography of the page's facts: at the bottom
  of the page in the docs hook, and on a Facts tab in the right-hand pane in `serve`. `serve` and the hook also say who sealed a page (several people, with the seal extensions: `signed 2 of 3: ann, bo`, and the
  Seal dialog says who has signed so far). One function, `bowerbird_facts.render`, feeds both.
- **An agent may run any fact check.** `factcheck fetch=true` and `factcheck file=… id=…` no longer need a person at a terminal: a person is still shown the plan and asked, an agent or a script is not and gets
  the plan back as `ran`. Only what `bower.yaml` declares can be called or run (a page cannot name a command), and a `manual` fact, which asks a person, is skipped for an agent.
- **A fact has a number.** `id` is the first key of a block's metadata, a whole number unique in the document; `factcheck` takes it (`id=3`), `fact` takes the next one, and `fix` numbers the blocks that have none (a fact with no
  `id` is still known by a fingerprint of its words, as in 2.2.0, and what was checked under the fingerprint moves to the number). A fact edited since its last check shows as unchecked. A check now writes
  `last_checked` (the day) into the block's metadata; a seal does not see `id`, `last_checked` or an empty `{}`, so neither numbering nor checking breaks one. `lint` has `duplicate_fact_id`.
- **`fact` writes the block.** `fact` with `kind`, `source` and `claim` writes `[fact.KIND]{metadata}(source) claim [fact.end]` into a document of any format (`after` a heading or a line; the end by default), checks a
  file-reading kind first and refuses a claim its source does not hold, records an `mcp` baseline from `result` (`-` or `@file` at a terminal), and with `harvest=true` lets a person pick a passage of a page. `fact` and `factcheck` are now
  offered to markdown and ADR servers. Without `claim` it is the older `sources` form.
- **One grammar for a fact: `[fact.KIND]{metadata}(source) the claim [fact.end]`.** The `{metadata}` is optional (the 2.2.0 form still reads): a JSON or YAML mapping with the keys `by`, `at`, `as_of`,
  `confidence`, `note`, `tags` and `stale_after` (any other key is kept), shown in the bibliography; `stale_after` makes `factcheck` list a fact as due. An agent may write the metadata as JSON and the
  source as a JSON string or array of strings. The metadata is not part of the fact's id. `lint` has a new `bad_fact_meta` warning, and a mapping that never closes is a `bad_fact` error.
- **The fact pack, `bowerbird-mcp[fact-pack]`** (`addons/fact-pack/`): the kinds `key` (a value in a JSON, YAML or TOML file), `git` (a tag, or a file at a revision), `until` (an end date), `manual` (a person is asked)
  and `script` (a command declared in the root `bower.yaml`, an argument list with no shell, terminal only). It registers through the new `bowerbird.fact_types` entry point; `facts:` takes
  `scripts:` and `manual_days:`. Without the pack, a page that uses one of its kinds is a `lint` error that says what to install.
- **Fact kinds `file` and `internal`.** `[fact.file](path#L10-20)` reads a file (absolute, `~/`, or relative to the document; no network), `[fact.internal](page.md#Heading)` reads a page or a section of
  this collection. Their checks only read files, so `factcheck file=... id=...` runs one with no prompt, for an agent too, and records it beside the document.
- **The format add-ons read more.** Inline `#tags` (and Logseq's `#[[two words]]`, `tags::`), frontmatter `aliases` and `alias` (and Logseq's `title::` and `alias::`) as other names a page answers to,
  Foam's `./`, `../` and `/` path links, Dendron's `dendron://vault/note` links scoped to the vault (from `dendron.yml`) with `#tag` and `@user` as links to `tags.*` and `user.*`, Logseq's
  `((uuid))` block references and the file name and journal title formats of its `config.edn`. A format sets these through `register_format(tags=, names=, resolve=)`.
- **Format add-ons: `obsidian`, `foam`, `dendron`, `logseq`.** Each is its own package under `addons/` (`bowerbird-obsidian`, ...), found through the `bowerbird.formats` entry point and
  selected with `format:` in `bower.yaml`; its files are markdown, read with that tool's rules for links (the alias side, how a name finds a file, the folders that are the tool's
  own, stub and journal pages). `register_format` in core takes `about`, `skip`, `alias_first`, `page`, `clean`, `links`, `virtual`, `quiet` and `lint`. A format that fails to load is
  said on stderr and left out. Each has a page under Formats.
- **`lint` is offered to markdown and ADR servers** (and so to the four format add-ons), and a link to a heading that a MkDocs snippet (`--8<-- "README.md:run"`) pulls in is no longer called dead.
- **`lint` checks the links of markdown and ADR files** (a `dead_link` or `dead_anchor` warning); until now it checked only OKF concepts' links.
- **Wikilinks, in every format.** `[[Note]]`, `[[Note#Heading]]`, `[[Note|alias]]` and `![[embed]]` are links: `links`, backlinks, `orphan` and `island` see
  them, and `lint` warns (`dead_link`, `dead_anchor`) when one does not resolve. A name matches the file's path (`.md` optional, case ignored), the shortest path first,
  then the nearest to the page. `#^block` ids are ignored. `move` keeps them; a rename leaves them behind for `lint` to report (they are not rewritten yet).

## 2.2.0 (2026-11-20)

### Added
- **`bowers:`**, a root `bower.yaml` key listing the folders (globs allowed) that carry their own `bower.yaml`. Only those
  override the root, a stray `bower.yaml` is never picked up, and a bower run inside the collection finds the root that
  lists it. A bower run alone is its own collection, and its whole-collection keys are ignored here, so it can ship with
  them. A name that matches no folder stops with an error. A root with no `bowers` key keeps the older rule, where every
  nested `bower.yaml` is an override.
- The agent rules without a file: an MCP resource `bowerbird://agent-rules` and a prompt `rules` serve the text `create` writes as
  `BOWERBIRD.md`, from the installed package.
- **Seal comments, and the `seal-extensions` extra.** Every seal can carry a one-line `comment` (`seal --comment "..."`, a Comment field in the
  MCP prompt and the `serve` dialog; up to 280 characters; kept on the review). With `seal: {extensions: true, quorum: N}` in `bower.yaml`
  (the `seal-extensions` extra, which has no dependency) different people can seal the same version of a file, kept together on its one
  `.waxseals.yaml` line as `seals: [...]`, and `seal check` reports `short_of_quorum` until N different people have (a machine check never
  counts; the file is `unverified` until then). Off, nothing changes: one latest review per file.
- **"Derived from the code" is recorded, not guessed.** A generator writes a `derived: <generator>` line, with the file's `sha256`, into
  `.waxseals.yaml` (`mark_derived(path, generator)`; `docs_tools.py` does it for `docs-src/tools.md`). `serve` and the docs build badge a
  file derived only while that line matches its bytes; `seal.exempt` no longer implies it (it only leaves a file out of `seal check`), so a
  page that is exempt but hand-written is no longer badged as built from the code. `hooks/seal_banner.py` now reads only the ledger: no
  `bower.yaml`, no globs, the same hash the tool uses, and several seals on one line. A generated folder gets one line for the whole folder (`mark_derived_dir`; `docs_tools.py` records `docs/` as built by mkdocs): everything under it is
  derived, exempt and badged blue. A derived line is not a review (it carries `by: generator:<name>` so a 2.1.x reader can still read the ledger).
- `serve` shows a link to the repository (from `origin`, when it has a web address) beside the theme and stop buttons. New docs page,
  [Status badges](https://bowerbird.voltpop.com/badges/): the site's review and fact badges, doing the same in another site generator, and a
  script that makes a README badge from `seal check`.
- **Facts, and `factcheck`.** A fact is a claim and what it rests on, written in a document as a block: `[fact.url](<address>) the words pasted from the page [fact.end]`, or
  `[fact.mcp](jira INFRA-27707) is open [fact.end]` (the kind, the source in parentheses, then the claim; one line or many). It works in every
  format. `factcheck` lists the blocks and their state (unchecked, checked, drifted). `factcheck --fetch`, for a person at a terminal,
  shows what it will fetch or call, asks, and compares each block with a fresh result: a page must still hold the words (shape ignored:
  whitespace, case, ticks; with `semantic: true` and the extra, a similar meaning also counts), an MCP call declared under `facts` in
  `bower.yaml` (tool, arg, watch; the only calls it may make) must return the value it did. State is kept in a `.facts.yaml` beside
  the document, which a check never changes. A drift ends every review of the file made before it (`seal check`: "a cited fact
  drifted after it was reviewed"). `lint` errors on an unclosed or stray tag. The kinds of fact (`url`, `mcp`) are a registry, `bowerbird_facts.FACT_TYPES`, so a new kind is a `register()` call, and the root `bower.yaml` can declare more with
  `facts: types:` (`[fact.ticket](INFRA-27707) is open [fact.end]`, backed by one tool of an MCP server the collection has). `create --facts` adds a commented
  block with one such kind per server in `.mcp.json` (Bowerbird's own is left out), also to a `bower.yaml` that is already there. The docs build shows each block with its state.
  For agents, `fact` (was `cite`) takes `result` and keeps its `fact_sha256`; `factcheck file= id= result=` compares.
- `--config` takes the folder holding a `bower.yaml` as well as the file, and a relative path, `~` or `$VARS`.
- **`new`**, a tool (MCP and CLI) that starts a document from a template: `new notes/deploy -t markdown -T "Deploy"`. `template`
  (`-t`) is `okf`, `markdown` or `adr` and defaults to what the folder holds, from `bower.yaml`; `title` (`-T`) defaults to the
  file name. It refuses a file that exists. It joins the `write` role (now 7 tools) and every format but seal-only, skos and
  asciidoc. All tools are now 36.
- **A bare `bowerbird-mcp` at a terminal** prints the help and, in a folder with no `bower.yaml`, offers to make a
  knowledgebase there (it runs `create`, which asks for the format, what the folder holds and your id). An MCP host starts the
  server with piped stdio, so it is unaffected. `create`'s prompts now say what each answer is.
- `create` writes `BOWERBIRD.md` at the collection root: rules for an AI agent using the tools, ending in a "Picking a tool"
  table (the job, the tool to use, and the one not to). It never overwrites a file, so a folder that already has one keeps it,
  and an older collection gets the file the next time you run `create`. The text is `AGENTS_MD` in `bowerbird_mcp.py`.
  `serve`'s setup modal and **New knowledgebase** run `create`, so they write it too.
- New docs page, [Agent rules](https://bowerbird.voltpop.com/agents/): what the file is, when `create` writes it, how to
  edit it and point an assistant at it, and its full text (a test keeps the page equal to `AGENTS_MD`).

### Changed
- **The collection's files as MCP resources**, at `bowerbird://{bower}/{path}`. Every file belongs to a bower, a folder that holds a
  `bower.yaml` (the root is one, named by its folder); the path inside it is the file's path as every tool takes it, so the bundle needs no
  segment of its own (`bowerbird://wiki/a.md`, `bowerbird://docs/sub/b.md`). `?lines=10-20` returns only those lines. They are listed
  (up to 1,000) and read for the `read` role; a dotfile, a link, a folder or anything outside the collection is refused. The SDK's
  templates match one path segment, so Bowerbird handles listing and reading for its own scheme and passes `okf://spec` and
  `bowerbird://agent-rules` through.
- **`okf export` and `okf import`**, a person's command (a terminal; not a tool) that moves an OKF concept's reviews and sources between its
  frontmatter and `.waxseals.yaml` and `.facts.yaml`, previewing until `--apply`. Export reads the documents and changes none (a review that holds is
  rebound so it holds in the ledger; a stale one stays behind). Import writes `verified` and `sources`; one that already went stale loads as stale
  history, and writing `sources` ends the reviews of the old bytes (the preview counts them: a new seal verifies what loaded). Both are idempotent.
- **The `kb` names are gone.** The settings file is `bower.yaml` (was `kbmcp.yaml`), the environment variables are `BOWERBIRD_*` (were `KB_*`),
  the lint skip file is `bower.nolint` (was `kbmcp.nolint`; the inline marker is `<!-- bower-nolint -->`), the index cache is `.bower/` (was
  `.kbmcp/`; a cache, rebuilt on first use), and the generated-list markers say `bowerbird-index` (the old `kb-index` is still read, and replaced
  the next time `index` runs). `serve` keeps its theme and search mode under `bowerbird-*` keys (the old ones are read once). The old file and
  variable names keep working for now: one is read with a one-line warning on stderr that names the new one (`git mv kbmcp.yaml bower.yaml`),
  and when both exist the new one wins. `KB_ROOT` and `BOWERBIRD_ROOT` are still refused. Inside, `KB_ROOT` is `ROOT`, `kbpath` is
  `bundle_name`, `kb_user` is `user_id`, and the module `serve` and the tests import is `bb`.
- **`init` is now `create`, and the old `create` is part of `new`.** `create` makes a collection, and also a bower: inside a collection
  with a `bowers:` list, `create docs` writes `docs/bower.yaml` (the whole commented template, with only your answers uncommented) and adds the folder to the root's list (comments kept); the root's
  `.mcp.json`, `.env` and `BOWERBIRD.md` serve it. `create [path] [--mcp] [--env] [--apply]`: no flag runs every step; `--mcp` writes
  `BOWERBIRD.md` (and prints its path) and adds bowerbird to `.mcp.json`, keeping the other servers and leaving a different bowerbird
  entry alone; `--env` writes `env.example` and the `.gitignore` line. Settings passed for a folder that already has a `bower.yaml` are
  reported as ignored. `new` writes a document and takes what the old `create` did (`type`, `description`, `resource`, `tags`, `status`,
  `body`, `by`): bare, it is the template; with those, it is written filled in. The old names print where they went (`init` says
  `create`; `create file=... type=...` says `new`). The web UI's New knowledgebase runs `create`.
- **Renamed:** `cite` is `fact`, and `recheck_plan` is `factcheck` (the old names print where they went). **Removed:**
  `recheck_apply`. A check is recorded by `factcheck` with a result, and only when the result is the evidence. It no longer
  adds a `verified` entry; `seal` is how a human confirms a file. The MCP tool list is now 34 tools (about 3,700 tokens).
- **Semantic search is an add-on.** `fastembed` (about 150 MB with its dependencies) moved from the package's dependencies to the
  `semantic` extra, so the base install is small and `uvx` starts faster. To keep meaning search, ask for the extra:
  `uvx --from 'bowerbird-mcp[semantic]' bowerbird-mcp`, or `uv tool install 'bowerbird-mcp[semantic]'`, and in a project's
  `.mcp.json` write `"bowerbird-mcp[semantic]>=2,<3"` after `--from`. A collection with `semantic: true` and no extra stops with
  a message that says so; nothing else changes.
- **The MCP tool list is about half the size.** What the server sends an agent for each tool is now a dense one- or two-line
  description (`MCP_TEXT`), with a preview note added for tools that take `apply`. All 34 tools cost about 3,700 tokens, down
  from about 7,250 for the 35 of 2.1.4 (descriptions went from about 4,600 to 1,430; the argument schemas from about 2,340 to 1,850,
  by leaving out the empty defaults and null wrappers an agent does not need). With the new `BOWERBIRD.md` (about 1,350 tokens), an
  agent's tool overhead is about 5,100 tokens, down from about 7,400. The full docstrings stay for `help <tool>`, the command line, the docs and the browser. The safety rules stay in the
  short text: `seal` never takes `human:<id>`, `passages` says to report a gap, and tools that write preview first.
- **`seal check` scans everything except what is exempt.** `seal.require` is gone, replaced by `seal.exempt`, a list of
  globs to leave out; every other file is checked, in every format. A `bower.yaml` that still has `seal.require` stops with
  an error that says so: list the files to leave out instead (a `!` glob in `require` becomes a plain entry in `exempt`). In
  seal-only there is no list to fill in, and `create holds=seal-only` writes no `seal` line. `unreadable` now points at
  `seal.exempt`.
- A bare `serve` prints its usage (every verb and option, `--config` included) and exits 0 instead of reporting status;
  `serve status` still does that.
- **The seal confirmation reads as facts.** Over MCP it opens "Confirm seal: path/file.md", and `serve`'s modal has the same
  heading, then title, word count, the full sha256, status and decision. The excerpt of the file's raw text is gone: you are
  reading the page, and over MCP the agent is told to show it first.
- `serve` docs: `--config` with `serve start` and `uvx --from 'bowerbird-mcp[serve]'`, and a note that `serve start` does
  nothing while a server already holds the port (run `serve stop` or `restart`, or pick another port).

### Docs
- The README's **Run** section (and the guide, which includes it) now says how to run Bowerbird: on the fly with `uvx`, installed
  with `uv tool install`, the basic commands, updating and pinning, and a table of the extras (`serve`, `syntax`, `semantic`,
  `skos`, `sqlite-vec`, `hnsw`) with how to ask for one on the fly, installed, with pip and in an MCP config.
- `new` is in the format pages and the format tool matrix, and `--config` is described in the command-line page.
- Getting started is one self-guided page: an empty folder to a working collection, the command line, the web UI, an assistant's configuration,
  searching and sealing.
- The extras section explains `--extra` against `--with` for `uv run`, `uvx` and `uv tool install`, and when to use which.

### Development
- `tools/QA.sh --rebuild` regenerates `docs-src/tools.md` and rebuilds `docs/` first; without it the script changes nothing. Ruff and mypy are
  now its last steps (both are clean; the mypy settings are in `pyproject.toml`), and a failure in either is reported after the other has run.
- `serve restart` has a subprocess test: start, a restart that replaces the process, stop, and a foreign listener on the port is refused.

### Fixed
- Outside a git work tree and with no root `bower.yaml`, nothing below the folder is scanned for nested `bower.yaml` files
  (a stray one in a temp folder could break `serve status` from `/tmp`).
- `SPEC.md` (OKF v0.2, copied from upstream) moved to `docs-src/prompts/`; the `okf://spec` resource reads it from there in a checkout.

## 2.1.4 (2026-11-19)

All of the `serve` changes need the `serve` extra (`bowerbird-mcp[serve]`).

### Added
- `serve`: **+ New file** fills the editor with a starting template by what the folder holds: OKF frontmatter (okf),
  title and tags (markdown), MADR (format adr, or a path through `adr`, `adrs` or `decisions`). A Template picker
  (okf, markdown, adr, blank) with a **Use template** button swaps it, keeping the file name. New `TEMPLATES` and
  `new_template(folder)` in `bowerbird_mcp.py`.
- `serve`: **New knowledgebase** in the tree runs `init` (preview, then confirm).
- `serve`: a setup modal opens when the collection has no `kbmcp.yaml`. It asks about, holds and your id, then runs `init`.
  Restart `serve` afterwards to load the config.
- `serve`: **Archive** in a page's settings cog, and **Unarchive** (a tree link that lists what is archived, and in the cog
  of a page in the archive). A page in the archive shows only Unarchive and Seal, with no edit.
- `serve`: the bowerbird version shows in the side pane and in the logo's tooltip.

### Fixed
- `serve`: a page could not be deleted in an okf bundle, because `index.md` and `log.md` counted as pages linking to it.
  They no longer block a delete, and the bundle's generated index list is rebuilt after it.
- `serve`: the settings cog button stretched to the width of its open menu.

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

### Changed
- `serve` takes a verb: `start`, `stop`, `restart` and `status`, each with an optional port (26937 when left out). A bare
  `serve` now only reports status, where it used to start a server, so scripts that ran `bowerbird serve` to start must run
  `bowerbird serve start`. `start` does nothing when ours is already on the port, and refuses a port something else holds.
  `stop` with nothing running exits 0. `restart` stops what it finds, waits for the port to clear, then starts.

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
