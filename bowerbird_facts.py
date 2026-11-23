"""Fact blocks: a span of a document that says what it rests on, and the state of checking it.

    [fact.url](https://example.com/page) The words copied from that page. [fact.end]

    [fact.mcp](jira INFRA-27707) is open [fact.end]

`parse` finds the blocks (and what is wrong with the markup), `.facts.yaml` beside a document keeps the last check of each block,
and `check_literal` / `page_text` / `call_mcp` do the checking. Self-contained, so the docs build hook can import it with only
PyYAML installed; the MCP client and the network are touched only inside the functions that need them.
"""
import dataclasses
import datetime as dt
import hashlib
import html
import html.parser
import json
import re
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import yaml

STATE = ".facts.yaml"  # beside the documents: the last check of each of their fact blocks (commit it, like .waxseals.yaml)
TAG = re.compile(r"\[fact\.([a-z]+)\]")  # [fact.<kind>](<source>) opens, [fact.end] closes
SOURCE = re.compile(r"\(([^)\n]*)\)")  # the source, right after an opening tag


@dataclasses.dataclass(frozen=True)
class FactType:
    """A kind of fact, `[fact.<name>](<source>) ... [fact.end]`. valid says what is wrong with a source (None: nothing); sample is an
    example one for messages. plan says what a check would do (shown before anything runs), and check does it: it takes the file, the
    block, the value last recorded and what `facts:` in bower.yaml declares, and returns (status, method, value), or raises when it cannot
    check. Both are attached by the code that has what a check needs (the network, an MCP client, the embedder)."""
    name: str
    sample: str
    valid: Callable[[str], str | None]
    plan: Callable | None = None
    check: Callable | None = None
    local: bool = False  # the check only reads files here (no network, no command): an agent may run it, with no prompt


FACT_TYPES: dict[str, FactType] = {}


def register(name: str, sample: str, valid: Callable[[str], str | None], plan: Callable | None = None, check: Callable | None = None,
             local: bool = False) -> FactType:
    """Add a kind of fact (or replace one of that name). Everything that reads blocks, lint and the docs build included, then knows it."""
    FACT_TYPES[name] = FactType(name, sample, valid, plan, check, local)
    return FACT_TYPES[name]


def attach(name: str, **fns) -> None:
    """Give an already registered kind its plan and check."""
    FACT_TYPES[name] = dataclasses.replace(FACT_TYPES[name], **fns)


register("url", "https://example.com/page", lambda s: None if re.fullmatch(r"https?://\S+", s) else f"needs the page's address in the parentheses, got {s!r}")
register("mcp", "jira INFRA-27707", lambda s: None if len(s.split()) == 2 else "needs a server and a key in the parentheses")
FILE_SOURCE = re.compile(r"(.+?)(?:#L(\d+)(?:-(\d+))?)?")  # path, then optionally #L10 or #L10-20


def valid_file(s: str) -> str | None:
    m = FILE_SOURCE.fullmatch(s)
    if not m or "#" in m.group(1):
        return "needs a path, then optionally #L10 or #L10-20 (the lines the claim rests on)"
    if "://" in m.group(1):
        return "that is an address: use [fact.url]"
    if m.group(3) and int(m.group(2)) > int(m.group(3)) or m.group(2) == "0":
        return "the lines run backwards, or start at 0 (lines count from 1)"
    return None


def valid_internal(s: str) -> str | None:
    path = s.partition("#")[0].strip()
    if not path:
        return "needs a page of this collection, then optionally #Heading"
    return "that is an address: use [fact.url]" if "://" in path else None


register("file", "src/app.py#L10-20", valid_file, local=True)  # read by the tool, no network; the checks are attached by bowerbird_mcp
register("internal", "docs/tools.md#links", valid_internal, local=True)  # a section of another page in this collection
PACK = ("key", "git", "manual", "until", "script")  # the kinds `bowerbird-mcp[fact-pack]` brings
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
    meta: dict = {}  # the optional `{...}` after the opening tag: who wrote it, when, how sure; free keys are kept. It is not part of the id.


STD_META = ("by", "at", "as_of", "confidence", "note", "tags", "stale_after")  # the keys with a meaning; any other key is kept and shown


def brace_end(text: str, pos: int) -> int:
    """The offset just past the `}` that closes the `{` at pos, counting nested braces and skipping "strings"; -1 when it never closes on the same paragraph."""
    depth, i, quoted = 0, pos, False
    while i < len(text):
        c = text[i]
        if quoted:
            quoted = not (c == '"') or text[i - 1] == "\\"
        elif c == '"':
            quoted = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c == "\n" and text[i + 1:i + 2] in ("\n", ""):
            return -1
        i += 1
    return -1


def source_text(raw: str) -> str | None:
    """The source as one string: words as written, or a JSON string or array of strings (`["jira", "INFRA-1"]`) joined with spaces, the form an agent writes. None: not valid JSON."""
    raw = raw.strip()
    if raw[:1] in ('"', "["):
        try:
            v = json.loads(raw)
        except ValueError:
            return None
        v = [v] if isinstance(v, str) else v
        return " ".join(v) if isinstance(v, list) and v and all(isinstance(x, str) for x in v) else None
    return " ".join(raw.split())


def meta_problems(m: dict) -> list:
    """What is wrong with the keys that have a meaning: by and note are text, at and as_of a date or datetime, confidence 0 to 1 or low, medium or high, tags a list of text,
    stale_after a number of days or a date."""
    def day(v):
        if isinstance(v, (dt.date, dt.datetime)):
            return True
        try:
            dt.date.fromisoformat(str(v)[:10])
            return len(str(v)) >= 10
        except ValueError:
            return False
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    out = []
    for k, v in m.items():
        if (k in ("by", "note") and not isinstance(v, str)) or (k in ("at", "as_of") and not day(v)) or (k == "tags" and not (isinstance(v, list) and all(isinstance(x, str) for x in v))) \
                or (k == "confidence" and not ((num(v) and 0 <= v <= 1) or v in ("low", "medium", "high"))) or (k == "stale_after" and not ((isinstance(v, int) and not isinstance(v, bool) and v >= 1) or day(v))):
            out.append(k)
    return out


def due(m: dict, st: dict) -> bool:
    """Is a fact due for another check? Only when its `stale_after` says so: a number of days since the last check (unchecked is due), or a date that has come."""
    s = m.get("stale_after")
    if s is None or isinstance(s, bool):
        return False
    if isinstance(s, int):
        try:
            return st["status"] == "unchecked" or not st.get("at") or dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(str(st["at"]).replace("Z", "+00:00")) >= dt.timedelta(days=s)
        except ValueError:
            return True
    try:
        return dt.date.today() >= dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return False


def mask(text: str) -> str:
    """text with code (fenced and inline) blanked out, newlines and offsets kept: an example of the syntax is not a fact."""
    return CODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def norm(text: str) -> str:
    """Content, not shape: code ticks and emphasis marks dropped, whitespace collapsed, case ignored."""
    return " ".join(re.sub(r"[`*]", "", text).split()).casefold()


def fact_id(kind: str, source: str, claim: str) -> str:
    return hashlib.sha256(f"{kind}\0{source}\0{norm(claim)}".encode()).hexdigest()[:12]


def parse(text: str, strict: bool = True) -> tuple:
    """(blocks, problems). problems are (line, kind, message): unclosed_fact, stray_fact_end, unknown_fact_kind, bad_fact.
    A block is `[fact.<kind>]{<metadata>}(<source>) <the claim> [fact.end]`: the optional metadata, a JSON or YAML mapping in braces right after the tag; the
    source in parentheses (it ends at the first `)`, so a `)` in an address is written %29; an agent may write it as a JSON string or array of strings); then
    the words that are checked, up to `[fact.end]`. strict=False also takes a kind nobody registered (the docs
    build shows a block by its recorded state without knowing the kind); `lint` is the strict one."""
    masked, blocks, problems, opened = mask(text), [], [], None
    line = lambda pos: text.count("\n", 0, pos) + 1
    for t in TAG.finditer(masked):
        name = t.group(1)
        if name != "end":
            if opened is not None:
                problems.append((line(opened[0].start()), "unclosed_fact", f"[fact.{opened[0].group(1)}] has no [fact.end] before the next fact"))
            ft = FACT_TYPES.get(name)
            if ft is None and strict:
                fix = ("install the fact pack: pip install 'bowerbird-mcp[fact-pack]'" if name in PACK else ", ".join("fact." + k for k in FACT_TYPES))
                problems.append((line(t.start()), "unknown_fact_kind", f"[fact.{name}] is not a kind of fact | fix: {fix}"))
            pos, meta, bad_meta = t.end(), {}, None
            if masked[pos:pos + 1] == "{":
                stop = brace_end(masked, pos)
                try:
                    meta = yaml.safe_load(text[pos:stop]) if stop > 0 else None
                except yaml.YAMLError:
                    meta = None
                if not isinstance(meta, dict):
                    bad_meta, meta = "its {metadata} is not a JSON or YAML mapping that closes", {}
                pos = stop if stop > 0 else pos + 1
            src = SOURCE.match(masked, pos) if not bad_meta else None
            if bad_meta and ft:
                problems.append((line(t.start()), "bad_fact", f"[fact.{name}] {bad_meta} | fix: [fact.{name}]{{by: me}}({ft.sample}) the claim [fact.end]"))
            elif src is None and ft:
                problems.append((line(t.start()), "bad_fact", f"[fact.{name}] needs its source in parentheses right after it | fix: [fact.{name}]({ft.sample}) the claim [fact.end]"))
            opened = (t, src, meta)
            continue
        if opened is None:
            problems.append((line(t.start()), "stray_fact_end", "[fact.end] closes no fact"))
            continue
        (o, src, meta), opened = opened, None
        ft = FACT_TYPES.get(o.group(1))
        if (ft is None and strict) or src is None:
            continue
        kind, source, where = o.group(1), source_text(src.group(1)), line(o.start())
        claim = text[src.end():t.start()].strip()
        if source is None:
            problems.append((where, "bad_fact", f"[fact.{kind}] its source is not a JSON string or array of strings | fix: [fact.{kind}]([\"a\", \"b\"]) the claim [fact.end]"))
            continue
        if ft and (bad := ft.valid(source)):
            problems.append((where, "bad_fact", f"[fact.{kind}] {bad} | fix: [fact.{kind}]({ft.sample}) the claim [fact.end]"))
            continue
        if not claim:
            problems.append((where, "bad_fact", f"[fact.{kind}] has no words to check | fix: put the claim between the source and [fact.end]"))
            continue
        blocks.append(Block(kind, source, claim, where, line(t.start()), fact_id(kind, source, claim), o.start(), t.end(), meta))
    if opened is not None:
        problems.append((line(opened[0].start()), "unclosed_fact", f"[fact.{opened[0].group(1)}] has no [fact.end] | fix: close it with [fact.end]"))
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


# ------------------------------------------------------------------ showing: a badge in the text, a bibliography of the page's facts


def state_label(st: dict) -> str:
    when = f" {str(st['at'])[:10]}" if st["at"] else ""
    label = {"unchecked": "not yet checked", "checked": f"checked{when}", "drifted": f"drifted{when}"}[st["status"]]
    return label + (f" ({st['method']})" if st["method"] and st["status"] != "unchecked" else "")


def render(markdown: str, folder: Path, name: str) -> tuple:
    """(the markdown with each fact block shown as a quotation, or as its claim inline, with a badge of its last check that links to its entry in the
    bibliography, and the entries): [{n, kind, source, claim, line, status, at, method, label}]. The state is read from the .facts.yaml in folder;
    nothing is written. The one place the docs hook and `serve` both ask, so the two show the same."""
    blocks, _ = parse(markdown, strict=False)
    out, pos, entries = [], 0, []
    for n, b in enumerate(blocks, 1):
        st = status_of(folder, name, b)
        label = state_label(st)
        entries.append({"n": n, "id": b.id, "kind": b.kind, "source": b.source, "claim": b.claim, "line": b.line, "meta": b.meta, "due": due(b.meta, st), **st, "label": label})
        badge = f'<a class="fact-badge" data-state="{st["status"]}" href="#fact-{n}">{html.escape(label)}</a>'
        if b.line == b.end_line:  # an inline fact: the claim, then its state (an address links the claim; a server and key read before it)
            out += [markdown[pos:b.start], (f"[{b.claim}]({b.source}) {badge}" if b.kind == "url" else f"{b.source} {b.claim} {badge}")]
        else:
            quote = "\n".join("> " + ln if ln.strip() else ">" for ln in b.claim.splitlines())
            link = f'<a href="{html.escape(b.source)}">source</a>' if b.kind == "url" else html.escape(b.source)
            out += [markdown[pos:b.start], f"{quote}\n>\n> {badge} {link}"]
        pos = b.end
    return "".join(out) + markdown[pos:], entries


def meta_html(m: dict) -> str:
    """A fact's metadata as one small line: who and when, how sure, a note, the tags, then any other key as `key: value`."""
    if not m:
        return ""
    bits = [f"by {m['by']}"] if m.get("by") else []
    bits += [f"as of {str(m['as_of'])[:10]}"] if m.get("as_of") else []
    bits += [f"written {str(m['at'])[:10]}"] if m.get("at") else []
    bits += [f"confidence {m['confidence']}"] if m.get("confidence") is not None else []
    bits += [", ".join(f"#{x}" for x in m["tags"])] if isinstance(m.get("tags"), list) and m["tags"] else []
    bits += [f"{k}: {v}" for k, v in m.items() if k not in STD_META and k != "stale_after"]
    note = f"<br><small>{html.escape(str(m['note']))}</small>" if m.get("note") else ""
    return f'<small class="fact-meta">{html.escape(" · ".join(map(str, bits)))}</small>{note}<br>' if bits or note else ""


def bibliography(entries: list) -> str:
    """The page's facts as an HTML list, one entry per block, each with the id its badge links to: kind, source, state, the line, the claim."""
    if not entries:
        return ""
    items = []
    for e in entries:
        src = f'<a href="{html.escape(e["source"])}">{html.escape(e["source"])}</a>' if e["kind"] == "url" else f"<code>{html.escape(e['source'])}</code>"
        claim = html.escape(" ".join(e["claim"].split())[:220])
        items.append(f'<li id="fact-{e["n"]}"><span class="fact-kind">{html.escape(e["kind"])}</span> {src}<br>'
                     f'<span class="fact-badge" data-state="{e["status"]}">{html.escape(e["label"])}</span> <small>line {e["line"]}{" · due for a check" if e.get("due") else ""}</small><br>'
                     f'{meta_html(e.get("meta") or {})}<q>{claim}</q></li>')
    return f'<section class="fact-bib" id="facts"><h2>Facts</h2><ol>{"".join(items)}</ol></section>'


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
        raise ValueError(f"the result has nothing at {path!r} | fix: set `watch` in bower.yaml to a path in the tool's result")
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
