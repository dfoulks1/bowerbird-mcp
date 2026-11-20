# OKF

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command and output on this page was run for real; long lines are shortened. -->

**Use it when** the knowledge needs to say where it came from, who checked it and when it expires, especially when
agents write part of it. [Open Knowledge Format](#what-okf-is) is a Markdown convention for exactly that: each
note (a *concept*) starts with a small header of facts, and the tools check that the whole folder is well formed.
It is the only format with the full toolset: `lint`, `fix`, `fact`, `factcheck`, `provenance`, `status`, `move`, `rename` and the rest.

## What OKF is

**Open Knowledge Format** (OKF) is a way of writing down what you know so that people and AI assistants can both
use it. The whole format is this: **a folder of Markdown files, each starting with a short block of facts about
the file.** The specification calls that block *frontmatter* and writes it in YAML. That is the entire
technology. There is no database, no server, no registry of allowed types and no required software. In the
specification's own words: if you can `cat` a file you can read OKF, and if you can `git clone` a repository you
can ship it.

OKF is published as a specification (this site follows version 0.2) in the `knowledge-catalog` repository on
GitHub. Bowerbird is one tool that implements it: it writes, checks and searches OKF folders. Nothing in
the format depends on this tool, which is the point.

### Why a format at all?

A pile of Markdown notes is already easy to read. The trouble starts when the pile grows, other people add to it,
and AI assistants begin to *write* parts of it. Then readers need answers a plain note does not give:

1. **Where did this come from?** (provenance)
2. **Has anyone checked it, and was it a person or a script?** (trust)
3. **Is it still true?** (freshness)
4. **Is this the current version, or an old draft?** (lifecycle)

Without a convention, every team invents its own answers, and no tool can rely on them. OKF fixes a *small* set of
conventions for exactly these questions and leaves everything else to you.

## The pieces

A collection is a folder of *bundles*; a bundle is a folder of concepts, one Markdown file each.

```text
notes/
  bower.yaml               format: okf (the default)
  index.md                 lists the bundles
  eng/                     a bundle: its index.md declares okf_version "0.2"
    index.md
    log.md                 what changed, newest first
    db.md
    runbooks/ship.md
    refs/pg.md
  mkt/
    index.md
    log.md
    launch.md
```

Each concept is frontmatter (what kind of thing it is, where its facts came from, who checked it) over an ordinary
Markdown body. Here is `eng/db.md`:

```markdown
---
type: Reference
title: Database
description: The PostgreSQL cluster behind every service.
sources:
  - id: pg
    resource: refs/pg.md
verified: { by: human:you, at: 2026-10-27T14:00:00Z }
---

We run PostgreSQL 16.4.[^pg] Deploys follow [the ship runbook](/runbooks/ship.md).

[^pg]: PostgreSQL release notes
```

### The header fields

Only one is required. `type` says what kind of thing the file is (`Playbook`, `Reference`, `Metric` and so on).
Types are not registered anywhere: pick words that explain themselves, and readers must cope with ones they have
not seen. A file with nothing but `type` is fully valid.

The others are recommended or optional, in three families:

| Family | Fields | Answers |
|---|---|---|
| **Describing** | `title`, `description` (one sentence), `tags`, `resource` (a URI for the thing it describes) | What is this, for indexes and search results |
| **Provenance and trust** | `sources` (what it was built from), `generated` (who or what wrote the current text, and when), `verified` (who confirmed it, and when) | Where it came from and how far to trust it |
| **Lifecycle** | `status` (`draft`, `stable`, `deprecated`; absent means stable), `stale_after` (a date after which the content counts as stale) | Is it current |

Every timestamp is ISO 8601 with an explicit UTC offset, such as `2026-11-13T15:00:00Z`. Anything else you add is
yours: tools should keep keys they do not understand and must not reject a file for having them.

### Trust tiers

The tier is *derived*, never typed in. Look at who is in `verified`:

- nobody: **unverified**;
- only scripts, processes or agents: **machine-confirmed**;
- at least one person: **human-reviewed**.

Who is who is decided by a naming convention for **actors**: `human:<id>` for a person (`human:ann`),
`process:<id>` for an automated process (`process:finance-nightly`), and `<producer>/<version>` for an agent or
tool (`reference_agent/gemini-2.5-pro`). Because the tier keys off the `human:` prefix, anything a person wrote or
confirmed must use it. Two things to keep in mind: `generated` and `verified` are kept apart on purpose, because
who *wrote* a note need not be who *checked* it; and tiers are advisory labels, not access control.

### Links and citations

Concepts point at each other in two ways: a Markdown **link** in the body, and a **citation** in `sources`, which
records where a fact came from. `web output=mermaid` draws both for the whole collection:

```mermaid
graph LR
  subgraph eng
    db["db.md"]
    ship["runbooks/ship.md"]
    pg["refs/pg.md"]
  end
  subgraph mkt
    launch["launch.md"]
  end
  db -.->|cites| pg
  db -->|links| ship
  ship -->|links| db
  ship -->|links| launch
  launch -->|links| db
```

Solid arrows are links; dotted ones are citations. The boxes are bundles, so an arrow that leaves its box crosses into
another bundle. That is allowed, but `lint` flags it, because the link breaks if one bundle is published alone.

Links are ordinary Markdown, either relative (`[the rollback steps](rollback.md)`) or from the bundle root with a leading
slash (`/runbooks/rollback.md`, which survives moving files around inside a folder). A link says "these are related"; the
sentence around it says how. A broken link is allowed by the format: it may simply be knowledge nobody has written yet
(`status` lists the pages that links ask for and nobody has written). A citation is different: the claim in the text points
at its entry in `sources` with a Markdown footnote (`[^pg]`). Links are for navigation, citations are for lineage.

### Facts: what a claim rests on, and drift

A **fact** is a claim together with where it came from, written so it can be checked again. Put the source and the words you
relied on in a block, in any Markdown document (it works in every format, not only OKF):

```markdown
[fact.url](https://stackoverflow.com/questions/8072700/how-to-restart-jenkins-manually)

(jenkins_url)/safeRestart - Allows all running jobs to complete. New jobs will remain in the queue to run after the restart is complete.

(jenkins_url)/restart - Forces a restart without waiting for builds to complete.

[fact.end]

The ticket: [fact.mcp](jira INFRA-27707) is open [fact.end]
```

- **`[fact.<kind>](<source>) <the claim> [fact.end]`** is the whole form. The kind says what the source is, the source goes in parentheses
  right after it (it ends at the first `)`, so write a `)` inside an address as `%29`), and the words up to `[fact.end]` are what is
  checked: paste them from the page. A block holds one source and any number of claims, on one line or many. In a Markdown renderer
  that knows nothing of facts, `fact.url` shows as a link to the source.
- **`[fact.url](address)`** is a page: its words must still appear there.
- **`[fact.<name>](key)`**, for a name the root `bower.yaml` declares under `facts: types:`, is a fact from one tool of an MCP server the collection
  already has, so the source is just the key: `[fact.ticket](INFRA-27707) is open [fact.end]`. Only the root declares one (a page cannot add a kind,
  or choose what runs), and `lint` flags a kind nobody declared.
- **`[fact.mcp](server key)`** is the general form, a fact from an MCP tool, for example `[fact.mcp](jira INFRA-27707) is open [fact.end]`. Which tool to
  call, with what, and which part of the result to watch is declared once in `bower.yaml`, under `facts` (see below).
- The kinds are a registry (`bowerbird_facts.FACT_TYPES`): `url` and `mcp` are registered, and a new kind is one `register(name, sample, valid)` call plus a `check` for
  `factcheck --fetch`. A block with no `[fact.end]`, an end with no start, or an unknown kind is a `lint` error. Blocks inside code are ignored, so
  examples like the one above are safe.

**Checking.** `factcheck` with no arguments lists every block and its state: *unchecked*, *checked* (with the date and how), or
*drifted*. It runs nothing. `factcheck --fetch`, run by a person at a terminal, shows what it will fetch or call, asks, and
then compares each block with a fresh result:

- a **page** must still hold the block's words. Whitespace, case, backticks and emphasis are ignored: it is the content that is
  compared, not the shape. With `semantic: true` and the `semantic` extra, a page that no longer says it word for word but still
  means it counts too, scored against `min_similarity` (the same settings as semantic search), and the result says "similar meaning"
  instead of "same words";
- an **MCP call** (only one declared under `facts`) must still return the value it did. The first check records that value.

```yaml
# bower.yaml, at the collection root: the only calls factcheck may make
facts:
  mcp:
    jira: {tool: get_issue, arg: issue_key, watch: fields.status.name}
  types:   # optional: a kind of fact for one tool, so the source is just the key
    ticket: {server: jira, tool: get_issue, arg: issue_key, watch: fields.status.name}
```

The document supplies only the key (`INFRA-27707`), never the tool, so a page cannot make `factcheck` call something it was not
told to. The server itself comes from `.mcp.json`. `--fetch` is a person's command: over MCP it is refused.

**State is kept beside the document**, in a `.facts.yaml` (commit it, as you do `.waxseals.yaml`). It holds the last check of each
block. The document is never changed by a check, so a check that finds nothing wrong does not disturb a human's review of it.
Edit the words of a block and it is a new fact, unchecked until it is checked.

**Drift breaks the seal.** A block that has drifted ends every [review](../sealing.md) of that file made before it, and `seal check`
reports `a cited fact drifted after it was reviewed`. Correct the claim and have a person review the file again: a review made after
the drift holds. A check that passes does not undo a drift.

**The docs build** shows each block as a quotation with its source and its state (not yet checked, checked on a date, or drifted).

**Moving between the two records.** A concept's reviews and sources can live in its frontmatter (`verified`, `sources`) or beside it
(`.waxseals.yaml`, `.facts.yaml`); [`okf export` and `okf import`](../cli.md#moving-an-okf-concepts-history-okf-export-and-okf-import) move them
between the two, previewing first.

**For an agent**, `fact` records a fact as a `sources` entry in the frontmatter (a call as `via: {server, tool, args}`, and
`result`, what it returned, as a `fact_sha256`), prints the footnote marker for the claim, and `factcheck file=... id=... result=...`
compares a result an agent got by replaying the call with it. Same result: the check is noted in `.facts.yaml`. A different one is a
drift. An agent runs no `--fetch`.

### Bundles, `index.md` and `log.md`

A **bundle** is a folder of concepts, with subfolders as you like. Two filenames are reserved at any level:

- **`index.md`** lists what is in a folder, with each concept's one-line description, so a reader (or an
  assistant) can see what is available before opening anything. The spec calls this *progressive disclosure*. At
  the top of a bundle it may carry one frontmatter key, `okf_version`. OKF makes it optional; Bowerbird
  uses it to recognise a folder as a bundle. Tools may generate `index.md`, and Bowerbird's `index` does.
- **`log.md`** is the history of changes to that folder, newest first, grouped by date.

A bundle can travel as a git repository (recommended, for the history and the diffs), a zip, or a subfolder of a
bigger repository. The word **collection**, as this site uses it, is not part of OKF: it means a bundle, or a
folder of bundles, that Bowerbird manages together.

## Try it

In an empty folder:

```sh
bowerbird-mcp create holds=okf about="Team runbooks." apply=true
bowerbird-mcp create deploy type=Playbook title="Deploy" description="How we ship a release." \
   body='Run the deploy script, then check the dashboard.' output=text
bowerbird-mcp fact deploy.md resource=https://example.com/runbook title="Ops runbook" output=text
bowerbird-mcp lint output=text
```

`new` starts a file from the OKF template (`bowerbird-mcp new deploy -t okf`), or, given its `type` and a few fields, writes one with its header filled in, `fact` records a source and prints the footnote tag (`[^runbook]`) to put next to
the claim it backs, and `lint` checks the whole collection:

```text
bowerbird-mcp lint: ok: 1 concept(s) in 1 bundle(s) checked, 0 finding(s), conformant: True
```

A file with no header, a broken link or a fact with no source is a finding, each naming the file, what is wrong and how to
fix it, and `bowerbird-mcp fix apply=true` repairs the mechanical ones.

## Reviewing

`bowerbird-mcp seal` writes a `verified` entry into the concept itself, with a `sha256` of the note. The trust tier
comes only from who verified: nobody means *unverified*, a script or agent means *machine-confirmed*, and a person
means *human-reviewed*. Hits show the tier and whether the note has gone stale. See The tiers are explained [above](#trust-tiers).

## Why it is good

These are the properties that follow from the format itself.

- **Readable with no tools.** It is text. Open a file, read it. If this project vanished tomorrow, you would keep
  every note, in a form any editor shows you. The way out of the format is "stop using the tool".
- **Diffable and reviewable.** Because it is plain text in a folder, git shows exactly what changed, who changed
  it and when, and a pull request can review a knowledge change like a code change.
- **Portable.** No schema registry or central authority, so a bundle moves between teams, tools and years
  without a conversion step.
- **Written for agents without a special SDK.** An assistant can read the files directly, and the structure
  (headings, a one-line description, tags, a type) is what a retrieval tool needs to cut a note into useful
  pieces and rank them.
- **Honest about trust.** Provenance, verification and freshness are part of the file, not a separate system.
  A reader, human or machine, can tell a checked fact from an unchecked one, and a current one from an expired
  one, *at the moment of reading*.
- **Minimal on purpose.** Only `type` is required, unknown fields are tolerated, and there is no fixed list of
  concept types. You can start with a few notes and add structure as you need it.

## What it does not do

It is worth being plain about the limits.

- **It does not check that anything is true.** `verified` records that someone or something *said* they checked.
  The format makes the claim visible; it cannot make it correct.
- **It does not control access.** Trust tiers and statuses are signals for readers, not permissions.
- **It is not a database or a search engine.** It prescribes no storage, serving or query system. Finding things
  is up to the tool you use on top.
- **It does not define your vocabulary.** Concept types, tags and structure are yours to choose and keep
  consistent. (`vocab` in Bowerbird lists what you actually use, so spellings do not drift.)
- **It will not replace domain schemas.** Where an asset already has a precise schema (an API description, a
  table definition), OKF points at it with `resource`; it does not copy it.

## Read on

- [Getting started](../getting-started.md): build one in ten minutes.
- [The specification][okf]: the exact rules, including attested computations, which this page leaves out.
- [Tools](../tools.md): every tool, by role. [The guide](../guide.md): layout, the archive, several bundles, CI and settings.

[okf]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/bad9bdbafa82c672b00d437d4f2cc8f17e9e5f58/okf/SPEC.md
