# Formats

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The tables are built from the code's own role and tier lists; each format's page has its commands and output, run for real. A person has not reviewed this page yet. -->

Bowerbird is not tied to one way of keeping knowledge. A `bower.yaml` at the root of a folder says what the folder
holds, with one line:

```yaml
format: markdown      # markdown | adr | okf | skos | asciidoc | seal-only, or one an add-on supplies: obsidian | foam | dendron | logseq
```

All of them share the same ideas: the folder is a git repository, `bower.yaml` is committed with it, and a human's
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

Each format's page has the same parts where they apply: when to use it, how to switch it on, what it reads, reviews (and lint), and its limits. The four add-on pages also
say what they were tested against and how to report a problem.

## What the Markdown formats share

Markdown, ADR and the four add-on formats are all Markdown files, so they share these:

- **Wikilinks.** `[[Note]]`, `[[Note#Heading]]`, `[[Note|alias]]` and `![[embed]]` are links, as well as `[text](note.md)`. `links`, backlinks, `orphan` and `island` see them. A name matches the
  file's path (the `.md` is optional, the case is ignored), the shortest path first, then the nearest to the page. OKF reads them the same way. AsciiDoc and SKOS files do not (in AsciiDoc, `[[x]]` is an anchor).
- **`lint`**, offered to Markdown and ADR servers. It checks [fact](facts.md) blocks and links that lead nowhere (`dead_link`, `dead_anchor`), as warnings. It does not judge the files as OKF concepts.
- **`fact` and `factcheck`**, offered to Markdown and ADR servers: a claim and its source, written in the page and checked later (see [Facts](facts.md)).
- **`new`**, which starts a page from a template (`markdown`, `adr` or `okf`).
- **Reviews** in a `.waxseals.yaml` in each file's folder. The file is never edited.

## Format add-ons

Obsidian, Foam, Dendron and Logseq write notes the same way (Markdown with `[[wikilinks]]`) and differ in the details: which side the alias is on, how a
name finds a file, which folders are the tool's own. Bowerbird reads the shared part itself. What is particular to one tool lives in an add-on that ships in the one `bowerbird-mcp` package
(a module beside the others), and `format: <name>` in `bower.yaml` selects it. The extra of the same name installs nothing more; it keeps the install line valid:

| Format | Install | Page |
|---|---|---|
| `obsidian` | `pip install 'bowerbird-mcp[obsidian]'` | [Obsidian](formats/obsidian.md) |
| `foam` | `pip install 'bowerbird-mcp[foam]'` | [Foam](formats/foam.md) |
| `dendron` | `pip install 'bowerbird-mcp[dendron]'` | [Dendron](formats/dendron.md) |
| `logseq` | `pip install 'bowerbird-mcp[logseq]'` | [Logseq](formats/logseq.md) |

Two other add-ons are not formats: the [fact pack](fact-pack.md) (five more kinds of fact)
and `seal-extensions` (several people seal one version; see [Sealing](sealing.md#several-signers-and-a-quorum-the-seal-extensions-add-on)).

An add-on's files are Markdown, so each format behaves as [Markdown](formats/markdown.md) (same tools, same sealing) with its own reading of links, tags and names.

**Writing one.** A third-party add-on is a Python package with an entry point in the group `bowerbird.formats` (the four above are bundled and need none), naming a function that takes the `bowerbird_mcp`
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
| `tags` | Turns the body into the inline `#tags` it holds (the frontmatter `tags` are always read). |
| `names` | Turns a file's text and frontmatter into the other names its page answers to (aliases, a `title::`). |
| `resolve` | Turns a link as written into a file: a path, `None` (no file, and not broken) or `False` (not this tool's: use the default). |

A format that fails to load is said once on stderr and left out, so a broken add-on does not stop Bowerbird. The four above are modules at the root of this repository
(`bowerbird_obsidian.py` and the rest); read one for a working example.

## Changing your mind

Change the `format` line and run `bowerbird-mcp reindex`; nothing else moves. Reviews are not converted between formats: an OKF
concept keeps its `verified` entries in its own frontmatter, while the other formats keep theirs in
`.waxseals.yaml`, so after a switch the notes may need sealing again. (`okf export` and `okf import` carry an OKF concept's reviews and sources
to and from the ledgers: see [the command line](cli.md#moving-an-okf-concepts-history-okf-export-and-okf-import).)

## Tools by format

Which tools a server offers, by role. The role is what `roles:` in `bower.yaml` turns on (all five are on by default;
`--role` or `BOWERBIRD_ROLE` picks one for a single server). Naming a role that is off refuses to start. The four add-on formats offer what Markdown does.

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
| **[`fact`](tools.md#fact)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`fix`](tools.md#fix)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`lint`](tools.md#lint)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
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
| **[`create`](tools.md#create)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`factcheck`](tools.md#factcheck)** | ✓ | ✓ | ✓ | CLI | CLI | CLI |
| **[`index`](tools.md#index)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`provenance`](tools.md#provenance)** | CLI | CLI | ✓ | CLI | CLI | CLI |
| **[`reindex`](tools.md#reindex)** | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| **[`upgrade`](tools.md#upgrade)** | CLI | CLI | ✓ | CLI | CLI | CLI |

| | [**Markdown**](formats/markdown.md) | [**ADR**](formats/adr.md) | [**OKF**](formats/okf.md) | [**SKOS**](formats/skos.md) | [**AsciiDoc**](formats/asciidoc.md) | [**Seal-only**](sealing.md#seal-only) |
|---|---|---|---|---|---|---|
| **Tools offered** | 16 | 17 | 34 | 3 | 4 | 1 |

(`dirs` sits in both `read` and `structure`, so it counts once. The 34 are all of [Tools](tools.md).)
