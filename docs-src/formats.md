# Formats

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The tables are built from the code's own role and tier lists; each format's page has its commands and output, run for real. -->

Bowerbird is not tied to one way of keeping knowledge. A `bower.yaml` at the root of a folder says what the folder
holds, with one line:

```yaml
format: markdown      # markdown | adr | okf | skos | asciidoc | seal-only, or one an add-on supplies: obsidian | foam | dendron | logseq
```

All six share the same ideas: the folder is a git repository, `bower.yaml` is committed with it, and a human's
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
- **Choose [Obsidian](formats/obsidian.md), [Foam](formats/foam.md), [Dendron](formats/dendron.md) or [Logseq](formats/logseq.md) if** your notes live in that tool and you want search, link checking and reviews over them as they are. Each is an add-on (see below).
- **Choose [Seal-only](sealing.md#seal-only) if** you need a guaranteed human review of code, configuration or any text files, and no search.

## Format add-ons

Obsidian, Foam, Dendron and Logseq write notes the same way (markdown with `[[wikilinks]]`) and differ in the details: which side the alias is on, how a
name finds a file, which folders are the tool's own. Bowerbird reads the shared part itself: `[[Note]]`, `[[Note#Heading]]`, `![[embed]]`, in every
format, with a broken one reported as a `dead_link` or `dead_anchor` warning by `lint`. What is particular to one tool lives in an add-on you install
as an extra:

| Format | Install | Page |
|---|---|---|
| `obsidian` | `pip install 'bowerbird-mcp[obsidian]'` | [Obsidian](formats/obsidian.md) |
| `foam` | `pip install 'bowerbird-mcp[foam]'` | [Foam](formats/foam.md) |
| `dendron` | `pip install 'bowerbird-mcp[dendron]'` | [Dendron](formats/dendron.md) |
| `logseq` | `pip install 'bowerbird-mcp[logseq]'` | [Logseq](formats/logseq.md) |

An add-on's files are markdown, so each format behaves as [Markdown](formats/markdown.md) (same tools, same sealing) with its own reading of links.

**Writing one.** An add-on is a Python package with an entry point in the group `bowerbird.formats`, naming a function that takes the `bowerbird_mcp`
module and calls `register_format(name, ...)`. Every argument after the name is optional:

| Argument | What it does |
|---|---|
| `about` | One line for the server's instructions: "an Obsidian vault". |
| `skip` | Folder names the tool leaves out: its own state (`.obsidian`). |
| `alias_first` | The alias is written first, `[[alias\|note]]`. |
| `page` | Turns a file's path (lowercase, without `.md`) into the page name a link uses for it. |
| `clean` | Removes what is not a link from the body before links are read (Obsidian's `%%comments%%`). |
| `links` | Links the tool writes besides wikilinks, each as `[[Note#heading]]`. |
| `virtual` | Says a page exists without a file (a Dendron stub, a Logseq journal). |
| `quiet` | Lint kinds the tool's files are not held to. |
| `lint` | A function `(root, docs)` returning the findings (`finding(...)`) for what the tool's files get wrong. |

A format that fails to load is said once on stderr and left out, so a broken add-on does not stop Bowerbird. The four above are in this repository
under `addons/`; read one for a working example.

## Changing your mind

Change the `format` line and run `bowerbird-mcp reindex`; nothing else moves. Reviews are not converted between formats: an OKF
concept keeps its `verified` entries in its own frontmatter, while the other formats keep theirs in
`.waxseals.yaml`, so after a switch the notes may need sealing again.

## Tools by format

Which tools a server offers, by role. The role is what `roles:` in `bower.yaml` turns on (all five are on by default;
`--role` or `BOWERBIRD_ROLE` picks one for a single server). Naming a role that is off refuses to start.

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
| **[`fact`](tools.md#fact)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`factcheck`](tools.md#factcheck)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`fix`](tools.md#fix)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`lint`](tools.md#lint)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`new`](tools.md#new)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
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
| **[`create`](tools.md#create)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`provenance`](tools.md#provenance)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`reindex`](tools.md#reindex)** | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| **[`upgrade`](tools.md#upgrade)** | CLI | CLI | ✓ | CLI | CLI | CLI |

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **Tools offered** | 13 | 14 | 34 | 3 | 4 | 1 |

(`dirs` sits in both `read` and `structure`, so it counts once. The 34 are all of [Tools](tools.md).)
