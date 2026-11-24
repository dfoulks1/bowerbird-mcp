---
status: accepted
status-note: "ratified by dfoulks 2026-11-23, as accepted in the seal dialog (decision: accepted in .waxseals.yaml)"
ratified-by: dfoulks
ratified-on: "2026-11-23"
owner: dfoulks
kind: architecture
built: partial
proof: test_bowerbird_mcp.py
owed: "org-roam and sphinx extras"
supersedes: nothing
amends: nothing
consulted: "Claude Sonnet 5.5 (options and drafting)"
---
# ADR-002 — Format plugins: a shared wikilink base, a registry, and each tool's part in its own extra

## Decision

Release 2.3.0 puts one wikilink resolver in core and a registry through which an add-on supplies a format. Every feature
add-on ships as an extra, `bowerbird-mcp[<name>]`.

- **Base.** One shared resolver handles `[[Note]]`, `[[Note#Heading]]`, `![[embed]]` and `#tags`, with alias order and skipped
  folders as settings. It is on for every format; the default format stays `okf`. A broken `[[link]]` is a lint **warning**.
- **Registry.** An add-on registers a format loader and that format's own lint rules together. Each format plugin is
  responsible for keeping its linter right. Discovery is by entry point, extending ADR-001's mechanism from fact kinds to formats.
- **Extras.** What is specific to one tool lives in that tool's extra, not in base: `bowerbird-mcp[obsidian]`, `[foam]`,
  `[dendron]` and `[logseq]`, then `[org-roam]` and `[sphinx]`, which are different markups with their own loaders. Each is
  its own distribution in this repository, pulled in by the extra, and versioned in lockstep with core.

## Context

The default format is `okf` (`bowerbird_mcp.py:84`). Core has no wikilink code today. Obsidian, Foam, Dendron and Logseq are
one family: they share the link shape and differ in details (alias order, skipped folders, naming, block references). The
loader registry already stands on `TODO.md` ("a seventh format is the time"); org-roam and Sphinx are the seventh and eighth.
ADR-001 rules entry points for fact kinds only and leaves formats unruled; this ADR rules them. The per-tool syntax listed
here is from memory and is to be verified against each tool's current documentation before coding.

Drivers:
- What every wikilink tool shares is infrastructure, so core carries it.
- What one tool alone does belongs to that tool's add-on.
- Lint stays correct without the core knowing each tool: a plugin updates its own rules.
- One repository, one release (owner), 2.3.0.

## Alternatives

### Shared resolver in base, each tool's quirks in its own extra, registry for loaders and lint (chosen: the owner's rule that the common part is infrastructure and the specific part lives in the add-on)
- Good: core stays small; each tool is added without touching core.
- Bad: needs a registry seam and a distribution per tool.

### The four profiles as data in base
- Good: about ten lines each, no new distributions.
- Bad: core learns every tool's quirks. Overruled: the specific parts live in the add-ons.

### Wikilinks off until a format sets them
- Good: no behaviour change for collections that never use wikilinks.
- Bad: the shared check would not exist for anyone. Overruled: wikilinks are baked into base for every format.

### Empty extras as switches, like `seal-extensions = []`
- Good: nothing to build or upload.
- Bad: an extra with no distribution behind it cannot carry a tool's code. Rejected.

### Broken wikilink as a lint error
- Good: the same rule as a broken markdown link.
- Bad: existing collections would gain failing findings on upgrade. Rejected for a warning.

## Consequences

- Existing collections gain lint warnings for `[[Missing]]` in 2.3.0; nothing fails.
- Each plugin owns its lint rules, so core's linter shrinks over time to the shared checks.
- Each tool is a distribution to build, test and upload, in lockstep.
- The registry seam is a plugin surface; it needs a stable shape before a second party writes against it.

## Asks left open

1. The registry's shape: how a plugin declares a format, its loader and its lint rules, and what `sync` dispatches on.
2. The entry-point group for formats (`bowerbird.formats`?), and distribution names (`bowerbird-obsidian`?).
3. Verify each tool's syntax and quirks against its current docs (Obsidian, Foam, Dendron, Logseq, org-roam, Sphinx).
4. The order: loader registry, then the shared resolver and `[obsidian]`, then the rest.

## History

- 2026-11-23: drafted from the owner's answers in the same session as ADR-001 (record
  `docs-src/prompts/2026-11-23-adr-fact-kinds.md`, rounds 3 to 5 and the format discussion). Not yet asked as rounds: the open
  asks above.
- 2026-11-23: ratified by dfoulks, as `decision: accepted` in the seal dialog (ledger entry at 2026-11-23T13:26Z). Earlier values, word for word: `status: proposed`, `status-note: "drafted 2026-11-23 from the owner's answers; awaiting ratification"`. The header was updated here because the dialog records the decision in `.waxseals.yaml` only, not in the ADR header.

- 2026-11-23: amended, at the owner's request (see the section below); the ruled text is unchanged. Earlier header values, word for word: `built: not started`, `proof: "queued in TODO.md (2.3 and Later, the wikilink family)"`.
- 2026-11-23: amended, at the owner's request (see the last section): packaging changed to one wheel; the ruled text is unchanged. No header value changed.

## Amendment — 2026-11-23, dfoulks (at the owner's request)

Touches the header and Asks left open, not the Decision. Built now: the shared wikilink resolver, `register_format`, and the four extras `obsidian`, `foam`, `dendron` and `logseq`. Owed: `[org-roam]` and `[sphinx]`.
Ask 2 is answered by the code: the entry-point group is `bowerbird.formats`, and the distributions are `bowerbird-obsidian`, `bowerbird-foam`, `bowerbird-dendron` and `bowerbird-logseq` (in `addons/`). Asks 1, 3 and 4 stay open. The ruled text above is left as it was. The line number `bowerbird_mcp.py:84` in the Context is from 2.2.0 code; the default format is now at line 66.

## Amendment — 2026-11-23, dfoulks (at the owner's request): one package

Touches the Decision, Context and Consequences wherever each format's part is its own distribution (`bowerbird-obsidian`, `bowerbird-foam`, `bowerbird-dendron`, `bowerbird-logseq`). The ruled text above is left as it was; read it with this change.

Packaging changed to one wheel. The owner's words: "I want one pypi package instead of several, I hate dependency management." The four format modules ship in `bowerbird-mcp` (`bowerbird_obsidian.py` and the rest), registered as Bowerbird starts. The extras `obsidian`, `foam`, `dendron` and `logseq` stay as switches that add nothing, so every `pip install 'bowerbird-mcp[obsidian]'` line stays valid. The entry-point group `bowerbird.formats` remains open to third-party formats, and the registry and shared wikilink base are unchanged.
