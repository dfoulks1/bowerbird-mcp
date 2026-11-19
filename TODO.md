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
      `seal.require` matches, never `.env`, ledger or gitignored files) with state from `reviews()`; (3) the reading pane shows
      them read-only as `<pre>` with line numbers, highlighted by pygments when installed, with the existing Seal modal; (4) new
      extra `syntax = ["pygments"]` (`bowerbird-mcp[serve,syntax]`); per-language extras only if a pack adds a tool (ruff, golangci-lint).
      Open: stop `SimpleHTTPRequestHandler` serving dotfiles such as `.env` (the listing links them); skip binary and huge files.

## 2.1.4

- [x] New file starts from a template by format (okf, markdown, adr), with a Template picker and a Use template button.
- [x] Web UI: New knowledgebase (`init`), and a setup modal when there is no `kbmcp.yaml`.
- [x] Archive management in the settings cog. Archive sends a page to the archive, unarchive sends it back (a page in the
      archive shows only Unarchive and Seal), plus an Unarchive link in the tree.

## 2.2.0

Full notes, and the questions still open: `docs-src/prompts/02-release-2.2.0.md`.
- [ ] Add an optional comment to a wax seal, I'd like to be able to denote something is sealed as historical record.
- [ ] Add a link to the repository if a git repository is detected on the right next to the theme and stop buttons.
- [ ] Remove the old `kb` / KnowledgeBaseMCP naming everywhere: docs (`kb` alias and `kb <tool>` examples), internal names,
      `kbmcp.yaml` to `bowerbird.yaml`, `KB_*` env vars to `BOWERBIRD_*`. Keep the old names working (with a warning) for a
      version or two, and keep reading the `kb-index` marker.
- [ ] Make semantic search an extra (`bowerbird-mcp[semantic]`), so the base install drops `fastembed` (about 150 MB).
- [ ] Record "derived from the code" in the seal ledger (`.waxseals.yaml`, by a generator, not a person), instead of
      guessing from `!` globs in `seal.require`. `serve`, `seal check` and the docs banner then all read the ledger.
- [ ] `hooks/seal_banner.py` reads only the ledger, with no copy of the glob logic and no `mcp` import.
- [ ] Settle `ruff` (29 findings; `tools/QA.sh` does not run it) and run mypy once.
- [ ] A subprocess test for `serve restart`.
- [ ] Housekeeping: delete the local `serve-verbs` branch; decide on `.kiro/` and `.mcp.json` (ignore or commit).
- [ ] Release: bump to 2.2.0 (`pyproject.toml`, `VERSION`, `uv lock`), CHANGELOG, rebuild docs after sealing; the owner
      builds and uploads to PyPI. No `gh release`.

## Next

- [ ] Vote tally (2.2.0 or later): a seal as a vote. A tally reads the ledger (`.waxseals.yaml`) and counts distinct human
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
      person sealed it, shown only while the sha256 still matches), plus a `Derived from the code` badge for pages left out of
      `seal.require`. Still to offer for any site generator, not only MkDocs.
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
