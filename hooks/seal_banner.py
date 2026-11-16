"""MkDocs hook: render a page's review badge from .waxseals.yaml at build time.

A page carries one constant line, `<!-- seal-banner: what is true of how it was made -->` (the text is kept in the source, not
shown). The build swaps it for a badge saying when a person sealed this exact version, or that nobody has, or that it changed since. The source bytes never
hold the seal data, so rendering cannot make a seal stale. A page without the line is left alone.
"""
import fnmatch
import hashlib
import re
from pathlib import Path

import yaml

MARK = re.compile(r"<!-- seal-banner:(.*?) -->", re.DOTALL)


def latest(ledger: Path, rel: str):
    """The latest review of rel in the ledger file (a list of one-line entries), or None."""
    if not ledger.is_file():
        return None
    c = yaml.safe_load(ledger.read_text()) or []
    es = [e for e in c if e.get("file") == rel and str(e.get("by", "")).startswith("human:")]
    return max(es, key=lambda e: str(e.get("at")), default=None)


def derived(rel: str, docs: Path) -> bool:
    """Is the page left out of the review policy (`seal.require` has a `!` glob for it), as a page built from the code is?
    shortcut: fnmatch globs, so `*` also crosses `/`; upgrade if a pattern needs gitignore rules."""
    f = docs / "kbmcp.yaml"
    req = ((yaml.safe_load(f.read_text()) or {}).get("seal") or {}).get("require") or [] if f.is_file() else []
    return any(fnmatch.fnmatchcase(rel, g[1:].lstrip("/")) for g in req if g.startswith("!"))


def banner(src: Path, rel: str, docs: Path, text: str, includes: bool) -> str:
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    last = latest(docs / ".waxseals.yaml", rel)
    now = last if last and last.get("sha256") == sha else None
    state, label = (("derived", "Derived from the code") if derived(rel, docs) else
                    ("reviewed", f"AI Generated, Human Reviewed at: {now['at']}") if now else
                    ("edited", "AI Generated, edited since its last human review") if last else
                    ("unreviewed", "AI Generated, not yet human reviewed"))
    # a badge, styled by .seal-badge in css/custom.css; the page's own text (what made it, who sealed it) stays in the source, unshown
    return (f'<p class="seal-badge" data-state="{state}">{label}</p>\n'
            + ('<p class="seal-note">Text included from the README is not covered by this seal.</p>\n' if includes else ""))


def on_page_markdown(markdown, page, config, files):
    m = MARK.search(markdown)
    if not m:
        return markdown
    docs = Path(config["docs_dir"])
    return markdown.replace(m.group(0), banner(Path(page.file.abs_src_path), page.file.src_path, docs,
                                              m.group(1), "--8<--" in markdown), 1)
