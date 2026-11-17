# In-toto export and FIDO2 sealing

Task: add in-toto export and optional FIDO2 sealing to bowerbird-mcp.

Repo: single module `bowerbird_mcp.py` (+ `test_bowerbird_mcp.py`). The ledger is
`<docs>/.waxseals.yaml`, a flat YAML list, one flow-style line per file:
`{file, sha256, by: 'human:<id>', at, bowerbird}`. Read `ledger_read`,
`ledger_by_file`, `ledger_put` (~line 2483) and the seal path (~line 2600)
first. No Pydantic; validation is regex and dicts. Use the house style.

## Step 1: in-toto export

- Add `bowerbird export --format=in-toto`. It reads each file's reviews
  through `reviews()` (not the ledger directly) and prints an
  `https://in-toto.io/Statement/v1` JSON statement to stdout.
- Known attestation gap: `okf` keeps reviews in frontmatter (`verified`);
  every other format keeps them in `.waxseals.yaml`; `content_hash` differs
  by format. Nothing reads both today. Reading ledger-only would emit nothing
  for reviewed notes in an `okf` collection. Add a test for each format.
- `subject`: one per sealed file, `{name: file, digest: {sha256: <hash>}}`.
- `predicateType`: `https://bowerbird.voltpop.com/attestation/waxseal/v1`
  (the owner controls the domain).
- `predicate`: ledger path, per-file `sealed_by`, `sealed_at`, and the current
  git revision (`git rev-parse HEAD`; omit the field if not a git repo).
- Deterministic: sorted subjects, sorted keys, stable output.
- Export only entries whose current bytes still match the ledger sha256.
  Report skipped files on stderr.
- Add tests: round-trip a small collection in `okf` and in `markdown`, assert
  shape and determinism.

## Step 2: spike, do not build on it yet

- Test whether `python-fido2` can make an assertion from a plain TTY (no
  browser). Report yes/no with the exact calls that worked. If no, stop and
  tell the owner. Do not start Step 3.

## Step 3: optional verification field (only after the owner approves the spike)

- Ledger entries may carry `verification: {method: interactive-tty|fido2,
  key_fingerprint, attestation_signature}`. Old lines without it stay valid.
- `fido2` lives behind an optional extra in `pyproject.toml`. No import at
  module load.
- `seal --attest` remains the human gate. Never sign or seal on the user's
  behalf; the human touches the key.
- Export includes `verification_method` per entry when present.

## Out of scope

SOC 2 and SSDF exports, GPG, any CC6 or "compliance" language.

## Rules

Follow `~/.claude/CLAUDE.md`. Before any commit, confirm the `Co-Authored-By`
trailer and human review with the owner. Add a CHANGELOG line. End with what
you skipped or did not check.
