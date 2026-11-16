# TODO

Nothing open for 1.0.1. Ideas for later:

## 2.0

- [ ] Addressable resources: concepts and passages as `kb://{bundle}/{file}` MCP resources.
- [ ] MCP prompts (answer from the knowledgebase and cite; review a decision record).
- [ ] Progress notifications from `reindex` over MCP (the CLI prints progress to stderr; the tool is not async).
- [ ] A loader registry, if a fourth format arrives (today `load_md` and `load_skos` are dispatched in `sync`).
- [ ] SKOS: count links across files for `hubs`.

## Done for this release (1.0.1)

- [x] Finish the rename to **bowerbird-mcp** (PyPI install lines, new logo
      wired into README, site, favicon and navbar, OG social-preview tags,
      description).
- [x] New logo (traced bowerbird) in `docs-src/img`, plus a light `logo-dark.svg`.
- [x] Domain set to `bowerbird.voltpop.com`: both `CNAME` files, `mkdocs.yml`
      `site_url`, `pyproject.toml` URLs, and the changelog note.
- [x] Docs rebuilt from `docs-src/` into `docs/` (mkdocs --strict, clean).
- [x] Lint clean (`TODO.md` added to `kbmcp.nolint`); tests green.
- [x] Merge to `main`, delete the stale branches.
