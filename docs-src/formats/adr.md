# ADR

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The commands and output on this page were run for real, except ratifying, which a person does; long lines are shortened. A person has not reviewed this page yet. -->

**Use it when** you keep decision records (ADR or MADR) and want to find them, see which are accepted, and have
a person ratify them.

## Switch it on

```text
platform/
  bower.yaml             format: adr
  docs/adr/
    0001-use-a-managed-queue.md      a Nygard record
    0002-use-postgresql.md           a MADR record
    .waxseals.yaml                   appears when someone ratifies a record (commit it)
```

```yaml
# bower.yaml
format: adr
about: Platform decisions.
seal: {exempt: [], exempt_status: [proposed, draft]}
```

## What it reads

Every Markdown file is a record (except `README.md` and `index.md`), whatever its name or folder. Bowerbird reads each
record's status as the author wrote it: from MADR 3 frontmatter, from a `## Status` section (Nygard), or from a
`* Status:` line (MADR 2). (In a [Markdown](markdown.md) folder, a numbered file name or a path through `adr`, `adrs` or `decisions` makes a note a record too.)

```markdown
# 1. Use a managed queue

Date: 2026-11-16

## Status

Accepted

## Context

The platypus service needs a queue.
```

```markdown
---
status: proposed
date: 2026-11-16
decision-makers: platform team
---
# Use PostgreSQL

## Context and Problem Statement

Which database for the narwhal?
```

Hits carry `type: adr` and the record's `status`:

```text
file: docs/adr/0001-use-a-managed-queue.md, line: 14, heading: 1. Use a managed queue > Decision, type: adr, status: Accepted, tier: unverified
file: docs/adr/0002-use-postgresql.md, line: 9, heading: Use PostgreSQL > Context and Problem Statement, type: adr, status: proposed, tier: unverified
```

Records link to each other with `[text](other.md)` or `[[0002-use-postgresql]]`, and `lint` warns of a link that leads nowhere (see [what the Markdown formats share](../formats.md#what-the-markdown-formats-share)).

**Starting a record.** `bowerbird-mcp new docs/adr/0003-use-vault.md -T "Use Vault"` writes the MADR template: status `proposed`,
today's date, and the headings Context and Problem Statement, Considered Options, Decision Outcome and Consequences. A folder that holds ADRs gets it by default.

## Reviews and lint

A record that says "Accepted" has only said so about itself. `bowerbird-mcp ratify` (the same function as `seal`,
under the word ADRs use) records that a person reviewed it and what they decided. The decision is required:

```sh
bowerbird-mcp ratify docs/adr/0001-use-a-managed-queue.md decision=accepted --attest
```

The `decision` (`accepted` or `rejected`) goes into the ledger, a `.waxseals.yaml` in the record's folder, and is written into the record as its `status` before the seal, so the file, the ledger
and `INDEX.md` agree. A record with the ADR+ header (`kind` or `built`) also gets `status-note`, `ratified-by`, `ratified-on` and a History line holding the old values.
A machine's seal (`by=`) does not rule. From then on the hit has `tier: human-reviewed`. See [Sealing](../sealing.md#decisions).

`bowerbird-mcp seal check=true` fails a commit when a record that needs a review lacks one: `unsigned` for a required record,
`claims_accepted` for one whose own status says accepted but no person reviewed it, and `stale_signature` for one
edited after its review. A `proposed` or `draft` record is exempt, so you can commit a proposal before it is reviewed.

**Seeing where the records stand.** `bowerbird-mcp status` and `bowerbird-mcp list` report a record as `stable` (proposed or accepted),
`superseded`, `rejected` or `deprecated`; a superseded record stays superseded. A person's seal is what makes a stable
record **accepted**; without one it is **proposed**, whatever the file says about itself. `accepted` is another command-line name for
`seal`, like `ratify`. With the two records above and no seal yet:

```text
$ bowerbird-mcp status -O text
concepts: 2
by_type: {"adr": 2}
by_status: {"stable": 2}
by_state: {"proposed": 2}
by_tier: {"unverified": 2}
stale: 0
$ bowerbird-mcp list status=proposed -O text
  - bundle: ., file: docs/adr/0001-use-a-managed-queue.md, status: stable, tier: unverified, stale: false, state: proposed
  - bundle: ., file: docs/adr/0002-use-postgresql.md, status: stable, tier: unverified, stale: false, state: proposed
```

`bowerbird-mcp list status=proposed` is the worklist of decisions nobody has reviewed. `stale` counts the records edited after a
review.

`lint` is offered to ADR servers, and checks fact blocks and links as it does for [Markdown](markdown.md). `move` is offered too, and keeps a record's seal when its text is unchanged.

## Limits

- Reading a status is only as good as the file: a status the three forms above do not hold is read as no status.
- An ADR ruling needs a person. An agent can only seal as itself, which does not rule, and `ratify` without `decision` stops.
- A record that is edited after its review is `stale` and goes back to **proposed** until a person rules again.
