"""bowerbird-mcp[logseq]: a Logseq file-based graph as a collection. Sources: docs.logseq.com and the Logseq 0.10.x source (file name format, properties, config.edn)."""
import re
import urllib.parse
from pathlib import Path

PROP = re.compile(r"^[ \t]*(?:-[ \t]+)?([\w-]+)::[ \t]*(.*?)[ \t]*$", re.MULTILINE)  # a property line: `title:: A page` (the first block's are the page's)
TAG = re.compile(r"(?<![\w&/#:.+@-])#(?:\[\[([^\]\n]+)\]\]|([^\s#\[\]()]+))")  # #tag and #[[a tag with spaces]]
BLOCK_REF = re.compile(r"\(\(([0-9a-fA-F-]{8,})\)\)")  # ((uuid)): a reference to the block that has `id:: uuid`
JAVA = {"yyyy": r"\d{4}", "yy": r"\d{2}", "MMMM": r"[a-z]+", "MMM": r"[a-z]{3}", "MM": r"\d{2}", "M": r"\d{1,2}", "dd": r"\d{2}", "do": r"\d{1,2}(?:st|nd|rd|th)",
        "d": r"\d{1,2}", "EEEE": r"[a-z]+", "EEE": r"[a-z]{3}"}  # the date pattern letters a journal title is made of (Logseq's :journal/page-title-format)
_ids: dict = {}  # id(pages) -> {block uuid: file}, built once per page index


def config(bb) -> str:
    """The text of logseq/config.edn, or "" when the graph has none."""
    try:
        return (bb.ROOT / "logseq" / "config.edn").read_text(encoding="utf-8")
    except OSError:
        return ""


def page(bb, name: str) -> str:
    """A file's page name. :triple-lowbar (the default, and what a graph with no config.edn is read as): `___` is `/`. :legacy (a config.edn with no :file/name-format
    key): `.` is `/`. Both undo percent-encoding, so `a%2Fb` is `a/b` too."""
    cfg = config(bb)
    legacy = bool(cfg) and ":file/name-format" not in cfg
    return urllib.parse.unquote(name.replace(".", "/") if legacy else name.replace("___", "/"))


def journal(bb):
    """A regex for a journal page's title, from :journal/page-title-format (default "MMM do, yyyy")."""
    m = re.search(r':journal/page-title-format\s+"([^"]+)"', config(bb))
    fmt = m.group(1) if m else "MMM do, yyyy"
    out = "".join(JAVA[t] if t in JAVA else re.escape(t) for t in re.findall(r"y+|M+|d[do]?|E+|[^yMdE]+", fmt))
    return re.compile(out)


def names(text: str, meta: dict) -> list:
    """`title::` (the page's name when it is not the file's) and `alias::` (comma-separated, with or without [[ ]])."""
    out = []
    for key, val in PROP.findall("\n".join(text.splitlines()[:8])):  # shortcut: the first block's properties are the first lines; a long first block loses a late one
        if key == "title":
            out.append(val)
        elif key == "alias":
            out += [a.strip().strip("[]") for a in val.split(",")]
    return out


def tags(bb, body: str) -> list:
    body = bb.CODE.sub("", body)
    found = [a or b for a, b in TAG.findall(body)]
    for key, val in PROP.findall(body):
        if key == "tags":
            found += [x.strip().strip("[]") for x in val.split(",") if x.strip()]
    return found


def resolve(bb, name: str, src: Path, r: Path, pages: list):
    """[[block:<uuid>]] (what a ((uuid)) block reference is read as) is the page holding `id:: <uuid>`. Any other link is the default."""
    if not name.startswith("block:"):
        return False
    ids = _ids.get(id(pages))
    if ids is None:
        ids = _ids.clear() or _ids.setdefault(id(pages), {})
        for _, p in pages:
            for m in re.finditer(r"^[ \t]*(?:-[ \t]+)?id::[ \t]*([0-9a-fA-F-]+)", p.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
                ids[m.group(1).lower()] = p
    return ids.get(name[6:].strip().lower(), r / f"{name[6:]}.md")


def register(bb):
    def virtual(name: str, pages: list) -> bool:
        return bool(journal(bb).fullmatch(name))  # the config is read each time: a graph's settings can change while the server runs

    bb.register_format(
        "logseq",
        about="a Logseq graph (markdown pages in pages/ and journals/; a [[link]] makes its page)",
        skip=("logseq", ".recycle"),  # the graph's config and backups
        page=lambda n: page(bb, n),
        virtual=virtual,
        names=names,
        tags=lambda body: tags(bb, body),
        links=lambda body: [f"[[block:{u}]]" for u in BLOCK_REF.findall(bb.CODE.sub("", body))],
        resolve=lambda name, src, r, pages: resolve(bb, name, src, r, pages),
        quiet=("dead_link", "dead_anchor"),  # a link to a page with no file is how a Logseq page is born, not a mistake
    )
