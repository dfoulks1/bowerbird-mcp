# Facts

<!-- seal-banner: Written with Claude Sonnet 5.5. What the page says is what the tests check, on made-up files; nothing has run against your collection. A person has not reviewed this page yet. -->

A **fact** is a claim together with where it came from, written so that it can be checked again. It is one span of text, in any Markdown document of any
[format](formats.md), and nothing else is needed: a person and an agent write the same thing.

```text
[fact.file]{id: 3, by: ann}(deploy.sh#L10-14) rollback runs the previous tag [fact.end]
```

That says: this claim rests on lines 10 to 14 of `deploy.sh`, and it is fact number 3 of this page. Later, `factcheck` reads those lines and says whether they still hold the words.
When they do not, the fact has **drifted**, and every [review](sealing.md) of the page made before it stops holding.

## The block

```text
[fact.KIND]{metadata}(source) the claim [fact.end]
```

| Part | What it is |
|---|---|
| `[fact.KIND]` | Opens the block. The kind says what the source is: `url`, `file`, `mcp` and so on (the table below). |
| `{metadata}` | Optional. A JSON or YAML mapping directly after the tag: a number, who wrote it, how sure. |
| `(source)` | The source, in the kind's own words: an address, a path with lines, a server and a key. It ends at the first `)`, so write a `)` inside it as `%29`. |
| the claim | The words the source says, up to `[fact.end]`. Paste them; a check compares them with the source. One line or many. |
| `[fact.end]` | Closes the block. |

A block with no metadata is the form of 2.2.0 and is still valid. A page may hold any number of blocks. A block inside a code fence or a code span is an example, not a fact. In a Markdown
renderer that knows nothing of facts, a `url` block shows as a link to its source.

**For an agent**, both the metadata and the source may be JSON, so a block can be written exactly: `{"id": 3, "by": "claude", "tags": ["db"]}` and `(["jira", "INFRA-1"])`, which reads as the words `jira INFRA-1`.
A `}` or `)` inside a JSON string is written `}` or `%29`.

### Its number

`id` is the fact's number: a whole number, first in the mapping, unique in the page. `factcheck file=deploy.md id=3` checks it. The claim can be edited without losing the number, and
a fact whose words or source changed since its last check shows as **unchecked** until it is checked again. A fact with no `id` is known by a fingerprint of its kind, source and words (what
2.2.0 did); `fix` numbers those, moving what was checked under the fingerprint to the number, and `fact` takes the next free number when it writes one.

### The rest of the metadata

| Key | Meaning |
|---|---|
| `id` | The fact's number (above). |
| `by` | Who wrote it: a person's name, or the exact `<tool>/<model>` of an agent. Never invented. |
| `at` | The day it was written. |
| `as_of` | The day the claim was true as of. |
| `confidence` | `0` to `1`, or `low`, `medium`, `high`. |
| `note` | One line for the reader. |
| `tags` | A list of words. |
| `stale_after` | Days since the last check after which the fact is **due** (an unchecked fact is due), or a date. `factcheck` lists what is due. |
| `last_checked` | The day of the last check. Written by a check, not by hand. |

Any other key is kept and shown. `lint` warns of a wrong value in a key that has a meaning.

## The kinds

Nine kinds. The first four are in `bowerbird-mcp`; the other five are the [fact pack](fact-pack.md), which you install with `pip install 'bowerbird-mcp[fact-pack]'`.

| Kind | Source | Holds while | An agent may check it |
|---|---|---|---|
| `url` | `https://example.com/page` | the page still holds the words (with `semantic: true`, or still means them) | yes |
| `mcp` | `jira INFRA-1` (a server, a key) | the call, declared in `bower.yaml`, still returns the value it did | yes (only a call declared in `bower.yaml`) |
| `file` | `src/app.py#L10-20` | the lines still hold the words (the whole file without `#L`) | yes |
| `internal` | `docs/tools.md#Links` | the page, or that heading's section, still holds the words | yes |
| `key` | `pyproject.toml project.version` | the value at that path in a JSON, YAML or TOML file is what it was | yes |
| `git` | `tag v2.3.0` or `file main docs/x.md` | the tag, or the file at that revision, is what it was | yes |
| `until` | `2026-12-31` | today is on or before the date | yes |
| `manual` | `ops standup` | a person says it still holds | no: it asks a person, so an agent's run skips it |
| `script` | `uvver` or `latest v2` | the command's output is what it was | yes (only a command declared in the root `bower.yaml`) |

`file` and `key` read paths that are absolute, `~/`, or relative to the page's folder, and may lie outside the collection. `internal` reads another page of the collection, from its root, and
does not look at whether that page is sealed. The first check of a `mcp`, `key`, `git` or `script` fact records the value; later ones compare. Each kind is explained in
[OKF](formats/okf.md#facts-what-a-claim-rests-on-and-drift) and, for the pack's, on [its page](fact-pack.md).

## Writing a fact

By hand, as above. Or with `fact`, which writes the block and numbers it:

```sh
bowerbird-mcp fact notes/deploy.md kind=file source='deploy.sh#L10-14' claim='rollback runs the previous tag' after='Rollback'
bowerbird-mcp fact notes/db.md kind=mcp source='jira INFRA-1' claim='is open' meta='{"by": "ann", "confidence": "high"}' result=@issue.json
```

`after` is a heading's text (the block goes at the end of its section) or a line number; the default is the end of the file. `meta` is the metadata (`at` is added). A kind that only reads files
here (`file`, `internal`, `key`, `git`, `until`) is **checked first**, and `fact` refuses a claim the source does not hold, so a quotation that is not there never reaches the page (`check=false`
writes it anyway). For `mcp`, `result` is what the call returned, and its watched value becomes the baseline. At a terminal, `result=-` reads standard input and `result=@file` a file, and
`harvest=true` with `kind=url` fetches the page, shows its paragraphs and asks which to quote. An agent cannot harvest or read `-` and `@file`.

## Checking

`factcheck` with no arguments lists every block and its state, and the facts that are due. It runs nothing.

| State | Meaning |
|---|---|
| unchecked | never checked, or the words or the source were edited since |
| checked | the source still holds the words (or the value is the one recorded) |
| drifted | it does not |

```sh
bowerbird-mcp factcheck notes/deploy.md              # the facts on the page and their state
bowerbird-mcp factcheck notes/deploy.md id=3         # check fact 3 (file, internal, key, git, until: read here, no prompt)
bowerbird-mcp factcheck --fetch                      # a person: show every fetch and call, ask, then check them all
```

`--fetch` checks every block against a fresh result. For a person at a terminal it first lists what it will fetch, call or run (an address, a call, a command), asks `Run these? [y/N]`, then checks each block; an agent, or a script, is not asked, and the list comes back with the result as `ran`. A page is fetched, an `mcp` call is made
(only one declared under `facts` in `bower.yaml`), a `manual` fact asks a person `Still true?` (skipped when no one is there), and a `script` runs (only one declared in the root `bower.yaml`). A check ends as checked, drifted, **skipped** (not declared, or the command failed:
nothing is recorded) or **error** (the source could not be read: nothing is recorded). The command exits 1 if anything drifted.

**Where the result goes.** Each check is recorded in a `.facts.yaml` beside the page (commit it, as you do `.waxseals.yaml`), and the day is written into the block as `last_checked`.

## Drift and seals

A fact that drifted ends every review of its page made before it: `seal check` reports `a cited fact drifted after it was reviewed`. Correct the claim, and have a person review the page again; a review
made after the drift holds, and a later check that passes does not undo the drift.

A check writes `last_checked`, and `fix` and `fact` write `id`. Neither breaks a seal: a review is of the page **without** its facts' `id` and `last_checked` and without an empty `{}`, so numbering a
fact or checking it leaves the review in place. Everything else in a block is part of what the person reviewed.

## Showing facts

The docs build ([status badges](badges.md)) and [`serve`](serve.md) show each block as its claim and a **badge** of its last check (not yet checked, checked on a date, or drifted). The badge links to an
entry in the page's **bibliography**: at the bottom of a built page, and on the Facts tab of the right-hand pane in `serve`. Each entry has the kind, source, state, line, claim and metadata, and says
when the fact is due for a check.

## Settings

In the root `bower.yaml`:

```yaml
facts:
  mcp:                 # the only MCP calls a check may make
    jira: {tool: get_issue, arg: issue_key, watch: fields.status.name}
  types:               # a kind of fact for one tool: the source is just the key
    ticket: {server: jira, tool: get_issue, arg: issue_key, watch: fields.status.name}
  scripts:             # the fact pack's `script` kind: an argument list, run with no shell
    uvver: {cmd: [uv, --version]}
  manual_days: 90      # the pack's `manual` kind: skip the question for this many days after a yes
```

A page never names a command or a tool, only a key; only the root `bower.yaml` declares them. `bowerbird-mcp create --facts` writes a commented block to start from.

## What `lint` says

| Finding | Meaning |
|---|---|
| `unclosed_fact`, `stray_fact_end` | an opening tag with no `[fact.end]`, or an end with no start |
| `unknown_fact_kind` | a kind nobody registered (for a pack kind, it says to install the pack) |
| `bad_fact` | a source the kind cannot read, no words to check, or metadata that never closes |
| `bad_fact_meta` | a wrong value in a key that has a meaning (a warning) |
| `duplicate_fact_id` | two facts on one page with the same number |
| `undeclared_fact_source` | an `mcp` fact whose server is not declared under `facts.mcp` (a warning) |

## The older forms

- A block with no metadata, as in 2.2.0, still reads and checks.
- In an [OKF](formats/okf.md) concept, `fact` with a `resource` and no `claim` records a frontmatter `sources` entry and prints a footnote marker. `okf export` and `okf import` move those to and from the blocks and
  `.facts.yaml`.

## Report a problem

A fact that checked wrong, a drift that should not be, or a block that would not read: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to
[dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Give the kind, the version (`bowerbird-mcp --version`) and the smallest page that shows it, never a private one. More on
[reporting a problem](troubleshooting.md#reporting-a-problem).
