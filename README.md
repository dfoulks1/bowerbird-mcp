<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
            srcset="https://raw.githubusercontent.com/dfoulks1/bowerbird-mcp/main/docs-src/img/logo-dark-v2.svg">
    <img src="https://raw.githubusercontent.com/dfoulks1/bowerbird-mcp/main/docs-src/img/logo-readme.png"
         alt="Bowerbird: a bower of sticks rising from an open book, with a small bird" width="260">
  </picture>
</p>

# Bowerbird

Keep a folder of Markdown notes in order, and let an AI assistant, a script or
you search and check them. It is for anyone who keeps notes, runbooks or documentation
as Markdown in a folder or repository. It works on collections in [Open Knowledge Format][okf]
(OKF) v0.2: one Markdown file per *concept*, each starting with a small header of
facts (its type, a description, where it came from, who checked it). A *bundle* is
a folder of concepts; a collection is a bundle, or a folder of bundles.
It is not tied to one format: one `format:` line in `bower.yaml` points it at other
formats too ([Formats](#formats)).

It is an MCP server (MCP, the Model Context Protocol, is how AI assistants call
tools) and a command line. It
checks, maintains and imports concepts, and finds the passages that answer a
question. It cares how a concept is written, never what it says. Local files only,
no network (but see semantic search, which downloads a model once). Never writes
to git. One contract, three users: an agent over MCP, CI, and a person, at a
terminal or in a browser, with no AI.

Try it (needs [uv](https://docs.astral.sh/uv/); its installer is `curl -LsSf
https://astral.sh/uv/install.sh | sh`, which downloads and runs a script, so read it first
if you prefer). Install the tool once with `uv tool install bowerbird-mcp`, or put `uvx` in front of any command below. In an
empty folder:

```sh
bowerbird-mcp create apply=true output=text
bowerbird-mcp create deploy type=Playbook title="Deploy" description="How we deploy." \
   body="Run the deploy script, then check the dashboard. To roll back, redeploy the previous tag." output=text
bowerbird-mcp passages 'how do we roll back' output=text     # the best passages, with file and line
bowerbird-mcp lint output=text                               # ends: bowerbird-mcp lint: ok: ...
```

Run with no arguments at a terminal, `bowerbird-mcp` prints the help and, in a folder with no `bower.yaml`, offers to make a
knowledgebase there. `new` starts a document from a template (`okf`, `markdown` or `adr`, by what the folder holds):
`bowerbird-mcp new notes/deploy -t markdown -T "Deploy"`.

Prefer a browser to a terminal? `uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve start` opens the collection at
`http://127.0.0.1:26937/` to browse, search, edit and seal, with no AI involved (see [Serve](https://bowerbird.voltpop.com/serve/)).

Personal project. Apache-2.0 (see [LICENSE](https://github.com/dfoulks1/bowerbird-mcp/blob/main/LICENSE); [NOTICE](https://github.com/dfoulks1/bowerbird-mcp/blob/main/NOTICE) credits the
spec), built under the [ASF generative-tooling guidelines][asf-gt]. Bugs and ideas:
[GitHub Issues](https://github.com/dfoulks1/bowerbird-mcp/issues) or dfoulks@voltpop.com; security reports: [SECURITY.md](https://github.com/dfoulks1/bowerbird-mcp/blob/main/SECURITY.md).

<!-- --8<-- [start:run] -->
## Run

Requires [uv](https://docs.astral.sh/uv/). There is nothing to clone. Two ways to run it, from PyPI:

| | Command | Use it for |
|---|---|---|
| **On the fly** | `uvx bowerbird-mcp <command>` | trying it, scripts, CI, an MCP entry in `.mcp.json` |
| **Installed** | `uv tool install bowerbird-mcp`, then `bowerbird-mcp <command>` | daily use at a terminal |

`bowerbird` is a shorter name for the same command, installed with it: `bowerbird status` == `uvx bowerbird-mcp status` == `uv run bowerbird_mcp.py status` (from a checkout). With `uvx` always write `bowerbird-mcp` (`uvx bowerbird` is another package). And `pip install bowerbird-mcp` works too. The basics, either way:

```sh
uvx bowerbird-mcp help                          # the everyday commands; `help all` lists every one, `help <tool>` one
uvx bowerbird-mcp                               # no arguments, at a terminal: the help, and an offer to make a knowledgebase here
uvx bowerbird-mcp status                        # what is in the collection
uvx bowerbird-mcp passages 'how do we deploy'   # the best sections, with file and line to cite
uvx bowerbird-mcp new notes/deploy              # a new document from a template
uvx bowerbird-mcp seal check=true               # which files lack a human review
uvx bowerbird-mcp --config ~/notes status    # a collection elsewhere: --config (before the command) takes a bower.yaml or its folder
uv tool upgrade bowerbird-mcp                   # update an installed tool (uv tool uninstall bowerbird-mcp removes it)
uvx bowerbird-mcp@2.2.0 --version               # pin a version
```

If `uv tool install` says its `bin` folder is not on your `PATH`, run `uv tool update-shell` once.

### Extras

The base install is small: search, lint, seal, the MCP server and the CLI. Anything heavier is an extra you ask for:

| Extra | Adds | You need it for |
|---|---|---|
| `serve` | `markdown` | `serve`, the browser UI |
| `syntax` | `pygments` | highlighted code files in `serve` (use with `serve`) |
| `semantic` | `fastembed` (about 150 MB; the model, about 65 MB, downloads once) | `semantic: true`, matching passages by meaning |
| `skos` | `rdflib` | `format: skos` |
| `sqlite-vec` | `sqlite-vec` | `vector_index: sqlite-vec` |
| `hnsw` | `hnswlib` | `vector_index: hnsw` |
| `seal-extensions` | the add-on `bowerbird-seal-extensions` | `seal: {extensions: true, quorum: 2}`: several people seal one version, with a quorum |

Ask for one, or several, in the same places:

```sh
uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve start        # on the fly
uv tool install 'bowerbird-mcp[serve,semantic]'                    # installed; run it again with other extras to add them
pip install 'bowerbird-mcp[serve]'                                 # pip
```

**`--extra` and `--with` are different things.** An *extra* is a named bundle the package declares (`serve` is `markdown`, `semantic` is
`fastembed`, and so on). `--with` adds any package you name yourself, at any version, whether or not Bowerbird lists it as an extra. Which
flag you use depends on how you run the command:

| How you run it | An extra | A package you name |
|---|---|---|
| `uv run`, in a checkout | `uv run --extra serve --extra semantic bowerbird_mcp.py status` | `uv run --with markdown --with fastembed bowerbird_mcp.py status` |
| `uvx`, from PyPI | `uvx --from 'bowerbird-mcp[serve,semantic]' bowerbird-mcp status` | `uvx --from bowerbird-mcp --with markdown --with fastembed bowerbird-mcp status` |
| installed once | `uv tool install 'bowerbird-mcp[serve,semantic]'` | `uv tool install bowerbird-mcp --with markdown --with fastembed` |

- In `uvx`, `--from` says which package provides the command (and which of its extras), and `--with` adds more packages to the same
  one-off environment. `uvx` has no `--extra` flag: the extra goes in brackets on `--from`.
- `uv run --extra` reads the extras from a `pyproject.toml`, so it needs a checkout. `--with` works anywhere, including the bare script.
- Prefer the extra: it is what Bowerbird says it needs, so it stays right if an extra's contents change. Use `--with` for something no
  extra covers (a backend you bring yourself) or to pin a version (`--with 'markdown<4'`).
- In an MCP config the two look like this: `"args": ["--from", "bowerbird-mcp[semantic]>=2,<3", "bowerbird-mcp"]`, or
  `"args": ["--from", "bowerbird-mcp>=2,<3", "--with", "fastembed", "bowerbird-mcp"]`.

A feature that needs an extra you did not ask for stops with a message that names it.

In the examples below, `uv run bowerbird_mcp.py ...` means the same command run
from a checkout of this repository (or beside a saved copy of that one file).
To run the latest unreleased code instead of the PyPI release, give uv the repository:
`uvx --from git+https://github.com/dfoulks1/bowerbird-mcp bowerbird-mcp help`.

### Settings: bower.yaml

*Renamed in 2.2.0; the old names were dropped in 2.3.0.* The file was `kbmcp.yaml`, the variables began `KB_`, the lint skip file was `kbmcp.nolint`, and the index cache was
`.kbmcp/`. A `kbmcp.yaml` with no `bower.yaml` beside it now stops the run (`git mv kbmcp.yaml bower.yaml`); the `KB_*` variables, `kbmcp.nolint` and
`kb-index` markers are no longer read. Delete the old `.kbmcp/` folder.

A `bower.yaml` is the collection's configuration. Commit it. The collection's root is the outermost one at or above
the current directory, inside the same git work tree (a repository inside another is its own collection), or you
name one with `--config`, so a server needs no env block. `--config` takes the file or the folder holding it, from
anywhere: a relative path, or `~`, not only a full path. A `bower.yaml` in a folder below the root overrides the
root's for that folder and everything under it ([mixed formats](#mixed-formats-in-one-collection)).
`create` writes a mostly filled-in one (see below); `config apply=true` writes the all-commented example, and
neither overwrites a file. The old `BOWERBIRD_ROOT` variable is gone and is refused: the base is wherever `bower.yaml` is.

```yaml
about: Engineering runbooks.   # shown to the agent; tells collections apart
user: your-id         # your id in confirmation prompts: personal, prefer BOWERBIRD_USER in .env
ai_producers: [zed]   # extra AI names for the provenance check (BOWERBIRD_AI_PRODUCERS)
passages: true        # false removes the passages and reindex tools
format: okf           # okf | adr | markdown | skos | asciidoc | seal-only: what the folder holds (see Formats)
hubs: true            # concepts many others link to rank a little higher
semantic: false       # also match by meaning (see Reading the collection)
semantic_model: BAAI/bge-small-en-v1.5
min_similarity: 0.6   # how close in meaning a passage must be
vector_index: scan    # scan | sqlite-vec | hnsw: how semantic search finds neighbours
index: .bower/index.db   # one SQLite file: passages, BM25, links, vectors; "" = memory
build: auto           # auto: passages keeps the index current; manual: only `reindex`
roles: [read, write, structure, lifecycle, seal]   # roles the server may offer (see Register)
seal: {exempt: [], exempt_status: [proposed, draft]}   # files seal check leaves out (see Sealing)
```

### Overrides: .env and the environment

`bower.yaml` is shared, so what is yours alone does not go in it. [`env.example`](https://github.com/dfoulks1/bowerbird-mcp/blob/main/env.example)
lists every override as a `BOWERBIRD_<KEY>` variable (`BOWERBIRD_USER`, `BOWERBIRD_ABOUT`, `BOWERBIRD_SEMANTIC`, `BOWERBIRD_VECTOR_INDEX`, `BOWERBIRD_BUILD`,
and so on; lists are comma separated). Copy it to `.env` beside `bower.yaml` and uncomment what you change: `.env` is
not committed (`create` and `config` list it in `.gitignore`). Precedence, last wins: `bower.yaml`, then `.env`, then
real environment variables. `format` is the collection's own and no override touches it. `BOWERBIRD_ROLE` (singular)
is the same as `--role`.

`create` fills in what it can: `format` is guessed from the folder (thesaurus files mean `skos`, `.adoc` files mean
`asciidoc`, mostly numbered or `adr/decisions` Markdown means `adr`, other Markdown with no OKF types means `markdown`,
else `okf`), and it asks for what it cannot know: `about`, your `user` id (kept in `.env`)
and `holds` (the format, to confirm). Over MCP it asks the human with a prompt; at a terminal it asks on the
command line; or pass them (`create about="Runbooks." holds=markdown user=you apply=true`). Only an `okf` folder
gets a first bundle.

### The index

With no `bower.yaml` the defaults apply. The index is a cache derived from
the concepts: safe to delete, never committed (a new `.bower/` folder ignores
itself). To build it apart from the server, run `reindex` (incremental: only
changed files are read) and set `build: manual`, so `passages` only reads it:

```sh
uvx bowerbird-mcp reindex output=text     # first semantic run embeds everything: minutes, once
```

```yaml
# .pre-commit-config.yaml: refresh after you commit and after pulls
repos:
  - repo: local
    hooks:
      - id: bowerbird-reindex
        name: Bowerbird reindex
        entry: uvx bowerbird-mcp reindex
        language: system
        pass_filenames: false
        always_run: true
        verbose: true
        stages: [pre-commit, post-merge, post-checkout]
```

### Where tools look

A collection is where its `bower.yaml` is: the tool looks for one from the
current directory up (or takes `--config path/to/bower.yaml`) and treats that
file's folder as the base. With none, it uses the current directory. In an `okf` collection it is one bundle at its root, or a set of sibling bundles (other formats are just the folder). A
directory whose `index.md` declares `okf_version` is a bundle root; bundles do
not nest. An `index.md` at the collection root lists its bundles (`index
apply=true` there writes it), and tools find the root from inside a bundle
through it. `bundles` lists them, `split` makes a directory its own bundle,
`rename` moves or renames one, `migrate` moves a concept between bundles,
`archive` and `unarchive` retire and restore a concept or a whole bundle,
`ingest keep_okf=true` merges one in, and `upgrade` converts OKF v0.1.

Tools follow where you are: in a bundle, that bundle; at the collection
root, every bundle (`lint`, `fix`, `baseline`, `status`, `list`, `search`,
`factcheck`). Name files or directories to lint just those
(`lint notes/a.md docs/`). Files are named the OKF way: a bundle and the
path within it (`bundle=eng file=runbooks/deploy.md`), in every input and
output. On the command line, without `bundle=`, paths are relative to where
you are. Write tools act in the bundle the file belongs to. In a git work
tree, files git ignores are skipped.

### Running a tool

```sh
wget https://raw.githubusercontent.com/dfoulks1/bowerbird-mcp/main/bowerbird_mcp.py
uv run bowerbird_mcp.py help                 # the everyday commands for your format
uv run bowerbird_mcp.py help all             # every tool, one line each
uv run bowerbird_mcp.py help move            # one tool: what it does, its arguments
uv run bowerbird_mcp.py lint output=text
uv run bowerbird_mcp.py create apply=true       # start a new bundle
```

Any tool runs as `<name> name=value ...` or `<name> '<json object>'`. Flags work
the same way, for people: `create -t markdown -a "Docs" --apply`, `seal -cp`,
`-h` for a command's flags. They become the same `name=value` arguments (they
are not abbreviated: `--app` is not `--apply`). At a terminal the output is
text; piped, in CI or in a script it is JSON; `-O json|text|github|sarif` (or
`-F`, or `output=`) chooses. The daily commands have fixed short flags; the
others take the first free letter, so use their long flags in scripts. Bare
arguments fill the required ones in order (`move a.md b.md`); on `set`, any
other `key=value` is frontmatter (`set a.md status=deprecated tags=[x,y]`).
Write tools that touch many files default to `apply=false` and show a diff.

`--attest` records you, as `human:<BOWERBIRD_USER>` (else your git `user.email`), on
`new` and `provenance` (`generated`) and `seal`
(`verified`). It exists
only on the command line: no MCP call can pass it.

Output is JSON; `output=text` prints one key per line and diffs as is.

Exit codes: 0 ok, 1 findings, 2 usage error.

<!-- --8<-- [end:run] -->
## Formats

<!-- --8<-- [start:formats] -->
Bowerbird is not tied to one format. `format` in `bower.yaml` says what a folder holds, and the same
search, index and review tools work across them.

- `okf` (the default): [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/bad9bdbafa82c672b00d437d4f2cc8f17e9e5f58/okf/SPEC.md) bundles. Every tool is available.
- `adr`: ADR and MADR decision records. Every Markdown file is a record (except `README.md` and `index.md`), whatever
  its name or folder, and no frontmatter is needed. A hit gets type `adr` and its `status`, read from MADR frontmatter,
  a `## Status` section (Nygard) or a `* Status:` line (MADR 2).
- `markdown`: any other folder of Markdown, no frontmatter needed; `index.md` and `log.md` are ordinary files. A
  numbered file name (`0007-use-queue.md`) or a path through `adr`, `adrs` or `decisions` still counts as an ADR.
- `asciidoc`: AsciiDoc (`*.adoc`, `*.asciidoc`), no frontmatter needed. One passage per section; the document header's
  `:name: value` attributes (or YAML front matter) are the metadata, and `xref:`, `link:` and `<<file.adoc#id>>` links count.
  `include::` is not followed.
- `skos`: SKOS thesauri as Turtle, RDF/XML, JSON-LD, N-Triples or N3 (`*.ttl`, `*.rdf`, `*.jsonld`, `*.nt`, `*.n3`;
  needs `pip install rdflib`). One passage per concept, headed by its broader chain, with its labels, notes and
  broader, narrower and related concepts in the text.
- `seal-only`: any text files (code, configuration), with nothing indexed or searched. Every file is checked; name the ones
  to leave out in `seal.exempt`. The one tool is `seal`, and `bowerbird-mcp seal check=true` fails when a file has no human
  review of its current version.

Outside `okf` a server offers only the tools that format uses: `passages`, `reindex` and `seal` for every format but
`seal-only` (just `seal`); `markdown` adds `get`, `search`, `dirs`, `links`, `list`, `status`, `heatmap`, `create` and
`config`; `adr` adds `move`; `asciidoc` adds `heatmap`. The command line always has every tool. A hit is `unverified`
until a human seals that exact file (see [Sealing](https://bowerbird.voltpop.com/sealing/)): reviews go in
`.waxseals.yaml`, not in the file. `create` guesses
the format from the folder, and the agent's instructions follow it.

<!-- --8<-- [end:formats] -->
<!-- --8<-- [start:layout] -->
## OKF layout

> **OKF only, and not required.** Everything in this section (bundles, `index.md`, `log.md`, the archive) is how an `okf`
> collection keeps its concepts in order. A `markdown`, `adr`, `skos`, `asciidoc` or `seal-only` folder needs only a
> `bower.yaml` and its files, in any layout you like.

```
notes/                       the collection (bower.yaml sits here)
  index.md                   lists the bundles; no frontmatter
  .gitattributes             log.md and index.md merge=union
  eng/                       a bundle
    index.md                 okf_version, then the list of its concepts
    log.md                   its history (§9)
    runbooks/
      index.md               optional: this directory's concepts
      deploy.md              a concept
  archive/                   the archive: a collection of its own, set apart
    index.md                 lists the archived bundles
    eng/old-runbook.md       archived from eng (archive/eng is a bundle)
```

### OKF index.md

OKF §8: an index lists what is in its directory, for progressive disclosure.
Every index has the same body shape, sections under headings with one entry
per item:

```markdown
# Engineering

Hand-written text is kept.

<!-- bowerbird-index:start (generated by bowerbird-mcp index; do not edit between the markers) -->

### runbooks

* [Deploy](./runbooks/deploy.md) - How we deploy.

<!-- bowerbird-index:end -->
```

- The tool owns what is between the markers and rebuilds it from frontmatter
  (title, else first heading, else file name; `description`, else the first
  sentence). Write anything else around them.
- **Collection root:** no frontmatter (it is not a bundle). The list has one
  entry per bundle, titled by that bundle's first heading. Tools find the
  collection by walking up from a bundle to the nearest `index.md` that links
  to it.
- **Bundle root:** frontmatter holds only `okf_version: "0.2"`, which is what
  makes the directory a bundle (§12). The list covers every concept, a section
  per top-level folder.
- **Any other directory:** no frontmatter. The list covers that directory's
  concepts and subdirectories (`index dirs=true` writes one everywhere).
- Being listed counts as being linked, so a listed concept is not an orphan.
- `get` synthesizes a missing index from frontmatter (§8 allows this).

### OKF log.md

OKF §9: date headings, newest first, one entry per line. Each tool write adds an
entry to the nearest `log.md` above the change, with a hidden unix-time stamp:

```markdown
## 2026-10-27

* <!-- 1761588000 --> **Update**: Moved deploy.md to [ship.md](/runbooks/ship.md).
```

`record "note"` writes one by hand (link the concept it is about). `log file=x.md`
reads a concept's history: the entries linking to it in every `log.md` above it,
and the git commits that changed it. `log` alone shows the bundle's recent
entries.

For an `okf` bundle `create` adds `log.md merge=union` and `index.md merge=union` to the
collection's `.gitattributes`, so git keeps both sides when parallel
branches log or index. After such a merge, `fix` merges duplicate log date
sections, orders stamped entries by time, and rebuilds the generated index
lists. A section with a
hand-written, unstamped entry keeps its order.

### The OKF archive

`archive/` is a collection within the collection, and a special one. Its
`index.md` lists its bundles, like the collection root's. `archive file=x.md
bundle=eng` moves a concept to `archive/eng/x.md` (starting `archive/eng` as a
bundle); `archive bundle=eng` moves the whole bundle to `archive/eng/`, still a
bundle. `unarchive eng/x.md` or `unarchive eng` puts them back. Links follow
both ways.

The live collection does not see the archive: lint, list, search, status
and web leave it out, nothing in it counts as nesting, and lint warns on links
into it (`archived_link`). Editing tools refuse archived concepts. That is the
only enforcement: the files are plain files, so an editor or a commit can still
change them. It works whether the collection root is a set of bundles or a
bundle itself.

### Mixed formats in one collection

One monorepo can hold several formats: an OKF bundle with a folder of ADRs, or a markdown collection with one. A
`bower.yaml` in a folder overrides the one above it for that folder and everything under it, key by key, the nearest one
winning, like an inherited ACL: the whole tree is OKF, and that one part is ADR.

```yaml
# bower.yaml, at the root
format: okf
```

```yaml
# adr/bower.yaml
format: adr
seal: {exempt: ["drafts/*.md"], exempt_status: []}   # its globs start at this folder
```

A folder may override `format`, `seal`, `about`, `hubs` and `min_similarity`. The rest (`roles`, `passages`, `index`,
`semantic`, `semantic_model`, `vector_index`, `build`) belongs to the whole collection, which has one index, one
ledger and one embedding model; a folder that sets one is refused, with the fix. Nested files are read once, at
startup, and found with `git ls-files`, so `.gitignore` is respected; restart the server after adding one.

**Bowers.** Instead of finding nested files by looking, the root can name them. Each folder with a `bower.yaml` of its own
that belongs to the collection is a *bower* (not an OKF bundle):

```yaml
# bower.yaml, at the root
format: markdown
bowers: [docs-src, adr/*]   # folders (globs are fine) that carry their own bower.yaml
```

- Only the listed folders override the root, so a stray `bower.yaml` is never picked up. A name that matches no folder
  with a `bower.yaml` stops with an error, which catches a typo.
- A bower ships with its own `bower.yaml`. Run on its own it is its own collection. Run inside the collection, the nearest
  folder above it whose `bowers` lists it is the root. A bower may set only `format`, `seal`, `about`, `hubs` and
  `min_similarity`; its other keys are ignored here (the root decides them), so one shipped alone can carry them.
- Without a `bowers` key the older rule applies and every nested `bower.yaml` is an override.
- With no root `bower.yaml` and no git repository, nothing below the folder is scanned.

What each tool does with the ADR folder inside an OKF bundle: `passages`, `search`, `list`, `status`, `links`, `web`
and `seal` include it, each file read in its own format (an ADR's status, its review in `.waxseals.yaml`). `lint`,
`fix`, `index`, `provenance` and `upgrade` leave it out, since they judge and rewrite OKF concepts. `move` and `migrate` still
rewrite links in it, and a moved ADR keeps its review. Links between the two work in both
directions. A server offers the tools of every format in use.

<!-- --8<-- [end:layout] -->
<!-- --8<-- [start:register] -->
## Register with an MCP client

`create` writes a `.mcp.json` at the root of the collection: commit it, and whoever clones the repository has the
tools with nothing to register on their own machine (Claude Code asks once to approve a project's server). It also
writes a `BOWERBIRD.md` of rules for the assistant (commit and edit it; never overwritten; [Agent rules](https://bowerbird.voltpop.com/agents/)). For
another client, or a folder without one, add this to the client's servers file: `.mcp.json` in the project for
Claude Code, `claude_desktop_config.json` for Claude Desktop, `.cursor/mcp.json`
for Cursor. VS Code's `.vscode/mcp.json` takes the same entry under `"servers"`.

```json
{
  "mcpServers": {
    "bowerbird": {
      "command": "uvx",
      "args": ["bowerbird-mcp"]
    }
  }
}
```

The server runs in the project folder, so it finds the `bower.yaml` there (your
id is `user:` in it). To point at one elsewhere, add `"--config",
"/path/to/collection/bower.yaml"` to `args`. Or, in Claude Code:

```sh
claude mcp add bowerbird -- uvx bowerbird-mcp --config /path/to/collection/bower.yaml
```

Several collections at once: one entry each, with its own `--config`. The
client prefixes tool names with the entry name, and each file's `about:` tells
the agent what that collection holds. Each keeps its own index.

The client loads the tool list at start. After editing the script, restart
the client or reconnect the server (`/mcp` in Claude Code).

### Files as resources

A client that lists MCP resources sees each file of the collection at `bowerbird://{bower}/{path}`: the bower is the folder that holds the
file's `bower.yaml` (the root is one, named by its folder), and the path is the file's path inside it, as the tools take it. Add
`?lines=10-20` for only those lines. They need the `read` role, and a dotfile, a link or a path outside the collection is refused.
`bowerbird://agent-rules` is the agent rules, and `okf://spec` the OKF specification (in a checkout).

### Roles: a smaller tool list per agent

All 34 tools cost an agent about 3,700 tokens of schema (an estimate: each tool's name, description and argument
schema as the client receives them, in characters divided by four); the first four roles are each about a quarter of that, and `seal` is one tool. Register the same
script more than once, each with a role (`--role`, or `BOWERBIRD_ROLE`; several with
commas), and each server offers only that role's tools:

| Role | Tools | Schema |
|---|---|---|
| `read` | find and read, nothing written: `dirs` `get` `heatmap` `links` `list` `log` `passages` `search` `status` `vocab` | 10, ~930 tokens |
| `structure` | shape, repair and reorganization: `archive` `bundles` `dirs` `ingest` `migrate` `move` `rename` `split` `unarchive` `web` | 10, ~880 tokens |
| `write` | write a concept and check it: `fact` `fix` `lint` `new` `record` `set` | 6, ~900 tokens |
| `lifecycle` | keep it current: `baseline` `config` `create` `factcheck` `index` `provenance` `reindex` `upgrade` | 8, ~880 tokens |
| `seal` | a human's review of a file, and the check for it: `seal` | 1, ~200 tokens |

```json
{
  "mcpServers": {
    "bowerbird-read":  { "command": "uvx", "args": ["bowerbird-mcp", "--role", "read"] },
    "bowerbird-write": { "command": "uvx", "args": ["bowerbird-mcp", "--role", "write"] }
  }
}
```

The `read` server is read-only, so a client can approve it without asking; the others
change files (`seal` only writes a review: a ledger entry, or a concept's own `verified` key). A tool can belong to more than one role (`dirs` is in `read` and
`structure`), and a server with no `--role` offers them all. With no `--role` the server offers every role that `roles:` in
`bower.yaml` leaves on; naming a role that is off refuses to start. Outside `okf` the format limits it further, to the tools
that format uses (see Formats). The CLI always has every tool.

<!-- --8<-- [end:register] -->
<!-- --8<-- [start:ci] -->
## Sealing: who reviewed what

`seal` is the one function for a human's review, in every format. It shows the human the exact file in a
prompt, asks for their id, and records who reviewed that version and when. Over MCP the human types their own id;
at a terminal `--attest` records you; in `serve` (the browser) a dialog asks the same two things; an assistant can only seal as itself (`by=process:<id>`), never as a human.
`verify` (the OKF word), and `ratify` or `accepted` (the ADR words), are its command-line names too.

- **`okf`:** a `verified: {by, at, sha256}` entry in the concept's own frontmatter.
- **`markdown`, `adr`, `skos`, `asciidoc` and `seal-only`:** one dense line per file in `.waxseals.yaml` at the collection root (commit it), holding only the latest
  review: file, sha256, who, when, `bowerbird` (the version that wrote it), and `decision=accepted|rejected` for an ADR. The file itself is never edited, so Nygard ADRs, MADR and
  thesauri all work.

Like a wax seal, a review breaks when the file changes, and only a new review makes a new one (it replaces the old line; git has the history). The sha256 covers the file's exact bytes (line endings normalized; for `okf`, without the `verified` key). Edit the
file after sealing and the seal is broken: `passages` shows the hit `unverified` and `stale`. A ledger decision
becomes the hit's `status`.

`seal check=true` changes nothing and exits 1 on findings, for a pre-commit hook and for CI (`since=origin/main`
limits it to a pull request's files):

- `unsigned`: a file has no review by a human.
- `stale_signature`: reviewed, then edited.
- `claims_accepted`: its own status says accepted, but no human reviewed it.
- `unreadable`: a file is not UTF-8 text, so it cannot be reviewed here (leave it out with `seal.exempt`).
- `orphan_signature`: a ledger entry for a file that is gone (a warning).

The policy is the `seal` key in the committed `bower.yaml` (nothing local can loosen it); every file
is checked, except those whose status is `proposed` or `draft`, and any file `exempt` names:

```yaml
seal: {exempt: [], exempt_status: [proposed, draft]}
```

`exempt` is a list of globs for files that need no review, such as a generated page: `exempt: ["/tools.md"]`.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: bowerbird-seal
        name: Bowerbird seal check
        entry: uvx bowerbird-mcp seal check=true output=text
        language: system
        pass_filenames: false
        always_run: true
```

Limits: a hook can be skipped (`--no-verify`), so run the same command in CI. `seal` proves a ledger entry exists
for these bytes, not who typed it: protect `.waxseals.yaml` and `bower.yaml` with `CODEOWNERS` or branch
protection so changes to them need a named reviewer. A SKOS file is sealed whole, not per concept.

## Before you push

```sh
uv run bowerbird_mcp.py lint output=text      # what's wrong, each with a fix
uv run bowerbird_mcp.py fix apply=true        # mechanical repairs, then re-lint
uv run bowerbird_mcp.py lint output=text      # what's left needs you
```

`scope=okf` limits the check to the spec; `scope=house` to hygiene (links,
anchors, orphans, islands, stubs, duplicate titles, reference links,
filenames, tags, generated indexes). `only=` and `ignore=` keep or drop finding
kinds: `lint only=stub,island`.

## CI

Vendor `bowerbird_mcp.py` into the bundle's repo, then:

```yaml
# .github/workflows/okf.yml
name: okf
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # provenance needs full history
      - uses: astral-sh/setup-uv@v6
      - run: uv run bowerbird_mcp.py lint scope=okf output=github
```

Findings show as annotations on the PR. `output=sarif` suits code scanning.
On PRs, `since=origin/${{ github.base_ref }}` limits findings to the files the PR
changed.
On a large existing collection, commit a `baseline apply=true` snapshot and
run `lint baseline=.okf-baseline.json`, so only new findings fail. The
snapshot sits at the collection root and matches from any directory. CI lints;
it does not push fixes (fork PRs get a read-only token anyway).

To skip files outright, list them in a `bower.nolint` file. It works like
`.gitignore`: it may sit in any directory, patterns are relative to it, the
last match wins and `!` re-includes. At the collection root it covers every
bundle. Skipped files are still read, so links to them resolve. One file can
skip itself with the line `<!-- bower-nolint -->`.

```gitignore
# bower.nolint: agent instructions are not concepts
AGENTS*
CLAUDE.md
.kiro/
```

pre-commit, lint only (a hook that edits files leaves the commit unstaged).
`lint` always ends with a verdict line, such as `bowerbird-mcp lint: ok: 214
concept(s) in 3 bundle(s) checked, 0 finding(s), conformant: True`, so you can
see it ran. pre-commit prints a passing hook's output only with `verbose: true`:

```yaml
repos:
  - repo: local
    hooks:
      - id: okf-lint
        name: OKF lint
        entry: uv run bowerbird_mcp.py lint output=text
        language: system
        pass_filenames: false
        verbose: true
```

<!-- --8<-- [end:ci] -->
<!-- --8<-- [start:limits] -->
## Reading the collection

- Find things in three steps, each small: `dirs` maps the bundle (each
  directory and how many concepts it holds); `search` ranks concepts by where
  every word matches (title, then id, tags, type, description, body), with
  `type=`, `tag=` and `dir=` filters; `get` reads only the top hit. `vocab`
  lists the tags and types in use, the words those filters take.

  ```sh
  uv run bowerbird_mcp.py dirs output=text
  uv run bowerbird_mcp.py search deploy rollback dir=runbooks output=text
  uv run bowerbird_mcp.py get runbooks/deploy.md output=text
  ```

- `passages` answers a question. It cuts concepts at
  headings (a long section is cut again at blank lines, each piece repeating the
  last short paragraph of the one before) and returns the best sections, each with file, line, heading,
  trust tier and staleness, so the answer can cite and qualify its sources.
  Ranking is BM25 (rarer words count more; any one word may match; no
  stemming), with title, tags, type and description counting too, and
  concepts many others link to a little higher (`hubs`). With `semantic` on,
  passages are also matched by meaning and the two rankings are fused.
  `vector_index` picks how: `scan` (exact, in Python; fine to a few thousand
  passages), `sqlite-vec` (exact, in C; `pip install sqlite-vec`) or `hnsw`
  (approximate, for 100K+; `pip install hnswlib`; it keeps the top 500 before the
  type, tag and dir filters). No hit
  returns `gap: true`: say the collection has nothing, don't guess. Passages
  are indexed in one SQLite file (`index` in `bower.yaml`), updated from the
  files that changed. `reindex` builds it ahead of time, for a hook, and with
  `build: manual` `passages` only reads it; `reindex info=true` reports what it
  holds and how far behind it is, `drop=true` deletes it. `passages: false` removes
  both tools.

  ```sh
  uv run bowerbird_mcp.py reindex output=text
  uv run bowerbird_mcp.py passages 'how do we roll back a deploy' output=text
  ```

- `web` maps links and citations: bundles at the collection root, concepts
  in a bundle. `output=text` for the terminal, `output=mermaid` for anything
  that draws Mermaid (GitHub, GitLab).
- `heatmap days=30` ranks concepts by how many commits changed them (the ones
  most likely to collide across branches) and by how many people did; who
  changes the most; and concepts only one person has ever touched. In OKF
  index.md and log.md are left out; the other formats count their own files
  (`.md`, or `.adoc` and `.asciidoc`).
- `status` lists what needs a person next: longest since review, oldest
  drafts, concepts without sources, the longest concepts, and what goes stale
  within `due_days`; the most linked-to concepts (`hubs`); and the pages links
  want that do not exist yet (`wanted`), most wanted first. In `markdown` and `adr`
  it counts by type, status, state (a decision record is accepted once a person
  has sealed it, else proposed; superseded is final) and tier, and the records
  edited since a review (`stale`); `list status=proposed` is the unreviewed worklist.
- `log file=x.md` is a concept's history.

## Known limits

- A human `seal` over MCP needs a client that supports elicitation
  (confirmation prompts); otherwise the human runs it from the CLI.
- `move`, `migrate`, `split`, `rename`, `archive` and `unarchive` rewrite links
  (code blocks included; read the diff) and §6.2 path fields (`resource`,
  `computation`, `executor`/`attester`, `sources[].resource`). A value naming
  an existing file is a path; one naming nothing is a path only if it has a
  file extension or a leading `/`, `./` or `../`, else a scope description.
- OKF makes `okf_version` optional; here it is how a bundle is found. An
  undeclared bundle is any folder until you pass it as `bundle=`.
- `ingest` does not convert other formats or check licenses. Its plan says so.
- With `format: skos`, links between concepts are not counted, so `hubs` does
  nothing, and a file that does not parse is skipped without an error. With
  `format: asciidoc`, `include::` is not followed, and `move` is not offered.
- `passages` has no stemming ("rolling" will not match "roll"), and with
  `build: manual` it does not notice files changed since the last `reindex`.
  Semantic search downloads its model (~65 MB) once into
  `~/.cache/bowerbird-mcp/models`. `fastembed` and its dependencies (about 150 MB) are the
  `semantic` extra, not part of the base install: `uv tool install 'bowerbird-mcp[semantic]'`, or
  `uvx --from 'bowerbird-mcp[semantic]' bowerbird-mcp`, or `uv run --with fastembed` for the bare script. The index lives in the file
  `index` names and is safe to delete; nothing in the
  collection changes.

<!-- --8<-- [end:limits] -->
## Self-check

```sh
uv run test_bowerbird_mcp.py
```

## Spec

`docs-src/prompts/SPEC.md` is OKF v0.2, copied unchanged from
[GoogleCloudPlatform/knowledge-catalog][okf] at commit `bad9bdb`,
Apache-2.0.

[okf]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/bad9bdbafa82c672b00d437d4f2cc8f17e9e5f58/okf/SPEC.md
[asf-gt]: https://www.apache.org/legal/generative-tooling.html
