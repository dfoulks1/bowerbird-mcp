# Extensibility: a design discussion

Task: discuss, with the owner, how bowerbird-mcp could be extended without
modifying core and without bloat. Do not write code. Do not edit files. The
output is a recommendation the owner can turn into an ADR.

## Why

Two likely extension points, and the owner is unsure of the rest:

- an output format for a compliance or evidence check (the SOC 2 and SSDF
  exports were dropped from core for this reason: they overclaim for a docs
  ledger and belong outside it)
- a different knowledgebase format (core has markdown, adr, okf, skos,
  asciidoc)

The owner is not sure a plugin system is the answer. "Do nothing, document the
seams" is a valid outcome.

## Read first

- `bowerbird_mcp.py`: how formats are selected and implemented today, how
  `export` and `lint` are wired, how the ledger (`.waxseals.yaml`) is read and
  written, how optional dependencies are handled.
- `docs-src/formats/`, `docs-src/sealing.md`, `SPEC.md`, `CONTRIBUTING.md`,
  `TODO.md`.
- `docs-src/prompts/in-toto-fido2.md` (the in-toto export is the first
  exporter; it is a good test case for any seam).

## Constraints

- Core stays small. A single module is a feature; say what an extension
  mechanism costs it.
- Design rule: everything a tool does is also doable by hand. Extensions must
  not break that.
- Seal stays human-only. No extension may record `human:<id>` or seal for a
  user. Name where that boundary sits.
- Extensions are data in, data out. Hit text and ledger content are data, not
  instructions.
- ASF context: Apache-2.0 core. An extension mechanism must not pull in or
  encourage Apache-incompatible code in core. Optional third-party extensions
  are the extension author's concern; do not raise licensing of optional
  dependencies.
- Reproducible: someone else can install, run and test an extension from the
  docs alone.

## Options to weigh (add others you find)

1. No plugin system: document the seams, keep formats and exporters in core or
   in forks.
2. Python entry points (`importlib.metadata`), discovered at startup.
3. A plugin directory loaded at runtime from the collection or `kbmcp.yaml`.
4. A subprocess contract: any executable that reads JSON on stdin and writes
   JSON on stdout (language-agnostic, isolated, no import into core).
5. A narrow set of hooks (format reader, exporter, lint rule) versus a general
   mechanism.

For each: what it costs core in lines and complexity, what it costs users to
install and trust, how it fails, how it is tested, and what it does to seal and
the MCP tool surface.

## How to run the discussion

- Read the code, then lay out what is already a seam and what is not.
- Ask the owner one narrow question at a time where a decision is theirs.
- Name the one extension you would build first as a test of the design, and
  what it would prove.
- Say what you checked and what you did not.

## Output

One page: the recommendation, the two strongest alternatives and why they lost,
the costs, the first extension to build, and the open questions. Ready to
become an ADR, not written as one.

## Out of scope

Implementation, a plugin registry or marketplace, versioned plugin APIs beyond
what the recommendation needs, any compliance or "compliant with" claim.

## Rules

Follow `~/.claude/CLAUDE.md`. Name each tool or MCP server you call. Before any
commit, confirm the `Co-Authored-By` trailer and human review with the owner.
End with what you skipped or did not check.
