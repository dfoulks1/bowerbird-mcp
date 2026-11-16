# ADR

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command and output on this page was run for real; long lines are shortened. -->

**Use it when** you keep decision records (ADR or MADR) and want to find them, see which are accepted, and have
a person ratify them.

```text
platform/
  kbmcp.yaml             format: adr
  docs/adr/
    0001-use-a-managed-queue.md      a Nygard record
    0002-use-postgresql.md           a MADR record
  .waxseals.yaml
```

```yaml
# kbmcp.yaml
format: adr
about: Platform decisions.
seal: {require: ["docs/adr/*.md"], exempt_status: [proposed, draft]}
```

Every Markdown file is a record (except `README.md` and `index.md`), whatever its name or folder. Bowerbird reads each
record's status as the author wrote it: from MADR 3 frontmatter, from a `## Status` section (Nygard), or from a
`* Status:` line (MADR 2).

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
file: docs/adr/0001-use-a-managed-queue.md, heading: 1. Use a managed queue > Decision, type: adr, status: Accepted, tier: unverified
file: docs/adr/0002-use-postgresql.md, heading: Use PostgreSQL > Context and Problem Statement, type: adr, status: proposed, tier: unverified
```

**Ratifying.** A record that says "Accepted" has only said so about itself. `kb ratify` (the same function as `seal`,
under the word ADRs use) records that a person reviewed it and what they decided:

```sh
kb ratify docs/adr/0001-use-a-managed-queue.md decision=accepted --attest
```

The `decision` goes into `.waxseals.yaml`, and from then on it is the hit's `status`, with `tier: human-reviewed`.
`kb seal check=true` fails a commit when a record that needs a review lacks one: `unsigned` for a required record,
`claims_accepted` for one whose own status says accepted but no person reviewed it, and `stale_signature` for one
edited after its review. A `proposed` or `draft` record is exempt, so you can commit a proposal before it is reviewed.

**Seeing where the records stand.** `kb status` and `kb list` report a record as `stable` (proposed or accepted),
`superseded`, `rejected` or `deprecated`; a superseded record stays superseded. A person's seal is what makes a stable
record **accepted**; without one it is **proposed**, whatever the file says about itself. `accepted` is another command-line name for
`seal`, like `ratify`. With two records that both write "Accepted" and no seal yet:

```text
$ kb status
concepts: 2, by_status: {stable: 2}, by_state: {proposed: 2}, by_tier: {unverified: 2}, stale: 0
$ kb list status=proposed
adr/0001-use-postgres.md   status: stable, state: proposed, tier: unverified
adr/0002-use-redis.md      status: stable, state: proposed, tier: unverified
```

`kb list status=proposed` is the worklist of decisions nobody has reviewed. `stale` counts the records edited after a
review.
