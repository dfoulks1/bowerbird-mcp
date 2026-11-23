# The fact pack

<!-- seal-banner: Written with Claude Sonnet 5.5. The behaviour is what the tests check, on made-up files and a throwaway git repository; nothing has run against your collection. A person has not reviewed this page yet. -->

**Use it when** a claim rests on something other than a web page, a file or another page of the collection: a value in a config file, a tag in git, a date, a
command's output, or something only a person can say.

`bowerbird-mcp` has four kinds of [fact](formats/okf.md#facts-what-a-claim-rests-on-and-drift): `url`, `mcp`, `file` and `internal`. The pack adds five. It is a separate
package (`bowerbird-fact-pack`, in `addons/fact-pack/`), so what runs a command or reads your repository is off until you install it.

## Install

```sh
pip install 'bowerbird-mcp[fact-pack]'        # or: uvx --from 'bowerbird-mcp[fact-pack]' bowerbird-mcp ...
```

Bowerbird finds the pack through the `bowerbird.fact_types` entry point. Without it, a page that uses one of its kinds is a `lint` error that says what to install, and the docs
build still shows the block from its recorded state.

## The five kinds

Each is a block, `[fact.<kind>](<formats/source>) the claim [fact.end]`, on one line or many. A check records its result beside the document in `.facts.yaml`, never in the document.

| Kind | Source | Holds while | First check |
|---|---|---|---|
| `key` | `pyproject.toml project.version` | the value at that path in the file is what it was | records the value |
| `git` | `tag v2.3.0` or `file main docs/x.md` | the tag, or the file at that revision, is what it was | records the commit, or the file's blob |
| `until` | `2026-12-31` | today is on or before the date | nothing to record |
| `manual` | `ops standup` (who or where it came from) | a person says it still holds | asks the person |
| `script` | `uvver` or `latest v2` (a name, then optionally one key) | the command's output is what it was | records the output |

**`key`.** The file is a JSON, YAML or TOML file, found as for `file`: absolute, `~/`, or relative to the document's folder. The path into it is dotted, with a number for a list item
(`servers.0.host`). The value is compared as text, and a number or list is written as JSON. TOML needs Python 3.11, or `tomli`, which the pack requires on 3.10. A missing file or key is a
drift.

**`git`.** `tag NAME` is the commit the tag points at; `file REVISION PATH` is the file's blob at that revision (`main`, a tag, a commit). The repository is the one around the
document. A tag that moved or was deleted, or a file that changed, is a drift. A name or revision cannot start with `-`. The command that runs is always `git rev-parse`.

**`until`.** A claim with an end date: a freeze, a deadline, a promise. Nothing is read. Once the date passes it drifts, and editing the date makes a new fact.

**`manual`.** What no machine can read. `factcheck --fetch`, run by a person at a terminal, shows the source and the claim and asks `Still true? [y/N]`; no is a drift. An agent cannot
answer it, so its run skips a `manual` fact. Nothing forces a re-check: set `facts: {manual_days: 90}` in `bower.yaml` and a fact confirmed in the last 90 days is skipped, without it the question is asked each time.

**`script`.** A command's output. The command is declared once, in the **root** `bower.yaml`, as an argument list that is run with no shell:

```yaml
facts:
  scripts:
    uvver: {cmd: [uv, --version]}
    latest: {cmd: [git, describe, --tags, "{key}"], timeout: 10}   # 30 seconds unless `timeout` says otherwise
```

A page names the script and may give one key (`[fact.script](latest main) ...`), which replaces `{key}` in the arguments. The key is one word of letters, digits and `. / : @ = + -`, and it
cannot start with `-`, so it cannot become a second argument or a shell command; anything else is not a fact. A page can never name a command, and a script in a nested `bower.yaml` is
ignored. A person at a terminal is shown the command by `--fetch` and asked first; an agent runs it without being asked, and the command comes back with the result. A command that exits non-zero is skipped, not a drift.

**Read the plan before you answer `y`.** A script runs with your privileges, and a collection you did not write can declare one in its root `bower.yaml`.

## What an agent can run

An agent may check every kind except `manual`: `factcheck file=... id=...` with no result runs one fact, and `factcheck fetch=true` all of them, with no prompt, and the check is recorded. A `script` runs
only if the root `bower.yaml` declares it, and a page cannot name a command. A `manual` fact asks a person, so an agent's run skips it.

## Tested against

Made-up files in a temporary folder on Linux with Python 3.10, by the test suite (`test_bowerbird_mcp.py`):

- **`key`:** a JSON file, then the same file changed (a drift that names both values), a missing key, a missing file, and a YAML file.
- **`git`:** a throwaway repository with a tag, the tag moved with `git tag -f`, a tag that does not exist, and a file at `HEAD` before and after a new commit.
- **`until`:** a date far ahead and a date long past; and `soon` rejected as a source.
- **`manual`:** with no terminal (an error), with a terminal answering `y` and then `n`, and with `manual_days: 30` right after a yes (skipped).
- **`script`:** an undeclared script (skipped), `cat {key}` before and after the file changed, a failing command (skipped), a key with shell characters or a leading `-` (not a fact), and a
  declaration with an empty or non-list command, a zero timeout, or a bad name (refused when `bower.yaml` loads).

Not tested: TOML on Python 3.10 without `tomli`, Windows, a repository with a shallow clone, a command that prints a lot, or any real configuration of yours.

## Report a problem

A kind that checked wrong, a drift that should not be, or a command that should not have run: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Give the
kind, the version (`bowerbird-mcp --version`) and the smallest file that shows it, never a private one. More on [reporting a problem](troubleshooting.md#reporting-a-problem).
