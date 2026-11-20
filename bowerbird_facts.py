"""Fact blocks: a span of a document that says what it rests on, and the state of checking it.

    [fact.url] https://example.com/page

    The words copied from that page.

    [fact.end]

    [fact.mcp] jira INFRA-27707 is open [fact.end]

`parse` finds the blocks (and what is wrong with the markup), `.facts.yaml` beside a document keeps the last check of each block,
and `check_literal` / `page_text` / `call_mcp` do the checking. Self-contained, so the docs build hook can import it with only
PyYAML installed; the MCP client and the network are touched only inside the functions that need them.
"""
import hashlib
import html
import html.parser
import json
import re
import urllib.request
from pathlib import Path
from typing import NamedTuple

import yaml

STATE = ".facts.yaml"  # beside the documents: the last check of each of their fact blocks (commit it, like .waxseals.yaml)
KINDS = ("url", "mcp")
TAG = re.compile(r"\[fact\.([a-z]+)\]")  # [fact.<kind>] opens, [fact.end] closes
CODE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]*`", re.DOTALL)


class Block(NamedTuple):
    kind: str
    source: str  # a url, or `server key` for mcp
    claim: str  # the words that are checked
    line: int
    end_line: int
    id: str  # derived from the kind, the source and the words: edit the words and it is a new, unchecked fact
    start: int  # offsets of the whole block (both tags) in the text
    end: int


def mask(text: str) -> str:
    """text with code (fenced and inline) blanked out, newlines and offsets kept: an example of the syntax is not a fact."""
    return CODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def norm(text: str) -> str:
    """Content, not shape: code ticks and emphasis marks dropped, whitespace collapsed, case ignored."""
    return " ".join(re.sub(r"[`*]", "", text).split()).casefold()


def fact_id(kind: str, source: str, claim: str) -> str:
    return hashlib.sha256(f"{kind}\0{source}\0{norm(claim)}".encode()).hexdigest()[:12]


def parse(text: str) -> tuple:
    """(blocks, problems). problems are (line, kind, message): unclosed_fact, stray_fact_end, unknown_fact_kind, bad_fact."""
    masked, blocks, problems, opened = mask(text), [], [], None
    line = lambda pos: text.count("\n", 0, pos) + 1
    for t in TAG.finditer(masked):
        name = t.group(1)
        if name != "end":
            if opened is not None:
                problems.append((line(opened.start()), "unclosed_fact", f"[fact.{opened.group(1)}] has no [fact.end] before the next fact"))
            if name not in KINDS:
                problems.append((line(t.start()), "unknown_fact_kind", f"[fact.{name}] is not a kind of fact | fix: {', '.join('fact.' + k for k in KINDS)}"))
            opened = t
            continue
        if opened is None:
            problems.append((line(t.start()), "stray_fact_end", "[fact.end] closes no fact"))
            continue
        o, opened = opened, None
        if o.group(1) not in KINDS:
            continue
        kind, body = o.group(1), text[o.end():t.start()].strip()
        where = line(o.start())
        if kind == "url":
            m = re.match(r"(\S+)\s*(.*)", body, re.DOTALL)
            source, claim = (m.group(1), m.group(2).strip()) if m else ("", "")
            if not re.match(r"https?://\S+$", source):
                problems.append((where, "bad_fact", f"[fact.url] needs the page's address after it, got {source!r} | fix: [fact.url] https://..."))
                continue
        else:
            words = body.split()
            if len(words) < 2:
                problems.append((where, "bad_fact", "[fact.mcp] needs a server and a key, then the claim | fix: [fact.mcp] jira INFRA-27707 is open [fact.end]"))
                continue
            source, claim = f"{words[0]} {words[1]}", body
        if not claim:
            problems.append((where, "bad_fact", f"[fact.{kind}] has no words to check | fix: paste what the source says between the tags"))
            continue
        blocks.append(Block(kind, source, claim, where, line(t.start()), fact_id(kind, source, claim), o.start(), t.end()))
    if opened is not None:
        problems.append((line(opened.start()), "unclosed_fact", f"[fact.{opened.group(1)}] has no [fact.end] | fix: close it with [fact.end]"))
    return blocks, problems


# ------------------------------------------------------------------ state: .facts.yaml beside the document


def read_state(d: Path) -> dict:
    """{(file, id): entry} from the .facts.yaml in folder d; {} when there is none."""
    f = Path(d) / STATE
    if not f.is_file():
        return {}
    try:
        es = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        assert isinstance(es, list) and all(isinstance(e, dict) and e.get("file") and e.get("id") for e in es)
    except (yaml.YAMLError, AssertionError, OSError):
        raise ValueError(f"{f} is malformed | fix: it is a list of lines like `- {{file: a.md, id: ..., status: checked, at: ...}}`")
    return {(str(e["file"]), str(e["id"])): e for e in es}


def write_state(d: Path, state: dict) -> None:
    keys = ("file", "id", "kind", "source", "status", "method", "at", "value", "drifted_at")
    lines = ["- " + yaml.safe_dump({k: str(e[k]) if k in ("at", "drifted_at") else e[k] for k in keys if e.get(k) is not None},
                                   default_flow_style=True, sort_keys=False, allow_unicode=True, width=10 ** 6).strip()
             for _, e in sorted(state.items())]
    (Path(d) / STATE).write_text("# .facts.yaml: the last check of each fact block in these documents (`factcheck`). Commit it.\n"
                                 + "\n".join(lines) + "\n", encoding="utf-8")


def record(d: Path, file: str, fid: str, kind: str, source: str, status: str, method: str, at: str, value=None) -> dict:
    """Note a check of the fact `fid` (a block's id, or the id of a `sources` entry) of `file`. A drift is remembered (drifted_at)
    even after a later check passes: only a review made after it holds again. The state lives here, never in the document: a check
    that found nothing wrong must not change the bytes a human's review is bound to."""
    st = read_state(d)
    old = st.get((file, fid), {})
    e = {"file": file, "id": fid, "kind": kind, "source": source, "status": status, "method": method, "at": at}
    if value is not None:
        e["value"] = value
    if status == "drifted":
        e["drifted_at"] = at
    elif old.get("drifted_at"):
        e["drifted_at"] = old["drifted_at"]
    st[(file, fid)] = e
    write_state(d, st)
    return e


def drift_time(d: Path, file: str):
    """The latest time a block of `file` drifted (an ISO string), or None."""
    ts = [str(e["drifted_at"]) for (f, _), e in read_state(d).items() if f == file and e.get("drifted_at")]
    return max(ts, default=None)


def status_of(d: Path, file: str, b: Block) -> dict:
    """The block's last check: {status: unchecked|checked|drifted, at, method}."""
    e = read_state(d).get((file, b.id))
    return {"status": e["status"], "at": e.get("at"), "method": e.get("method")} if e else {"status": "unchecked", "at": None, "method": None}


# ------------------------------------------------------------------ checking


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style")
        self.out.append(" ")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style") and self.skip > 0
        self.out.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def page_text(url: str, timeout: int = 20, limit: int = 2_000_000) -> str:
    """The text of the page at url (scripts, styles and markup dropped). http and https only; at most `limit` bytes.
    shortcut: a page built by script in the browser has no text here, and one behind a login is not fetched; upgrade if that bites."""
    if not re.match(r"https?://", url):
        raise ValueError(f"{url} is not an http or https address")
    req = urllib.request.Request(url, headers={"User-Agent": "bowerbird-mcp factcheck", "Accept": "text/html,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw, kind = r.read(limit), r.headers.get("Content-Type", "")
    text = raw.decode("utf-8", errors="replace")
    if "html" not in kind and not text.lstrip().startswith("<"):
        return text
    p = _Text()
    p.feed(text)
    return html.unescape(" ".join(p.out))


def paragraphs(claim: str) -> list:
    return [p for p in re.split(r"\n\s*\n", claim) if p.strip()]


def check_literal(claim: str, text: str) -> tuple:
    """(found, total): how many paragraphs of the claim still appear in text, ignoring shape (whitespace, case, code ticks)."""
    hay, ps = norm(text), paragraphs(claim)
    return sum(norm(p) in hay for p in ps), len(ps)


def dotted(obj, path: str):
    """obj[a][b][0] for "a.b.0"; the whole obj when path is empty."""
    for part in filter(None, path.split(".")):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


async def call_mcp(spec: dict, tool: str, args: dict, timeout: int = 60) -> str:
    """The text a tool of the MCP server `spec` (a .mcp.json entry) returns for args: bowerbird as an MCP client over stdio."""
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=spec["command"], args=list(spec.get("args", [])), env=spec.get("env") or None)

    async def run():
        async with stdio_client(params) as (rd, wr), ClientSession(rd, wr) as session:
            await session.initialize()
            res = await session.call_tool(tool, args)
            text = "\n".join(c.text for c in res.content if getattr(c, "text", None) is not None)
            if res.isError:
                raise ValueError(f"{tool} failed: {text[:200]}")
            return text
    return await asyncio.wait_for(run(), timeout)


def watched(text: str, path: str) -> str:
    """The value at `path` of a tool's JSON result (the whole text when it is not JSON or no path is given), as a string."""
    try:
        value = dotted(json.loads(text), path) if path else text
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError(f"the result has nothing at {path!r} | fix: set `watch` in kbmcp.yaml to a path in the tool's result")
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
