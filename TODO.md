# TODO

Ideas for later:

## 2.1.3

- [x] Bug: viewer for seal-only collections (`bowerbird_serve.py`): today `/` falls through to a plain directory listing when there is no
      root `index.md`, and `scan()` indexes `*.md` only, so no code, YAML or config file has a page or a Seal button.
      Plan: (1) `/` renders the shell with the reading and details panes empty; (2) `scan()` also lists `sealonly_files()` (the
      `seal.require` matches, never `.env`, ledger or gitignored files) with state from `reviews()`; (3) the reading pane shows
      them read-only as `<pre>` with line numbers, highlighted by pygments when installed, with the existing Seal modal; (4) new
      extra `syntax = ["pygments"]` (`bowerbird-mcp[serve,syntax]`); per-language extras only if a pack adds a tool (ruff, golangci-lint).
      Open: stop `SimpleHTTPRequestHandler` serving dotfiles such as `.env` (the listing links them); skip binary and huge files.

## 2.2.0

Full notes, and the questions still open: `docs-src/prompts/02-release-2.2.0.md`.

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
