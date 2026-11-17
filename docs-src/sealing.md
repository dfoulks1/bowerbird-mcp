# Sealing

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. The commands and output below were run for real; long lines are shortened. -->

A seal is a person's review of one exact version of a file. It is how Bowerbird guarantees a human was in the loop: for stored
knowledge (a note, a concept, a page) and for decisions (an ADR). One function, `seal`, does it in every [format](formats.md).

## How a seal works

`seal` shows the person the file in a prompt, asks for their id, and records who reviewed it and when. The record is bound to
the sha256 of the file's exact bytes (line endings normalized; for OKF, without the `verified` key, which the review itself
writes). Edit the file afterwards and the hash no longer matches: the seal is broken, and a hit for that file shows
`unverified` and `stale`. Only a new review makes a new seal.

Like a wax seal, it proves the document was not changed after it was closed. It does not prove the reviewer read it all.

## Who can seal

- **A person:** over MCP they type their own id in the prompt. At a terminal, `--attest` records them. The result is a
  `human-reviewed` hit.
- **An agent or process:** it can only seal as itself, with `by=<tool>/<version>` or `by=process:<id>`. That is
  `machine-confirmed`, not `human-reviewed`. An agent never passes `human:<id>`, and should show the person the file first.

At the terminal `seal` also answers to `verify` (the OKF word), `ratify` and `accepted` (the ADR words). They are the same
function.

## Where a review is kept

| Format | The review lives in |
|---|---|
| OKF | the concept's own frontmatter, as `verified: {by, at, sha256}` |
| Markdown, ADR, SKOS, AsciiDoc, Seal-only | `.waxseals.yaml` at the collection root (commit it). The file itself is never edited |

```yaml
# .waxseals.yaml: the latest review of each file (`seal`); an edit breaks it, git has the earlier ones. Commit it.
- {file: config/limits.yaml, sha256: 3b1f…, by: 'human:you', at: '2026-11-16T15:02:10Z', bowerbird: 2.0.0}
- {file: src/app.py, sha256: ba1a531f581d2e6094e978ed6f7aca7a8d92eeb62c6e7ad73ee692f7f18bc772, by: 'human:you', at: '2026-11-16T15:01:31Z', bowerbird: 2.0.0}
```

There is one `.waxseals.yaml`, at the collection root beside `kbmcp.yaml`, with one dense line per file (its path from that
root). **Only the latest seal is kept**: sealing a file again replaces its line. That is deliberate. When an edit breaks a
seal, the line still names the version a person reviewed, and git shows what has changed since; the earlier reviews are in
the file's history. `bowerbird` is the version of Bowerbird that wrote the line, so a review can be traced to the tool that recorded it.

Because the file is untouched, Nygard ADRs, MADR, thesauri and AsciiDoc all work as they are. Reviews are not converted when
you [change format](formats.md#changing-your-mind); after a switch the files may need sealing again.

## Decisions

For an ADR, `decision=accepted` or `decision=rejected` goes into the ledger with the review and becomes the hit's `status`:

```sh
kb ratify docs/adr/0001-use-a-managed-queue.md decision=accepted --attest
```

A record that writes "Accepted" has only said so about itself. In `kb status` and `kb list` a decision record is
**accepted** only once a person has sealed it, and **proposed** until then. Superseded, rejected and deprecated are final. See
[ADR](formats/adr.md).

In OKF, `promote=true` also moves a concept from `draft` to `stable`, and only a human review may.

## Checking

`kb seal check=true` changes nothing and exits 1 on findings, so it can run in a pre-commit hook and in CI:

| Finding | Meaning |
|---|---|
| `unsigned` | a file the policy requires has no review by a human |
| `stale_signature` | it was reviewed, then edited |
| `claims_accepted` | its own status says accepted, but no human reviewed it |
| `orphan_signature` | a ledger entry for a file that is gone (a warning) |
| `unreadable` | required, but not UTF-8 text, so it cannot be reviewed here |

```text
$ kb seal check=true output=text
config/limits.yaml: error: unsigned: no review by a human | fix: a human reviews it: seal config/limits.yaml
src/app.py: error: unsigned: no review by a human | fix: a human reviews it: seal src/app.py
bowerbird-mcp seal: FAILED: 2 file(s) checked, 2 finding(s)
```

After an edit, the file fails again until someone reviews the new version:

```text
src/app.py: error: stale_signature: edited since it was reviewed | fix: review it again: seal src/app.py
```

`since=<git ref>` limits the check to files changed since its merge base with `HEAD`: `since=origin/main` for a pull request.

## The policy

The policy is the `seal` key in the committed `kbmcp.yaml`, so nothing local can loosen it. By default every file needs a review,
except those whose status is `proposed` or `draft`:

```yaml
seal: {require: ["**"], exempt_status: [proposed, draft]}
```

`require` is a list of globs, and a leading `/` anchors one at the collection root. `exempt_status` lets a proposal be committed
before it is reviewed.

## Enforcing it

A pre-commit hook:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: bowerbird-seal
        name: Bowerbird seal check
        entry: uvx bowerbird seal check=true output=text
        language: system
        pass_filenames: false
        always_run: true
```

And the same command in CI, with `since=origin/${{ github.base_ref }}` on pull requests. A hook can be skipped with
`--no-verify`; CI cannot.

## Moving and renaming

`move` keeps a file's seal when the file's text does not change (Markdown and ADR). If the move had to rewrite the file's own
relative links, its text changed, so it loses the seal, as any edit does. Files that linked to it are edited too, and lose theirs.

## Seal-only

Use `format: seal-only` when you have files (code, configuration, policy) and want a guaranteed human review of the exact
version, enforced at commit time, with nothing indexed or searched. The only tool is `seal`.

```text
service/
  kbmcp.yaml             format: seal-only
  .waxseals.yaml          the reviews (commit it)
  src/app.py
  config/limits.yaml
```

```yaml
# kbmcp.yaml
format: seal-only
about: Reviewed code.
seal: {require: ["src/**/*.py", "config/*.yaml"]}
```

`require` has to be set: `init holds=seal-only` writes it empty, and `kb seal check=true` refuses to run until you fill it
in. Any text file can be named.

```sh
kb init holds=seal-only about="Reviewed code." apply=true
kb seal check=true output=text
```

## Showing a review on a website

A badge naming the reviewer cannot be written into the sealed file. The build can fill it in from the ledger instead; see
[the website use case](formats/markdown.md#use-case-content-for-a-generated-website).

## Limits

- The prompt shows the start of the file; the reviewer is trusted to have read all of it, or the diff.
- `seal` proves a ledger entry exists for these bytes, not who typed it. Protect `.waxseals.yaml` and `kbmcp.yaml` with
  `CODEOWNERS` or branch protection, so a change to them needs a named reviewer.
- A SKOS file is sealed whole, not per concept. A page that includes text from another file is not covered for that text.
