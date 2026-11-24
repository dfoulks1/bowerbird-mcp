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
| `a___b.md` (or `a%2Fb.md`) | the page `a/b`: `___` and `%2F` in a file name are a namespace's `/` |
| `[[Sep 14th, 2020]]` | a journal page: it exists with no file of its own |
| `title:: A Better Title`, `alias:: tl, [[tt]]` | the page also answers to those names (the first lines of the file) |
| `((6700a8c1-...))` | a block reference: a link to the page that holds the block `id:: 6700a8c1-...` |
| `#tag`, `#[[two words]]`, `tags:: x, y` | tags of the page |

Logseq creates a page the moment you link to it, so **a link to a page with no file is not reported as broken**. It is how a page is born.
The files you see are only the pages that have content.

## How a name finds its page

By the page's file name with the encoding undone, case ignored (Logseq lowercases page names), or by a name the page gives itself with `title::` or `alias::`, so `[[A Title]]` finds a file `foo.md` that starts with `title:: A Title`.
The file name format comes from `:file/name-format` in `logseq/config.edn`: `___` is `/` (the default, and what a graph with no `config.edn` is read as), or, when a `config.edn` exists but has no `:file/name-format` (a legacy graph), `.`.
Journal titles are read in Logseq's default format, `MMM do, yyyy`, or the `:journal/page-title-format` of `config.edn`.

## Reviews and lint

Seal a file as in [Sealing](../sealing.md); the review goes in a `.waxseals.yaml` in the file's folder, and the file is never edited. `lint` is offered here as in [Markdown](markdown.md) and checks fact blocks. Because every page exists, it says nothing about links to
pages that have no file (`links` still shows them with `exists: false`); headings in `[[Page#Heading]]` are not checked either.

## Limits

- The outliner structure is not used: a page is searched as the markdown it is, with its bullets.
- Only the first lines of a file are read for `title::` and `alias::`; a property after the first few lines is missed.
- A journal page's file name (`journals/2020_09_14.md`) is a page named by the title format; the title format is read from `config.edn`, but other `config.edn` keys (`:hidden`, `:pages-directory`) are not.
- A journal file (`2020_09_14.md`) is named only for a date, so it is not read as an ADR record and sealing it asks for no `decision`.
- Queries (`{{query ...}}`) and the database version of Logseq are not read.

## Tested against

Made-up collections, not a real graph. The test builds this one in a temporary folder:

- `pages/z.md` holding `[[a/b]]`, `[[Sep 14th, 2020]]`, `[[nowhere]]`, `[[A Better Title]]`, `[[tl]]`, `((6700a8c1-...))`, `#tag1`, `#[[two words]]`, `#plain` and `tags:: x, y`; `pages/a___b.md`; `pages/titled.md` with `title::`, `alias::` and a block `id::`; `logseq/bak/old.md`; and a `logseq/config.edn`.
- What the test checks: `[[a/b]]` finds `pages/a___b.md`; a journal title needs no file; `[[A Better Title]]` and `[[tl]]` find `pages/titled.md`; the block reference finds `pages/titled.md`; `logseq/` is left out; a link to a page with no file is not reported; the tags are `tag1`, `two words`, `plain`, `x`, `y`; and a `config.edn` with no `:file/name-format` makes `.` a namespace slash, and a `:journal/page-title-format` of `yyyy-MM-dd` makes `[[2020-09-14]]` a journal page.
- Not tested: the legacy `a%2Fb.md` names, or any other `config.edn` key.

Nothing here has run against a real graph: only the small made-up collections above, in a temporary folder on Linux with Python 3.10, by the test suite
(`test_bowerbird_mcp.py`). Windows and macOS paths, large graphs and Logseq's own newer features are untested. The rules this page lists as unconfirmed come from
Logseq's own documentation, read second-hand.

## Report a problem

Something read wrong, a link reported broken that is not, or one missed: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Say which
format it is (`format: logseq`), the version (`bowerbird-mcp --version`), and give the smallest note or two that show it, never your private ones. More on
[reporting a problem](../troubleshooting.md#reporting-a-problem).
