---
status: accepted
status-note: accepted by dfoulks on 2026-11-23, in the seal dialog
owner: dfoulks
kind: architecture
built: not started
proof: "queued in TODO.md (2.3, OKF through import and export)"
supersedes: nothing
amends: nothing
consulted: "Claude Sonnet 5.5 (options and drafting)"
ratified-by: dfoulks
ratified-on: "2026-11-23"
---
# ADR-004 — OKF keeps its reviews and facts in the shared files, and import and export convert

## Decision

In an OKF bundle, reviews and facts live where every other format keeps them: reviews in `.waxseals.yaml`, facts as `[fact.*]` blocks in the text with their checks in `.facts.yaml`. What OKF's frontmatter
holds for the same things (`verified` for reviews, `sources` for the older form of a fact) is a form for OKF readers, produced and read by `okf export` and `okf import`, not the record the tools work from.
This covers anything else OKF puts in frontmatter that another format has a file for.

A setting in the root `bower.yaml` switches a collection over: `okf: {records: files}`. With it, `seal` and `fact` write the shared files for OKF concepts, every tool reads them from there, and `okf import`
writes the frontmatter OKF readers expect when a bundle is shipped on its own. Without it (the default in 2.3), OKF behaves as in 2.2.0: `seal` writes `verified` and `fact` without a claim writes `sources` into the frontmatter.
`okf export --apply` is the migration of an existing collection: it moves what the frontmatter holds into the files, previewing first, and a bundle can be switched over once it has run.

## Context

OKF is the odd format: it is the only one whose reviews and facts sit in each concept's frontmatter (`verified`, `sources`). Every other format uses the ledger and the blocks, which now have per-folder ledgers,
numbered facts and checks written to a file beside the page. The owner decided (2026-11-23) that OKF should rely on import and export for what other formats keep in a file, and confirmed it covers seals as well as facts.
`okf export` and `okf import` exist since 2.2.0 and move reviews and checks both ways.

Drivers:
- One place for a review and a fact, whatever the format, so every tool and every display reads one record.
- A 2.2.0 OKF collection keeps working until its owner chooses.
- An OKF bundle shipped on its own must still carry what a plain OKF reader expects.

## Alternatives

### A setting, off by default in 2.3, with `okf export` as the migration (chosen: nothing breaks on upgrade, and each collection moves when its owner runs the export)
- Good: no 2.2.0 collection changes by upgrading; the move is previewed and reversible with `okf import`.
- Bad: two behaviours for OKF until the default flips.

### Switch every OKF collection to the files in 2.3
- Good: one behaviour.
- Bad: an upgrade changes where every OKF seal and fact is written and read; collections that never ran `okf export` would look unreviewed.

### Keep OKF in the frontmatter for good
- Good: no work, and the bundle is self-contained.
- Bad: OKF stays the one format with its own record: every feature (ids, `last_checked`, the seal count, the bibliography) is built twice.

## Consequences

- `okf export` and `okf import` become the supported bridge, and are tested in both directions for seals and facts.
- A collection with `records: files` reads one record; one without it reads two (frontmatter first, as now).
- The default flips to `files` in a later release (3.0), with a warning for collections still on frontmatter.
- `fact` and `seal` need an OKF branch for each setting; the tests cover both.

## Asks left open

1. When the default flips (3.0 is my recommendation), and whether the upgrade warns before then.
2. Whether `okf import` runs by itself when a bundle is shipped (`create`, a release step) or only when asked.

## History

- 2026-11-23: drafted from the owner's words: OKF "will need to rely on import and export for the default formats", "yes. an okf will need to use import / export". The two migration questions were answered here with a recommendation.
- 2026-11-23: accepted by dfoulks, in the seal dialog. Earlier values, word for word: `status: proposed`, `status-note: "drafted 2026-11-23 from the owner's words; awaiting ratification"`.
