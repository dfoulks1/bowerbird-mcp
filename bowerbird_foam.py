"""bowerbird-mcp[foam]: a Foam (VS Code) workspace as a collection. Sources: the foambubble/foam docs (wikilinks, link reference definitions, note properties)."""
import os
import re
from pathlib import Path

# shortcut: the inline tag rule is Obsidian's (letters, digits, _ - /, one letter at least); Foam's docs do not give it. Upgrade if it bites.
TAG = re.compile(r"(?<![\w&/#:.+@-])#([\w/-]*[^\W\d][\w/-]*)")


def page(name: str) -> str:
    """A note's page name. [[projects]] means projects/index.md or projects/README.md when no projects.md sits beside them; the
    shortest-path rule makes the sibling win, as in Foam."""
    for leaf in ("/index", "/readme"):
        if name.endswith(leaf):
            return name[:-len(leaf)]
    return name


def names(text: str, meta: dict) -> list:
    """The note's `alias` property, which Foam documents as comma-separated (`aliases` too, as a list)."""
    got = meta.get("alias", meta.get("aliases"))
    return [x.strip() for x in got.split(",")] if isinstance(got, str) else [str(x) for x in got] if isinstance(got, list) else []


def resolve(name: str, src: Path, r: Path, pages: list):
    """[[./a]] and [[../b]] are paths from the citing note, [[/c]] one from the workspace root; the .md is optional. Any other name is an identifier: the default."""
    n = name.split("#")[0].strip()
    if not n.startswith(("/", ".")):
        return False
    q = (r / n.lstrip("/")) if n.startswith("/") else (src.parent / n)
    q = Path(os.path.normpath(q))
    return q if q.suffix else q.with_name(q.name + ".md")


def register(bb):
    bb.register_format(
        "foam",
        about="a Foam workspace (markdown notes; [[wikilinks]] resolve by any unique path suffix)",
        skip=(".foam", ".vscode"),  # Foam's templates (they hold $FOAM_* variables inside [[ ]]) and the editor's settings
        page=page,
        names=names,
        resolve=resolve,
        tags=lambda body: TAG.findall(bb.CODE.sub("", body)),
        quiet=("unused_ref",),  # Foam writes a `[note]: note.md` definition for every wikilink, so most are never used as [note]
    )
