# Command line

<!-- seal-banner: Written with Claude Sonnet 5.5, from the code's own help output. A person must review it. -->

Every tool is also a command: `bowerbird-mcp <tool> ...` (or `uvx bowerbird-mcp`, or `uv run bowerbird_mcp.py` from a
checkout). The command line has all the tools; an MCP server offers only the ones its [roles](guide.md#roles-a-smaller-tool-list-per-agent)
allow. For CI see the [guide](guide.md#ci), and for connecting an assistant see [getting started](getting-started.md).

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
  | `init` | `-A` apply, `-a` about, `-t` holds, `-B` bundle, `-u` user |
  | `seal` | `-f` file, `-b` by, `-p` promote, `-d` decision, `-c` check, `-s` since, `-B` bundle |
  | `lint` | `-s` scope, `-l` limit, `-b` baseline, `-S` since, `-a` all, `-f` file, `-i` ignore, `-B` bundle |
  | `search`, `passages` | `-q` query, `-t` type, `-g` tag, `-d` dir, `-l` limit, `-B` bundle |
  | `list` | `-t` type, `-g` tag, `-s` status, `-T` tier, `-S` stale, `-l` limit, `-B` bundle |
  | `status` | `-d` due-days, `-B` bundle |
  | `get`, `links` | `-f` file, `-B` bundle (`get` also `-l` limit) |

- Every other command takes the first free letter of each argument, in order. Those can shift, so use long flags in scripts.
- `-h` and `-O`/`-F` are reserved: `-h` is help, `-O` (or `-F`, or `output=`) chooses the output.

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

## Sealing as a person

`--attest` records you as a human, as `human:<KB_USER>` (else your git `user.email`). It works only on the command line,
needs a terminal (stdin a TTY), and no MCP call can pass it. It applies to `seal`, `create`, `provenance` and
`recheck_apply`.

```sh
bowerbird-mcp seal deploy.md --attest
bowerbird-mcp ratify docs/adr/0001-queue.md --attest decision=accepted   # ratify and verify are names for seal
bowerbird-mcp seal check=true since=origin/main                          # what lacks a review (exits 1 if any)
```

## Settings

`kbmcp.yaml` at the collection root sets the defaults, `.env` and `KB_*` variables override it, and the flags
`--config <path>` and `--role <role>` pick a collection and a role for the server. [The guide](guide.md) lists every key.
