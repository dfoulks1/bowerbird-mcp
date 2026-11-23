"""bowerbird-mcp[obsidian]: an Obsidian vault as a collection. Sources: obsidian.md/help (links, embeds, tags, properties, data storage)."""
import re

COMMENT = re.compile(r"%%.*?%%", re.DOTALL)  # Obsidian's own comments: a [[link]] inside one is not a link


def register(bb):
    bb.register_format(
        "obsidian",
        about="an Obsidian vault (markdown notes; [[wikilinks]] resolve by note name)",
        skip=(".obsidian", ".trash"),  # the vault's settings and its trash; neither holds notes
        clean=lambda body: COMMENT.sub("", body),
    )
