"""bowerbird-mcp[foam]: a Foam (VS Code) workspace as a collection. Sources: the foambubble/foam docs (wikilinks, link reference definitions, note properties)."""


def page(name: str) -> str:
    """A note's page name. [[projects]] means projects/index.md or projects/README.md when no projects.md sits beside them; the
    shortest-path rule makes the sibling win, as in Foam."""
    for leaf in ("/index", "/readme"):
        if name.endswith(leaf):
            return name[:-len(leaf)]
    return name


def register(bb):
    bb.register_format(
        "foam",
        about="a Foam workspace (markdown notes; [[wikilinks]] resolve by any unique path suffix)",
        skip=(".foam", ".vscode"),  # Foam's templates (they hold $FOAM_* variables inside [[ ]]) and the editor's settings
        page=page,
        quiet=("unused_ref",),  # Foam writes a `[note]: note.md` definition for every wikilink, so most are never used as [note]
    )
