# Logseq

<!-- seal-banner: Written with Claude Sonnet 5.5. The link rules come from Logseq's own documentation, read second-hand; the checks are tests on throwaway collections, not yet a real graph. A person has not reviewed this page yet. -->

**Use it when** your notes are a Logseq graph kept as files (the markdown, file-based graph, not the newer database graph) and you want search
and reviews over them.

## Install and switch it on

```sh
pip install 'bowerbird-mcp[logseq]'          # or: uvx --from 'bowerbird-mcp[logseq]' bowerbird-mcp ...
```

```yaml
# bower.yaml, at the root of the graph
format: logseq
about: My notes.
```

The add-on is its own package (`bowerbird-logseq`, in this repository, released with `bowerbird-mcp`). The extra pulls it in, and Bowerbird finds it through the
`bowerbird.formats` entry point. Without it, `format: logseq` stops with a message that says to install it. Everything else is the
[Markdown](markdown.md) format: the same tools, the same sealing (`.waxseals.yaml` beside the files), and ADR records in it are sealed
with an outcome as in [ADR](adr.md).

## What it reads

The markdown in `pages/` and `journals/`, and any other folder of `.md` files in the graph. It leaves out `logseq/` (the graph's configuration and
backups) and `.recycle/`.

| You write | Bowerbird reads it as |
|---|---|
| `[[Page]]`, `[[Page/Sub]]` | a link to the page with that name |
| `[text]([[Page]])` | a link to the page |
| `{{embed [[Page]]}}` | an embed, read as a link |
| `((uuid))` | a block reference: not followed |
| `a___b.md` (or `a%2Fb.md`) | the page `a/b`: `___` and `%2F` in a file name are a namespace's `/` |
| `[[Sep 14th, 2020]]` | a journal page: it exists with no file of its own |

Logseq creates a page the moment you link to it, so **a link to a page with no file is not reported as broken**. It is how a page is born.
The files you see are only the pages that have content.

## How a name finds its page

By the page's file name with the encoding undone, case ignored (Logseq lowercases page names). The `title::` property, which can give a page a
name different from its file's, is not read, so `[[A Title]]` for a file `foo.md` with `title:: A Title` finds nothing.
Journal titles are read in Logseq's default format, `MMM do, yyyy`.

## Reviews and lint

As in [Markdown](markdown.md): seals live in a `.waxseals.yaml` beside the file. Because every page exists, `lint` says nothing about links to
pages that have no file; headings in `[[Page#Heading]]` are not checked either.

## What it does not do yet

- `title::` and `alias::` properties, `#tags` and `#[[multi word tags]]`, and block references are not read.
- The outliner structure is not used: a page is searched as the markdown it is, with its bullets.
- `config.edn` is not read: a graph with other `:pages-directory`, `:journal/page-title-format` or `:file/name-format` settings than the defaults
  may not resolve every name.

## Tested against

Made-up collections, not a real graph. The test builds this one in a temporary folder:

- `pages/z.md` holding `[[a/b]]`, `[[Sep 14th, 2020]]` and `[[nowhere]]`; `pages/a___b.md`; and `logseq/bak/old.md`.
- What the test checks: `[[a/b]]` finds `pages/a___b.md`; a journal title needs no file; `logseq/` is left out; and a link to a page with no file is not reported.
- Not tested: the legacy `a%2Fb.md` file names, `title::`, or a `config.edn` with a different file name format.

Nothing here has run against a real graph: only the small made-up collections above, in a temporary folder on Linux with Python 3.10, by the test suite (`test_bowerbird_mcp.py`). Windows and macOS paths, large graphs and Logseq's own newer features are untested. The rules this page lists as unconfirmed come from Logseq's own documentation, read second-hand.

## Report a problem

Something read wrong, a link reported broken that is not, or one missed: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Say which
format it is (`format: logseq`), the version (`bowerbird-mcp --version`), and give the smallest note or two that show it, never your private ones. More on
[reporting a problem](../troubleshooting.md#reporting-a-problem).
