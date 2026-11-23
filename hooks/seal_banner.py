"""MkDocs hook: render a page's review badge from .waxseals.yaml at build time.

A page carries one constant line, `<!-- seal-banner: what is true of how it was made -->` (the text is kept in the source, not
shown). The build swaps it for a badge saying when a person sealed this exact version, that a generator made it, that nobody has sealed it,
or that it changed since. It reads only the ledgers, the `.waxseals.yaml` files: no policy, no globs. The source bytes never hold the seal data, so
rendering cannot make a seal stale. A page without the line is left alone.
"""
import hashlib
import html
import re
import sys
from pathlib import Path

import yaml

MARK = re.compile(r"<!-- seal-banner:(.*?) -->", re.DOTALL)


def entries(root: Path, rel: str) -> list:
    """Every ledger line for the file rel (a path from root), flat: a line may hold several seals (the seal extensions), and a generator's line
    says `derived`. A ledger sits beside the files it covers, with names relative to its folder; the nearest one with a line for the file wins:
    its own folder's, then each folder above, to the root's."""
    parts = Path(rel).parts
    for i in range(len(parts) - 1, -1, -1):
        ledger, name = root.joinpath(*parts[:i]) / ".waxseals.yaml", "/".join(parts[i:])
        if not ledger.is_file():
            continue
        c = yaml.safe_load(ledger.read_text()) or []
        flat = [x for e in c for x in ([{**s, "file": e["file"], "sha256": e.get("sha256"), "quorum": e.get("quorum")} for s in e["seals"] if isinstance(s, dict)]
                                       if isinstance(e.get("seals"), list) else [e])]
        if es := [e for e in flat if e.get("file") == name]:
            return es
    return []


def banner(src: Path, rel: str, docs: Path, text: str, includes: bool) -> str:
    # the same hash the tool takes: the text with CRLF turned into LF and any BOM removed
    text = src.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    sys.path.insert(0, str(Path.cwd()))
    try:
        import bowerbird_facts as F
        text = F.strip_checked(text)  # a fact's last_checked and an empty {} are written by the tools; the seal ignores them
    except ImportError:
        pass
    finally:
        sys.path.pop(0)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    root = Path.cwd()  # the repo root, where mkdocs runs; a ledger's paths start at its own folder
    es = entries(root, (docs.resolve().relative_to(root.resolve()) / rel).as_posix())
    made = next((e for e in es if e.get("derived") and e.get("sha256") == sha), None)  # a generator recorded these exact bytes
    humans = [e for e in es if str(e.get("by", "")).startswith("human:")]
    last = max(humans, key=lambda e: str(e.get("at")), default=None)
    now = last if last and last.get("sha256") == sha else None
    names = sorted({str(e["by"]).removeprefix("human:") for e in humans if e.get("sha256") == sha})  # each person who sealed these exact bytes
    state, label = (("derived", "Derived from the code") if made else
                    ("reviewed", f"AI Generated, Human Reviewed at: {now['at']}" + (f" by {', '.join(names)}" + (f" ({len(names)} of {now['quorum']} needed)" if now.get("quorum") else "") if len(names) > 1 or now.get("quorum") else "")) if now else
                    ("edited", "AI Generated, edited since its last human review") if last else
                    ("unreviewed", "AI Generated, not yet human reviewed"))
    # a badge, styled by .seal-badge in css/custom.css; the page's own text (what made it, who sealed it) stays in the source, unshown
    return (f'<p class="seal-badge" data-state="{state}">{label}</p>\n'
            + ('<p class="seal-note">Text included from the README is not covered by this seal.</p>\n' if includes else ""))


def facts(markdown: str, src: Path) -> str:
    """Show each fact block (`[fact.url](<address>) the claim [fact.end]`, `[fact.mcp](<server> <key>) the claim [fact.end]`) as a quotation with its source and
    the state of its last check, from the .facts.yaml beside the page: not yet checked, checked on a date, or drifted. The tags are
    not shown. Each badge links to the page's bibliography of facts, added at the bottom of the page. A page with no blocks, or no bowerbird_facts.py beside the repo's root, is left alone."""
    if "[fact." not in markdown:
        return markdown
    sys.path.insert(0, str(Path.cwd()))
    try:
        import bowerbird_facts as F
    except ImportError:
        return markdown
    finally:
        sys.path.pop(0)
    shown, entries = F.render(markdown, src.parent, src.name)
    return shown + ("\n\n" + F.bibliography(entries) + "\n" if entries else "")


def on_page_markdown(markdown, page, config, files):
    markdown = facts(markdown, Path(page.file.abs_src_path))
    m = MARK.search(markdown)
    if not m:
        return markdown
    docs = Path(config["docs_dir"])
    return markdown.replace(m.group(0), banner(Path(page.file.abs_src_path), page.file.src_path, docs,
                                              m.group(1), "--8<--" in markdown), 1)
