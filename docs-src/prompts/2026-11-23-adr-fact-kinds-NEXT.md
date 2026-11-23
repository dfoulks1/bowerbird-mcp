# Next agent: build the `file` fact kind (ADR-001, step 1)

Read first: `docs-src/decisions/ADR-001-fact-kinds-core-and-pack.md`, then the record
`docs-src/prompts/2026-11-23-adr-fact-kinds.md` (its Defaulted table is the spec for the unasked parts).
Also `bowerbird_facts.py` (`register`, `attach`, `check_literal`, `norm`) and `bowerbird_mcp.py` near `fact_check_url` (line ~3629)
and the `_F.attach` block (~3680). Follow `~/.claude/CLAUDE.md`. Name each tool you call.

## First step only

Add the `file` kind: `[fact.file](path#L10-20) the claim [fact.end]`.
- Register it in `bowerbird_facts.py` with a `valid` for `path` and `path#L<a>-<b>` (and `#L<a>`).
- Add its plan and check in `bowerbird_mcp.py`, attached beside `url` and `mcp`. The path is absolute, `~/`, or relative to
  the citing document's folder. Read-only. Read the file only inside a check. Check the lines with `F.check_literal`.
  A missing file or a range past the end is `drifted` with a plain message.
- Test in `test_bowerbird_mcp.py`: claim present in the range -> `checked`; the same block after the lines are edited -> `drifted`.
  **Red arm:** the drift test must fail if the check reads the whole file instead of the range. Show it failing, then passing.
- Update `docs-src/tools.md` (the `factcheck` paragraph), `BOWERBIRD.md` (the kinds line), `CHANGELOG.md` (unreleased) and `lint` if it
  lists kinds. Remove the `[fact.file]` line from `TODO.md` "More fact kinds".

## Do not touch

`internal` and the entry-point loader (steps 2 and 3), `fact-pack/`, `.waxseals.yaml`, `docs/` (generated), the version number.
Never seal, ratify or write `accepted`.

## Stop

Stop and report if a premise is wrong (for example `register`/`attach` are not as the ADR says) or the change spreads past
`bowerbird_facts.py`, `bowerbird_mcp.py`, the test file and the four doc files.

## Tier and review

Builder: mid tier (Sonnet 5.5, medium effort). It is a small, test-led change in two files. A different tier (the large tier,
read-only) reviews the diff before the owner does. The Budget block was not written (`budget-select` not run); add one if this is a comrun.

Nothing is committed. Confirm the trailer with the owner first.
