"""bowerbird-mcp[dendron]: a Dendron workspace as a collection. Sources: wiki.dendron.so (wiki links, hierarchies, note references, vaults, tags)."""
import os
import re
from pathlib import Path

VAULT_LINK = re.compile(r"dendron://([^/]+)/(.+)")  # [[dendron://vault/note.name]] and [[alias|dendron://vault/note.name]]: the note, in the named vault
HASHTAG = re.compile(r"(?<![\w&/#:@.+-])#([A-Za-z][\w.-]*[\w])")  # #a.b is a tag, and a link to the note tags.a.b
USER = re.compile(r"(?<![\w@.+-])@([A-Za-z][\w.-]*[\w])")  # @name is a link to the note user.name


def virtual(name: str, pages: list) -> bool:
    """A stub (a.b exists, with no file, as soon as a.b.c does), and the notes a #tag or @user points at, which need not be written."""
    return name.startswith(("tags.", "user.")) or any(p.rsplit("/", 1)[-1].startswith(name + ".") for p in pages)  # a page name is its path, and a note's name is its file's


def vaults(r: Path) -> dict:
    """{vault name: its folder under the workspace root} from dendron.yml (the `name`, or else the folder, of each `vaults` entry)."""
    import yaml
    try:
        cfg = yaml.safe_load((r / "dendron.yml").read_text(encoding="utf-8")) or {}
        return {str(v.get("name") or v["fsPath"]): str(v["fsPath"]).strip("/") for v in (cfg.get("workspace") or cfg).get("vaults", []) if isinstance(v, dict) and v.get("fsPath")}
    except (OSError, ValueError, KeyError, AttributeError, yaml.YAMLError):
        return {}


def resolve(name: str, src: Path, r: Path, pages: list):
    """A note in a named vault: [[dendron://vault/a.b]] finds a.b only among that vault's files (vaults come from dendron.yml). Any other link is the default."""
    m = VAULT_LINK.fullmatch(name.split("#")[0].strip())
    if not m:
        return False
    folder = vaults(r).get(m.group(1), m.group(1))
    note = m.group(2).lower().removesuffix(".md")
    hit = next((p for n, p in pages if n == note and (p.relative_to(r).as_posix() + "/").startswith(folder + "/")), None)
    return hit if hit else (r / folder / (m.group(2) + ".md") if (r / folder).is_dir() else None)


def register(bb):
    bb.register_format(
        "dendron",
        about="a Dendron workspace (dotted note names are the hierarchy; [[alias|note.name]])",
        alias_first=True,  # Dendron writes the alias on the left
        virtual=virtual,
        resolve=resolve,
        tags=lambda body: HASHTAG.findall(bb.CODE.sub("", body)),
        links=lambda body: [f"[[tags.{t}]]" for t in HASHTAG.findall(bb.CODE.sub("", body))] + [f"[[user.{u}]]" for u in USER.findall(bb.CODE.sub("", body))],
    )
