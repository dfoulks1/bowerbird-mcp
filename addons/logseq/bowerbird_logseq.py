"""bowerbird-mcp[logseq]: a Logseq file-based graph as a collection. Sources: docs.logseq.com and the Logseq 0.10.x source (file name format, properties)."""
import re
import urllib.parse

JOURNAL = re.compile(r"[a-z]{3} \d{1,2}(?:st|nd|rd|th), \d{4}")  # a journal page by its default title ("Sep 14th, 2020")
# shortcut: journal titles are read in the default format MMM do, yyyy; upgrade to read :journal/page-title-format from config.edn if that bites


def page(name: str) -> str:
    """A file's page name: `a___b` (triple-lowbar) and `a%2Fb` (legacy) are page `a/b`."""
    return urllib.parse.unquote(name.replace("___", "/"))


def virtual(name: str, pages: list) -> bool:
    return bool(JOURNAL.fullmatch(name))


def register(bb):
    bb.register_format(
        "logseq",
        about="a Logseq graph (markdown pages in pages/ and journals/; a [[link]] makes its page)",
        skip=("logseq", ".recycle"),  # the graph's config and backups
        page=page,
        virtual=virtual,
        quiet=("dead_link", "dead_anchor"),  # a link to a page with no file is how a Logseq page is born, not a mistake
    )
