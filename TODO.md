# TODO

Only what is open. What is done is in `CHANGELOG.md`. The 2.3 work is on the branch `2.3` (not pushed or merged).

## 2.3

Built and committed on `2.3`, ADR-004 included (`okf: {records: files}`, off by default). What is left is yours.

### Needs a person or a real environment

- [ ] Each format against a real vault (Obsidian, Foam, Dendron, Logseq). Only made-up collections have been tested (each format's page says which); the rules came from each tool's
      documentation, read second-hand, and the unconfirmed ones are listed on the page (case rules, duplicate names, what a tool does with links in code).
- [ ] A real MCP call for an `mcp` fact (it needs a `.mcp.json` and a server); every other kind has run for real.

### Release

- [ ] **Seal.** `seal check=true` is the list (about 40 files: the docs pages, the root `.md` files, the code and test files; the `docs-src/tools.md` page is derived and needs none). Three old
      ledger lines for files that moved or went (`addons/foam/...`, `addons/obsidian/...`, `bowerbird_seal.py`) are orphan warnings: delete those lines in `.waxseals.yaml`. `prompts/` is exempt.
- [ ] **Rebuild and commit.** `tools/QA.sh --rebuild` (badges come from the ledger, so after the seal); it must end `QA ok`. Commit the seals, ledgers and `docs/`. Untracked `docs-src/prompts/fact-test.md` and its `.facts.yaml`: delete or seal.
- [ ] **Merge, tag, build, upload, check:** the steps in `docs-src/releasing.md` (3 to 8): `git switch main && git merge --ff-only 2.3`, tag, build from the tag, `uvx twine upload dist/bowerbird_mcp-2.3.0*`, then check the install. One package; no `gh release`.

## Later

- [ ] **2.3.1: UI changes.** The badges and the Facts tab work (seen in a browser); polish goes in 2.3.1.

### Facts

- [ ] ADR-004 follow-ups: flip `okf.records` to `files` in 3.0 with a warning before; decide whether `okf import` runs by itself when a bundle ships; a test of `okf export` into a `files` collection and of the serve seal dialog on an OKF concept in `files` mode.
- [ ] Fact kinds nobody has asked for yet: scoped claims, and a quote to watch for paraphrases.
- [ ] Semantic mode passes a contradiction (a paraphrase scores 0.62 to 0.80, a swapped noun 0.65 to 0.80, so the score cannot tell them apart): require numbers and proper nouns to appear verbatim, or a second check.
- [ ] A captcha or login page with a lot of text still reads as a drift; only a redirect to another host and a page with almost no words are called an error.
- [ ] `okf import` gives a block fact of kind `file`, `key` and the rest the resource `<kind>:<source>`; decide what OKF readers should see for them.

### Seals

Everything optional about sealing belongs to the `seal-extensions` add-on (`bowerbird_seal_extensions.py`, in the one package), each feature off by default and switched on under `seal:` in `bower.yaml`; plain seals work unchanged
without it. Built there: several signers, a quorum and `seal.count`. The rest joins them:

- [ ] **Vote tally** (`seal.tally`: threshold, gate or inform). A seal as a vote. A tally counts distinct human sealers per file or ADR from the ledger, each only while the sha256
      still matches (an edit voids the votes, like a stale seal).
  - **Open, for the tally, break on purpose and strict-seal:** does the warning gate (refuse until broken) or only inform; who may break whose seal; one voter one vote, by what identity;
    threshold or quorum (ratify at N); approve only, or also object and abstain; where it shows. Each sealer also needs a way to find out (`seal check` in CI, or a notice on their next pull).
- [ ] **Break on purpose.** A file with N seals costs N to change: before an edit the tool warns "this was reviewed (N seals); once you change it, it
      must be resealed before you can commit", and each seal is broken as a named, ledgered act, not by silent hash drift. A pre-commit hook
      enforces the second half: no commit of a file whose seals are broken or stale until it is sealed again.
- [ ] **Strict-seal mode.** Editing a file with N seals opens a `serve` modal, one step per seal (who, when, "break this seal"); the edit unlocks after the
      last, and each break is a ledger entry. The real gate is a pre-commit or Claude Code hook that refuses writes to a file with live seals
      (agents included; they never break one). Likely rule: a person breaks only their own seal, and a ledgered owner override covers a departed
      sealer. Useful for ratified ADRs, charters, policy, security docs and release notes; pointless at N=1. Break as review-then-change: the
      person sees the proposed change and the seal it would break (the `review_ui` dialog, as RTC), approves, and only then does the edit apply.
      A denial writes nothing. Builds on the `rtc` branch, which stays off `main` until you say.
- [ ] **Seal count, what is left.** `seal.count` is built (`list`, `passages`, search rank, `seal check`'s `most_sealed`). Left: show N in the `serve` tree, rank `heatmap` by it
      (it ranks by git activity today), and rank a search by it for OKF (an OKF concept's count is shown, from its frontmatter seals, but only ledger seals move a search rank).
- [ ] **Move more into the add-on.** It holds four helpers (merge, collapse, signers, expand); the quorum logic, the count and the `serve` and docs displays are still in core. Put them behind a small
      interface (who signed, is the quorum met, how many) so core only asks. Optional: it changes nothing a user sees.

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
