# Troubleshooting

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The behavior described here was checked against the code and by running it. -->

## Searching

- **`passages` says `gap: true` for something you know is there.** It matches by words and has no stemming, so "rolling"
  does not match "roll". Try the file's own words. `kb search roll` matches by substring, so it finds `rollback`, and
  semantic search (`semantic: true`) matches by meaning. [Getting started](getting-started.md#4-search-it) covers all three.
- **A search from the wrong folder finds nothing, and says only `gap: true`.** Bowerbird looks for a `kbmcp.yaml` in the
  current folder and then in the folders above it, never below. From a folder that is not a collection, or from the parent
  of several, there is nothing to search. Run it inside the collection, or name the file:
  `kb --config path/to/kbmcp.yaml passages ...`.
- **A hit says `stale`.** The file changed after its review. Read it again and seal it again.

## Settings

- **`init holds=adr` did not change the format.** `holds` only applies when there is no `kbmcp.yaml` yet. On an existing
  collection, edit the `format:` line in `kbmcp.yaml` and run `kb reindex`.
- **`seal-only needs seal.require`.** In a `seal-only` collection the policy must name the files that need a review:
  `seal: {require: ["src/**/*.py"]}` in `kbmcp.yaml`.
- **My MCP server does not offer `seal`.** If `roles:` in `kbmcp.yaml` spells the roles out, `seal` has to be in the list.
  A file with no `roles:` line gets all five. Asking for a role that is left out (`--role seal`) refuses to start, with
  "role seal is off in kbmcp.yaml".
- **`KB_ROOT is no longer read`.** The old environment variable is gone. Put the folder's `kbmcp.yaml` where the tool runs,
  or name it with `--config`.

## Serve

- **`serve needs the markdown package`.** Install the extra: `pip install 'bowerbird-mcp[serve]'`.
- **`port 26937: Address already in use`.** It is already running (`serve status`), or something else has the port. Use
  `serve stop`, or pick a port: `serve 8080`.
- **The page does not show my change.** A file change shows on refresh; a change to `kbmcp.yaml`, or an update to
  Bowerbird, needs `serve stop` and `serve` again.
- **I lost the shell it started in.** Press ⏻ in the top bar of the page, or run `serve stop` from anywhere.

More in [Serve](serve.md).

## Installing

- **`rdflib is missing`** (a `skos` collection). Install the extra: `pip install rdflib`, or with `uvx`, ask for it:
  `uvx --from "bowerbird-mcp[skos]" bowerbird-mcp`.
- **Semantic search does not start with the bare script.** `uvx bowerbird-mcp` carries `fastembed`; the one-file script
  needs `uv run --with fastembed bowerbird_mcp.py`.
- **`uvx` runs an old build while you test local changes.** Add `--no-cache`.
