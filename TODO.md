# TODO

Ideas for later:

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
