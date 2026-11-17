# Releasing

<!-- seal-banner: Written with Claude Sonnet 5.5. Not published on the website (exclude_docs in mkdocs.yml); it is for the people who cut a release. The steps are the ones used for 2.1.0. -->

The short form is in [CONTRIBUTING.md](../CONTRIBUTING.md#releasing). This page is the order that worked, and what to check at each step.

## Names on PyPI

- The package is `bowerbird-mcp`: `pip install bowerbird-mcp`, `uvx bowerbird-mcp`. It also installs a `bowerbird` command.
- The name `bowerbird` on PyPI is held by another account (an empty project). A rename was tried for 2.1.0 and
  reverted when the upload returned 403. `/pypi/<name>/json` is not proof a name is free: it is 404 for a project with
  no files. Check `/simple/<name>/` (200 means it exists) before building a release around a new name.
- The `bowerbird-mcp [extra]` form is the install line: `pip install 'bowerbird-mcp[serve]'`.

## Steps

1. **Version.** `version` in `pyproject.toml` and `VERSION` in `bowerbird_mcp.py` (a test checks they agree), then
   `uv lock`. Add the `CHANGELOG.md` section. `grep -rn 'OLD.VERSION'` finds anything left behind.
2. **Docs.** Change `docs-src/`, run `uv run docs_tools.py` and `uvx --with pymdown-extensions mkdocs build`. Seal the
   pages a person reviewed first, since a build made before a seal is stale. Unsealed pages may ship; say so in the PR.
3. **Checks.** `tools/QA.sh` (every Python, every backend, docs fresh, lock matches). It changes nothing.
4. **Commit and merge.** A branch, a PR to `main`, merge. Commits carry the `Co-Authored-By` trailer and a
   "human review pending" line until a person has reviewed the AI-authored files.
5. **Tag** the merge commit on `main`: `git tag -a vX.Y.Z -m "..." <sha> && git push origin vX.Y.Z`.
6. **Build from the tag.** Delete the old `dist/` first, or a stale 2.0.x file rides along.
   `git checkout vX.Y.Z && uv build && uvx twine check dist/bowerbird_mcp-X.Y.Z*`.
7. **Upload only the new files.** `uvx twine upload dist/bowerbird_mcp-X.Y.Z*`, never `dist/*`. PyPI never takes the same
   version twice, and a name's first upload registers it to the account that holds the token. Try
   `--repository testpypi` first when in doubt.
8. **GitHub release.** `gh release create vX.Y.Z dist/bowerbird_mcp-X.Y.Z* --notes-file` (the CHANGELOG section).
9. **Check what shipped.** In a clean directory: `uvx bowerbird-mcp@X.Y.Z --version`, and `uvx --from 'bowerbird-mcp[serve]'
   bowerbird-mcp serve` if the release touches serve.
10. `git checkout main`.

## Public acts

Pushing, merging, tagging, the PyPI upload and the GitHub release each need a person's word. A PyPI upload cannot be
undone (a yanked release still holds its version number).

## A major version

Also change the pin `init` writes into `.mcp.json` (`MCP_JSON` in `bowerbird_mcp.py`) and the `bowerbird-mcp[skos]>=N,<N+1`
example in `docs-src/formats/skos.md`.
