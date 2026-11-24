---
status: accepted
status-note: accepted by dfoulks on 2026-11-23, in the seal dialog
ratified-by: dfoulks
ratified-on: "2026-11-23"
owner: dfoulks
kind: architecture
built: landed
proof: test_bowerbird_mcp.py
supersedes: nothing
amends: nothing
consulted: "Claude Sonnet 5.5 (options and drafting)"
---
# ADR-001 — Core ships four fact kinds, and the fact-pack ships the rest

## Decision

Release 2.3.0 ships four fact kinds in core: `url`, `mcp`, `file` and `internal`. Every other kind ships in a separate
distribution, `bowerbird-fact-pack`, built from `fact-pack/` in this repository and installed with
`bowerbird-mcp[fact-pack]`. Core finds the pack's kinds through the entry-point group `bowerbird.fact_types`; the pack calls
`register()` and `attach()`. The pack's first release has five kinds: `key`, `git`, `manual`, `until` and `script`. Core and
the pack share one version number and release together.

The four core kinds:

- **`url`** and **`mcp`** are unchanged.
- **`file`**, `[fact.file](path#L10-20) the claim [fact.end]`. The path is absolute, `~/…`, or relative to the citing
  document's folder; it may lie outside the collection. The lines are read, and every paragraph of the claim must still
  appear in them. Without `#L` the whole file is read. It is read-only, and the file is read only when a check is requested
  (a citation or a `factcheck`).
- **`internal`**, `[fact.internal](path/to/page.md#Heading) the claim [fact.end]`. The path is relative to the collection
  root and names a document in a bower. The section under the heading (the whole page without `#`) must still hold the
  claim's paragraphs. A missing page or heading is a drift. Seal state is not consulted.

The pack's five kinds:

- **`key`**: a value at a path in a structured file (JSON, YAML, TOML); the value is what is compared.
- **`git`**: a repository state, such as a tag or a path at a revision, read with the `git` binary.
- **`manual`**: a person's attestation of what no machine can read. A person confirms it at a terminal. No re-check is forced;
  an interval is opt-in (`facts: manual_days: N` in `bower.yaml`; unset means never due).
- **`until`**: a claim with an expiry date; it drifts when the date passes.
- **`script`**: a command's output, compared with the recorded output. The command is declared in the root `bower.yaml`
  only, as an argument list run without a shell; a page names a kind and a key and never a command. It runs only at a
  terminal, after the plan is shown. A non-zero exit is `skipped`, not `drifted`.

Without the pack, a page that uses one of its kinds is a lint error whose message names `bowerbird-mcp[fact-pack]`; the docs
build still renders the block from its recorded state.

## Context

Facts today are `url` and `mcp` (`bowerbird_facts.py:56-57`). `register()` and `attach()` are public (`bowerbird_facts.py:45-53`)
and `facts: types:` in the root `bower.yaml` already backs a kind with one MCP tool (`bowerbird_mcp.py`, `declared_type`), so the
registry exists and only discovery is new. `[fact.file]` was a TODO line only (`TODO.md:23`). The people who write facts need
kinds they can check themselves (a page, a file, another document); agents need the MCP kind. Everything else is either
optional or touches the machine, so it should not weigh on every install.

The collection's default format is `okf`; the Python floor is 3.10 (`pyproject.toml:10`), so `tomllib` is not guaranteed and `key`
on `.toml` needs `tomli` there. A plugin system was discussed and left open (`docs-src/prompts/extensibility-discussion.md`);
this ADR rules entry points for fact kinds only, and rules nothing about formats or exporters (see ADR-002 for formats).

Drivers:
- The core install stays small and checks only what a person or an agent can safely check.
- Kinds that run commands or read the machine are opt-in, by installing a package.
- One repository, one release, one test run (owner).
- A page may not add a kind or choose what runs.

## Alternatives

### Four kinds in core, the rest in a pack in this repo, found by entry points (chosen: smallest core that still ships the checks people need, and the only one where installing is the opt-in)
- Good: core stays lean; `script` and `git` stay off until someone installs the pack; one repo.
- Bad: a second distribution to build and upload; core and pack must release together.

### Every kind in core, switched on in `bower.yaml`
- Good: one package, no entry-point loader.
- Bad: `script` and `git` ship in every install; the owner chose a pack.

### A module list in `bower.yaml` instead of entry points
- Good: explicit, no startup discovery.
- Bad: installing the pack is no longer enough to use it. Overruled by the owner in favour of entry points.

### Release as 2.2.1
- Good: ships sooner.
- Bad: a new core surface (a loader, two kinds) in a patch number. Overruled: it is 2.3.0, with the format extras (ADR-002).

### Independent versions with a floor
- Good: a pack-only fix needs no core release.
- Bad: two version lines to explain. Overruled by the owner: lockstep, so a pack-only fix cuts a core release too.

### `script` held to a later pack release
- Good: the riskiest kind gets its rules tested before it ships.
- Bad: delays a kind the owner wants. Overruled: it ships in the first release, with its guardrails (declared in the root
  `bower.yaml`, no shell, terminal only).

### Read `file` only inside the collection, or only at a terminal
- Good: a page cannot send a checker to a path the owner never saw.
- Bad: friction for every outside path. Overruled: the read is read-only and happens only when a check is requested. No allow-list.

## Consequences

- `file` and `internal` let a person cite a file or another page and have a check, with no network.
- A page can name any path a checker may read (`file`, absolute paths included). The read is read-only and lazy; nothing
  is returned beyond whether the claim still holds, but a checker run by someone else reads what the page names.
- `bowerbird-mcp[fact-pack]` requires `bowerbird-fact-pack`, which requires `bowerbird-mcp`. pip and uv accept the loop.
- Lockstep means the pack carries core's version number. A pack-only fix is a core release.
- Decisions are published and sealed (owner). Each ADR needs a seal on top of its ratification, and a line in the site's `nav:`.
- 2.2.0 ships as built. This work is 2.3.0.

## Asks left open

1. Does `move` rewrite an `internal` source when its target page moves, as it does for links?
2. The exact source syntax for `key` (`file key.path`?), `git` and `until`, and `manual`'s record of who confirmed.
3. `file` line ranges: if lines shift, is that a drift (the default) or should the check search the file for the claim?

## History

- 2026-11-23: drafted from the owner's answers (question record `docs-src/prompts/2026-11-23-adr-fact-kinds.md`). Asks
  1 to 3 were defaulted as listed in the record's Defaulted table; the owner may veto.
- 2026-11-23: ratified by dfoulks, as `decision: accepted` in the seal dialog (ledger entry at 2026-11-23T13:26Z). Earlier values, word for word: `status: proposed`, `status-note: "drafted 2026-11-23 from the owner's answers; awaiting ratification"`. The header was updated here because the dialog records the decision in `.waxseals.yaml` only, not in the ADR header.
- 2026-11-23: accepted by dfoulks, in the seal dialog. Earlier values, word for word: `status: accepted`, `status-note: "ratified by dfoulks 2026-11-23, as accepted in the seal dialog (decision: accepted in .waxseals.yaml)"`.

## Amendment — 2026-11-23, dfoulks

Touches the Decision (the pack's `script` and `manual`) and Consequences. The owner ruled that an agent should run anything it needs to check a fact. So `script` no longer runs only at a terminal, and
`--fetch` is no longer refused over MCP: a person at a terminal is still shown the plan and asked, and an agent or a script is not, and gets the plan back as `ran`. What does not change: only a command
declared in the root `bower.yaml` runs (a page never names one), and `manual`, which asks a person, is skipped for an agent. The ruled text above is left as it was.

- 2026-11-23: amended (see the section above); the ruled text is unchanged.

## Amendment — 2026-11-23, dfoulks (at the owner's request)

Touches the Context only. The line numbers in the ruled text (`bowerbird_facts.py:56-57` and `:45-53`, `TODO.md:23`, `pyproject.toml:10`) refer to the 2.2.0 code; in 2.3.0 `register()` and `attach()` are at `bowerbird_facts.py:48-57` and the `url` and `mcp` kinds at lines 60-61. The ruled text above is left as it was.

- 2026-11-23: amended (see the section above); the ruled text is unchanged.
