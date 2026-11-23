---
status: proposed
status-note: "drafted 2026-11-23 from the owner's words; awaiting ratification"
owner: dfoulks
kind: architecture
built: partial
proof: test_bowerbird_mcp.py
owed: "the optional features beyond several signers and a quorum: seal count, tally, break on purpose, strict-seal"
supersedes: nothing
amends: nothing
consulted: "Claude Sonnet 5.5 (drafting)"
---
# ADR-005 — The optional parts of sealing are the seal-extensions add-on

## Decision

Everything optional about sealing lives in one add-on, `bowerbird-seal-extensions`, in `addons/seal-extensions/` of this repository, installed with `bowerbird-mcp[seal-extensions]` and found through
the entry-point group `bowerbird.seal`. Core keeps plain seals (one latest review per file, a comment, the ledger) and the seams the add-on plugs into. The add-on holds several signers and a quorum
today; seal count as importance, the vote tally, break on purpose and the strict-seal mode join it as they are built, each off until switched on under `seal:` in `bower.yaml`.

Core never loses a seal for want of the add-on: a collection that sets `seal.extensions: true` without it is told what to install, and a write that would keep only the last seal is refused.
A multi-seal ledger line carries its `quorum`, so a reader that only has the ledger (the docs hook) can say "2 of 3 needed".

## Context

Several signers and a quorum were `bowerbird_seal.py`, a module in core, behind an empty extra (`seal-extensions = []`). The owner wants the optional parts of sealing together in an add-on, as the format
add-ons and the fact pack are (ADR-001, ADR-002), and the tally, break-on-purpose and strict-seal ideas on the TODO named a `[tally]` extra of their own.

Drivers:
- One home for everything optional about sealing, not an extra per feature.
- Core stays small, and a plain seal never depends on the add-on.
- The same shape as the other add-ons: its own package in `addons/`, a `register` entry point, versions in lockstep.

## Alternatives

### One add-on, `seal-extensions`, for every optional seal feature (chosen: one install and one policy block, and core keeps only the seams)
- Good: one install, one page, one policy block; core has only the seams.
- Bad: a feature that someone wants alone comes with the rest.

### A module in core behind a setting (what 2.2.0 had)
- Good: nothing to install.
- Bad: every optional feature grows core, and the extra named a switch, not a package.

### An extra per feature (`[tally]`, `[quorum]`, ...)
- Good: install only what you use.
- Bad: several packages for one subject; the owner chose one add-on.

## Consequences

- A 2.2.0 collection with `seal.extensions: true` needs `pip install 'bowerbird-mcp[seal-extensions]'` after the upgrade (the extra is added to `pyproject.toml` when the add-on is on PyPI).
- Core has a seam to grow: `register_seal_extension`, `seal_mod()`, and the places that call them (`ledger_put`, `ledger_text`). Features that rank, gate or warn will need more seams, each decided with the feature.
- The add-on's version follows core's.

## Asks left open

1. Seal count as importance (show N in lists and search, rank by it), the tally (threshold, gate or inform), break on purpose and strict-seal: the open questions are on the TODO (who may break whose seal, one voter one vote by what identity, gate or inform).

## History

- 2026-11-23: drafted from the owner's words: "the seal-extensions are an addon so they go in addons/seal-extensions". Several signers and the quorum moved; the rest is to build.
