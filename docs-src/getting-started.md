# Getting started

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command on this page was run for real. Long output lines are shortened, and the person sealing in the examples is a made-up user called `example`. -->

In about ten minutes you will turn a folder into a collection, ask it a question and get an answer with the file and
line to cite, have a person seal a file so a changed file is never mistaken for a reviewed one, and connect an AI
assistant. You do not need to know anything about AI tooling to start, and nothing here sends your files anywhere.

## What this is, in plain words

A **collection** is a folder of files you want to keep in order: notes, decisions, vocabularies, even code. Bowerbird
looks after it for three kinds of user:

- **A person at a terminal** can search the collection and seal files. No AI involved.
- **An AI assistant** (through MCP, the protocol assistants use to call tools) can look things up and answer from them,
  saying which file and line it used and whether a person has reviewed it.
- **CI**, your automated checks, can fail a change that has no human review.

It is not tied to one format. A `format:` line in `kbmcp.yaml` says what a folder holds: Markdown, ADR, OKF, SKOS or
seal-only. [Formats](formats.md) shows each one. This page uses plain Markdown as the example: it asks nothing of your
files, and it does more than seal them, because it searches them too. Use whichever is right for you.

## 1. Install uv

The tool runs through [uv](https://docs.astral.sh/uv/), a fast Python launcher. If you do not have it:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

There is nothing else to install and nothing to clone. Make a shortcut so the rest of this page is short:

```sh
alias kb='uvx bowerbird-mcp'
kb help          # the everyday commands for your format; `kb help all` lists every one
kb help seal     # one command: what it does, its arguments, an example
```

## 2. Choose what it holds

A collection holds one kind of thing, and you say which when you make it. Pick the one that fits what you keep:

| `holds=` | Use it for |
|---|---|
| `markdown` | notes, runbooks, wikis, docs: any Markdown, with nothing to add to your files |
| `adr` | decision records (ADR or MADR), with each record's status |
| `okf` | knowledge that says where it came from, who checked it and when it expires, with the full toolset |
| `skos` | glossaries, vocabularies and thesauri |
| `seal-only` | any text files (code, configuration) with nothing searched: just a guaranteed human review of each |

Leave `holds=` out and `init` guesses from the folder, then asks you for what it cannot know. The choice is written to
`kbmcp.yaml` as `format:`, and you can change it later by editing that line. [Formats](formats.md) shows what each one
looks like and what each can do. The examples on this page use `markdown`.

## 3. Make a collection

Any folder of files will do. Make a small one:

```sh
mkdir notes && cd notes
echo '# Deploy

Run the deploy script, then check the dashboard. If something looks wrong, follow [the rollback steps](rollback.md).' > deploy.md
echo '# Rollback

To roll back a release, redeploy the previous tag, then confirm the dashboard is green. Back to [Deploy](deploy.md).' > rollback.md
```

Then make it a collection:

```sh
kb init -t markdown -a "Team notes." --apply
```

```text
edited: {}
config: {"files": ["kbmcp.yaml", ".env", "env.example", ".mcp.json"], "missing": [], "gitignore": "not a git work tree"}
```

At a terminal a command prints readable lines. Piped, in a script or in CI it prints JSON; `-O text` or `-O json` (checks
also take `github` and `sarif` for CI) overrides either. That is only about how the answer is printed, and has nothing to do
with a collection's format. Every flag has a `name=value` form too (`holds=markdown` is `-t markdown`), which is what scripts
and AI assistants use; `kb help init` lists both.

Your notes are not touched. `init` wrote the collection's settings:

- `kbmcp.yaml`: the collection's own configuration, with its `format`. Commit it.
- `.mcp.json`: how an AI assistant starts the tool for this folder. Commit it too (see step 6).
- `env.example` lists every personal override, and `.env` holds your id from `KB_USER` or your git email. `.env`
  stays out of git.

If you leave `holds=` or `about=` out, `init` asks (at a terminal, or in a prompt over MCP) for what it cannot know:
the format, a sentence on what the folder holds, and your id.

## 4. Search it

Bowerbird has three kinds of search, from the most predictable to the smartest. Use whichever fits the question.

| | **Deterministic** | **Ranked-result** | **Semantic** |
|---|---|---|---|
| **Command** | `search` | `passages` | `passages`, with `semantic: true` |
| **Finds** | whole files holding every word you typed | the best sections for a question | sections that mean what you asked |
| **Same answer every time** | yes | yes | nearly: a different machine or library version can rank close calls differently |
| **Needs** | nothing | the search index, built on first use | the model download |

### Deterministic: `search`

Use it when you know the words. It returns the files that hold **every** word of your query, anywhere in the file:

```sh
kb search dashboard
```

```text
total: 2
hits:
  - bundle: ., file: deploy.md, title: Deploy, type: null, score: 1, matched: ["body"], line: 3, text: Run the deploy script, then check the dashboard. If something looks
  - bundle: ., file: rollback.md, title: Rollback, type: null, score: 1, matched: ["body"], line: 3, text: To roll back a release, redeploy the previous tag, then confirm
```

- **Matching is by substring, ignoring case.** A word matches anywhere inside the text, so `roll` finds `rollback`, and
  `kb search 'roll back'` also lists `deploy.md`, which links to `rollback.md`.
- **The score says where the words landed.** Each field a word matches adds its weight: title 5, file path 4, tags 3,
  type 2, description 2, body 1. `matched` lists the fields, so a hit explains itself. In plain Markdown there are no tags,
  type or description, so only the title (the first heading), the path and the body count.
- **The same query on the same files always gives the same answer.** There is no index and no model, and ties come out in a
  fixed order. That makes it the one to script and to test against.
- **Narrow it with filters:** `type=`, `tag=`, `dir=`, `fields=` (look only in some fields: `fields=title` finds only files
  titled `Deploy`), and `limit=` and `offset=` to page through a long list.

On an MCP server, `search` is offered for `okf` collections. The other formats offer `passages`. At the command line `search`
reads any folder of Markdown, but it cannot see SKOS files.

### Ranked-result: `passages`

Use it for a question. It cuts every file into sections at its headings and returns the **sections** that best answer it,
best first:

```sh
kb passages 'how do I undo a bad release'
```

```text
total: 1
gap: false
hits:
  - bundle: ., file: rollback.md, line: 2, heading: Rollback, match: 100, title: Rollback, type: null, status: stable, tier: unverified, stale: false, links: 1, text: To roll back a release, redeploy the previous tag, then confirm the dashboard is gr...
```

The first `passages` also builds a small search index in a `.kbmcp/` folder beside your files. It is a cache: safe to delete,
and it ignores itself in git.

For each section you get:

- **file and line**, so an answer can say exactly where it came from;
- **match**, a percentage of the *best hit's* score. The top hit is always 100, so read it as "how the others
  compare", not "how good the best one is";
- **tier** and **stale**, so a reader knows whether a person has reviewed the file and whether it has changed since
  (step 5);
- **links**, how many other files link to this one;
- **gap: true** when nothing matches at all. That is a real answer: the collection has nothing on the subject, and
  an assistant should say so, not guess.

Unlike `search`, one word is enough to match, and **rarer words count more**, so a question does not have to be phrased
exactly. The title, tags, type and description count too, and a file many others link to ranks a little higher. It does
not know that "revert" means "undo": for that, there is semantic search.

### Semantic: find what you meant

By words alone, a search for something you wrote differently finds nothing:

```sh
kb passages revert
```

```text
total: 0
gap: true
hits: []
```

Semantic search also matches by **meaning**. Turn it on in `kbmcp.yaml` (or for your machine only, with `KB_SEMANTIC=true`
in `.env`):

```yaml
semantic: true
```

```sh
kb passages revert
```

```text
total: 1
gap: false
hits:
  - bundle: ., file: rollback.md, line: 2, heading: Rollback, match: 100, title: Rollback, type: null, status: stable, tier: unverified, stale: false, links: 0, text: To roll back a release, redeploy the previous...
```

`rollback.md` never says "revert", and now it is found. The two rankings, words and meaning, are combined, and a passage
must be at least `min_similarity` close in meaning (0.6 by default) to count.

- **The model downloads once.** It is `BAAI/bge-small-en-v1.5`, about 65 MB, fetched into `~/.cache/bowerbird-mcp/models`.
  That download is the only network use in the whole tool: after it, searching runs on your machine and nothing leaves it.
- **The first search takes a moment,** because every passage is embedded. On a large collection that takes minutes, and an
  interrupted run resumes. `kb reindex` does it ahead of time (a good fit for a hook), and `kb reindex --info` shows
  what is held: here `passages: 2`, `vectors: 2`, `vectors_model: BAAI/bge-small-en-v1.5`.
- **`uvx bowerbird-mcp` carries what it needs** (the `fastembed` library). The bare one-file script needs
  `uv run --with fastembed`.
- **For tens of thousands of passages,** `vector_index: sqlite-vec` or `hnsw` makes the meaning search faster: see
  [the guide](guide.md#reading-the-collection).
- **It applies to** `markdown`, `adr`, `okf` and `skos`. `seal-only` searches nothing, so it has no use for it.

## 5. Seal a file

Every hit says `tier: unverified`: nobody has said a person looked at these files. A **seal** is a person's review of
one exact version of a file. At a terminal, `--attest` records you:

```sh
kb seal deploy.md --attest
```

```text
edited: {".": [".waxseals.yaml"]}
file: deploy.md
sha256: ad8a91f41bd95de8219914500b961592af12670328c1af7743577ea7ecb108ad
bowerbird: 2.0.0
tier: human-reviewed
```

The review goes into `.waxseals.yaml` (commit it), and your file is not touched:

```yaml
- {file: deploy.md, sha256: ad8a91f41bd95de8219914500b961592af12670328c1af7743577ea7ecb108ad, by: 'human:example', at: '2026-11-16T15:29:29Z', bowerbird: 2.0.0}
```

One line per file, and only the latest seal is kept: seal it again and the line is replaced (git has the earlier ones).

Search now shows the difference: `deploy.md` is `tier: human-reviewed`, and `rollback.md` is still `unverified`.

Like a wax seal, a review breaks when the file changes. Edit `deploy.md` and check:

```sh
echo "Also tell the team in chat." >> deploy.md
kb seal -c
```

```text
deploy.md: error: stale_signature: edited since it was reviewed | fix: review it again: seal deploy.md
rollback.md: error: unsigned: no review by a human | fix: a human reviews it: seal rollback.md
bowerbird-mcp seal: FAILED: 2 file(s) checked, 2 finding(s)
```

The `sha256` ties the review to the file's exact contents, so an edited file can never pass for a reviewed one, and `passages` shows
it as `unverified` and `stale` until a person reviews it again. `-c` (`--check`) changes nothing and exits with a failure
code, which is what makes it useful in a hook or in CI (step 7).

A person's review is only ever recorded with that person's own confirmation: `--attest` at their terminal, or a
prompt over MCP. An AI assistant can seal as itself (`by=process:<id>`), never as a person. These tiers are advisory
labels, not access control: the guarantee is only as strong as who can write to the repository, so protect `.waxseals.yaml`
and `kbmcp.yaml` with `CODEOWNERS` or branch protection.

## 6. Connect an AI assistant

`kb init` wrote a `.mcp.json` at the root of the collection. **Commit it**: anyone who clones the repository then has the
tools, with nothing to set up on their own machine (Claude Code asks once to approve a project's server; `/mcp` shows
it). The collection is the repository: its settings, its reviews and its client configuration all travel with it.

If your folder has no `.mcp.json`, or you use another assistant, add the tool to your assistant's servers file
(`.mcp.json` in your project for Claude Code; the same entry works in `claude_desktop_config.json` for Claude Desktop and
`.cursor/mcp.json` for Cursor):

```json
{
  "mcpServers": {
    "notes": {
      "command": "uvx",
      "args": ["bowerbird-mcp",
               "--config", "/full/path/to/notes/kbmcp.yaml"]
    }
  }
}
```

Restart the assistant (in Claude Code, `/mcp` reconnects). It now has the tools and a short instruction on how to use
them: look at `passages`, cite the file and line, and say so when the answer is a gap or the file is unverified or stale.
Open `kbmcp.yaml` and check `about:`; the assistant is told it, which matters most when you load several collections.

An OKF collection gets all 35 tools, about 7,250 tokens of tool definitions (an estimate: each tool's name, description
and argument schema, in characters divided by four) before the assistant has said a word. Give each assistant only what
it needs with a role: `"--role", "read"` (find and read only, 10 tools, safe to auto-approve), `write`, `structure`,
`lifecycle` or `seal` (record a human's review). The first four are each about a quarter of the total. [The
guide](guide.md#roles-a-smaller-tool-list-per-agent) has the tool lists. You can load several different collections side
by side, each with its own `--config`.

### Which Bowerbird does Claude run?

There can be two on one machine: the one the project's `.mcp.json` starts (the project's own choice, usually pinned to a
version), and one you installed and registered for yourself, for every project (`claude mcp add -s user bowerbird -- uvx
bowerbird-mcp`). If both are called `bowerbird`, **the project's wins**: Claude Code's documentation ranks a local entry
first, then the project's `.mcp.json`, then your user-level one, and uses the winning entry whole, without merging.

To use your own instead, switch the project's off **for you only**, without touching the committed file. In
`.claude/settings.local.json`, which is personal and not committed:

```json
{
  "disabledMcpjsonServers": ["bowerbird"]
}
```

Claude then skips the project's entry and uses the user-level one. To see which entry a name resolves to and exactly what
it would run, ask Claude Code:

```sh
claude mcp get bowerbird
```

```text
bowerbird:
  Scope: Project config (shared via .mcp.json)
  Status: ✘ Rejected (see disabledMcpjsonServers in settings)
  Type: stdio
  Command: uvx
  ...
```

The `Scope:` line says where the entry came from, and `Command:` is what would start. A project's server also needs your
approval the first time Claude Code sees it, and shows `Pending approval` until you run `claude` and say yes.

## 7. Check it

Bowerbird is also a checker. Two commands read a collection and **exit with a failure code when something is wrong**, so
anything that can run a command can use them: your terminal, an editor task, a script, a scheduled job, CI, a git hook.
Nothing about them needs git.

| Command | It checks | For |
|---|---|---|
| `lint` | the form of every file: a header, links that resolve, no empty files, no duplicate titles, no secrets that look like keys, index and log files well formed | `okf` |
| `seal -c` | that a person has reviewed the current version of every file the policy requires | every format |

Each finding names the file, what is wrong and how to fix it, and a last line says the check ran, whether it passed or not.
The exit code is 0 when clean, 1 when there are findings, and 2 for a usage error. `seal -c` you met in step 5.

### Run it

```sh
kb lint
```

```text
bowerbird-mcp lint: ok: 1 concept(s) in 1 bundle(s) checked, 0 finding(s), conformant: True
```

Add a file that breaks the rules and run it again:

```text
old1.md: error: no_frontmatter: no frontmatter (§4) | fix: start the file with a `---` block holding at least `type:`
bowerbird-mcp lint: FAILED: 2 concept(s) in 1 bundle(s) checked, 1 finding(s), conformant: False
```

Some problems are purely mechanical (a stale table of contents, inconsistent tag spelling), and `kb fix --apply`
repairs those for you.

### Adopt it on an existing collection

A collection with years of old problems would fail every check on day one. Take a snapshot of today's findings, and only
**new** ones fail from then on:

```sh
kb baseline --apply
```

```text
findings: 1
path: .okf-baseline.json
written: true
```

```sh
kb lint -b .okf-baseline.json
```

```text
bowerbird-mcp lint: ok: 2 concept(s) in 1 bundle(s) checked, 0 finding(s), conformant: False
```

The old file is still not conformant (`conformant: False` says so), but it no longer fails the check. Add another bad file
and it does:

```text
new1.md: error: no_frontmatter: no frontmatter (§4) | fix: start the file with a `---` block holding at least `type:`
bowerbird-mcp lint: FAILED: 3 concept(s) in 1 bundle(s) checked, 1 finding(s), conformant: False
```

### Narrow it

- `--since origin/main` (`-S`) checks only the files changed since that ref, which suits a pull request. It is the one option that
  needs git.
- `--only stub,island` keeps just those kinds of finding, and `--ignore` (`-i`) drops some.
- Name files or folders (`kb lint notes/a.md docs/`) to check just those.
- `--scope okf` is the format's own rules; `--scope house` is the tidiness rules on top.
- A `kbmcp.nolint` file lists files to skip, in `.gitignore` syntax.

### Where to run it

- **By hand, or as an editor or build task.** It is just a command.
- **In CI.** `-O github` turns each finding into an annotation on the pull request, and `-O sarif` feeds code
  scanning:

  ```text
  ::error file=new1.md,title=no_frontmatter::no frontmatter (§4) | fix: start the file with a `---` block holding at least `type:`
  ```

- **On a schedule**, such as a nightly job that reports what has drifted.
- **As a git hook.** One option among these. With [pre-commit](https://pre-commit.com/), in `.pre-commit-config.yaml`:

  ```yaml
  repos:
    - repo: local
      hooks:
        - id: bowerbird-lint
          name: Bowerbird lint
          entry: uvx bowerbird-mcp lint -O text
          language: system
          pass_filenames: false
          verbose: true
        - id: bowerbird-seal
          name: Bowerbird seal check
          entry: uvx bowerbird-mcp seal -c -O text
          language: system
          pass_filenames: false
          always_run: true
          verbose: true
  ```

  Keep the hooks you use: `lint` is for OKF collections, `seal check` for any. `verbose: true` makes pre-commit print the
  verdict line even when the check passes. What `seal check` requires is the `seal` key in `kbmcp.yaml`: by default every
  file in the collection needs a person's review.

[The guide](guide.md#ci) has full workflows for GitHub Actions, baselines and pull requests.

## Where next

- [Formats](formats.md): what each kind of collection looks like.
- [The guide](guide.md): layout, settings, sealing, CI and every setting in `kbmcp.yaml`.
- [Command line](cli.md): flags, short flags, output and exit codes. Everything above works with no AI at all.
- [Tools](tools.md): every command, with its arguments and examples.
- [Troubleshooting](troubleshooting.md): when something does not behave.
- [OKF](formats/okf.md): what the richest format is and why it is built this way.
