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

- **A person:** over MCP they type their own id in the prompt. At a terminal, `--attest` records them. In the browser,
  [`serve`](serve.md#seal-from-the-browser) opens a dialog that asks the same two things (tick that you reviewed it, and
  type your id). The result is a `human-reviewed` hit.
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

There is one `.waxseals.yaml`, at the collection root beside `bower.yaml`, with one dense line per file (its path from that
root). **Only the latest seal is kept**: sealing a file again replaces its line. That is deliberate. When an edit breaks a
seal, the line still names the version a person reviewed, and git shows what has changed since; the earlier reviews are in
the file's history. `bowerbird` is the version of Bowerbird that wrote the line, so a review can be traced to the tool that recorded it.

**A seal can carry a comment.** `seal` takes `comment`, a one-line note kept with the review: `seal src/app.py --attest --comment "checked
the limits against the runbook"`. The MCP confirmation prompt and the `serve` seal dialog have a Comment field too. A comment is up to 280
characters, a single line, and is stored on the seal itself (`comment:` in the ledger line, or in the OKF `verified` entry). It needs no
setting and no extra.

Because the file is untouched, Nygard ADRs, MADR, thesauri and AsciiDoc all work as they are. Reviews are not converted when
you [change format](formats.md#changing-your-mind) on their own; after a switch the files may need sealing again, or `okf export` and
`okf import` carry an OKF concept's reviews and sources between its frontmatter and the ledgers (see [the command line](cli.md#moving-an-okf-concepts-history-okf-export-and-okf-import)).

## Several signers and a quorum (the `seal-extensions` extra)

By default a version of a file has one review: the latest. Where a change should be reviewed by more than one person, switch the seal
extensions on in the root `bower.yaml`:

```yaml
seal: {extensions: true, quorum: 2}
```

- **`extensions: true`** lets different people seal the same version of a file. Their seals are kept together on the file's one ledger
  line, each with its own date, version of Bowerbird and comment:
  ```yaml
  - {file: docs/limits.md, sha256: 3b1f…, seals: [{by: 'human:ann', at: '2026-11-20T10:02:10Z', bowerbird: 2.2.0, comment: "limits match the runbook"}, {by: 'human:bo', at: '2026-11-20T11:40:03Z', bowerbird: 2.2.0}]}
  ```
  The same person sealing again replaces their own seal. An edit ends every seal of the old version; the next seal starts the list again.
- **`quorum: N`** (2 or more needs `extensions: true`) is how many *different people* a version needs. Until it has them, `seal check`
  reports `short_of_quorum` (`1 of 2 human reviews of this version`) and the file's tier is `unverified`, not `human-reviewed`. A machine
  check (`by=<tool>`) is never counted as a person.
- A folder can set its own, since `seal` is one of the keys a [bower](formats.md) may override.
- **The extra** is called `seal-extensions`. It has no dependency: `uv tool install 'bowerbird-mcp[seal-extensions]'` installs nothing
  more, and the setting is what turns the behaviour on. Without it, seals work as before, one latest review per file, comments included.
- Turn it off again and the ledger still reads: the latest seal of each line counts.

## Decisions

For an ADR, `decision=accepted` or `decision=rejected` goes into the ledger with the review and becomes the hit's `status`:

```sh
bowerbird-mcp ratify docs/adr/0001-use-a-managed-queue.md decision=accepted --attest
```

A record that writes "Accepted" has only said so about itself. In `bowerbird-mcp status` and `bowerbird-mcp list` a decision record is
**accepted** only once a person has sealed it, and **proposed** until then. Superseded, rejected and deprecated are final. See
[ADR](formats/adr.md).

In OKF, `promote=true` also moves a concept from `draft` to `stable`, and only a human review may.

## Checking

`bowerbird-mcp seal check=true` changes nothing and exits 1 on findings, so it can run in a pre-commit hook and in CI:

| Finding | Meaning |
|---|---|
| `unsigned` | a file the policy requires has no review by a human |
| `stale_signature` | it was reviewed, then edited, or a [fact](formats/okf.md#facts-what-a-claim-rests-on-and-drift) it rests on drifted after the review |
| `claims_accepted` | its own status says accepted, but no human reviewed it |
| `orphan_signature` | a ledger entry for a file that is gone (a warning) |
| `unreadable` | required, but not UTF-8 text, so it cannot be reviewed here |

```text
$ bowerbird-mcp seal check=true output=text
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

The policy is the `seal` key in the committed `bower.yaml`, so nothing local can loosen it. By default every file needs a review,
except those whose status is `proposed` or `draft`:

```yaml
seal: {exempt: [], exempt_status: [proposed, draft]}
```

`exempt` is a list of globs for files that need no review, and a leading `/` anchors one at the collection root.
`exempt_status` lets a proposal be committed before it is reviewed.

A file `exempt` names, such as `exempt: ["src/gen_*.py"]`, is left out of `seal check`. That says nothing about *who made it*, so it is not
badged as built from the code on that account alone.

**Derived from the code** is recorded by the generator, in the ledger: after it writes a file (a tool list, a generated table, markdown or
not), a script that uses Bowerbird as a library calls `mark_derived(path, "gen.py")`, which adds a line with `derived: gen.py` and the
file's `sha256` (`docs_tools.py` does this for `docs-src/tools.md`). `serve` and the docs build then badge the file "derived from the code",
and `serve` offers no Seal button. It is not a tool, so an agent cannot declare a file free of review. Edit the file by hand and the hash no
longer matches: it stops being derived, and the next run of the generator records it again. The line carries a `by` so that an older
Bowerbird can still read the ledger; the `derived` key is what says it is not a person's review.

A generated *folder*, such as the site's output, gets one line for the whole folder, not one per file (`mark_derived_dir("docs", "mkdocs")`,
which `docs_tools.py` calls). A folder has no hash, so it is the location that says so: everything under it is derived (binaries too),
left out of the check, and badged blue, and nothing is compared per file.

```yaml
- {file: docs/, by: 'generator:mkdocs', at: '2026-11-21T09:00:00Z', bowerbird: 2.2.0, derived: mkdocs}
- {file: docs-src/tools.md, sha256: 5d1c…, by: 'generator:docs_tools.py', at: '2026-11-20T15:02:10Z', bowerbird: 2.2.0, derived: docs_tools.py}
```

## Enforcing it

A pre-commit hook:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: bowerbird-seal
        name: Bowerbird seal check
        entry: uvx bowerbird-mcp seal check=true output=text
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
  bower.yaml             format: seal-only
  .waxseals.yaml          the reviews (commit it)
  src/app.py
  config/limits.yaml
```

```yaml
# bower.yaml
format: seal-only
about: Reviewed code.
seal: {exempt: ["src/gen_*.py"]}
```

Nothing has to be set: every text file is checked, and `exempt` names the ones to leave out.

```sh
bowerbird-mcp create holds=seal-only about="Reviewed code." apply=true
bowerbird-mcp seal check=true output=text
```

[`serve`](serve.md#what-you-see) shows these files too: each named file is a read-only page, numbered and (with the `syntax`
extra) highlighted, with a Seal button. The dialog's wording is the one every file gets ("I reviewed this concept"), so it
reads loosely for code. Files in hidden folders (`.github/`), binary files and files over 512 KB are sealed from the command
line only.

## Showing a review on a website

A badge naming the reviewer cannot be written into the sealed file. The build can fill it in from the ledger instead; see
[the website use case](formats/markdown.md#use-case-content-for-a-generated-website) and [Status badges](badges.md). The MkDocs hook,
`hooks/seal_banner.py`, reads only `.waxseals.yaml`: a person's seal, an edit since, or a generator's `derived` line. It does not read
`bower.yaml` or apply any glob.

## Limits

- The prompt shows the start of the file; the reviewer is trusted to have read all of it, or the diff.
- `seal` proves a ledger entry exists for these bytes, not who typed it. Protect `.waxseals.yaml` and `bower.yaml` with
  `CODEOWNERS` or branch protection, so a change to them needs a named reviewer.
- A SKOS file is sealed whole, not per concept. A page that includes text from another file is not covered for that text.
