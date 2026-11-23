# AsciiDoc

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The commands and output on this page were run for real; long lines are shortened. A person has not reviewed this page yet. -->

**Use it when** your docs are written in AsciiDoc (manuals, guides, books) and you want to ask questions of them and
know which a person has checked.

## Switch it on

```text
manual/
  bower.yaml             format: asciidoc
  rollback.adoc
  deploy.adoc
  .waxseals.yaml         appears when someone seals a file (commit it)
```

```yaml
# bower.yaml
format: asciidoc
about: The operations manual.
```

## What it reads

The files `*.adoc` and `*.asciidoc`.


```asciidoc
= Rollback runbook
:tags: ops, deploy
:status: stable

How to undo a bad release.

== Steps

Run the rollback script, then check the dashboards.

See xref:deploy.adoc[the deploy guide].
```

The `= Title` is the document title and each `==` section is one passage. The header's `:name: value` attributes are
the file's metadata (`tags`, `status`, `description`); a YAML front matter block works too, and wins where both say
the same thing.

```text
file: rollback.adoc, line: 8, heading: Rollback runbook > Steps, type: asciidoc, status: stable, tier: unverified
text: Run the rollback script, then check the dashboards. / See xref:deploy.adoc[the deploy guide].
```

Links written as `xref:`, `link:` or `<<file.adoc#id>>` count towards ranking (`links` on `deploy.adoc` is 1 here).

## Reviews and lint

A file is sealed as a whole, in a `.waxseals.yaml` in the file's folder (see [Sealing](../sealing.md)). A server offers `passages`, `reindex`, `seal` and `heatmap` (who edits what, from git history).
There is no `lint` or `fact` for AsciiDoc, and `[[wikilinks]]` are not read (in AsciiDoc, `[[x]]` is an anchor).

## Limits

- `include::` lines are not followed, so a passage holds the file's own text.
- A link to a file that is not `.adoc` or `.asciidoc` is not a link here.
- A server does not offer `get`, `list`, `status`, `links`, `search` or `move`; those are Markdown tools.
- A review covers the file's own text, not what it includes.
