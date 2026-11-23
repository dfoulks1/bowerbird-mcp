# ADR record: fact kinds, the core four and the fact-pack

2026-11-23 · makeadr, new ADR, 12 questions · lead Sonnet 5.5 · owner dfoulks. Not committed.

## Premises (checked)

| # | Premise | Checked by |
|---|---------|------------|
| P1 | Core has two kinds, `url` and `mcp`; `register()` and `attach()` are public | `bowerbird_facts.py:45-53`, `bowerbird_mcp.py:3680-3681` |
| P2 | `facts: types:` in root `bower.yaml` already makes any MCP tool a kind (`[fact.ticket]`) | `bowerbird_mcp.py` `declared_type` |
| P3 | `[fact.file](path#L10-20)` is a TODO line only, nothing built | `TODO.md:23` |
| P4 | An empty extra already exists as a switch: `seal-extensions = []` | `pyproject.toml:34` |
| P5 | Python floor is 3.10 (so `tomllib` is not guaranteed; `tomli` needed for `key` on `.toml`) | `pyproject.toml:10` |
| P6 | No decisions folder, no ADR, no entry-point code in the repo | `ls`, `grep entry_points` |
| P7 | A plugin system was discussed and left open: the owner "is not sure a plugin system is the answer"; entry points are its option 2 | `docs-src/prompts/extensibility-discussion.md:17,51` |
| P8 | `docs/` is generated from `docs-src/` by `tools/QA.sh --rebuild` | `TODO.md:9` |
| P9 | `TODO.md` is sealed (`by: human:dfoulks`); an edit makes the seal stale | `.waxseals.yaml:9` |

## Ruled in the chat (cited, not asked again)

- Rule, owner 2026-11-23: every feature add-on ships as an extra, `bowerbird-mcp[<name>]` (`[obsidian]`, `[fact-pack]`).
- Four core kinds: `mcp` (agents), `url`, `file`, `internal` (people). Owner, 2026-11-23.
- `file` may sit anywhere, outside the repo included; `internal` always names a document in a bower. Owner.
- `internal` keeps that name (not `bower`, not `kb`). Owner.
- Extra kinds ship outside core: `key`, `git`, `manual`, `until`, plus script output. Owner.
- Install handle: `bowerbird-mcp[fact-pack]` pulling a separate `bowerbird-fact-pack`. Owner.
- The pack lives in this repo, not its own. Owner.

## Defaulted

| Question | Default | Who does it so | veto |
|----------|---------|----------------|------|
| `internal` path base | root-relative, so it survives moving the citing page | markdown links in this collection use `/path` from root | veto: name another base |
| `file` path base | absolute, `~/`, or relative to the citing document's folder | markdown relative links | veto: root-relative instead |
| Release | 2.3.0 for the core four and the pack, with the format extras (the owner said "2.3.0 for the new format extras"; extended to the fact work to keep one minor release) | one release, lockstep (Q10) | veto: ship the core four as 2.2.1 |
| `file` line drift | the range is checked literally; shifted lines drift, re-baseline by editing the range | `url` checks words, not places | veto: search the whole file for the claim |
| `script` | root `bower.yaml` declares the argument list, no shell, terminal-only after the plan, stdout compared, non-zero exit is `skipped` | the `declared_type` rule: a page never picks what runs | veto: name another rule |
| `manual` interval | opt-in with `facts: manual_days: N`; unset is never due | Q9 | veto: a default of N days |
| Record location | `docs-src/prompts/` (where 01 and 02 live), not `docs/bbq` (build output) | P8 | veto: name a folder |

## Rounds

### Round 1

- Setup: template ADR+; folder `docs-src/decisions/` (README and TEMPLATE written; owner `dfoulks`, taken from the seal id, veto if wrong).
- Q1 seam: **fact kinds only**, entry-point group `bowerbird.fact_types`; nothing else about plugins is ruled.
- Q2 release: owner said "2.2.1 perhaps?" (tentative; asked again in round 2).

### Round 2

- Q3 release: **2.2.1**, confirmed after the semver note (a minor-sized change in a patch number; recorded as overruled in Alternatives).
- Q4 pack 1.0: **all five** (`key`, `git`, `manual`, `until`, `script`); recommendation to hold `script` to 1.1 overruled.
- Q5 pack missing: **lint error** naming `bowerbird-mcp[fact-pack]`; the docs build renders the block from recorded state (non-strict parse).
- Q6 site: **decisions are published and sealed**. Recommendation to keep them repo-only overruled. Consequence: each ADR needs a seal beside its ratification, and `decisions/` joins the nav.

### Round 3

- Q7 file trust: owner's words: "it's a read only process, the read is triggered by either a citation or a fact_check. only when it is requested that the fact be verified should the file be read." So: **read-only, read lazily, only when a check is requested**; no root allow-list and no terminal-only rule. Recommendation overruled. Risk to state in Consequences: a page can name any path a checker may read.
- Q8 internal: **text only, ignore seals.** A missing page or heading drifts; seal state is not consulted.
- Q9 manual: owner: "I don't think we should force fact_checks, make that optional." **No forced due date**; a re-confirm interval is opt-in. How it is switched on: open (asked in round 4).
- Q10 versioning: **lockstep**, same version, released together. Recommendation (independent with a floor) overruled.

### Round 4 and close

- Q3 reopened by the owner: "2.3.0 for the new format extras". Defaulted: the fact work rides in 2.3.0 too (see Defaulted).
- The rest of round 4 (`file` drift, `script`, `manual` opt-in) went to the Defaulted table: the owner said "I need you to write those please".
- The closing question ("Anything else to protect or avoid?") was skipped on the owner's instruction to write.
- Second ADR, `ADR-002-format-plugins.md`, written from the format discussion (wikilink base, registry, extras, lint owned by plugins).
- Not committed. The `Co-Authored-By` trailer and human review are to be confirmed before any commit.
