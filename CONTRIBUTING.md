# Contributing

<!-- --8<-- [start:body] -->
Bowerbird is a personal project, Apache-2.0 licensed, built under the
[ASF generative-tooling guidelines][asf-gt]. AI assists; a human reviews before
anything public-facing ships.

## Feedback

Bugs, ideas and OKF edge cases: [GitHub Issues](https://github.com/dfoulks1/bowerbird-mcp/issues), or write to dfoulks@voltpop.com. Doc fixes are welcome too.
Security problems: see [SECURITY.md](https://github.com/dfoulks1/bowerbird-mcp/blob/main/SECURITY.md), and please do not open a public issue for them.

## What it serves

A folder of files in one of six formats: bundles in the [Open Knowledge Format][okf] (OKF), Markdown, ADR records, SKOS
thesauri, AsciiDoc, or any text files you name (seal-only); Obsidian, Foam, Dendron and Logseq folders too, through add-ons. Search and the human-review `seal` work across all of them;
the full toolset is OKF's. Everything a tool does is also doable by hand (edit the file, run `lint`). The tools make it
cheaper and more consistent, not possible.

## How we build

One brief, then refinement. [`docs-src/prompts/rewrite-brief.md`](https://github.com/dfoulks1/bowerbird-mcp/blob/main/docs-src/prompts/rewrite-brief.md) is the current brief (AI source
material kept in the repository, not on the website; a draft in the beta process);
use cases drive changes to it. Core stays one file.

## ASF generative-tooling compliance

- ICLA §§4/5/7/8 and conditions 2.1–2.3 apply.
- Third-party licensing must allow Apache-2.0 output. No GPL or
  Apache-incompatible reproduced code.
- A human reviews AI-generated public-facing output before it ships; label it
  AI-generated if unreviewed.
- Provenance trailer on commits: the exact string your tool is configured
  with, confirmed before committing, never fabricated. For example:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

## Running the checks

```sh
tools/QA.sh                      # every check a release asks for, in one command (needs uv); PYTHONS="3.12" tools/QA.sh for one Python
uv run test_bowerbird_mcp.py     # self-check against throwaway bundles
uv run --with rdflib --with sqlite-vec --with hnswlib test_bowerbird_mcp.py   # also the optional backends (skipped otherwise)
```

`tools/QA.sh` runs the tests with every optional backend on Python 3.10 to 3.14, checks that `docs-src/tools.md` is what the
tools' docstrings produce, that `docs/` is a fresh build of `docs-src/`, and that `uv.lock` matches `pyproject.toml`. It
changes nothing in the working tree and stops at the first failure.

## Releasing

1. Set `version` in `pyproject.toml`, `VERSION` in `bowerbird_mcp.py` (a test checks they agree) and in each of the six add-ons in
   `addons/*/pyproject.toml` (lockstep: `seal-extensions`, `fact-pack`, `obsidian`, `foam`, `dendron`, `logseq`), run `uv lock` (the
   lockfile records the version), and add a section to `CHANGELOG.md`. For a new major version, also change the pin `create`
   writes into `.mcp.json` (`MCP_JSON` in `bowerbird_mcp.py`) and the `bowerbird-mcp[skos]>=N,<N+1` example in
   `docs-src/formats/skos.md`. Then run `tools/QA.sh`.
2. Seal the pages a person has reviewed, rebuild the docs site (below) and commit. Merge to `main`.
3. Tag and publish a GitHub release, `git tag -a vX.Y.Z` then `gh release create vX.Y.Z`, with the
   `CHANGELOG.md` section as the notes. This only creates the release: nothing publishes automatically.
4. Publish to PyPI by hand, from the tag, after the checks above pass. The six add-ons go first (each is its own package,
   `uv build addons/NAME --out-dir dist`, then `uvx twine upload dist/bowerbird_NAME-X.Y.Z*`). Their extras are added to
   `pyproject.toml` only now, then `uv lock`, then Bowerbird itself:

   ```sh
   git checkout vX.Y.Z && uv build && uvx twine check dist/bowerbird_mcp-X.Y.Z* && uvx twine upload dist/bowerbird_mcp-X.Y.Z*
   git checkout main
   ```

   Never upload `dist/*`. `twine` asks for credentials: the username `__token__` and a project-scoped PyPI API token as the
   password (or set `TWINE_PASSWORD`). Keep the token out of the repository and the shell history. PyPI never
   accepts the same version twice, so a mistake means a new version. To try it first,
   add `--repository testpypi` to the upload.

## Docs site

`docs-src/` is the source and `docs/` the built site, committed so GitHub Pages
serves it from `main` `/docs`. No CI builds it. After changing the README, a
tool or `docs-src/`, rebuild locally and commit both:

```sh
uv run docs_tools.py                          # docs-src/tools.md, from the tools' docstrings
uvx --with pymdown-extensions mkdocs build    # docs-src/ -> docs/
```

`docs-src/` is also a collection (its own `bower.yaml`): a person reviews each page and seals it, and the build draws each
page's review badge from `docs-src/.waxseals.yaml` (`hooks/seal_banner.py`). So seal first, then build, then commit
`docs/`: a build made before a seal is stale, and `tools/QA.sh` fails it. See what still needs a review with:

```sh
uv run bowerbird_mcp.py seal check=true --config docs-src/bower.yaml
```

`tools.md` is built from the code and left out of the review policy (`/tools.md` in `seal.exempt`). `mkdocs serve`
loads `hooks/` once, so restart the preview after changing them.

[asf-gt]: https://www.apache.org/legal/generative-tooling.html
[okf]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/bad9bdbafa82c672b00d437d4f2cc8f17e9e5f58/okf/SPEC.md
<!-- --8<-- [end:body] -->
