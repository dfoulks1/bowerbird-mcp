---
status: proposed
status-note: "drafted 2026-11-23 from the owner's words; awaiting ratification"
owner: dfoulks
kind: design
built: landed
proof: test_bowerbird_mcp.py
supersedes: nothing
amends: ADR-001 (the form of a fact block)
consulted: "Claude Sonnet 5.5 (drafting)"
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

The metadata keys that mean something are `by`, `at`, `as_of`, `confidence`, `note`, `tags` and `stale_after`; any other key is kept and shown. The metadata is not part of a fact's id
(the kind, the source and the claim are), and a check never writes to it: results stay in `.facts.yaml`, so a check cannot change the document or stale a review.

## Context

Facts today are `[fact.KIND](source) claim [fact.end]` (`bowerbird_facts.py`, ADR-001), with the state of each check beside the document and a second record, `sources` in OKF frontmatter, for
agents. The owner wants the bracketed span to be all a fact needs, with a place for who wrote it, when, and how sure, and a form an agent can write exactly. 2.2.0 collections already hold
blocks in the old form, so the new one must be a superset.

Drivers:
- One form for people and agents, so no second record is needed.
- Nothing already written breaks.
- A check must not change the document (a review is bound to its bytes).

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

### Writing the date of the last check into the metadata
- Good: the date is visible in the text.
- Bad: it is accepted as any other key, but no tool writes it: writing it would change the document at every check and break the review of it. The owner's example showed it; rejected as a written field.

## Consequences

- `fact` (the tool) writes this form (`kind`, `source`, `claim`, `meta`), so an agent's fact is a block; without `claim` it is still the older `sources` entry.
- The bibliography (the docs hook and `serve`) shows the metadata, and `factcheck` lists a fact as due when its `stale_after` says so.
- `lint` has `bad_fact_meta` (a wrong value in a key with a meaning) and reports a mapping that never closes.
- Closing a `)` or `}` inside a string needs an escape (`%29`, `\\u007d`); a source with a literal `)` still ends at the first one.

## Asks left open

1. Should `fix` add an empty `{}` or `{by: ...}` to old blocks? (I would not: it changes bytes and stales reviews.)
2. Is `lastchecked` better as a computed field in `factcheck` output than as a key a person may write?

## History

- 2026-11-23: drafted from the owner's words: `[fact.TYPE]{KV: METADATA}(SOURCE CRITERIA)CLAIM[fact.end]`, "{metadata} optional", and "the idea is that `[fact.*] ... [fact.end]` is all you should need".
