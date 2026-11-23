# Prompt 1: `bowerbird-mcp[obsidian]`, read an Obsidian vault

## Goal
Bowerbird reads an Obsidian vault as a collection. Switch: `obsidian: true` in `bower.yaml`, and an
`obsidian` extra in `pyproject.toml` (empty list, like `seal-extensions`, unless a dependency proves needed).

## Read first
- `bowerbird_mcp.py`: `walk()` (~1013), `links()` (~1978), `hrefs()`, `target()`, `tags_of()`, `search()`.
- `bower.yaml` settings handling, `CHANGELOG.md`, `CONTRIBUTING.md`, `test_bowerbird_mcp.py`.
- Confirm by grep what `hrefs()` and `target()` accept today. I found no wikilink handling.

## Build (smallest complete change)
1. `walk()` skips `.obsidian/` (and `.trash/`) when `obsidian` is on. Off by default, no behavior change.
2. Wikilink resolver: `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[Note#^block]]`, `![[embed]]`.
   Obsidian matches by shortest unique file name (case-insensitive, extension optional), or by path when
   given. Ambiguous name: resolve to none and report it, never guess. Ignore links inside code fences/spans.
3. Feed it into `links()` (`out` and `in`) so broken wikilinks show `exists: false`.
4. `aliases` frontmatter: searchable and resolvable as link targets. `tags`: accept `#a/b` nested tags and
   the YAML list or string forms, merge with inline `#tag` only if cheap; otherwise name it as skipped.
5. Frontmatter is optional in a vault. Make sure a vault with none still scans and lints clean outside okf.
6. Docs: one page in `docs-src` (set up, what is read, what is not). Keep seal prominent in the docs.

## Rules
- Show the diff before applying. Back up before any big patch.
- No dependency for a few lines. Any shortcut gets a `shortcut: <limit>, <when to upgrade>` comment.
- Do not raise license questions about optional deps; the owner decided.
- Tests: assert-based, with a small fixture vault (nested folders, a duplicate name, an alias, an embed,
  a code-fenced fake link, a `.obsidian/` folder). Run the full existing suite; nothing may regress.
- Never run seal, ratify or verify --attest. Humans sign.
- Before any commit: confirm the provenance trailer and review plan with me. No commit or push unasked.

## Done means
Fixture vault passes; `links` on a note returns correct in/out with wikilinks; suite green; CHANGELOG entry;
docs page; a final two-line note of what was skipped and any risk.
