# Contributing

Bowerbird is a personal project, Apache-2.0 licensed, built under the
[ASF generative-tooling guidelines][asf-gt]. AI assists; a human reviews before
anything public-facing ships.

## Feedback

Bugs, ideas and OKF edge cases: [GitHub Issues](https://github.com/dfoulks1/bowerbird-mcp/issues). Doc fixes are welcome too.
Security problems: see [SECURITY.md](https://github.com/dfoulks1/bowerbird-mcp/blob/main/SECURITY.md), and please do not open a public issue for them.

## What it serves

Bundles in the [Open Knowledge Format][okf] (OKF). Everything a tool does is
also doable by hand (edit the file, run `lint`). The tools make it cheaper and
more consistent, not possible.

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
uv run test_bowerbird_mcp.py     # self-check against throwaway bundles
uv run --with rdflib --with sqlite-vec --with hnswlib test_bowerbird_mcp.py   # also the optional backends (skipped otherwise)
```

## Releasing

1. Set `version` in `pyproject.toml` and `VERSION` in `bowerbird_mcp.py` (a test checks they agree), add a section to `CHANGELOG.md`, and run the checks above (the tests
   run on Python 3.10 to 3.14: `uv run --python 3.10 test_bowerbird_mcp.py`).
2. Rebuild the docs site (below) and commit. Merge to `main`.
3. Tag and publish a GitHub release, `git tag -a vX.Y.Z` then `gh release create vX.Y.Z`, with the
   `CHANGELOG.md` section as the notes. This only creates the release: nothing publishes automatically.
4. Publish to PyPI by hand, from the tag, after the checks above pass:

   ```sh
   git checkout vX.Y.Z && uv build && uvx twine check dist/* && uv publish
   git checkout main
   ```

   `uv publish` asks for credentials: the username `__token__` and a project-scoped PyPI API token as the
   password (or set `UV_PUBLISH_TOKEN`). Keep the token out of the repository and the shell history. PyPI never
   accepts the same version twice, so a mistake means a new version. To try it first,
   `uv publish --publish-url https://test.pypi.org/legacy/` uploads to TestPyPI.

## Docs site

`docs-src/` is the source and `docs/` the built site, committed so GitHub Pages
serves it from `main` `/docs`. No CI builds it. After changing the README, a
tool or `docs-src/`, rebuild locally and commit both:

```sh
uv run docs_tools.py                          # docs-src/tools.md, from the tools' docstrings
uvx --with pymdown-extensions mkdocs build    # docs-src/ -> docs/
```

[asf-gt]: https://www.apache.org/legal/generative-tooling.html
[okf]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
