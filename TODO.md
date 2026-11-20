# TODO

What is done is in `CHANGELOG.md`; this file is only what is still open. Notes on the 2.2.0 scope are in `docs-src/prompts/02-release-2.2.0.md`.

## Before 2.2.0 ships (the owner)

- [ ] QA round: `tools/QA.sh` on 3.10 to 3.14 (3.12 failed once on a test that spawns a subprocess without `yaml`), `mkdocs build --strict`,
      the Web UI in a browser, the docs banner hook with fact blocks, and `uvx --from 'bowerbird-mcp[semantic]'` end to end (needs 2.2.0 on PyPI).
- [ ] Re-seal the pages edited since they were sealed, then `tools/QA.sh --rebuild` to rebuild `docs/` (a build made before a seal is stale).
- [ ] Commit the work since `a1c0724` (confirm the `Co-Authored-By` trailer first), then tag, build and upload to PyPI. No `gh release`.

## 2.3

- [ ] Drop the fallbacks for the old names: `kbmcp.yaml`, `KB_*`, `kbmcp.nolint`, the `.kbmcp/` cache, and reading `kb-index` markers.
- [ ] Distributed waxseals: a ledger per folder, not one `.waxseals.yaml` at the collection root. A wiki started for a code project often grows into
      sealing the code assets too, and the seals should live beside what they cover (the way a folder's own `bower.yaml` already scopes its
      format). Open: where a ledger sits when a file's folder has none, how `move` carries a seal across ledgers, and how `seal check` and `serve`
      merge them.

### Facts and seals: what 2.2.0 left

- [ ] Writing a fact as a person is still clunky: a `fact` that writes the block into the document for an agent; `fact` for a person
      (`result=-` and `result=@file`); a `--harvest`-style capture; the terminal "still true? y/n" walk for sources a machine cannot read.
- [ ] More fact kinds, now that they are a registry: `[fact.file](path#L10-20)` (read by the tool, no network), scoped claims, and a quote to watch for paraphrases.
- [ ] Two fact records exist side by side: the blocks (`.facts.yaml` only) and the agent's `sources` frontmatter plus its `fact_sha256`.
      Decide whether one replaces the other.
- [ ] `serve`: show a block's fact state, and a file's several signers and comments (the banner hook shows the latest seal only).
- [ ] `factcheck --fetch` is tested against a local page and a stand-in MCP server only: try real pages (StackOverflow may block it) and a real
      Jira. Semantic mode is tested with a fake embedder.
- [ ] `seal-extensions`: the `serve` modal and the docs banner could show "N of M signed"; `move` carries every seal but has no test.
- [ ] The facts and seal helpers are their own files (`bowerbird_facts.py`, `bowerbird_seal.py`); a lone copy of `bowerbird_mcp.py` loses them, as it
      does `serve`. Consider the same split for the semantic, SKOS and vector-index code.

## Later

- [ ] Vote tally (partly built in 2.2.0: several signers and a quorum, behind `seal-extensions`; still open: the break-on-purpose and
      strict-seal modes, seal count as importance, `seal.tally`): a seal as a vote. A tally reads the ledger (`.waxseals.yaml`) and counts distinct human
      sealers per file or ADR, each only while the sha256 still matches (an edit voids the votes, like a stale seal).
      Weight of the edit: a file with N seals costs N to change. Before an edit (or a `seal` write) the tool warns
      "this breaks N seals" and makes you break each one on purpose (a named, ledgered act), not by a silent hash drift.
      Optional, not core: off by default, switched on in config (`seal.tally`: threshold, gate or inform), or shipped as an
      add-on extra (`bowerbird-mcp[tally]`). Plain seals work unchanged without it.
      Strict-seal mode (consider for sure): editing a file with N seals opens a modal in `serve`, one step per seal (who,
      when, "break this seal"); the edit unlocks after the last. Each break is a ledger entry. The real gate is a pre-commit
      or Claude Code hook that refuses writes to a file with live seals (agents included; they never break one). Likely
      rule: a person breaks only their own seal; a ledgered owner override covers a departed sealer. Useful for ratified
      ADRs, charters, policy, security docs and release notes; pointless at N=1.
      Break as review-then-change: the person sees the proposed change and the seal it would break (same `review_ui`
      dialog as RTC), approves, and only then does the edit apply and the seal drop. A denial writes nothing. Builds on
      the `rtc` branch, which stays off `main` until you say.
      The prompt says it plainly: "This was reviewed (N seals). Are you sure you want to change it? Once you do, it must be
      resealed before you can commit." A pre-commit hook enforces the second half: no commit of a file whose seals are
      broken or stale until it is sealed again.
      Seal count as a metric of importance: show N wherever a file shows (docs badge, `serve` list, `seal check`, search
      results), and let `heatmap` and search rank by it. Count only live seals (sha256 matches).
      A seal is a costly signal: each one is a person who judged the file worth their review, so the count is earned
      importance, not a guess.
      Importance reads two ways, both only when multi-seal mode is on: a heavily sealed file marks its subject as important,
      and a recurring multi-seal workflow marks the process as common. With the mode off, a count carries no such meaning.
      Why: five seals on a document is a shared agreement that cannot drift unseen, because every sealer's seal breaks
      when it changes. Needs a way for each sealer to find out (`seal check` in CI, or a notice on their next pull).
      Open: does the warning gate (refuse until broken) or only inform; who may break whose seal; one voter one vote (by what identity);
      threshold or quorum (e.g. ratify at N); approve only, or also object/abstain; where it shows (`seal check`, `serve`, docs badge).
- [ ] Search for a generated site: `reindex export=search-index.json` writes every passage (file, heading, text, `status`, trust
      `tier`, stale) as JSON, and the theme loads it with a client-side library (MiniSearch or lunr), badging each result by
      tier. Keyword only (no semantic search in a static site); the generator maps file and heading to a URL. The stock MkDocs
      `search` plugin is the zero-code alternative, without tiers.
- [ ] A status badge plugin for other site generators. `docs-src/badges.md` is the recipe (it works from `list`, `factcheck` and the ledger);
      a ready-made one for Hugo or Jekyll would be the next step.
- [ ] MCP prompts: answer from the collection and cite; review a decision record (`rules` is the only one so far).
- [ ] Progress notifications from `reindex` over MCP (the CLI prints progress to stderr; the tool is not async).
- [ ] A loader registry (`sync` dispatches `load_md`, `load_skos` and `load_adoc` by format; a seventh format is the time).
- [ ] SKOS: count links across files for `hubs`.
