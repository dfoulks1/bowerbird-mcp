# TODO

Only what is open. What is done is in `CHANGELOG.md`.

## Before 2.2.0 ships (the owner)

- [ ] QA: `tools/QA.sh` on 3.10 to 3.14 (3.12 once failed a test that starts a subprocess without `yaml`), the Web UI in a browser, the docs
      hook with fact blocks, `factcheck --fetch` on a real page and a real Jira, and `uvx --from 'bowerbird-mcp[semantic]'` (needs 2.2.0 on PyPI).
- [ ] Re-seal the pages edited since they were sealed, then `tools/QA.sh --rebuild` to rebuild `docs/`, and commit it.
- [ ] Tag, build and upload to PyPI. No `gh release`.

## 2.3

- [ ] Drop the fallbacks for the old names: `kbmcp.yaml`, `KB_*`, `kbmcp.nolint`, the `.kbmcp/` cache, and reading `kb-index` markers.
- [ ] Distributed waxseals: a ledger per folder, not one `.waxseals.yaml` at the collection root, so seals live beside what they cover (as a
      folder's own `bower.yaml` already scopes its format). Open: where a ledger sits when a file's folder has none; how `move` carries a seal
      across ledgers; how `seal check` and `serve` merge them.

### Facts and seals

- [ ] Writing a fact as a person: `fact` writing the block into the document for an agent; `result=-` and `result=@file`; a `--harvest` capture;
      a terminal "still true? y/n" walk for sources a machine cannot read.
- [ ] More fact kinds (the registry takes them): `[fact.file](path#L10-20)`, read by the tool with no network; scoped claims; a quote to watch
      for paraphrases.
- [ ] Two fact records exist: blocks (`.facts.yaml`) and the agent's `sources` frontmatter with `fact_sha256`. `okf export` and `okf import`
      bridge them. Decide whether one should replace the other.
- [ ] `serve`: show a block's fact state, and a file's several signers and comments (the docs hook shows the latest seal only).
- [ ] `seal-extensions`: show "N of M signed" in the `serve` modal and the docs badge; test that `move` carries every seal.
- [ ] `factcheck --fetch` against real pages that block it (StackOverflow, say); semantic mode against the real embedder.

## Later

- [ ] Vote tally. Several signers and a quorum exist (`seal-extensions`); still open: a seal as a vote, a break-on-purpose and a strict-seal mode,
      seal count as importance, `seal.tally`. A tally counts distinct human sealers per file or ADR from the ledger, each only while the sha256
      still matches (an edit voids the votes, like a stale seal).
  - **Break on purpose.** A file with N seals costs N to change: before an edit the tool warns "this was reviewed (N seals); once you change it, it
    must be resealed before you can commit", and each seal is broken as a named, ledgered act, not by silent hash drift. A pre-commit hook
    enforces the second half: no commit of a file whose seals are broken or stale until it is sealed again.
  - **Strict-seal mode.** Editing a file with N seals opens a `serve` modal, one step per seal (who, when, "break this seal"); the edit unlocks after the
    last, and each break is a ledger entry. The real gate is a pre-commit or Claude Code hook that refuses writes to a file with live seals
    (agents included; they never break one). Likely rule: a person breaks only their own seal, and a ledgered owner override covers a departed
    sealer. Useful for ratified ADRs, charters, policy, security docs and release notes; pointless at N=1. Break as review-then-change: the
    person sees the proposed change and the seal it would break (the `review_ui` dialog, as RTC), approves, and only then does the edit apply.
    A denial writes nothing. Builds on the `rtc` branch, which stays off `main` until you say.
  - **Seal count as importance.** Show N wherever a file shows (docs badge, `serve` list, `seal check`, search results), and let `heatmap` and search
    rank by it, counting only live seals. Each seal is a person who judged the file worth their review, so the count is earned, not guessed.
    A heavily sealed file marks its subject as important, and a recurring multi-seal workflow marks the process as common; with the mode off
    a count means neither.
  - **Optional, not core:** off by default, switched on with `seal.tally` (threshold, gate or inform), or shipped as an add-on extra
    (`bowerbird-mcp[tally]`). Plain seals work unchanged without it.
  - **Open:** does the warning gate (refuse until broken) or only inform; who may break whose seal; one voter one vote, by what identity;
    threshold or quorum (ratify at N); approve only, or also object and abstain; where it shows. Each sealer also needs a way to find out
    (`seal check` in CI, or a notice on their next pull).
- [ ] Search for a generated site: `reindex export=search-index.json` writes every passage (file, heading, text, `status`, trust `tier`, stale) as JSON,
      and the theme loads it with a client-side library (MiniSearch or lunr), badging each result by tier. Keyword only; the generator maps file and
      heading to a URL. The stock MkDocs `search` plugin is the zero-code alternative, without tiers.
- [ ] A status-badge plugin for other site generators (`docs-src/badges.md` is the recipe): a ready-made one for Hugo or Jekyll.
- [ ] MCP prompts: answer from the collection and cite; review a decision record.
- [ ] Progress notifications from `reindex` over MCP (the CLI prints progress to stderr; the tool is not async).
- [ ] A loader registry (`sync` dispatches `load_md`, `load_skos` and `load_adoc` by format; a seventh format is the time).
- [ ] SKOS: count links across files for `hubs`.
