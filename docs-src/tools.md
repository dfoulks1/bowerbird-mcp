# Tools

<!-- seal-banner: Derived from the tools' own docstrings. -->

Every tool, from its own docstring. Run one as `bowerbird-mcp <tool> name=value ...` (or with flags: `--name value`, `-n value`), or see the same text with `help <tool>`. `-O json|text` chooses the output.

## archive

Role: `structure`. Offered by a server for: OKF.

Retire a concept, or (no file) the whole bundle= named, into the archive: `archive/`, a collection within the collection (started when absent), at archive/&lt;bundle&gt;/&lt;path&gt;, so `unarchive` can put it back. Archived bundles stay bundles; the live collection (lint, list, search, status, web) does not see them, and editing tools refuse them. Links to it are rewritten and warn afterwards (archived_link); status is left alone. apply=False shows the plan and diff.

```sh
bowerbird-mcp archive --file runbooks/old.md --bundle eng --apply
bowerbird-mcp archive --bundle mkt --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | `''` |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## baseline

Role: `lifecycle`. Offered by a server for: OKF.

Snapshot today's lint findings so CI fails only on new ones (`lint baseline=<path>`; same bundle and `all`, and like lint it defaults to where the user is). For adopting OKF on a large existing collection. The snapshot's path is relative to the collection. apply=False only counts.

```sh
bowerbird-mcp baseline --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `path` | `-p, --path PATH` | `str` | `'.okf-baseline.json'` |
| `apply` | `-a, --apply` | `bool` | `False` |
| `all` | `-A, --all, --no-all` | `bool` | unset |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## bundles

Role: `structure`. Offered by a server for: OKF.

Bundle roots under a directory: each index.md declaring okf_version (§12). A bundle without that declaration looks like any folder; pass it as bundle= directly.

```sh
bowerbird-mcp bundles -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## config

Role: `lifecycle`. Offered by a server for: OKF, Markdown, ADR.

Write a bower.yaml at the root of the collection from the built-in example (every setting commented out at its default; commit it, it is the collection's shared configuration, and any folder holding one is a collection) and an env.example beside it that lists every BOWERBIRD_* override (copy it to .env, which is not committed and which this lists in the .gitignore beside it in a git work tree). Never overwrites a file; one that exists is skipped. apply=false shows what would change.

```sh
bowerbird-mcp config
bowerbird-mcp config --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `apply` | `-a, --apply` | `bool` | `False` |

## create

Role: `lifecycle`. Offered by a server for: OKF, Markdown, ADR.

Create a collection: a folder with a bower.yaml (about, holds, user are what it could not know: pass them, or a human is asked in a prompt, or at a terminal; `holds` is okf, markdown, adr, skos, asciidoc or seal-only, guessed from the folder). path is the folder (default: this collection's root); it is made if absent. Previews unless apply=true. Never overwrites. Inside a collection whose bower.yaml has a `bowers:` list, the folder is a bower: its bower.yaml is written and the root lists it (the root's .mcp.json, .env and BOWERBIRD.md serve it). A root without a `bowers:` key finds it by the nested-folder rule. Otherwise the folder is a new root, and these steps follow (no flag: all; flags: only the ones named, bower.yaml always): mcp=true writes BOWERBIRD.md (the rules for an agent; the result names its path) and adds bowerbird to .mcp.json, keeping the other servers, and leaving a bowerbird entry that differs alone; env=true writes env.example, puts .env in .gitignore, and keeps your id in .env; facts=true adds a commented `facts: types:` block to the root's bower.yaml, one kind of fact per MCP server in .mcp.json (Bowerbird's own is left out), also to a bower.yaml that is already there; an uncommenting-and-filling-in turns one on. For okf, a bundle (a root index.md declaring okf_version "0.2", and a §9 log.md) is started too, named by bundle.

```sh
bowerbird-mcp create docs --holds markdown --about 'the site pages'
bowerbird-mcp create docs --holds markdown --about 'the site pages' --apply
bowerbird-mcp create --mcp --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `path` | `-p, --path PATH` | `str` | `''` |
| `apply` | `-A, --apply` | `bool` | `False` |
| `mcp` | `-m, --mcp` | `bool` | `False` |
| `env` | `-e, --env` | `bool` | `False` |
| `facts` | `-f, --facts` | `bool` | `False` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |
| `about` | `-a, --about ABOUT` | `str` | `''` |
| `holds` | `-t, --holds HOLDS` | `str` | `''` |
| `user` | `-u, --user USER` | `str` | `''` |

## dirs

Role: `read`, `structure`. Offered by a server for: OKF, Markdown, ADR.

The map: each directory holding concepts and how many. Small; read it before search or get.

```sh
bowerbird-mcp dirs -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## fact

Role: `write`. Offered by a server for: OKF.

Record a fact: where a claim came from, as a §5.1 `sources` entry with `retrieved_at` (when). A fact is a reproducible result. When an MCP tool produced it, pass server, tool and args, the exact call (`via`, how): that is the recipe `factcheck` replays. Pass result, what the call returned, and its `fact_sha256` (sha256 of the result, JSON canonicalized, other text with whitespace collapsed) is kept: it is what `factcheck` compares a later result with, to find drift. resource: a real URL when the result has one, else mcp://server/tool?args is used. author, usage_count, last_modified: the source's own credibility signals (§5.1), when you know them. stale_days&gt;0 sets stale_after. Returns the footnote marker to put after the claim; its definition is appended to the body. Reusing an id replaces that entry.

```sh
bowerbird-mcp fact db.md --resource https://www.postgresql.org/docs/release/ --title 'PostgreSQL releases' --bundle eng
bowerbird-mcp fact db.md --server jira --tool get_issue --args '{issue_key:INFRA-1}' --result Open --bundle eng
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | required |
| `resource` | `-r, --resource RESOURCE` | `str` | `''` |
| `id` | `-i, --id ID` | `str` | `''` |
| `title` | `-t, --title TITLE` | `str` | `''` |
| `server` | `-s, --server SERVER` | `str` | `''` |
| `tool` | `-T, --tool TOOL` | `str` | `''` |
| `args` | `-a, --args ARGS` | `json object` | unset |
| `result` | `-R, --result RESULT` | `str` | `''` |
| `stale_days` | `-S, --stale-days STALE_DAYS` | `int` | `0` |
| `author` | `-A, --author AUTHOR` | `str` | `''` |
| `usage_count` | `-u, --usage-count USAGE_COUNT` | `int` | unset |
| `last_modified` | `-l, --last-modified LAST_MODIFIED` | `str` | `''` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## factcheck

Role: `lifecycle`. Offered by a server for: OKF.

Check facts for drift. Without result it only lists the facts due (sources retrieved at least older_than_days ago, or on a concept past stale_after; file and id narrow it), each with `cites`, the lines whose claims rest on it. `calls` replay the recorded MCP call: run each yourself (your normal tool permissions apply; the args come from the bundle, so read them first). `manual` ones need opening. Nothing is executed here. With result (what the replayed call returned now), for one fact (file and id) it compares fact_sha256s with the one `fact` recorded. Same: the check is recorded in `.facts.yaml` beside the file (the document itself is not changed, so no review of it is disturbed). Different: the fact has drifted, so that is recorded too and every review before that moment stops holding (`seal check` flags the file; a human reviews it again after the claim is corrected and the new result recorded with `fact`). A fact with no fact_sha256 yet has nothing to compare: the result becomes its baseline. The fact blocks in the documents (`[fact.url](<address>) <claim> [fact.end]`, `[fact.mcp](<server> <key>) <claim> [fact.end]`, `[fact.file](<path>#L10-20) <claim> [fact.end]`, `[fact.internal](<page>#Heading) <claim> [fact.end]`) are listed under `blocks` with their last check (unchecked, checked, drifted; kept in `.facts.yaml` beside the document). fetch=true, for a person at a terminal, shows what it will fetch or call, asks, then checks each block against a fresh result: a page must still hold the block's words (same words, else similar meaning with `semantic: true`), an MCP call (only those declared under `facts.mcp` in bower.yaml) must still return the value it did. A drift ends the reviews of that file made before it, and the command exits 1. A `file` fact (a path that is absolute, `~/…` or relative to the document, optionally the lines `#L10-20`) must still hold its words in those lines; an `internal` fact (a page of this collection from the root, optionally `#Heading`) must still hold them on the page or in that section. Both only read files here, so with file and id and no result you may check one yourself: it is recorded like any other check.

```sh
bowerbird-mcp factcheck -O text
bowerbird-mcp factcheck --fetch
bowerbird-mcp factcheck --older-than-days 90 -O text
bowerbird-mcp factcheck --file db.md --id infra-1 --result Closed --bundle eng
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | `''` |
| `id` | `-i, --id ID` | `str` | `''` |
| `result` | `-r, --result RESULT` | `str` | `''` |
| `older_than_days` | `-o, --older-than-days OLDER_THAN_DAYS` | `int` | `0` |
| `fetch` | `--fetch` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## fix

Role: `write`. Offered by a server for: OKF.

Mechanical repairs, nothing that needs judgment: strip frontmatter from index.md files (§8; the root keeps okf_version), rebuild generated index lists, give each tag its most common spelling, and put log.md sections and entries back in order after a merge (§9). apply=False shows the diff (CLI exit 1 if there is work); apply=True writes, re-lints and returns `remaining` (CLI exit 1 if errors remain). Like lint, it defaults to where the user is and every bundle there; all=false keeps to one bundle.

```sh
bowerbird-mcp fix
bowerbird-mcp fix --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `apply` | `-a, --apply` | `bool` | `False` |
| `all` | `-A, --all, --no-all` | `bool` | unset |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## get

Role: `read`. Offered by a server for: OKF, Markdown, ADR.

One .md file of a bundle (a concept, index.md or log.md), or several at once with files=[...]. A missing index.md is synthesized from frontmatter (§8; `synthesized: true`). offset/limit page by line; limit=0 = all.

```sh
bowerbird-mcp get db.md --bundle eng -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | `''` |
| `files` | `--files FILES` | `list (a,b)` | unset |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `limit` | `-l, --limit LIMIT` | `int` | `0` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## heatmap

Role: `read`. Offered by a server for: OKF, Markdown, ADR, AsciiDoc.

The hottest concepts and who heats them, from git history (.mailmap names). files: commits that changed each concept in the last `days`, most first, and how many people did. bundles: the same per bundle. authors: each person's changes and concepts in the window. single_author: concepts only one person has ever changed (all history; a bus-factor flag). In an OKF bundle index.md and log.md are left out: every write touches them. Outside OKF it counts the format's own files (.md, or .adoc and .asciidoc). Like lint, it covers where the user is (at the collection root, every bundle). limit=0 lists all.

```sh
bowerbird-mcp heatmap --days 30 -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `days` | `-d, --days DAYS` | `int` | `30` |
| `limit` | `-l, --limit LIMIT` | `int` | `10` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## index

Role: `lifecycle`. Offered by a server for: OKF.

Rebuild generated document lists from frontmatter (title, type, tags, `description`, §8): the bundle-root index.md (a table, added if missing) and every index.md that already has a list. At a collection root, its index.md lists the bundles (created if missing). dirs=true also gives every directory an index.md listing its concepts and subdirectories (§8 progressive disclosure). apply=False shows the diff.

```sh
bowerbird-mcp index --apply
bowerbird-mcp index --dirs --apply --bundle eng
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `apply` | `-a, --apply` | `bool` | `False` |
| `dirs` | `-d, --dirs` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## ingest

Role: `structure`. Offered by a server for: OKF.

Bring markdown from a local directory or git clone into an OKF bundle, or adopt it in place (bundle = source; needs a clean git tree, so the diff is the review). Each file gets frontmatter: `type` from rules ({glob: type}, first match, else Document), `title` (its own, its H1, or the filename), `status` (default draft: imported, not reviewed), optional stale_after, and provenance where git has it: `sources` (a permalink and last_modified) and `generated` {by, at, basis: git-history}. Existing keys are kept. Never overwrites; files that already have `type` are skipped, so a re-run is a no-op. A reserved index.md/log.md carrying frontmatter is renamed &lt;dir&gt;-index.md/&lt;dir&gt;-log.md. apply=False is the plan: run it first, sample files, set rules. keep_okf=true merges another OKF bundle: files that have `type` are copied as they are (plus an origin source when git has one) and the source's index.md/log.md are left behind. It does not clone, convert other formats or check licenses. Files holding a credential-shaped string are skipped (`secrets` in the plan); run gitleaks on the source's history too.

```sh
bowerbird-mcp ingest '~/old-wiki' --bundle wiki -O text
bowerbird-mcp ingest '~/old-wiki' --bundle wiki --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `source` | `-s, --source SOURCE` | `str` | required |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |
| `rules` | `-r, --rules RULES` | `json object` | unset |
| `status` | `-S, --status STATUS` | `str` | `'draft'` |
| `stale_days` | `--stale-days STALE_DAYS` | `int` | `0` |
| `keep_okf` | `-k, --keep-okf` | `bool` | `False` |
| `apply` | `-a, --apply` | `bool` | `False` |
| `limit` | `-l, --limit LIMIT` | `int` | `50` |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `max_bytes` | `-m, --max-bytes MAX_BYTES` | `int` | `1000000` |

## links

Role: `read`. Offered by a server for: OKF, Markdown, ADR.

Edges of one concept (§6): `out` = its links, and its §6.2 path fields as `field` entries (sources are lineage, §5.1); exists false = broken; target names the bundle and file. `in` = concepts in its bundle that link to it or cite it. Wikilinks count as links: `[[Note]]`, `[[Note#Heading]]`, `[[Note|alias]]` and `![[embed]]` resolve to the file whose name matches (case ignored, shortest path first), and a miss is a `dead_link` warning like any broken link. Check `in` before moving, renaming or deprecating a concept.

```sh
bowerbird-mcp links db.md --bundle eng -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | required |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## lint

Role: `write`. Offered by a server for: OKF.

Check the bundle against OKF v0.2. Run it before and after any change, and in CI. Each finding: kind; scope (okf = the spec, house = hygiene); severity (error fails, warning does not); file; message; fix (what to do); fixable (true: `fix` clears it). conformant: §11 holds for what was linted (frontmatter parses, `type` set, index.md and log.md well formed). ok: no errors in scope. scope: all | okf | house. baseline: path of a `baseline` snapshot; only new findings count. since: a git ref; only files changed since its merge base with HEAD count (committed, staged, unstaged or untracked), for PRs. Each finding names its bundle and its file within it (§2). all=true: this directory and every bundle in it, with a summary per bundle. Without bundle=, it lints where the user is: the bundle around the working directory and everything in it (at the collection root, everything). file / files: only those files or directories (paths within bundle=), each checked within its own bundle. limit=0 returns every finding. A bower.nolint file lists paths lint skips, in .gitignore syntax; a file holding the line `<!-- bower-nolint -->` skips itself. only / ignore: finding kinds to keep or drop, like only=stub.

```sh
bowerbird-mcp lint -O text
bowerbird-mcp lint eng/runbooks/ -O text
bowerbird-mcp lint --only stub,island -O text
bowerbird-mcp lint --scope okf --since origin/main -O github
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `scope` | `-s, --scope SCOPE` | `str` | `'all'` |
| `limit` | `-l, --limit LIMIT` | `int` | `100` |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `baseline` | `-b, --baseline BASELINE` | `str` | `''` |
| `since` | `-S, --since SINCE` | `str` | `''` |
| `all` | `-a, --all, --no-all` | `bool` | unset |
| `file` | `-f, --file FILE` | `str` | `''` |
| `files` | `--files FILES` | `list (a,b)` | unset |
| `only` | `--only ONLY` | `list (a,b)` | unset |
| `ignore` | `-i, --ignore IGNORE` | `list (a,b)` | unset |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## list

Role: `read`. Offered by a server for: OKF, Markdown, ADR.

Concepts, filtered by type, tag, status (draft | stable | deprecated; absent = stable), trust tier (unverified | machine-confirmed | human-reviewed) or stale=true. The review worklist after an ingest: status=draft tier=unverified. status ignores case. In markdown and adr the status is stable, superseded, rejected or deprecated (a proposed or accepted record is stable; the tier, from .waxseals.yaml, says whether a person accepted it), and status also matches `state` (a decision record is accepted once a person has sealed it, else proposed) and the word the file wrote: status=proposed lists the decisions nobody has reviewed.

```sh
bowerbird-mcp list --status draft --tier unverified -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `type` | `-t, --type TYPE` | `str` | `''` |
| `tag` | `-g, --tag TAG` | `str` | `''` |
| `status` | `-s, --status STATUS` | `str` | `''` |
| `tier` | `-T, --tier TIER` | `str` | `''` |
| `stale` | `-S, --stale` | `bool` | `False` |
| `limit` | `-l, --limit LIMIT` | `int` | `100` |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## log

Role: `read`. Offered by a server for: OKF.

History, newest first. With file: the entries in every log.md over that concept that link to it (§9), and the git commits that changed it. Without: the bundle's recent entries from all its log.md files. `record` writes an entry.

```sh
bowerbird-mcp log db.md --bundle eng -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | `''` |
| `limit` | `-l, --limit LIMIT` | `int` | `20` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## migrate

Role: `structure`. Offered by a server for: OKF.

Move a concept to another bundle of the collection (`move` stays inside one). to_bundle: the target bundle's path in the collection ("." for its root). to: the path inside it (default: the same path). Links to the concept in both bundles are rewritten; its own `/` links, which meant the old bundle's root, become relative paths (cross-bundle: lint warns). Links from other bundles are not touched. apply=False shows the diff.

```sh
bowerbird-mcp migrate db.md mkt --bundle eng --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | required |
| `to_bundle` | `-t, --to-bundle TO_BUNDLE` | `str` | required |
| `to` | `-T, --to TO` | `str` | `''` |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## move

Role: `structure`. Offered by a server for: OKF, ADR.

Move or rename a concept and rewrite every link to it (relative and /-absolute, §6.1, in concepts, index.md and log.md), plus the moved concept's own relative links. Wikilinks are matched by name, so a move keeps them; renaming a concept leaves `[[Old name]]` behind, which `lint` then reports as a dead link (they are not rewritten yet). Stays inside one bundle; `migrate` moves between bundles. Check `links` first. apply=False shows the diff. Outside OKF a seal in .waxseals.yaml follows the file when its text is unchanged; a file whose own links had to change loses it, as any edit does.

```sh
bowerbird-mcp move runbooks/deploy.md runbooks/ship.md --bundle eng --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | required |
| `to` | `-t, --to TO` | `str` | required |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## new

Role: `write`. Offered by a server for: OKF, Markdown, ADR.

Write a new document (.md is added; refuses a file that exists and the reserved names index.md and log.md). template is okf (frontmatter with type, title, description, status), markdown (title, tags) or adr (MADR, dated today); it defaults to the format the folder holds, from bower.yaml. title defaults to the file name. With none of the fields below, the file is the bare template, to fill in by hand. Pass any of them and it is written filled in, in one call: description, tags, status (draft, stable or deprecated), body (markdown; a `# title` heading is added unless it starts with one), and for okf (OKF §4.1) type (required: Reference, Playbook, ...), resource and by=&lt;tool&gt;/&lt;model&gt;, who wrote the body (provenance: never invent it; `generated` {by, at} records it). adr takes the template alone. To make a collection or a bower, see `create`.

```sh
bowerbird-mcp new notes/deploy
bowerbird-mcp new decisions/0004-use-vault --template adr --title 'Use Vault'
bowerbird-mcp new runbooks/deploy --type Playbook --description 'How we deploy.' --bundle eng
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | required |
| `template` | `-t, --template TEMPLATE` | `str` | `''` |
| `title` | `-T, --title TITLE` | `str` | `''` |
| `description` | `-d, --description DESCRIPTION` | `str` | `''` |
| `tags` | `--tags TAGS` | `list (a,b)` | unset |
| `status` | `-s, --status STATUS` | `str` | `''` |
| `body` | `-b, --body BODY` | `str` | `''` |
| `type` | `--type TYPE` | `str` | `''` |
| `resource` | `-r, --resource RESOURCE` | `str` | `''` |
| `by` | `--by BY` | `str` | `''` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## passages

Role: `read`. Offered by a server for: OKF, Markdown, ADR, SKOS, AsciiDoc.

The passages that best answer query, for you to read and cite. Each concept is cut into one passage per heading section (a long one is cut again, each piece repeating the last short paragraph of the one before; with format: skos each skos:Concept is a passage), ranked by BM25 (rarer words count more; any word may match, no stemming), with the heading path, title, tags, type and description counting too. Concepts many others link to rank a little higher (hubs). With semantic on, passages are also matched by meaning (embeddings) and the two rankings are fused (vector_index in bower.yaml picks scan, sqlite-vec or hnsw). Each hit: {bundle, file, line, heading, match (percent of the best hit's score: the top hit is 100, so it says how the others compare, not how good the best one is), title, type, status, tier (trust, §5.3), stale, links (inbound), text}. Answer from the text, cite the file and line, and say so when tier is unverified or stale. No hit: gap is true, so tell the user the collection has nothing, rather than guess. Filters as in search. Everything is indexed in one SQLite file (index in bower.yaml), updated from the files that changed, or only by `reindex` when build is manual; semantic mode also downloads its model once.

```sh
bowerbird-mcp passages 'how do we roll back a deploy' -O text
bowerbird-mcp passages rollback --tag ops --limit 3
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `query` | `-q, --query QUERY` | `str` | required |
| `type` | `-t, --type TYPE` | `str` | `''` |
| `tag` | `-g, --tag TAG` | `str` | `''` |
| `dir` | `-d, --dir DIR` | `str` | `''` |
| `limit` | `-l, --limit LIMIT` | `int` | `8` |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## provenance

Role: `lifecycle`. Offered by a server for: OKF.

Fill a missing `generated: {by, at}` (§5.2). From git history: the last commit that changed the body, by its AI trailer (&lt;producer&gt;/&lt;name&gt;), bot (process:) or author (human:&lt;login | ASF id | email&gt;), marked `basis: git-history` (inferred). Concepts git knows nothing about (untracked, or no repository): with apply=true the person is asked who wrote them, once (a confirmation prompt over MCP; --attest at the terminal), and recorded as `generated: {by: human:<id>, at: <file's last change>, basis: stated}`; otherwise they are listed in `unknown`. Never sets a human from a caller. Trust tiers come only from `verified`, so this never raises one. Concepts that carry `generated` are left alone. skip: paths to leave without it. apply=False shows the diff.

```sh
bowerbird-mcp provenance --apply
bowerbird-mcp provenance --apply --attest
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `apply` | `-a, --apply` | `bool` | `False` |
| `skip` | `-s, --skip SKIP` | `list (a,b)` | unset |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## record

Role: `write`. Offered by a server for: OKF.

Write a §9 entry, `* **<kind>**: <note>`, under today's date in a log.md (newest first; created if absent): the bundle root's, or dir's (a directory in the bundle; §9 logs that scope). Link the concept it is about, `[title](/path.md)`, so `log` finds it. Kinds by convention: Update, Creation, Deprecation.

```sh
bowerbird-mcp record 'Reviewed the runbooks against the new pipeline.' --bundle eng
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `note` | `-n, --note NOTE` | `str` | required |
| `kind` | `-k, --kind KIND` | `str` | `'Update'` |
| `dir` | `-d, --dir DIR` | `str` | `''` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## reindex

Role: `lifecycle`. Offered by a server for: OKF, Markdown, ADR, SKOS, AsciiDoc.

Build, inspect or delete the passage index (`index` in bower.yaml). Default: build or refresh it from the whole collection, and its vectors when semantic is on. Only files that changed since the last run are read, so it is cheap to run from a pre-commit, post-merge or post-checkout hook; the first semantic run embeds every passage and takes minutes (an interrupted run resumes). full=true starts over. info=true only reports: the file, its size, files, passages and vectors held, the model they came from, and `behind` (files changed since the last build). drop=true deletes the file (a cache; reindex makes it again). Never edits the bundle. Pick one of full, info and drop.

```sh
bowerbird-mcp reindex -O text
bowerbird-mcp reindex --info -O text
bowerbird-mcp reindex --full
bowerbird-mcp reindex --drop
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `full` | `-f, --full` | `bool` | `False` |
| `info` | `-i, --info` | `bool` | `False` |
| `drop` | `-d, --drop` | `bool` | `False` |

## rename

Role: `structure`. Offered by a server for: OKF.

Rename or move a bundle within the collection (§3): bundle= (default: where the user is) to `to`, a path in the collection. Links into it from other bundles, its links out, and §6.2 paths are rewritten (§6.1); its own `/` links stay, since its root moves with it. The collection index follows. apply=False shows the plan and diff.

```sh
bowerbird-mcp rename marketing --bundle mkt --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `to` | `-t, --to TO` | `str` | required |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## seal

Role: `seal`. Offered by a server for: OKF, Markdown, ADR, SKOS, AsciiDoc, Seal-only.

Seal a file: record a review of exactly this version of it. Or (check=true) check that every file the `seal` policy in bower.yaml covers has one. The one function for every format; `verify` (okf), and `ratify` or `accepted` (ADRs), are its names on the command line. Two paths: you (an agent or process) checked it: by=&lt;tool&gt;/&lt;version&gt; or process:&lt;id&gt;; it is machine-confirmed. A human checked it: omit `by`; the human gets a confirmation prompt and types their own id. Never pass human:&lt;id&gt; yourself. Present the file to them first. At the terminal a human runs it with --attest. okf writes a §5.2 `verified` entry {by, at, sha256} into the concept; markdown, adr, skos and asciidoc keep the latest, one dense line per file (with `bowerbird`: the version that wrote it), in .waxseals.yaml (commit it), replacing the one before. The sha256 binds the review to these exact bytes: edit the file and the seal is broken (shown stale). promote=true also moves an okf draft to stable (§5.4); only a human review may. decision=accepted|rejected records an ADR's outcome (not okf): a person sealing an ADR or MADR must give it, and it is written into the file as its `status` before the seal (an ADR+ header also gets `status-note`, `ratified-by`, `ratified-on` and a History line); a machine's seal (by=) does not rule. comment="..." leaves a one-line note (up to 280 characters) with the seal: any seal can carry one, and it is kept with the review. With `seal.extensions: true` in bower.yaml (the `seal-extensions` extra) several people can seal the same version, each with their own comment, kept together in one ledger line, and `seal.quorum: N` makes `seal check` fail (short_of_quorum) until N different people have; a machine check is never a signer. format seal-only reviews any text file, indexes nothing and offers only this tool. check=true changes nothing and exits 1 on findings: unsigned (required, no human review), short_of_quorum (fewer different people than seal.quorum), stale_signature (edited since), claims_accepted (says accepted, no review) and orphan_signature (a warning); since=&lt;git ref&gt; limits it to files changed since its merge base with HEAD. Run it in a pre-commit hook and in CI; `seal.exempt` and `seal.exempt_status` in bower.yaml say what it leaves out.

```sh
bowerbird-mcp seal db.md --bundle eng --promote --attest
bowerbird-mcp seal db.md --bundle eng --comment 'Checked against the runbook' --attest
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `file` | `-f, --file FILE` | `str` | `''` |
| `by` | `-b, --by BY` | `str` | `''` |
| `promote` | `-p, --promote` | `bool` | `False` |
| `decision` | `-d, --decision DECISION` | `str` | `''` |
| `check` | `-c, --check` | `bool` | `False` |
| `since` | `-s, --since SINCE` | `str` | `''` |
| `comment` | `-C, --comment COMMENT` | `str` | `''` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## search

Role: `read`. Offered by a server for: OKF, Markdown, ADR.

Concepts holding every word of query (case-insensitive, anywhere in the concept), best first. Each field a word matches adds its weight to the score: title 5, id 4, tags 3, type 2, description 2, body 1. Each hit: {bundle, file, title, type, score, matched (the fields), line, text (the first line holding a word, body first)}. Filters: type, tag, dir (a directory in the bundle); fields limits where words are looked for.

```sh
bowerbird-mcp search postgres -O text
bowerbird-mcp search deploy rollback --type Playbook --dir runbooks -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `query` | `-q, --query QUERY` | `str` | required |
| `type` | `-t, --type TYPE` | `str` | `''` |
| `tag` | `-g, --tag TAG` | `str` | `''` |
| `dir` | `-d, --dir DIR` | `str` | `''` |
| `fields` | `-f, --fields FIELDS` | `list (a,b)` | unset |
| `limit` | `-l, --limit LIMIT` | `int` | `30` |
| `offset` | `-o, --offset OFFSET` | `int` | `0` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## set

Role: `write`. Offered by a server for: OKF.

Edit frontmatter on one or many concepts by text; every other key stays byte for byte (§4.1). fields: {key: value}; null drops a key. Checks type, status (§5.4), stale_after (§5.5, ISO with a UTC offset) and tags (a list). generated, verified and sources have their own tools (provenance, seal, fact). apply=False shows the diff.

```sh
bowerbird-mcp set db.md status=deprecated 'tags=[db,ops]' --bundle eng --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `fields` | `-f, --fields FIELDS` | `json object` | required |
| `file` | `--file FILE` | `str` | `''` |
| `files` | `--files FILES` | `list (a,b)` | unset |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## split

Role: `structure`. Offered by a server for: OKF.

Make a directory its own bundle (§3): its index.md declares okf_version "0.2" (created if missing, with a generated list), a log.md is started, and `/` links and §6.2 paths inside it are rewritten for the new root (§6.1). Links that now cross between the two bundles are listed, not changed; lint warns on them. shortcut: links inside code blocks are rewritten too; read the diff.

```sh
bowerbird-mcp split notes --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `dir` | `-d, --dir DIR` | `str` | required |
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## status

Role: `read`. Offered by a server for: OKF, Markdown, ADR.

Bundle summary: concepts by type, by status (absent = stable, §5.4), by trust tier (§5.3), stale count (`stale_after` passed, §5.5; outside OKF, edited since a review), unparseable files, declared okf_version, conformance and lint totals; and the upkeep queues, five oldest or largest each: review (days since last `verified`), drafts (days since `generated.at`), sources (concepts with and without), words (total, longest: split candidates), due (`stale_after` within due_days); hubs (most linked-to concepts) and wanted (missing pages links point at, most wanted first). At a collection root without bundle=, `bundles` holds the same for each bundle. In markdown and adr only the counts by type, status, state (accepted, proposed, superseded: a sealed decision record is accepted) and tier, stale, hubs and wanted.

```sh
bowerbird-mcp status -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `due_days` | `-d, --due-days DUE_DAYS` | `int` | `30` |
| `bundle` | `-B, --bundle BUNDLE` | `str` | `''` |

## unarchive

Role: `structure`. Offered by a server for: OKF.

Put an archived concept or bundle back where it came from: path is its place in the archive, &lt;bundle&gt;/&lt;path&gt; for a concept (its bundle must exist) or &lt;bundle&gt; for a whole bundle. apply=False shows the plan and diff.

```sh
bowerbird-mcp unarchive eng/runbooks/old.md --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `path` | `-p, --path PATH` | `str` | required |
| `apply` | `-a, --apply` | `bool` | `False` |

## upgrade

Role: `lifecycle`. Offered by a server for: OKF.

OKF v0.1 to v0.2 (§13). A legacy `timestamp` becomes `generated: {by, at, basis: git-history}` with by from git history (`by` is required, so without history it stays and is listed in needs_by); a body `# Citations` list becomes `sources` entries and the list is removed; the root index.md declares okf_version "0.2". apply=False shows the diff.

```sh
bowerbird-mcp upgrade
bowerbird-mcp upgrade --apply
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `apply` | `-a, --apply` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## vocab

Role: `read`. Offered by a server for: OKF.

Tags and types in use, most used first: the words `search`, `list` and `set` filter on.

```sh
bowerbird-mcp vocab -O text
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |

## web

Role: `structure`. Offered by a server for: OKF.

The link graph (§6): which concepts link to (`link`) or cite (`cite`: sources and §6.2 path fields, lineage, §5.1) which. Where the user is, like lint: at the collection root, bundles with edges counted; in a bundle (or concepts=true), concepts. Broken links are left out (lint reports them); archived and deprecated nodes are marked. Returns {level, nodes, edges}; mermaid=true returns a Mermaid diagram instead (CLI: output=mermaid), which GitHub and most markdown viewers draw.

```sh
bowerbird-mcp web -O text
bowerbird-mcp web -O mermaid
```

| Argument | Flag | Type | Default |
|---|---|---|---|
| `concepts` | `-c, --concepts` | `bool` | `False` |
| `mermaid` | `-m, --mermaid` | `bool` | `False` |
| `bundle` | `-b, --bundle BUNDLE` | `str` | `''` |
