---
status: accepted
status-note: accepted by dfoulks on 2026-11-23, in the seal dialog
owner: dfoulks
kind: design
built: landed
proof: test_bowerbird_mcp.py
supersedes: nothing
amends: ADR-001 (the form of a fact block)
consulted: "Claude Sonnet 5.5 (drafting)"
ratified-by: dfoulks
ratified-on: "2026-11-23"
---
# ADR-003 — A fact is `[fact.KIND]{metadata}(source) claim [fact.end]`, and nothing else is needed

## Decision

A fact is the span from `[fact.KIND]` to `[fact.end]`, in this form:

```text
[fact.KIND]{metadata}(source) the claim [fact.end]
```

The `{metadata}` is optional, a JSON or YAML mapping directly after the tag. The `(source)` is the kind's own words (`file path#L10-20`, `jira INFRA-1`). The old form without
metadata, `[fact.KIND](source) claim [fact.end]`, stays valid. The brackets delimit everything, so a person and an agent write the same thing and a parser needs no other record.
An agent may write the metadata as JSON, and the source as a JSON string or an array of strings, which read as the words joined by spaces.

**A fact's identity is its number**: `id`, the first key of the metadata, a whole number unique in the document. `factcheck` takes it. A fact with no `id` is known by a fingerprint of its
kind, source and claim, as in 2.2.0. The fingerprint is also kept with each check, so a fact whose words or source changed since its last check shows as unchecked, whatever its number.
`fix` gives each unnumbered block the next number (moving what was checked under the fingerprint to the number), and the `fact` tool takes the next number when it writes one.

The other metadata keys that mean something are `by`, `at`, `as_of`, `confidence`, `note`, `tags`, `stale_after` and `last_checked`; any other key is kept and shown. Results stay in
`.facts.yaml`. **A check writes `last_checked` (the day) into the metadata**, and a review ignores `id`, `last_checked` and an empty `{}` when it hashes the document, so numbering a fact
and checking it never stale a seal. Everything else in the metadata is part of what a person reviewed.

## Context

Facts today are `[fact.KIND](source) claim [fact.end]` (`bowerbird_facts.py`, ADR-001), with the state of each check beside the document and a second record, `sources` in OKF frontmatter, for
agents. The owner wants the bracketed span to be all a fact needs, with a place for who wrote it, when, and how sure, and a form an agent can write exactly. 2.2.0 collections already hold
blocks in the old form, so the new one must be a superset.

Drivers:
- One form for people and agents, so no second record is needed.
- Nothing already written breaks.
- A check and a renumbering must not break a review, though they write to the document (a review is bound to its bytes).

## Alternatives

### An optional `{metadata}` mapping and a JSON form for agents (chosen: one grammar, a superset of the old form)
- Good: old blocks still read; JSON and YAML both parse as one flow mapping; the id ignores metadata, so a note is not a new fact.
- Bad: two spellings of a source (words, or JSON) to document and test.

### Metadata required
- Good: one strict shape.
- Bad: every 2.2.0 block fails lint until rewritten. Rejected.

### Splitting `(SOURCE CRITERIA)` into two parts for every kind
- Good: uniform.
- Bad: it rewrites what every kind reads today. The owner kept each kind's own words in the parentheses.

### The check state kept only beside the document
- Good: a check never touches the document.
- Bad: the date and the number are not visible in the text, and a fact cannot be named without the state file. The owner chose to write `last_checked` and `id` into the metadata, and to have a seal ignore them.

## Consequences

- `fact` (the tool) writes this form (`kind`, `source`, `claim`, `meta`), so an agent's fact is a block; without `claim` it is still the older `sources` entry.
- The bibliography (the docs hook and `serve`) shows the metadata, and `factcheck` lists a fact as due when its `stale_after` says so.
- `lint` has `bad_fact_meta` (a wrong value in a key with a meaning) and reports a mapping that never closes.
- `fix` and `fact` write `id`, a check writes `last_checked`; both stay out of a review's hash, so a seal holds.
- Closing a `)` or `}` inside a string needs an escape (`%29`, `\\u007d`); a source with a literal `)` still ends at the first one.

## Asks left open

None. The owner settled the two that were open: `fix` adds the number to old blocks, and `factcheck` writes `last_checked`.

## History

- 2026-11-23: drafted from the owner's words: `[fact.TYPE]{KV: METADATA}(SOURCE CRITERIA)CLAIM[fact.end]`, "{metadata} optional", and "the idea is that `[fact.*] ... [fact.end]` is all you should need".
- 2026-11-23: the owner settled the open asks and added the number: `fix` adds `{id: N}` to old blocks, `factcheck` writes `last_checked`, a fact is named by its `id` (a number, first in the metadata), and a seal ignores `id` and `last_checked`.
- 2026-11-23: accepted by dfoulks, in the seal dialog. Earlier values, word for word: `status: proposed`, `status-note: "drafted 2026-11-23 from the owner's words; awaiting ratification"`.
