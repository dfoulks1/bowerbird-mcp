# TODO

Only what is open. What is done is in `CHANGELOG.md`. The 2.3 work is on the branch `2.3` (not pushed or merged).

## 2.3

### Still to build

- [ ] **`fact` writes blocks.** `fact` writes the `[fact.*]` block into the document (it records a frontmatter `sources` entry today), for a person and an agent alike;
      `result=-` and `result=@file`; a `--harvest` capture of a page's words into a block.
- [ ] **Agent-run `factcheck` beyond the local kinds.** `url` and `mcp` still need a person at a terminal (`--fetch`). Decide what an agent may run, and what the plan and
      prompt look like.
- [ ] **OKF through import and export** (decided 2026-11-23). OKF keeps facts (`sources`) and reviews (`verified`) in frontmatter; it should use the records every other format
      uses (`.facts.yaml`, `.waxseals.yaml`), with `okf export` and `okf import` converting to and from the frontmatter OKF readers expect. Write the ADR first (ADR-003).
      Open: does it cover seals as well as facts; how an existing OKF collection migrates; what `fact` and `seal` write for OKF meanwhile.
- [ ] **Seal and fact state as data** for other tools (a JSON function, or `/_api/status` for the Obsidian plugin): `bowerbird_facts.render` returns the facts' side; the seals'
      side is still in the hook and `serve`.
- [ ] **The quorum's M in the docs hook.** The hook reads only the ledger, so a badge says who signed (`by ann, bo`) but not "2 of 3".
- [ ] **ADR-001's header** still says `built: not started`. The loader, `file`, `internal` and the pack are built (proof: `test_bowerbird_mcp.py`, `addons/fact-pack/`); make it
      `partial` until `fact` writes blocks, then `landed`. Editing it stales its seal.

### Needs a person or a real environment

- [ ] `factcheck --fetch` against real pages that block it (StackOverflow, say), and semantic mode against the real embedder.
- [ ] The new badges and the Facts tab in a real browser, and the bibliography in the built site (`tools/QA.sh --rebuild`); the tests cover the HTML, not how it looks.
- [ ] Each format against a real vault (Obsidian, Foam, Dendron, Logseq). Only made-up collections have been tested (each format's page says which); the rules came from each tool's
      documentation, read second-hand, and the unconfirmed ones are listed on the page (case rules, duplicate names, what a tool does with links in code).
- [ ] QA: `tools/QA.sh` on 3.10 to 3.14 (3.12 once failed a test that starts a subprocess without `yaml`), the Web UI in a browser, the docs hook with fact blocks, and
      `uvx --from 'bowerbird-mcp[semantic]'`.

### Release

- [ ] Re-seal the pages edited since they were sealed (the two ADRs, `TODO.md`, `BOWERBIRD.md`, the four new format pages and the other pages that changed; `docs-src/tools.md` is
      derived and needs none), then `tools/QA.sh --rebuild` to rebuild `docs/`, and commit it.
- [ ] Build and upload the add-on distributions to PyPI first (`bowerbird-fact-pack` and the four format add-ons, each at the release's version), then add the extras to
      `pyproject.toml` (`fact-pack`, `obsidian`, `foam`, `dendron`, `logseq`; `uv.lock` cannot resolve them before), then core. Tag; no `gh release`.
- [ ] Merge `2.3`. `prompts/` (the Obsidian drafts) is still untracked: commit it or leave it.

## Later

### Facts

- [ ] Fact kinds nobody has asked for yet: scoped claims, and a quote to watch for paraphrases.

### Seals

Everything optional about sealing belongs to `seal-extensions`: several signers and a quorum are there now; the rest below joins them.

- [ ] Vote tally. Several signers and a quorum exist (`seal-extensions`); still open: a seal as a vote, a break-on-purpose and a strict-seal mode,
      seal count as importance, `seal.tally`. A tally counts distinct human sealers per file or ADR from the ledger, each only while the sha256
      still matches (an edit voids the votes, like a stale seal).
- [ ] **Break on purpose.** A file with N seals costs N to change: before an edit the tool warns "this was reviewed (N seals); once you change it, it
      must be resealed before you can commit", and each seal is broken as a named, ledgered act, not by silent hash drift. A pre-commit hook
      enforces the second half: no commit of a file whose seals are broken or stale until it is sealed again.
- [ ] **Strict-seal mode.** Editing a file with N seals opens a `serve` modal, one step per seal (who, when, "break this seal"); the edit unlocks after the
      last, and each break is a ledger entry. The real gate is a pre-commit or Claude Code hook that refuses writes to a file with live seals
      (agents included; they never break one). Likely rule: a person breaks only their own seal, and a ledgered owner override covers a departed
      sealer. Useful for ratified ADRs, charters, policy, security docs and release notes; pointless at N=1. Break as review-then-change: the
      person sees the proposed change and the seal it would break (the `review_ui` dialog, as RTC), approves, and only then does the edit apply.
      A denial writes nothing. Builds on the `rtc` branch, which stays off `main` until you say.
- [ ] **Seal count as importance.** Show N wherever a file shows (docs badge, `serve` list, `seal check`, search results), and let `heatmap` and search
      rank by it, counting only live seals. Each seal is a person who judged the file worth their review, so the count is earned, not guessed.
      A heavily sealed file marks its subject as important, and a recurring multi-seal workflow marks the process as common; with the mode off
      a count means neither.
- [ ] **Optional, not core:** all of it lives in `seal-extensions` (`bowerbird_seal.py`, the extra that already holds several signers and the quorum), not in a separate
      `[tally]` extra. Each feature is off by default and switched on under `seal:` in `bower.yaml` (`seal.tally`: threshold, gate or inform). Plain seals work unchanged without it.
- [ ] **Open:** does the warning gate (refuse until broken) or only inform; who may break whose seal; one voter one vote, by what identity;
      threshold or quorum (ratify at N); approve only, or also object and abstain; where it shows. Each sealer also needs a way to find out
      (`seal check` in CI, or a notice on their next pull).

### Formats

- [ ] Format add-ons, what is read but not followed (take one when a real vault needs it): links inside Obsidian `.canvas` and `.base` files; Dendron schemas and wildcard and
      range references; Logseq `{{query}}` and `config.edn` keys other than the file name format and the journal title format; the Logseq database version.
- [ ] Other markups, each its own loader and extra: `[org-roam]` (org-mode, ID links) and `[sphinx]` (reStructuredText, `:ref:`, toctrees). They are not profiles of
      markdown, so they need the loader registry below.
- [ ] A loader registry (`sync` dispatches `load_md`, `load_skos` and `load_adoc` by format; a seventh format is the time). The registry for the markdown family
      (`register_format`, `bowerbird.formats`) is done; this one is for formats that are not markdown.
- [ ] SKOS: count links across files for `hubs`.
- [ ] The Obsidian plugin proper (`prompts/obsidian-plugin.md`), once the format is checked against a real vault.
- [ ] `[gollum]`, GitHub wiki repos, as a candidate add-on: the label comes before the pipe (`[[label|Page]]`) and page names turn spaces into dashes. From memory, unchecked: read the Gollum docs first.
      The base keeps label-after-pipe (`[[Note|label]]`) as its default; label-first stays a per-format setting (`alias_first`), not auto-detected.

### Other

- [ ] Search for a generated site: `reindex export=search-index.json` writes every passage (file, heading, text, `status`, trust `tier`, stale) as JSON,
      and the theme loads it with a client-side library (MiniSearch or lunr), badging each result by tier. Keyword only; the generator maps file and
      heading to a URL. The stock MkDocs `search` plugin is the zero-code alternative, without tiers.
- [ ] A status-badge plugin for other site generators (`docs-src/badges.md` is the recipe): a ready-made one for Hugo or Jekyll.
- [ ] MCP prompts: answer from the collection and cite; review a decision record.
- [ ] Progress notifications from `reindex` over MCP (the CLI prints progress to stderr; the tool is not async).
