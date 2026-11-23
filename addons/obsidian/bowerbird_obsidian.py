"""bowerbird-mcp[obsidian]: an Obsidian vault as a collection. Sources: obsidian.md/help (links, embeds, tags, properties, aliases, data storage)."""
import re

COMMENT = re.compile(r"%%.*?%%", re.DOTALL)  # Obsidian's own comments: a [[link]] inside one is not a link
# #tag: letters, digits, _ - / (nested), at least one letter or underscore, not inside a word, a path or an entity (`a/#b`, `&#39;`)
# shortcut: #2024-01-01 is not a tag here (Obsidian may take it: its rule says one non-numeric character); upgrade if that bites
TAG = re.compile(r"(?<![\w&/#:.+@-])#([\w/-]*[^\W\d][\w/-]*)")


def tags(bb, body: str) -> list:
    return TAG.findall(COMMENT.sub("", bb.CODE.sub("", body)))


def names(text: str, meta: dict) -> list:
    """The note's `aliases` property (a list; a lone string too): [[Alias]] finds the note."""
    got = meta.get("aliases", meta.get("alias"))
    return [str(a) for a in got] if isinstance(got, list) else [str(got)] if got else []


def register(bb):
    bb.register_format(
        "obsidian",
        about="an Obsidian vault (markdown notes; [[wikilinks]] resolve by note name)",
        skip=(".obsidian", ".trash"),  # the vault's settings and its trash; neither holds notes
        clean=lambda body: COMMENT.sub("", body),
        tags=lambda body: tags(bb, body),
        names=names,
    )
