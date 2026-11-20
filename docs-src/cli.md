# Command line

<!-- seal-banner: Written with Claude Sonnet 5.5, from the code's own help output. A person must review it. -->

Every tool is also a command: `bowerbird-mcp <tool> ...` (or `uvx bowerbird-mcp`, or `uv run bowerbird_mcp.py` from a
checkout). The command line has all the tools; an MCP server offers only the ones its [roles](guide.md#roles-a-smaller-tool-list-per-agent)
allow. For CI see the [guide](guide.md#ci), and for connecting an assistant see [getting started](getting-started.md).

For the sake of clarity, this document assumes that `bowerbird`, a convenience command provided by bowerbird-mcp, was installed using `uv tool install bowerbird-mcp`. Each line below is the same command:

```sh
bowerbird status                  # as written on this page (installed with uv tool install)
uvx bowerbird-mcp status          # no install (not `uvx bowerbird`: that is a different package)
uv run bowerbird_mcp.py status    # from a checkout of the repo, in its folder
```

## Extras

The base install is small: search, lint, seal, the MCP server and this command line. Anything heavier is an extra you ask for:

| Extra | Adds | You need it for |
|---|---|---|
| `serve` | `markdown` | `serve`, the browser UI |
| `syntax` | `pygments` | highlighted code files in `serve` (use with `serve`) |
| `semantic` | `fastembed` (about 150 MB; the model, about 65 MB, downloads once) | `semantic: true`, matching passages by meaning |
| `skos` | `rdflib` | `format: skos` |
| `sqlite-vec` | `sqlite-vec` | `vector_index: sqlite-vec` |
| `hnsw` | `hnswlib` | `vector_index: hnsw` |
| `seal-extensions` | nothing | `seal: {extensions: true, quorum: 2}`: several people seal one version, with a quorum |

Name one, or several, the same way each time:

```sh
uv tool install 'bowerbird-mcp[serve,semantic]'                   # installed: `bowerbird` now has them (run it again with other extras to add them)
uvx --from 'bowerbird-mcp[serve,semantic]' bowerbird-mcp status   # no install: name them with --from, and the command after it
pip install 'bowerbird-mcp[serve,semantic]'                       # pip
```

A feature that needs an extra you did not ask for stops with a message that names it and the fix. The same table, and the MCP-config form, are in the [guide](guide.md#extras).

## Finding your way

```sh
bowerbird-mcp help            # the everyday commands for this collection's format, grouped
bowerbird-mcp help all        # every command, one line each
bowerbird-mcp help seal       # one tool: what it does, its arguments, examples
bowerbird-mcp seal -h         # the same, as flags
bowerbird-mcp --version
```

`help` shows only what the collection's `format` uses. An unknown command prints the help and exits 2.

## Two ways to pass arguments

```sh
bowerbird-mcp lint scope=okf output=github      # name=value: the stable form, for scripts and agents
bowerbird-mcp lint -s okf -O github             # flags: the same call, for people
bowerbird-mcp seal '{"file": "db.md"}'          # or one JSON object
```

Flags are turned into the same `name=value` words, so both behave alike. Lists are `a,b` or JSON. Bare words fill the
required arguments in order (`move a.md b.md`); on `set`, any other `key=value` is frontmatter
(`set a.md status=deprecated tags=[x,y]`).

- Long flags are the argument's name (`--due-days`) and are never abbreviated: `--app` is not `--apply`.
- The everyday commands have pinned short flags that never change, and `-B` is `bundle` on all of them:

  | Command | Short flags |
  |---|---|
  | `create` | `-p` path, `-A` apply, `-m` mcp, `-e` env, `-B` bundle, `-a` about, `-t` holds, `-u` user |
  | `seal` | `-f` file, `-b` by, `-p` promote, `-d` decision, `-c` check, `-s` since, `-B` bundle |
  | `lint` | `-s` scope, `-l` limit, `-b` baseline, `-S` since, `-a` all, `-f` file, `-i` ignore, `-B` bundle |
  | `search`, `passages` | `-q` query, `-t` type, `-g` tag, `-d` dir, `-l` limit, `-B` bundle |
  | `list` | `-t` type, `-g` tag, `-s` status, `-T` tier, `-S` stale, `-l` limit, `-B` bundle |
  | `status` | `-d` due-days, `-B` bundle |
  | `get`, `links` | `-f` file, `-B` bundle (`get` also `-l` limit) |

- Every other command takes the first free letter of each argument, in order. Those can shift, so use long flags in scripts.
- `-h` and `-O`/`-F` are reserved: `-h` is help, `-O` (or `-F`, or `output=`) chooses the output.

## Serve

`bowerbird serve` opens the collection in a browser at `http://127.0.0.1:26937/`, as a front end to the same tools, for a
person: browse, search four ways, edit, create, move, delete, tag, lint and seal, with no AI in it. The full guide is on the
[Serve](serve.md) page.

```
bowerbird serve             # a bare `serve` prints the help: every verb and option, `--config` included
bowerbird serve status      # information only: is it running? exit 0 if so, 1 if not
bowerbird serve start       # in the background; a no-op if ours is already on the port
bowerbird serve start -f    # in the foreground (ctrl-c stops)
bowerbird serve stop        # end it; nothing running is not an error
bowerbird serve restart     # stop what is found, then start: always ends with a running server
bowerbird serve start 8080  # another port (any verb takes one; 26937 when left out)
bowerbird --config ~/notes serve start   # another collection, from anywhere: --config takes a kbmcp.yaml or its folder (a relative
                                         # path, ~ or a full path) and goes BEFORE `serve`; without it, run inside the collection
```

It needs the `serve` [extra](#extras). With `uv tool install 'bowerbird-mcp[serve]'` the `bowerbird` lines above work as written. With `uvx`, name the extra with `--from`:

```sh
uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve start   # the same as `bowerbird serve start`
```

Or `pip install 'bowerbird-mcp[serve]'`.

## Output

At a terminal the output is text. Piped, in CI or in a script it is JSON. `-O json|text|github|sarif` overrides either
(`github` and `sarif` are for `lint`). Text prints diffs as they are.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | done, or nothing found |
| 1 | findings: `lint` errors, or `seal check=true` has unsigned, stale or claimed-accepted files |
| 2 | a usage error: unknown flag, missing argument, or `--attest` without a terminal |

## Changing things safely

Tools that touch many files default to `apply=false`: they print the plan and the diff and write nothing. Read it, then
repeat with `--apply` (or `apply=true`).

```sh
bowerbird-mcp rename new-name --bundle old-name            # the plan and diff
bowerbird-mcp rename new-name --bundle old-name --apply    # write it
```

### Lint, then fix

`lint` only reports: it never changes a file. `fix` is its repair half, for what needs no judgment (generated index lists,
tag spelling, `log.md` order, `index.md` frontmatter). It follows the same rule: no `--apply`, a diff.

```sh
bowerbird-mcp lint                # what is wrong (exit 1 on errors)
bowerbird-mcp fix                 # the repairs as a diff (exit 1 if there is work)
bowerbird-mcp fix --apply         # write them, re-lint, report what remains
```

## Making a collection or a bower

`create` makes a folder into a collection: a `kbmcp.yaml`, and for a new root the files an assistant needs. It previews until you add
`--apply`, and it never overwrites. Run bare at a terminal it asks for what it cannot guess (what the folder holds, one sentence
about it, your id).

```sh
bowerbird create                                  # preview: this collection's root (a new one, if there is none)
bowerbird create --apply                          # write it: kbmcp.yaml, BOWERBIRD.md, .mcp.json, env.example, .env in .gitignore
bowerbird create --mcp --apply                    # only the assistant's part: BOWERBIRD.md, and bowerbird added to .mcp.json
bowerbird create --env --apply                    # only env.example and the .gitignore line for .env
bowerbird create docs -t markdown -a "Site pages" --apply   # a folder: a bower, if it is inside a collection; else a new root
```

- With no flag, every step runs. With `--mcp` or `--env`, only those steps run (and `kbmcp.yaml`, if it is missing).
- `--mcp` prints the path of `BOWERBIRD.md`. `.mcp.json` keeps the other servers it holds, adds bowerbird, and leaves a bowerbird
  entry that differs from the default alone (you may have set extras or `--config` in it).
- **A bower.** Inside a collection whose `kbmcp.yaml` has a `bowers:` list, `create docs` writes `docs/kbmcp.yaml` and adds `docs` to that
  list, keeping the file's comments. The new file is the whole commented template (every setting, with its documentation), with only what
  you answered (`about`, `format`) uncommented, and a note on top that a bower reads only `format`, `seal`, `about`, `hubs` and
  `min_similarity`. The rest are the root's to decide. A root with no `bowers:` key finds the new folder by the older rule, and `create` says
  so. A bower shares the root's `.mcp.json`, `.env` and `BOWERBIRD.md`.
- Settings you pass (`about`, `holds`, `user`) are ignored for a folder that already has a `kbmcp.yaml`, and the result says so.
- A document is not made here: `new` writes one.

## Sealing as a person

`--attest` records you as a human, as `human:<KB_USER>` (else your git `user.email`). It works only on the command line,
needs a terminal (stdin a TTY), and no MCP call can pass it. It applies to `seal`, `new` and `provenance`.

```sh
bowerbird-mcp seal deploy.md --attest
bowerbird-mcp ratify docs/adr/0001-queue.md --attest decision=accepted   # ratify and verify are names for seal
bowerbird-mcp seal check=true since=origin/main                          # what lacks a review (exits 1 if any)
```

## Settings

`kbmcp.yaml` at the collection root sets the defaults, `.env` and `KB_*` variables override it, and the flags
`--config <path>` and `--role <role>` pick a collection and a role for the server. `--config` takes a `kbmcp.yaml` or the folder
holding one, as a relative path, with `~`, or in full. [The guide](guide.md) lists every key.
