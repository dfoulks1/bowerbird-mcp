# AsciiDoc

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command and output on this page was run for real; long lines are shortened. -->

**Use it when** your docs are written in AsciiDoc (manuals, guides, books) and you want to ask questions of them and
know which a person has checked.

```text
manual/
  kbmcp.yaml             format: asciidoc
  rollback.adoc
  deploy.adoc
```

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

Links written as `xref:`, `link:` or `<<file.adoc#id>>` count towards ranking. `include::` lines are not followed, so a
passage holds the file's own text. A file is sealed as a whole, in `.waxseals.yaml`.
