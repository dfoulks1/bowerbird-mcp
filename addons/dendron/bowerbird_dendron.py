"""bowerbird-mcp[dendron]: a Dendron workspace as a collection. Sources: wiki.dendron.so (wiki links, hierarchies, note references, vaults)."""
import re

VAULT = re.compile(r"(\[\[(?:[^\[\]|\n]*\|)?)dendron://[^/\]\n]+/")  # [[dendron://vault/note]] and [[alias|dendron://vault/note]]: the vault prefix is not a note


def virtual(name: str, pages: list) -> bool:
    """A Dendron stub: a.b exists, with no file, as soon as a.b.c does."""
    return any(p.startswith(name + ".") for p in pages)


def register(bb):
    bb.register_format(
        "dendron",
        about="a Dendron workspace (dotted note names are the hierarchy; [[alias|note.name]])",
        alias_first=True,  # Dendron writes the alias on the left
        clean=lambda body: VAULT.sub(r"\1", body),
        virtual=virtual,
    )
