# Troubleshooting

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The behavior described here was checked against the code and by running it. -->

## Names

- **`warning: ... kbmcp.yaml is the old name of bower.yaml`** (or `KB_USER is the old name of BOWERBIRD_USER`). Before 2.2.0 the settings
  file was `kbmcp.yaml`, the environment variables began `KB_`, the lint skip file was `kbmcp.nolint` and the index cache was `.kbmcp/`. The
  old names still work, and the warning says what to rename: `git mv kbmcp.yaml bower.yaml`, `KB_X` to `BOWERBIRD_X` (in the environment or in
  `.env`), `kbmcp.nolint` to `bower.nolint`. When both names exist, the new one is used. The old `.kbmcp/` cache folder can just be deleted.
  A generated `index.md` written under the old `kb-index` markers is read as it was, and rewritten with the new markers the next time `index` runs.

## Searching

- **`passages` says `gap: true` for something you know is there.** It matches by words and has no stemming, so "rolling"
  does not match "roll". Try the file's own words. `bowerbird-mcp search roll` matches by substring, so it finds `rollback`, and
  semantic search (`semantic: true`) matches by meaning. [Getting started](getting-started.md#5-searching) covers all three.
- **A search from the wrong folder finds nothing, and says only `gap: true`.** Bowerbird looks for a `bower.yaml` in the
  current folder and then in the folders above it, never below. From a folder that is not a collection, or from the parent
  of several, there is nothing to search. Run it inside the collection, or name the file:
  `bowerbird-mcp --config path/to/bower.yaml passages ...`.
- **A hit says `stale`.** The file changed after its review. Read it again and seal it again.

## Settings

- **`create holds=adr` did not change the format.** `holds` only applies when there is no `bower.yaml` yet. On an existing
  collection, edit the `format:` line in `bower.yaml` and run `bowerbird-mcp reindex`.
- **`seal takes exempt and exempt_status`.** `seal.require` is gone. Every file is checked, so `bower.yaml` lists only the
  ones to leave out: `seal: {exempt: ["src/gen_*.py"]}`.
- **My MCP server does not offer `seal`.** If `roles:` in `bower.yaml` spells the roles out, `seal` has to be in the list.
  A file with no `roles:` line gets all five. Asking for a role that is left out (`--role seal`) refuses to start, with
  "role seal is off in bower.yaml".
- **`BOWERBIRD_ROOT is no longer read`.** The old environment variable is gone. Put the folder's `bower.yaml` where the tool runs,
  or name it with `--config`.

## Serve

- **`serve needs the markdown package`.** Install the extra: `pip install 'bowerbird-mcp[serve]'`.
- **`port 26937: Address already in use`.** It is already running (`serve status`), or something else has the port. Use
  `serve stop`, or pick a port: `serve start 8080`.
- **The page does not show my change.** A file change shows on refresh; a change to `bower.yaml`, or an update to
  Bowerbird, needs `serve restart`.
- **I lost the shell it started in.** Press ⏻ in the top bar of the page, or run `serve stop` from anywhere.

More in [Serve](serve.md).

## Installing

- **`rdflib is missing`** (a `skos` collection). Install the extra: `pip install rdflib`, or with `uvx`, ask for it:
  `uvx --from "bowerbird-mcp[skos]" bowerbird-mcp`.
- **Semantic search does not start (`needs the semantic extra`).** It is an add-on: `uv tool install 'bowerbird-mcp[semantic]'`,
  or `uvx --from 'bowerbird-mcp[semantic]' bowerbird-mcp`; the one-file script needs `uv run --with fastembed bowerbird_mcp.py`.
- **`uvx` runs an old build while you test local changes.** Add `--no-cache`.
