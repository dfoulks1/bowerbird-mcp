# Formats

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The tables are built from the code's own role and tier lists; each format's page has its commands and output, run for real. -->

Bowerbird is not tied to one way of keeping knowledge. A `kbmcp.yaml` at the root of a folder says what the folder
holds, with one line:

```yaml
format: markdown      # markdown | adr | okf | skos | asciidoc | seal-only
```

All six share the same ideas: the folder is a git repository, `kbmcp.yaml` is committed with it, and a human's
review is recorded against the exact bytes they reviewed (see [Sealing](sealing.md)).
`seal` is what guarantees a person was in the loop, for stored knowledge and for decisions alike. Renaming a file with
`move` keeps its seal when its text is unchanged.

Each format exists for a reason. Pick whichever fits what you keep; you can change your mind later (see
[Changing your mind](#changing-your-mind)).

- **Choose [Markdown](formats/markdown.md) if** you have notes, runbooks or docs, want to ask questions of them and know which a person has checked.
- **Choose [ADR](formats/adr.md) if** you record decisions and want a person's review to be what makes one accepted.
- **Choose [OKF](formats/okf.md) if** your knowledge needs sources, trust and freshness, kept by people and agents, and you want every tool.
- **Choose [SKOS](formats/skos.md) if** you keep a controlled vocabulary: a glossary, taxonomy or thesaurus.
- **Choose [AsciiDoc](formats/asciidoc.md) if** your manuals and guides are written in AsciiDoc.
- **Choose [Seal-only](sealing.md#seal-only) if** you need a guaranteed human review of code, configuration or any text files, and no search.

## Changing your mind

Change the `format` line and run `kb reindex`; nothing else moves. Reviews are not converted between formats: an OKF
concept keeps its `verified` entries in its own frontmatter, while the other formats keep theirs in
`.waxseals.yaml`, so after a switch the notes may need sealing again.

## Tools by format

Which tools a server offers, by role. The role is what `roles:` in `kbmcp.yaml` turns on (all five are on by default;
`--role` or `KB_ROLE` picks one for a single server). Naming a role that is off refuses to start.

**✓** a server offers it. **CLI** command line only (written for OKF files, so not offered outside OKF). **—** nothing to act on (seal-only indexes nothing).

### `seal`

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **[`seal`](tools.md#seal)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### `read`

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **[`dirs`](tools.md#dirs)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`get`](tools.md#get)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`heatmap`](tools.md#heatmap)** | ✓ | ✓ | ✓ | CLI | ✓ | CLI |
| **[`links`](tools.md#links)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`list`](tools.md#list)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`log`](tools.md#log)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`passages`](tools.md#passages)** | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| **[`search`](tools.md#search)** | ✓ | ✓ | ✓ | CLI | CLI | — |
| **[`status`](tools.md#status)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`vocab`](tools.md#vocab)** | CLI | CLI | ✓ | CLI | CLI | CLI |

### `write`

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **[`cite`](tools.md#cite)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`create`](tools.md#create)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`fix`](tools.md#fix)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`lint`](tools.md#lint)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`record`](tools.md#record)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`set`](tools.md#set)** | CLI | CLI | ✓ | CLI | CLI | CLI |

### `structure`

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **[`archive`](tools.md#archive)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`bundles`](tools.md#bundles)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`dirs`](tools.md#dirs)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`ingest`](tools.md#ingest)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`migrate`](tools.md#migrate)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`move`](tools.md#move)** | CLI | ✓ | ✓ | CLI | CLI | CLI |
| **[`rename`](tools.md#rename)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`split`](tools.md#split)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`unarchive`](tools.md#unarchive)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`web`](tools.md#web)** | CLI | CLI | ✓ | CLI | CLI | CLI |

### `lifecycle`

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **[`baseline`](tools.md#baseline)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`config`](tools.md#config)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`index`](tools.md#index)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`init`](tools.md#init)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`provenance`](tools.md#provenance)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`recheck_apply`](tools.md#recheck_apply)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`recheck_plan`](tools.md#recheck_plan)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`reindex`](tools.md#reindex)** | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| **[`upgrade`](tools.md#upgrade)** | CLI | CLI | ✓ | CLI | CLI | CLI |

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **Tools offered** | 12 | 13 | 35 | 3 | 4 | 1 |

(`dirs` sits in both `read` and `structure`, so it counts once. The 35 are all of [Tools](tools.md).)
