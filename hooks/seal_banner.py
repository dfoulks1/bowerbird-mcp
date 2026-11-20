"""MkDocs hook: render a page's review badge from .waxseals.yaml at build time.

A page carries one constant line, `<!-- seal-banner: what is true of how it was made -->` (the text is kept in the source, not
shown). The build swaps it for a badge saying when a person sealed this exact version, that a generator made it, that nobody has sealed it,
or that it changed since. It reads only the ledger, `.waxseals.yaml`: no policy, no globs. The source bytes never hold the seal data, so
rendering cannot make a seal stale. A page without the line is left alone.
"""
import hashlib
import html
import re
import sys
from pathlib import Path

import yaml

MARK = re.compile(r"<!-- seal-banner:(.*?) -->", re.DOTALL)


def entries(ledger: Path, rel: str) -> list:
    """Every line of the ledger for rel, flat: a line may hold several seals (the seal extensions), and a generator's line says `derived`."""
    if not ledger.is_file():
        return []
    c = yaml.safe_load(ledger.read_text()) or []
    flat = [x for e in c for x in ([{**s, "file": e["file"], "sha256": e.get("sha256")} for s in e["seals"] if isinstance(s, dict)]
                                   if isinstance(e.get("seals"), list) else [e])]
    return [e for e in flat if e.get("file") == rel]


def banner(src: Path, rel: str, docs: Path, text: str, includes: bool) -> str:
    # the same hash the tool takes: the text with CRLF turned into LF and any BOM removed
    sha = hashlib.sha256(src.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8")).hexdigest()
    root = Path.cwd()  # the repo root, where mkdocs runs and .waxseals.yaml lives; its paths start at the repo root
    es = entries(root / ".waxseals.yaml", (docs.resolve().relative_to(root.resolve()) / rel).as_posix())
    made = next((e for e in es if e.get("derived") and e.get("sha256") == sha), None)  # a generator recorded these exact bytes
    humans = [e for e in es if str(e.get("by", "")).startswith("human:")]
    last = max(humans, key=lambda e: str(e.get("at")), default=None)
    now = last if last and last.get("sha256") == sha else None
    state, label = (("derived", "Derived from the code") if made else
                    ("reviewed", f"AI Generated, Human Reviewed at: {now['at']}") if now else
                    ("edited", "AI Generated, edited since its last human review") if last else
                    ("unreviewed", "AI Generated, not yet human reviewed"))
    # a badge, styled by .seal-badge in css/custom.css; the page's own text (what made it, who sealed it) stays in the source, unshown
    return (f'<p class="seal-badge" data-state="{state}">{label}</p>\n'
            + ('<p class="seal-note">Text included from the README is not covered by this seal.</p>\n' if includes else ""))


def facts(markdown: str, src: Path) -> str:
    """Show each fact block (`[fact.url](<address>) the claim [fact.end]`, `[fact.mcp](<server> <key>) the claim [fact.end]`) as a quotation with its source and
    the state of its last check, from the .facts.yaml beside the page: not yet checked, checked on a date, or drifted. The tags are
    not shown. A page with no blocks, or no bowerbird_facts.py beside the repo's root, is left alone."""
    if "[fact." not in markdown:
        return markdown
    sys.path.insert(0, str(Path.cwd()))
    try:
        import bowerbird_facts as F
    except ImportError:
        return markdown
    finally:
        sys.path.pop(0)
    blocks, _ = F.parse(markdown, strict=False)
    out, pos = [], 0
    for b in blocks:
        st = F.status_of(src.parent, src.name, b)
        when_ = f" {str(st['at'])[:10]}" if st["at"] else ""
        label = {"unchecked": "not yet checked", "checked": f"checked{when_}", "drifted": f"drifted{when_}"}[st["status"]]
        label += f" ({st['method']})" if st["method"] and st["status"] != "unchecked" else ""
        badge = f'<span class="fact-badge" data-state="{st["status"]}">{html.escape(label)}</span>'
        if b.line == b.end_line:  # an inline fact: the claim, then its state (an address links the claim; a server and key read before it)
            out += [markdown[pos:b.start], (f"[{b.claim}]({b.source}) {badge}" if b.kind == "url" else f"{b.source} {b.claim} {badge}")]
        else:
            quote = "\n".join("> " + ln if ln.strip() else ">" for ln in b.claim.splitlines())
            link = f'<a href="{html.escape(b.source)}">source</a>' if b.kind == "url" else html.escape(b.source)
            out += [markdown[pos:b.start], f"{quote}\n>\n> {badge} {link}"]
        pos = b.end
    return "".join(out) + markdown[pos:]


def on_page_markdown(markdown, page, config, files):
    markdown = facts(markdown, Path(page.file.abs_src_path))
    m = MARK.search(markdown)
    if not m:
        return markdown
    docs = Path(config["docs_dir"])
    return markdown.replace(m.group(0), banner(Path(page.file.abs_src_path), page.file.src_path, docs,
                                              m.group(1), "--8<--" in markdown), 1)
