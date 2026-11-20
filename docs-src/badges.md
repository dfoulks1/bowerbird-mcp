# Status badges

<!-- seal-banner: Written with Claude Sonnet 5.5. The commands and the script were run on this repository. A person has not reviewed this page yet. -->

A status badge says, at a glance, whether a person has reviewed something and whether it still holds. Bowerbird already keeps the
facts a badge needs: `.waxseals.yaml` (who reviewed which version of a file) and `.facts.yaml` (the last check of each
[fact block](formats/okf.md#facts-what-a-claim-rests-on-and-drift)). Nothing here needs a service. A badge is drawn from those two
files, at the time you build or run a command.

## On the pages of a MkDocs site

This site does it with `hooks/seal_banner.py`. Put one line in a page:

```markdown
<!-- seal-banner: what is true of how this page was made -->
```

and the build swaps it for a badge, from the ledger, comparing the page's current `sha256` with the one that was reviewed:

| Badge | When |
|---|---|
| reviewed, with the date | a person sealed this exact version |
| edited since its last review | it was sealed, then changed |
| not yet reviewed | no person has sealed it |
| derived from the code | a generator recorded these exact bytes in the ledger (`derived: <generator>`) |

The badge is a `<p class="seal-badge" data-state="reviewed|edited|unreviewed|derived">`. Colour comes from the CSS in
`docs-src/css/custom.css` (`.seal-badge[data-state="reviewed"] { --seal: var(--bs-success); }` and so on), and the wording from the
hook, so both are yours to change. The hook is listed under `hooks:` in `mkdocs.yml`. It reads only `.waxseals.yaml`, so commit that file; a
page the generator has not recorded, or that was edited since, is not badged as derived.

**Fact blocks** are drawn by the same hook as a quotation with a `fact-badge` (`data-state="unchecked|checked|drifted"`) that says
when it was last checked and how. It reads the `.facts.yaml` beside the page, so commit that file.

## In another site generator

Ask Bowerbird for each file's state and draw whatever you like. For Markdown, ADR and OKF files, `list` gives one record per file:

```sh
bowerbird-mcp list -O json limit=0
# {"file": "docs/limits.md", "tier": "human-reviewed", "stale": false, ...}
```

`tier: human-reviewed` with `stale: false` is *reviewed*; `stale: true` is *edited since its last review*; `tier: unverified` is *not
yet reviewed*. For every fact block, `factcheck` lists its state with no side effects:

```sh
bowerbird-mcp factcheck -O json
# {"blocks": [{"file": "notes.md", "line": 3, "status": "checked", "at": "2026-11-20T13:32:56Z", "method": "same words"}, ...]}
```

If you would rather read the ledger yourself (seal-only files have no other source): `.waxseals.yaml` is a YAML list with one line per
file, `{file, sha256, by, at, bowerbird}`, and where `seal.extensions` is on a line holds `seals: [{by, at, comment}, ...]`. Hash the
file as `sha256` of its text with CRLF turned into LF and any BOM removed; a seal whose `by` starts with `human:` and whose `sha256`
equals that hash is *reviewed*, and a human seal with a different hash is *edited*. (An OKF concept keeps its review in its own
frontmatter, as `verified`, so use `list` for those.)

## In a README

A badge for the repository can be a number: how many files a person has reviewed. `seal check` already knows, and exits `1` when
something lacks a review. This script turns its JSON into a [shields.io endpoint](https://shields.io/badges/endpoint-badge) file:

```python
#!/usr/bin/env python3
"""badge.py: write badge.json, a shields.io endpoint badge, from `seal check`."""
import json
import subprocess

run = subprocess.run(["bowerbird-mcp", "seal", "check=true", "-O", "json"], capture_output=True, text=True, check=False)
r = json.loads(run.stdout)
total = r["files_checked"]
lacking = len({f["file"] for f in r["findings"] if f["severity"] == "error"})
colour = "brightgreen" if lacking == 0 else "yellow" if lacking < total / 2 else "orange"
json.dump({"schemaVersion": 1, "label": "human reviewed", "message": f"{total - lacking}/{total}", "color": colour}, open("badge.json", "w"))
```

Run it in CI after the checkout, publish `badge.json` (to GitHub Pages, a gist, or a branch), and embed it:

```markdown
![human reviewed](https://img.shields.io/endpoint?url=https://example.org/badge.json)
```

For facts, count the `status` values in `factcheck -O json` the same way, for a badge such as `facts: 4 checked, 1 drifted`.

## What a badge does not say

- A badge shows the state **when it was made**. A fact's state changes only when someone runs `factcheck --fetch`, so a badge is as
  fresh as the last run.
- *Reviewed* means a person reviewed that exact version, not that it is correct. *Checked* means the source still says what the block
  says, not that the source is right.
- A page's badge only counts reviews in the committed ledger. An uncommitted `.waxseals.yaml` or `.facts.yaml` is invisible to a build
  from a clean checkout.
