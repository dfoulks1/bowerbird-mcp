# TODO

Ideas for later:

- [ ] Distributed waxseals: a ledger per folder, not one `.waxseals.yaml` at the collection root. A wiki started for a code
      project often grows into sealing the code assets too, and the seals should live beside what they cover (the way a
      folder's own `kbmcp.yaml` already scopes its format). Open: where a ledger sits when a file's folder has none, how
      `move` carries a seal across ledgers, and how `seal check` and `serve` merge them.

## 2.1.3

- [x] Bug: viewer for seal-only collections (`bowerbird_serve.py`): today `/` falls through to a plain directory listing when there is no
      root `index.md`, and `scan()` indexes `*.md` only, so no code, YAML or config file has a page or a Seal button.
      Plan: (1) `/` renders the shell with the reading and details panes empty; (2) `scan()` also lists `sealonly_files()` (the
      files minus `seal.exempt`, never `.env`, ledger or gitignored files) with state from `reviews()`; (3) the reading pane shows
      them read-only as `<pre>` with line numbers, highlighted by pygments when installed, with the existing Seal modal; (4) new
      extra `syntax = ["pygments"]` (`bowerbird-mcp[serve,syntax]`); per-language extras only if a pack adds a tool (ruff, golangci-lint).
      Open: stop `SimpleHTTPRequestHandler` serving dotfiles such as `.env` (the listing links them); skip binary and huge files.

## 2.1.4

- [x] New file starts from a template by format (okf, markdown, adr), with a Template picker and a Use template button.
- [x] Web UI: New knowledgebase (`init`), and a setup modal when there is no `kbmcp.yaml`.
- [x] Archive management in the settings cog. Archive sends a page to the archive, unarchive sends it back (a page in the
      archive shows only Unarchive and Seal), plus an Unarchive link in the tree.

## 2.2.0

Full notes, and the questions still open: `docs-src/prompts/02-release-2.2.0.md`. The user-facing list is in `CHANGELOG.md`.

### Built (in the tree, tests green; not committed)

- [x] **Agent rules**: `BOWERBIRD.md` ("Picking a tool"), written by `create --mcp`, never overwritten; docs page `agents.md`; also served with
      no file as the MCP resource `bowerbird://agent-rules` and the prompt `rules`.
- [x] **MCP tool list about 45% smaller** (short MCP text per tool, `MCP_TEXT`); the CLI help, docs and tooltips stay generous. 34 tools.
- [x] **Seal policy inverted**: `seal.require` is gone, `seal.exempt` lists the exceptions, everything else is checked. New seal dialog
      ("Confirm seal: path", facts, who it records).
- [x] **Seal comments**: every seal carries an optional one-line `comment` (CLI `--comment`, MCP prompt, `serve` dialog).
- [x] **`seal-extensions` extra** (no dependency, a named switch): `seal: {extensions: true, quorum: N}`: several people seal one version
      (one ledger line, `seals: [...]`), `short_of_quorum` in `seal check`, tier `unverified` until the quorum is met.
- [x] **`bowers:`** (a root lists the member folders that carry their own `kbmcp.yaml`), and **`--config`** takes a folder, a relative path,
      `~` and `$VARS`.
- [x] **`create`** (was `init`): a collection, or a bower of one; `create [path] [--mcp] [--env] [--apply]`; `.mcp.json` merged; settings it
      ignores are reported. **`new`** writes a document (the old `create` is folded in). Bare `bowerbird-mcp` at a terminal offers a wizard;
      bare `serve` prints its full help. The old names (`init`, `cite`, `recheck_*`) print where they went.
- [x] **Semantic search is an extra** (`bowerbird-mcp[semantic]`); the base install drops `fastembed`. Extras documented (run and install with
      `uvx` or `uv tool`).
- [x] **Facts**: `[fact.url] <address>` ... `[fact.end]` and `[fact.mcp] jira KEY claim [fact.end]` blocks, in any format. `factcheck` lists them;
      `factcheck --fetch` (terminal only, asks first) fetches a page or calls a declared MCP tool and compares (same words, or similar
      meaning with `semantic: true`); state in `.facts.yaml` beside the document, never in the sealed file; a drift ends earlier reviews;
      `lint` errors on bad tags; the docs build shows each block's state. `fact` (was `cite`) and `factcheck file= id= result=` for agents.
      `facts: {mcp: ...}` in `kbmcp.yaml` is the allowlist of calls.
- [x] Getting started is one self-guided page; the docs cover all of the above.
- [x] A short docs page on status badges (`docs-src/badges.md`): the site's page and fact badges, other generators, and a README badge script.

### To do before the release

- [ ] QA round (owner): `tools/QA.sh` on 3.10 to 3.14 (3.12 failed once on a test that spawns a subprocess without `yaml`), `mkdocs build --strict`,
      the Web UI in a browser, `uvx --from 'bowerbird-mcp[semantic]'` end to end (needs 2.2.0 on PyPI), the docs banner hook with fact blocks.
- [ ] Re-seal the pages edited since sealing; rebuild `docs/`.
- [ ] Decide README lines about `--config /path/to/kb/kbmcp.yaml` (a folder is enough now).
- [ ] Merge decisions: delete `BOWERBIRD.new.md` (done), keep or drop the ledger move to the repo root and the hook change.
- [ ] Commit (confirm the `Co-Authored-By` trailer first), tag, build, upload to PyPI; no `gh release`.

### Open from the old 2.2.0 list

- [x] Link to the repository (from `origin`, when it has a web address) beside the theme and stop buttons in `serve`.
- [ ] Remove the old `kb` / KnowledgeBaseMCP naming everywhere: docs, internal names, `kbmcp.yaml` to `bowerbird.yaml`, `KB_*` to
      `BOWERBIRD_*`, with the old names working (and a warning) for a version or two. Large; probably not 2.2.0.
- [x] "Derived from the code" is a ledger line a generator writes (`mark_derived`), not a guess from `seal.exempt`; `serve`, the docs build
      and `hooks/seal_banner.py` read it, and the hook reads only the ledger.
- [x] `ruff` and `mypy` are clean (the mypy settings are in `pyproject.toml`); `tools/QA.sh` runs both, last.
- [x] A subprocess test for `serve restart` (start, restart replaces the process, stop, and a foreign listener on the port is refused).
- [x] Housekeeping: the local `serve-verbs` branch is deleted (it was merged); `.kiro/settings/lsp.json` and `.mcp.json` are already committed, and stay.

### Follow-ups the facts and seal work left (not blocking)

- [ ] Writing a fact as a person is still clunky: a `fact` that writes the block into the document for an agent; `fact` for a person
      (`result=-` and `result=@file`); a `--harvest`-style capture; the terminal "still true? y/n" walk for sources a machine cannot read.
- [ ] More fact kinds: `[fact.file] path#L10-20` (read by the tool, no network), scoped claims, and a quote to watch for paraphrases.
- [ ] Two fact records exist side by side: the blocks (`.facts.yaml` only) and the agent's `sources` frontmatter plus its `fact_sha256`.
      Decide whether one replaces the other.
- [ ] `serve`: show a block's fact state and a file's several signers and comments (the banner hook shows the latest seal only).
- [ ] `factcheck --fetch` is tested against a local page and a stand-in MCP server only: try real pages (StackOverflow may block it) and
      a real Jira; semantic mode is tested with a fake embedder.
- [ ] `seal-extensions`: the `serve` modal and the docs banner could show "N of M signed"; `move` carries every seal but has no test.
- [ ] The facts and seal helpers are their own files (`bowerbird_facts.py`, `bowerbird_seal.py`); a lone copy of `bowerbird_mcp.py` loses
      them, as it does `serve`. Consider the same split for the semantic, SKOS and vector-index code.

## Next

- [ ] Vote tally (partly built in 2.2.0: several signers and a quorum, behind `seal-extensions`; still open: the break-on-purpose and
      strict-seal modes, seal count as importance, `seal.tally`): a seal as a vote. A tally reads the ledger (`.waxseals.yaml`) and counts distinct human
      sealers per file or ADR, each only while the sha256 still matches (an edit voids the votes, like a stale seal).
      Weight of the edit: a file with N seals costs N to change. Before an edit (or a `seal` write) the tool warns
      "this breaks N seals" and makes you break each one on purpose (a named, ledgered act), not by a silent hash drift.
      Optional, not core: off by default, switched on in config (`seal.tally`: threshold, gate or inform), or shipped as an
      add-on extra (`bowerbird-mcp[tally]`). Plain seals work unchanged without it.
      Strict-seal mode (consider for sure): editing a file with N seals opens a modal in `serve`, one step per seal (who,
      when, "break this seal"); the edit unlocks after the last. Each break is a ledger entry. The real gate is a pre-commit
      or Claude Code hook that refuses writes to a file with live seals (agents included; they never break one). Likely
      rule: a person breaks only their own seal; a ledgered owner override covers a departed sealer. Useful for ratified
      ADRs, charters, policy, security docs and release notes; pointless at N=1.
      Break as review-then-change: the person sees the proposed change and the seal it would break (same `review_ui`
      dialog as RTC), approves, and only then does the edit apply and the seal drop. A denial writes nothing. Builds on
      the `rtc` branch, which stays off `main` until you say.
      The prompt says it plainly: "This was reviewed (N seals). Are you sure you want to change it? Once you do, it must be
      resealed before you can commit." A pre-commit hook enforces the second half: no commit of a file whose seals are
      broken or stale until it is sealed again.
      Seal count as a metric of importance: show N wherever a file shows (docs badge, `serve` list, `seal check`, search
      results), and let `heatmap` and search rank by it. Count only live seals (sha256 matches).
      A seal is a costly signal: each one is a person who judged the file worth their review, so the count is earned
      importance, not a guess.
      Importance reads two ways, both only when multi-seal mode is on: a heavily sealed file marks its subject as important,
      and a recurring multi-seal workflow marks the process as common. With the mode off, a count carries no such meaning.
      Why: five seals on a document is a shared agreement that cannot drift unseen, because every sealer's seal breaks
      when it changes. Needs a way for each sealer to find out (`seal check` in CI, or a notice on their next pull).
      Open: does the warning gate (refuse until broken) or only inform; who may break whose seal; one voter one vote (by what identity); threshold or quorum (e.g. ratify at N); approve only, or also
      object/abstain; where it shows (`seal check`, `serve`, docs badge).
- [x] Attested provenance badge, built for 2.0.0: `hooks/seal_banner.py` draws each docs page's badge from `.waxseals.yaml` (when a
      person sealed it, shown only while the sha256 still matches), plus a `Derived from the code` badge for pages left out by
      `seal.exempt`. Still to offer for any site generator, not only MkDocs.
- [ ] Search for a generated site: `reindex export=search-index.json` writes every passage (file, heading, text, `status`, trust
      `tier`, stale) as JSON, and the theme loads it with a client-side library (MiniSearch or lunr), badging each result by
      tier. Keyword only (no semantic search in a static site); the generator maps file and heading to a URL. The stock MkDocs
      `search` plugin is the zero-code alternative, without tiers.
- [ ] Addressable resources: concepts and passages as `kb://{bundle}/{file}` MCP resources.
- [ ] MCP prompts (answer from the collection and cite; review a decision record).
- [ ] Progress notifications from `reindex` over MCP (the CLI prints progress to stderr; the tool is not async).
- [ ] A loader registry (`sync` dispatches `load_md`, `load_skos` and `load_adoc` by format; a seventh format is the time).
- [ ] SKOS: count links across files for `hubs`.

## Done for this release (1.0.1)

- [x] Finish the rename to **bowerbird-mcp** (PyPI install lines, new logo
      wired into README, site, favicon and navbar, OG social-preview tags,
      description).
- [x] New logo (traced bowerbird) in `docs-src/img`, plus a light `logo-dark.svg`.
- [x] Domain set to `bowerbird.voltpop.com`: both `CNAME` files, `mkdocs.yml`
      `site_url`, `pyproject.toml` URLs, and the changelog note.
- [x] Docs rebuilt from `docs-src/` into `docs/` (mkdocs --strict, clean).
- [x] Tests green.
- [x] Merge to `main`, delete the stale branches.
