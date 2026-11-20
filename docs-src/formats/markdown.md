# Markdown

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command and output on this page was run for real; long lines are shortened. -->

**Use it when** you have a folder of notes and want to ask questions of it and know which of them a person has
checked. There is nothing to learn and nothing to convert.

```text
notes/
  bower.yaml             format: markdown
  deploy.md              plain Markdown, no header needed
  rollback.md
  .waxseals.yaml    appears when someone seals a note (commit it)
```

```yaml
# bower.yaml
format: markdown
about: Team notes.
```

```sh
bowerbird-mcp create holds=markdown about="Team notes." apply=true
bowerbird-mcp passages 'how do I roll back' output=text
```

A hit is a section of a note, with its file and line:

```text
file: rollback.md, line: 2, heading: Rollback, match: 100, type: null, status: stable, tier: unverified, links: 1
text: To roll back, redeploy the previous tag and confirm the dashboard is green.
```

Every hit says `tier: unverified` until a human has sealed that file. `links` counts the notes that link to it
(`deploy.md` links to `rollback.md`, so it is 1). Files named `index.md` and `log.md` are ordinary notes here.

**Reviewing.** At a terminal, `bowerbird-mcp seal deploy.md --attest` records you; over MCP a prompt asks you instead. The review
goes into `.waxseals.yaml`, never into the note:

```yaml
- {file: deploy.md, sha256: 6205ee8f20e4fa49559acc629e6639e87cc7ac5233fe496f18158236bdf659f6, by: 'human:you', at: '2026-11-16T14:40:51Z'}
```

One line per file; sealing it again replaces the line, and git keeps the earlier ones.

Edit the note afterwards and the `sha256` no longer matches: the review is broken, and the hit shows `unverified` and
`stale`. `bowerbird-mcp seal check=true` lists what has no review (for a pre-commit hook or CI).

**Starting a page.** `bowerbird-mcp new notes/deploy -T "Deploy"` writes `notes/deploy.md` from the markdown template (a title and
`tags`, then a heading) and refuses a file that exists. `-t okf` or `-t adr` picks another template.

## Use case: content for a generated website

Use Bowerbird to manage the content behind a website that a generator builds. The content is a folder of
Markdown or [AsciiDoc](asciidoc.md), the two formats site generators read. Bowerbird does
not build the site. It searches the source, and it guarantees that a person reviewed the exact text of each page before it
ships.

### Setup

A `bower.yaml` at the root of the content folder. This is the one this site uses:

```yaml
format: markdown      # or asciidoc
about: Bowerbird's documentation pages (the site source). Each page needs a human review.
seal: {exempt: ["/tools.md", "/prompts/**"], exempt_status: []}
```

Every page needs a review except the ones `seal.exempt` lists. A leading `/` anchors a pattern at the content folder's root.

### The loop

1. People and agents write and edit pages. An agent can search them with `passages`, which returns the section, file and
   line to cite, and whether a person has reviewed it.
2. `bowerbird-mcp seal check=true` lists the pages without a review of their current text. It changes nothing and exits 1 on findings:

   ```text
   $ bowerbird-mcp seal check=true
   files_checked: 16, total: 12
   unsigned  contributing.md
   unsigned  formats/adr.md
   unsigned  formats.md
   ...
   ```

3. A person reads a page and seals it, in the confirmation prompt or at a terminal with `--attest`. An agent never
   seals for them.
4. In CI, `bowerbird-mcp seal check=true since=origin/main` fails a pull request that changes a page without a review of the new
   version. Any edit after a seal makes it stale (`stale_signature`), so a reviewed page cannot change silently.
5. The generator builds the site.

Renaming a page with `move` keeps its seal when its text does not change (Markdown and ADR folders; AsciiDoc does not
offer `move`).

### Showing the review on the page

A badge that says who reviewed a page cannot live in the page: the seal covers its exact bytes, so writing the reviewer's name
into the file would break it. Keep one constant line in the source instead, and let the build fill it in from
`.waxseals.yaml`:

```text
<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. -->
```

This site does it with a MkDocs hook, `hooks/seal_banner.py`. At build time it hashes the page and looks the hash up in the
ledger, then renders one of four badges:

- **Reviewed:** "AI Generated, Human Reviewed at: *date-time*", when a person's seal matches this exact text.
- **Edited since its last human review:** the page has a seal, but the text has changed since.
- **Not yet human reviewed:** no person has sealed it.
- **Derived from the code:** the page is built from the code (the tool list, from its docstrings), so `seal.exempt` leaves it out and it needs no review.

The badge is built from the ledger, so it cannot go stale and the source never changes. A page that includes text from
elsewhere (as the Guide includes the README) is marked as not covered for that text.

The hook is written for MkDocs, which reads Markdown. For an AsciiDoc generator the pattern is the same (a constant line in
the source, a build step that reads `.waxseals.yaml`), but this site does not ship that hook and it is untested there.

### Order matters

The badge comes from the ledger, so every new seal changes the built site. Seal first, then build, then commit the build.
This repository's `tools/QA.sh` checks that the committed site matches a fresh build, so a build made before sealing fails it.

### What it does not do

- It does not check that the reviewer read the page. The prompt shows the start of the file; the reviewer is trusted to have
  read all of it, or the diff.
- The seal binds the source text, not the rendered page. A change to the theme or the generator does not touch it.
- Text a page includes from another file is not covered by the page's seal.
