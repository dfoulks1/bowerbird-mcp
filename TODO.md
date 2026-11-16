# TODO

Ideas for later:

## Next

- [ ] Attested provenance badge: "AI wrote this, a person waxsealed it". Build each docs page's banner from `.waxseal.yaml`
      (who sealed it, when), shown only while the page's sha256 still matches; otherwise "AI-generated, not yet reviewed".
      Probably worth offering for any collection, pairing `generated` (an AI wrote it) with `seal` (a person reviewed it).
- [ ] Addressable resources: concepts and passages as `kb://{bundle}/{file}` MCP resources.
- [ ] MCP prompts (answer from the collection and cite; review a decision record).
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
- [x] Tests green.
- [x] Merge to `main`, delete the stale branches.
