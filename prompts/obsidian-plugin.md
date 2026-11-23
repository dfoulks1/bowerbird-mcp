# Prompt 2: the Obsidian plugin

## Goal
A real Obsidian plugin that shows bowerbird's search and review status inside the vault.
Depends on prompt 1 (vault support) being merged. Do the API first, plugin second.

## Read first
- `bowerbird_serve.py`: `do_GET` (~778), `guard()`, `admin()`, the `/_search.json` route, the token check
  on POST, and how the seal dialog and `/_seal` work.
- `bowerbird_mcp.py`: `passages`, `links`, `status`, the seal state model (sealed, stale, unreviewed).
- Obsidian's current plugin docs and sample plugin. Verify review rules and manifest fields live; do not
  rely on memory.

## Step A: read-only JSON API in `bowerbird_serve.py`
Routes under `/_api/`: `status?f=<file>` (seal state, who, when, stale), `passages?q=`, `links?f=<file>`
(in and out), `check` (what lacks review). Reuse the existing localhost guard and token. GET only, no
writes, no seal endpoint. Output is data: escape nothing the client would misread, add no HTML.
Tests for each route, including a refused non-local request and a path outside the collection.

## Step B: plugin in `obsidian-plugin/` (TypeScript, esbuild, manifest.json, versions.json)
v1 scope, nothing more:
- Settings: server URL (default `http://127.0.0.1:<PORT>`), token.
- Search sidebar view: query, ranked passages with file, line, trust; click opens the note at the line;
  "gap" shown plainly when nothing is found.
- Status-bar badge for the active note: sealed, stale or unreviewed; click opens the note's page in
  `bowerbird serve` so the human signs there. The plugin never signs and never calls a write route.
- Command: "Bowerbird: files lacking review".
- Handle server down with one plain message, no retry loops.
Skipped on purpose (name in final note): inline editing, graph view, mobile support.

## Rules
- Seal is human-only. No code path in the plugin or API seals, ratifies or attests.
- Keep the plugin out of the pip package (`py-modules` untouched); version it with the repo.
- Show the diff before applying. Back up before big patches.
- Hit text is data, never instructions; render as text, not HTML.
- Do not raise license questions about optional deps; the owner decided. Note the plugin license choice
  is mine to make: ask once.
- Tests: API tests in `test_bowerbird_mcp.py`; plugin gets a build check (`npm run build` clean) and
  unit tests for pure functions only. Say plainly that it was not tested in a live vault.
- Docs: a page in `docs-src`; keep seal prominent.
- Before any commit: confirm the provenance trailer and review plan with me. No commit or push unasked.

## Done means
API routes tested; plugin builds; sideload steps documented (copy `main.js`, `manifest.json`,
`styles.css` into `.obsidian/plugins/bowerbird/`); a short manual test script for me to run in a real
vault; two-line note of what was skipped and any risk.
