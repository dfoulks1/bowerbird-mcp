# Releasing

<!-- seal-banner: Written with Claude Sonnet 5.5. Not published on the website (exclude_docs in mkdocs.yml); it is for the people who cut a release. The steps are the ones used for 2.1.0, with the add-ons folded into the one package for 2.3.0. -->

The short form is in [CONTRIBUTING.md](../CONTRIBUTING.md#releasing). This page is the order that worked, and what to check at each step.

## Names on PyPI

- The package is `bowerbird-mcp`: `pip install bowerbird-mcp`, `uvx bowerbird-mcp`. It also installs a `bowerbird` command.
- The name `bowerbird` on PyPI is held by another account (an empty project). A rename was tried for 2.1.0 and
  reverted when the upload returned 403. `/pypi/<name>/json` is not proof a name is free: it is 404 for a project with
  no files. Check `/simple/<name>/` (200 means it exists) before building a release around a new name.
- The `bowerbird-mcp [extra]` form is the install line: `pip install 'bowerbird-mcp[serve]'`. The extras are `serve`, `syntax`,
  `semantic` (`fastembed`, kept out of the base install on purpose), `skos`, `sqlite-vec` and `hnsw`, plus one extra per add-on
  (`seal-extensions`, `fact-pack`, `obsidian`, `foam`, `dendron`, `logseq`); the README's Run section lists them.
- **One package.** The six add-ons are modules in the `bowerbird-mcp` wheel (`bowerbird_obsidian.py` and the rest sit beside `bowerbird_mcp.py`
  and are listed in `py-modules`). Their extras are switches that add nothing (`fact-pack` adds `tomli` on Python below 3.11), so there is
  one upload and one version. The entry-point groups stay open to third-party add-ons.

## Steps

Each step needs the one before it. Steps 5, 7, 8 and 9 are public acts: stop and get the owner's word first.

1. **Version.** `version` in `pyproject.toml` and `VERSION` in `bowerbird_mcp.py` (a test checks they agree), then `uv lock`. Add the `CHANGELOG.md` section. `grep -rn 'OLD.VERSION'` finds anything left behind.
2. **Seal.** A person seals the pages they reviewed (`seal check=true` lists what waits). Do this before the build: the badges on the site come from the ledger, so a build made before a seal is stale.
3. **Rebuild the site and check.** `tools/QA.sh --rebuild` regenerates `docs-src/tools.md`, rebuilds `docs/`, and runs every check (every Python, every backend, docs fresh, lock matches, the wheel holds the six add-on modules, ruff, mypy). It must end `QA ok`. Then commit the sealed pages, the ledgers and `docs/` on the release branch, with the `Co-Authored-By` trailer and a "human review pending" line until a person has reviewed the AI-authored files.
4. **Merge.** Fast-forward `main` to the release branch (`git switch main && git merge --ff-only 2.3`), or a PR if you want one. Nothing goes to PyPI from an unmerged branch.
5. **Tag** the merge commit on `main`: `git tag -a vX.Y.Z -m "..." <sha> && git push origin main vX.Y.Z`.
6. **Build from the tag.** Delete the old `dist/` first, or a stale file rides along.
   `rm -rf dist && git checkout vX.Y.Z && uv build && uvx twine check dist/*`. It must say PASSED twice (the wheel and the sdist), and `unzip -l dist/*.whl` lists
   `bowerbird_mcp.py` and the six add-on modules.
7. **Upload.** `uvx twine upload dist/bowerbird_mcp-X.Y.Z*` (the username is `__token__`, the password a project-scoped PyPI token). PyPI never takes the same version twice, so
   try `--repository testpypi` first when in doubt. This is the only upload: the add-ons are in the one package.
8. **Check what shipped.** PyPI can take a few minutes to show it. In a clean directory: `uvx bowerbird-mcp@X.Y.Z --version`; `uvx --from 'bowerbird-mcp[fact-pack]==X.Y.Z' bowerbird-mcp --version`
   (an extra resolves); and, if the release touches serve, `uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve start`.
9. **Back to work.** `git checkout main` (it is where the release is). No GitHub release is cut unless the owner asks for one: the tag and the CHANGELOG are the record.

## Public acts

Pushing, merging, tagging and the PyPI upload each need a person's word. A PyPI upload cannot be
undone (a yanked release still holds its version number).

## A major version

Also change the pin `create` writes into `.mcp.json` (`MCP_JSON` in `bowerbird_mcp.py`) and the `bowerbird-mcp[skos]>=N,<N+1`
example in `docs-src/formats/skos.md`.
