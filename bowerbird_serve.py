"""bowerbird serve: browse the collection in a browser (localhost only, rereads files on every request).

Search is bowerbird's own `passages` (BM25 ranked sections, semantic too when kbmcp.yaml turns it on). Seal state comes
from bowerbird's own hash and ledger, so a page reads sealed, stale or unsealed exactly as `seal check=true` would.
A human's front end to the CLI, with no AI in it. Writes go through the same tools the CLI runs (a diff first, then
Confirm). A human seals from a modal that asks what the MCP prompt asks. Nothing here stamps `generated`.

Needs `markdown` (pip install 'bowerbird-mcp[serve]').
"""
import asyncio
import hashlib
import html
import inspect
import io
import json
import os
import re
import secrets
import signal
import socket
import sys
import threading
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bowerbird_logo import PATHS, VIEWBOX

PORT = 26937  # BOWER on a phone keypad (2 6 9 3 7)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
LOGO = f'<svg class=logo viewBox="{VIEWBOX}" role=img aria-label=bowerbird>{PATHS}</svg>'
CSS = """
:root{--bg:#fff;--fg:#1c1c1c;--mut:#666;--line:#8884;--acc:#0b5fff;--bad:#c62828;--ok:#2e7d32;--warn:#b26a00;--logo:#1e2a4a}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161616;--fg:#e6e6e6;--mut:#9a9a9a;--acc:#6ea8ff;--bad:#ef5350;--ok:#66bb6a;--warn:#ffb74d;--logo:#e8ecf5}}
:root{color-scheme:light dark}:root[data-theme=light]{color-scheme:light}:root[data-theme=dark]{color-scheme:dark}
:root[data-theme=dark]{--bg:#161616;--fg:#e6e6e6;--mut:#9a9a9a;--acc:#6ea8ff;--bad:#ef5350;--ok:#66bb6a;--warn:#ffb74d;--logo:#e8ecf5}
.logo-dark{display:none}  /* docs pages carry both logos, as the MkDocs theme expects: show the one that fits */
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) .logo-light{display:none}:root:not([data-theme=light]) .logo-dark{display:inline}}
:root[data-theme=dark] .logo-light{display:none}:root[data-theme=dark] .logo-dark{display:inline}
img{max-width:100%;height:auto}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui}a{color:var(--acc)}
.wrap{display:grid;grid-template-columns:17rem minmax(0,1fr) 15rem;gap:1.5rem;max-width:100rem;margin:0 auto;padding:0 1rem}
nav,aside{position:sticky;top:3rem;align-self:start;max-height:calc(100vh - 3rem);overflow:auto;padding:1rem 0;font-size:13px}
nav details{margin:.1rem 0}nav summary{cursor:pointer;font-weight:600}nav a{display:block;padding:.1rem .4rem;text-decoration:none;color:var(--fg);border-radius:4px}
nav a:hover{background:var(--line)}nav a.cur{background:var(--acc);color:#fff}nav details details{margin-left:.7rem}
main{padding:1rem 0;min-width:0}h1{margin-top:.2rem}table{border-collapse:collapse;display:block;overflow:auto}
td,th{border:1px solid var(--line);padding:.25rem .5rem;vertical-align:top}code,pre{background:var(--line);border-radius:3px}code{padding:0 .2rem}pre{padding:.6rem;overflow:auto}pre code{background:none}
.meta{color:var(--mut);font-size:13px;border:1px solid var(--line);border-radius:6px;padding:.4rem .7rem;margin-bottom:1rem}
.b{display:inline-block;padding:0 .4rem;border-radius:9px;border:1px solid currentColor;font-size:12px;margin-right:.3rem}
.sealed{color:var(--ok)}.derived{color:var(--mut)}.broken-seal{color:var(--bad)}.unsealed{color:var(--warn)}a.broken{color:var(--bad);text-decoration:line-through}
aside h4{margin:.8rem 0 .2rem;color:var(--mut);text-transform:uppercase;font-size:11px}aside ul{margin:0;padding-left:1rem}
input{width:100%;padding:.3rem;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}
#top{position:sticky;top:0;z-index:5;display:flex;gap:.5rem;align-items:center;height:3rem;padding:0 1rem;background:var(--bg);border-bottom:1px solid var(--line)}
#top a.brand{display:flex;align-items:center}.logo{height:1.35rem;width:auto;flex:none}.logo path{fill:var(--logo)}
#top button{background:none;border:1px solid var(--line);color:var(--fg);border-radius:4px;padding:.15rem .5rem;cursor:pointer}
#crumbs{color:var(--mut);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}#crumbs a{color:var(--mut)}
#sw{position:relative;width:24rem;display:flex;gap:.3rem}#sw select{width:auto;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}#res{display:none;position:absolute;top:2.2rem;left:0;right:0;z-index:7;background:var(--bg);border:1px solid var(--line);border-radius:6px;max-height:70vh;overflow:auto;box-shadow:0 6px 20px #0004}
#res a{display:block;padding:.3rem .6rem;text-decoration:none;color:var(--fg)}#res a.sel,#res a:hover{background:var(--acc);color:#fff}#res small{color:inherit;opacity:.7}
.dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;margin-right:.35rem;background:var(--warn)}.dot.sealed{background:var(--ok)}.dot.derived{background:var(--line)}.dot.broken-seal{background:var(--bad)}
aside li.act>a{font-weight:700}kbd{border:1px solid var(--line);border-radius:3px;padding:0 .3rem;font-size:12px}.dot.none{background:var(--line)}
.diff .a{color:var(--ok)}.diff .d{color:var(--bad)}nav a.new{color:var(--mut);font-size:12px}.menu{position:relative}.menu summary{list-style:none;cursor:pointer;border:1px solid var(--line);border-radius:4px;padding:.15rem .6rem}.menu summary::-webkit-details-marker{display:none}
.menu div{position:absolute;right:0;z-index:6;min-width:9rem;background:var(--bg);border:1px solid var(--line);border-radius:6px;box-shadow:0 6px 20px #0004;padding:.2rem}.menu div a,.menu div button{display:block;width:100%;text-align:left;border:0;padding:.3rem .6rem;background:none;color:var(--fg);font:inherit;cursor:pointer;text-decoration:none}.menu div a:hover,.menu div button:hover{background:var(--acc);color:#fff}
aside .bar{margin-top:0}aside .menu div{position:static;box-shadow:none;margin-top:.2rem;min-width:0}  /* the pane scrolls: a floating menu would be clipped */
.bar{display:flex;align-items:flex-start;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.bar a.cur{background:var(--acc);color:#fff}.bar a,button.go{border:1px solid var(--line);border-radius:4px;padding:.15rem .6rem;text-decoration:none;background:none;color:var(--fg);cursor:pointer;font:inherit}button.go.hot{background:var(--acc);color:#fff;border-color:var(--acc)}
textarea{width:100%;min-height:60vh;font:13px/1.45 ui-monospace,monospace;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}
label{display:block;margin:.4rem 0}label small{color:var(--mut)}.err{border:1px solid var(--bad);color:var(--bad);border-radius:6px;padding:.4rem .7rem}dialog{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;max-width:38rem}
.hit{margin:.8rem 0}.hit small{color:var(--mut)}@media(max-width:60rem){.wrap{display:block}nav,aside{position:static;max-height:none}}
"""
JS = r"""
(()=>{
const $=(q,e=document)=>e.querySelector(q), $$=(q,e=document)=>[...e.querySelectorAll(q)];
const root=document.documentElement, mq=matchMedia('(prefers-color-scheme:dark)'), tb=$('#theme'), ST=['auto','light','dark'], IC={auto:'◐',light:'☀',dark:'☾'};
let mode='auto'; try{const t=localStorage.getItem('kbtheme'); if(ST.includes(t)) mode=t;}catch(e){}
const applyTheme=()=>{if(mode==='auto')delete root.dataset.theme;else root.dataset.theme=mode;tb.textContent=IC[mode];tb.title='theme: '+mode+(mode==='auto'?' (follows system, now '+(mq.matches?'dark':'light')+')':'')+' (t)'};
tb.onclick=()=>{mode=ST[(ST.indexOf(mode)+1)%3];try{localStorage.setItem('kbtheme',mode)}catch(e){}applyTheme()};
mq.addEventListener('change',applyTheme); applyTheme();
$('#back').onclick=()=>history.back(); $('#fwd').onclick=()=>history.forward();
const q=$('#q'), res=$('#res'); let sel=-1, tm;
const md=$('#mode'); try{const m=new URLSearchParams(location.search).get('mode')||localStorage.getItem('kbmode'); if(m&&[...md.options].some(o=>o.value===m)) md.value=m;}catch(e){}
const show=items=>{res.innerHTML=items.map(r=>r.error?`<a>${r.error}</a>`:`<a href="${r.href}"><b>${r.title}</b><br><small>${r.sub}</small></a>`).join('')||'<a>nothing in the collection</a>';res.style.display='block';sel=-1;};
const run=()=>{clearTimeout(tm);const v=q.value.trim();if(!v){res.style.display='none';return}tm=setTimeout(()=>fetch('/_search.json?mode='+md.value+'&q='+encodeURIComponent(v)).then(r=>r.json()).then(show),200)};
q.oninput=run; md.onchange=()=>{try{localStorage.setItem('kbmode',md.value)}catch(e){}run()};
q.onkeydown=e=>{const a=$$('a[href]',res);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();sel=(sel+(e.key==='ArrowDown'?1:-1)+a.length)%a.length;a.forEach((x,i)=>x.classList.toggle('sel',i===sel))}
 else if(e.key==='Enter'){e.preventDefault();location=sel>=0?a[sel].href:'/_search?mode='+md.value+'&q='+encodeURIComponent(q.value)}else if(e.key==='Escape'){res.style.display='none';q.blur()}};
document.addEventListener('click',e=>{if(!e.target.closest('#sw'))res.style.display='none';$$('details.menu[open]').forEach(m=>{if(!m.contains(e.target))m.open=false})});
const links=$$('nav a[data-seal]'), cur=links.findIndex(a=>a.classList.contains('cur'));
const jump=(d,unsealed)=>{for(let i=1;i<=links.length;i++){const a=links[(cur+d*i+links.length*2)%links.length];if(!unsealed||!['sealed','derived'].includes(a.dataset.seal)){location=a.href;return}}};
document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea')||e.metaKey||e.ctrlKey||e.altKey)return;
 if(e.key==='/'){e.preventDefault();q.focus()}else if(e.key==='t')$('#theme').click();else if(e.key==='n')jump(1,true);else if(e.key==='p')jump(-1,true);else if(e.key==='j')jump(1,false);else if(e.key==='k')jump(-1,false);else if(e.key==='['){history.back()}else if(e.key===']'){history.forward()}});
const heads=$$('main h2[id],main h3[id]'), tl=new Map($$('aside a[href^="#"]').map(a=>[a.getAttribute('href').slice(1),a]));
if(heads.length&&'IntersectionObserver' in window){const io=new IntersectionObserver(es=>es.forEach(en=>{if(en.isIntersecting){$$('aside .act').forEach(x=>x.classList.remove('act'));const a=tl.get(en.target.id);if(a)a.parentElement.classList.add('act')}}),{rootMargin:'-10% 0px -80% 0px'});heads.forEach(h=>io.observe(h))}
const c=$('nav a.cur'); if(c)c.scrollIntoView({block:'center'});
})();
"""


def pidfile(port: int) -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "bowerbird-mcp" / f"serve-{port}.pid"


def listening(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), 0.5).close()
        return True
    except OSError:
        return False


def found(port: int):
    """The pid of our server on port (the pid file names it and the port answers), else None."""
    try:
        pid = int(pidfile(port).read_text())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return None
    return pid if listening(port) else None


def status(port: int = PORT) -> int:
    """Information only: say whether our server is on port (exit 0), or not (exit 1). Changes nothing."""
    pid, f = found(port), pidfile(port)
    if pid:
        print(f"running: http://127.0.0.1:{port}/ (pid {pid}; `bowerbird-mcp serve stop{'' if port == PORT else f' {port}'}` ends it)")
        return 0
    print(f"not running on port {port}" + (" (a stale pid file was left)" if f.exists() else ""))
    return 1


def stop(port: int = PORT) -> int:
    """Stop our server if there is one on port. Nothing there is not an error (exit 0): the port is as free as asked."""
    f = pidfile(port)
    pid = found(port)  # a stale pid file's number may belong to another process now: only a live answer is killed
    if pid:
        os.kill(pid, signal.SIGTERM)
        print(f"stopped the server on port {port}")
    else:
        print(f"nothing running on port {port}")
    f.unlink(missing_ok=True)
    return 0


def start(kb, port: int = PORT, foreground: bool = False) -> int:
    """Start only when nothing is on the port: ours already there is a no-op (exit 0), something else is an error (exit 1)."""
    if found(port):
        return status(port)
    if listening(port):
        print(f"error: port {port} is in use by something else | fix: pick another port (`serve start 8080`)")
        return 1
    return run(kb, port, foreground)


def restart(kb, port: int = PORT, foreground: bool = False) -> int:
    """Stop what is found on port (if anything), wait for the port to clear, then start."""
    stop(port)
    for _ in range(50):  # up to 5 s for the old server to let go of the port
        if not listening(port):
            break
        time.sleep(0.1)
    return start(kb, port, foreground)


def run(kb, port: int = PORT, foreground: bool = False) -> int:
    """Serve the collection kb (the bowerbird_mcp module) on localhost:port, in the background unless foreground."""
    # kb is the bowerbird_mcp module, passed in by its `serve` command.
    try:
        import markdown
    except ImportError:
        print("error: serve needs the markdown package | fix: pip install 'bowerbird-mcp[serve]' (or uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve)")
        return 2
    ROOT = kb.KB_ROOT
    SKIP, MAXSIZE = [set()], 512 * 1024  # seal-only files not shown (binary or oversized); the size cap in bytes
    os.chdir(ROOT)  # tools default to the bundle around the working directory: serve means the whole collection, wherever it was started
    href = lambda rel: "/" + urllib.parse.quote(rel)
    esc = html.escape

    def scan():
        """rel path -> {title, meta, body, state, by, at}, with seals checked by bowerbird's own hash and ledger."""
        try:
            ledger = kb.ledger_by_file()
        except ValueError:
            ledger = {}
        docs = {}
        skip = set()
        for p in sorted(ROOT.rglob("*.md")):
            rel = p.relative_to(ROOT)
            if p.is_symlink() or any(part.startswith(".") for part in rel.parts):  # never follow a link, never show a dotfile
                continue
            key, text = rel.as_posix(), kb.read(p)
            if text is None:
                continue
            d = kb.meta(text)[0] or {}
            es, valid = kb.reviews(d, key, text, ledger)
            last = (valid or es or [{}])[-1]
            docs[key] = {"title": kb.title_of(d, text, p), "meta": d, "fm": kb.meta(text)[0] is not None, "body": kb.split(text)[1],
                         "state": "derived" if kb.derived(p) else "unsealed" if not es else "sealed" if valid else "broken-seal",
                         "by": last.get("by", ""), "at": last.get("at", "")}
        for p, made in [(q, False) for q in kb.sealonly_files()] + [(q, True) for q in kb.derived_files()]:  # seal-only files: a page each, read-only; derived ones are marked, not sealed
            rel = p.relative_to(ROOT)
            key = rel.as_posix()
            if made and key in docs:
                continue
            if p.is_symlink() or any(part.startswith(".") for part in rel.parts):  # sealable from the CLI, not shown here
                continue
            text = kb.read(p) if p.stat().st_size <= MAXSIZE else None
            if text is None:  # binary or over the cap: not listed, not shown
                skip.add(key)
                continue
            es, valid = kb.reviews({}, key, text, ledger)
            last = (valid or es or [{}])[-1]
            docs[key] = {"title": key, "meta": {}, "fm": False, "body": "", "code": True, "text": text,
                         "state": "derived" if made else "unsealed" if not es else "sealed" if valid else "broken-seal",
                         "by": last.get("by", ""), "at": last.get("at", "")}
        SKIP[0] = skip  # one assignment, so a request in another thread never sees it half built
        return docs

    def code_html(name, text):
        """A file read-only, numbered: pygments picks the lexer by file name when it is installed, else plain."""
        try:
            import pygments
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_for_filename
            from pygments.util import ClassNotFound
            try:
                lexer = get_lexer_for_filename(name)
            except ClassNotFound:
                lexer = None
        except ImportError:
            lexer = None
        if lexer is None:
            return "<pre class=code>" + "".join(f"<span class=l>{esc(ln)}</span>\n" for ln in text.splitlines()) + "</pre>"
        css = HtmlFormatter(style="default").get_style_defs(".highlight")
        dark = HtmlFormatter(style="monokai")  # light set above, dark set under the page's own colour-scheme rules
        css += (f"@media(prefers-color-scheme:dark){{{dark.get_style_defs(':root:not([data-theme=light]) .highlight')}}}"
                + dark.get_style_defs(":root[data-theme=dark] .highlight"))
        return f"<style>{css}.highlight pre{{background:none}}.linenos{{color:var(--mut);margin-right:1em;user-select:none}}</style>" + pygments.highlight(
            text, lexer, HtmlFormatter(linenos="inline"))

    def resolve(src, url):
        if re.match(r"[a-z]+:", url):
            return None
        base = ROOT if url.startswith("/") else (ROOT / src).parent
        try:
            return (base / urllib.parse.unquote(url).lstrip("/")).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return None

    def badge(d):
        word = {"sealed": "sealed", "broken-seal": "seal broken by edit", "unsealed": "unsealed", "derived": "derived from the code"}[d["state"]]
        who = f" {esc(str(d['by']))} {esc(str(d['at']))}" if d["by"] else ""
        return f'<span class="b {d["state"]}">{word}</span>{who}'

    def nav(docs, cur):
        """The whole directory under the collection's root folder."""
        tree = {}
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            if p.is_symlink() or any(x.startswith(".") for x in rel.parts) or rel.parts[-1] == ".DS_Store":
                continue
            if p.is_dir():
                node = tree
                for part in rel.parts:
                    node = node.setdefault(part + "/", {})
                continue
            node = tree
            for part in rel.parts[:-1]:
                node = node.setdefault(part + "/", {})
            node[rel.parts[-1]] = rel.as_posix()

        newlink = lambda d: f'<a class=new href="/_new?dir={urllib.parse.quote(d.rstrip("/"))}">+ New file</a>'

        def walk(node, pre=""):
            out = []
            for k in sorted(node, key=lambda k: (not k.endswith("/"), k.lower())):
                v = node[k]
                if isinstance(v, dict):
                    out.append(f"<details{' open' if cur.startswith(pre + k) else ''}><summary>{esc(k)}</summary>{walk(v, pre + k)}{newlink(pre + k)}</details>")  # folded unless it holds the current page
                elif v in SKIP[0]:
                    continue
                elif v in docs:
                    st = docs[v]["state"]
                    out.append(f'<a href="{href(v)}" data-seal="{st}" title="{esc(docs[v]["title"])}" class="{"cur" if v == cur else ""}"><span class="dot {st}"></span>{esc(k)}</a>')
                else:
                    out.append(f'<a href="{href(v)}"><span class="dot none"></span>{esc(k)}</a>')
            return "".join(out)
        return f"<details open><summary>{esc(ROOT.name)}/</summary>{walk(tree)}{newlink('')}<a class=new href=/_lint>Lint all</a><a class=new href=/_tags>Tags</a></details>"

    def page(title, left, body, right="", rel=""):
        parts = rel.split("/") if rel else []
        crumbs = [f'<a href="/">{esc(ROOT.name)}</a>'] + [
            f'<a href="{href("/".join(parts[:i + 1]))}">{esc(x)}</a>' if i < len(parts) - 1 and (ROOT / "/".join(parts[:i + 1]) / "index.md").exists() else esc(x)
            for i, x in enumerate(parts)]
        top = (f'<div id=top><a class=brand href="/" title="bowerbird">{LOGO}</a><button id=back title="back ([)">◀</button><button id=fwd title="forward (])">▶</button>'
               f'<span id=crumbs>{" / ".join(crumbs)}</span><div id=sw><select id=mode title="what to search: passages (ranked sections), concepts (whole pages), meaning (passages matched by meaning), tags">{"".join(f"<option value={m}>{n}" for m, n in modes())}</select><input id=q placeholder="search ( / )" autocomplete=off><div id=res></div></div><form method=post action=/_stop onsubmit="return confirm(&quot;Stop the bowerbird server? Reopen it with: bowerbird-mcp serve&quot;)" style=margin:0><input type=hidden name=_t value="{TOKEN}"><button title="stop this server" aria-label="stop this server">⏻</button></form><button id=theme title="theme (t)">◐</button></div>')
        hint = '<h4>Keys</h4><small><kbd>/</kbd> search <kbd>n</kbd>/<kbd>p</kbd> next/prev unsealed<br><kbd>j</kbd>/<kbd>k</kbd> next/prev doc <kbd>t</kbd> theme <kbd>[</kbd><kbd>]</kbd> history</small>'
        return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>{esc(title)} · bowerbird</title>"
                f"<link rel=icon type=image/svg+xml href=/_logo.svg><script>try{{var t=localStorage.getItem('kbtheme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}}catch(e){{}}</script>"
                f"<style>{CSS}</style>{top}<div class=wrap><nav>{left}</nav><main>{body}</main><aside>{right}{hint}</aside></div><script>{JS}</script>").encode()

    MODES = ("passages", "concepts", "semantic", "tags")
    NAMES = {"passages": "Passages", "concepts": "Concepts", "semantic": "Meaning", "tags": "Tags"}
    modes = lambda: [(m, NAMES[m]) for m in MODES if m != "semantic" or kb.OPTS["semantic"]]  # meaning is offered only when kbmcp.yaml turns it on
    pth = lambda b, f: f if b in (".", "") else f"{b}/{f}"

    def ask(q, mode="passages"):
        """(hits, error) for the four searches. A hit: {path, title, line, heading, extra, text}.
        passages: ranked sections by keyword. concepts: whole pages (`search`). semantic: passages fused with meaning,
        when kbmcp.yaml turns it on. tags: pages carrying a tag that contains q."""
        mode = mode if mode in MODES else "passages"
        try:
            if mode == "concepts":
                return [{"path": pth(h["bundle"], h["file"]), "title": h["title"], "line": h["line"], "heading": "",
                         "extra": f'{h["type"] or ""} · matched {", ".join(h["matched"])}', "text": h["text"]}
                        for h in kb.REG["search"](q, limit=12)["hits"]], ""
            if mode == "tags":
                want, out = q.lower(), []
                for b, x in kb.every(kb.KB_ROOT, ""):
                    hit = [t for t in map(str, kb.tags_of(x)) if want in t.lower()]
                    if hit:
                        out.append({"path": pth(kb.kbpath(b), x.rel), "title": kb.title_of(x.meta or {}, x.text, x.path), "line": 1, "heading": "",
                                    "extra": "tags: " + ", ".join(hit), "text": str((x.meta or {}).get("description") or "")})
                return sorted(out, key=lambda h: h["path"])[:50], ""
            if mode == "semantic" and not kb.OPTS["semantic"]:
                return [], "meaning search is off | fix: set `semantic: true` in kbmcp.yaml (it needs fastembed), then reindex"
            with LOCK:  # passages reads one global switch: keyword mode turns it off for this call
                keep = kb.OPTS["semantic"]
                kb.OPTS["semantic"] = keep and mode == "semantic"
                try:
                    r = kb.REG["passages"](q, limit=12)
                finally:
                    kb.OPTS["semantic"] = keep
        except (ValueError, KeyError, OSError) as e:
            return [], str(e).split(" | ")[0]
        return [{"path": pth(h["bundle"], h["file"]), "title": h["title"], "line": h["line"], "heading": h["heading"] or "",
                 "extra": f'{h["tier"]}{" · stale" if h["stale"] else ""} · {h["match"]}%', "text": h["text"]} for h in r["hits"]], ""

    TOKEN, LOCK = secrets.token_urlsafe(16), threading.RLock()  # the kb module holds global state: one tool at a time
    HOSTS = {f"127.0.0.1:{port}", f"localhost:{port}"}  # a Host we did not bind is DNS rebinding
    FORMS = {"move", "archive", "fix"}  # the tools a button here leads to; the rest are the CLI's (`bowerbird-mcp help`)
    HIDE = {"by", "ctx", "apply"}  # `by` is never asked: nothing here stamps `generated`
    uq = urllib.parse.quote  # not `q`: do_GET has its own

    def err_box(e):
        msg, _, fix = str(e).partition(" | fix: ")
        return f'<p class=err>{esc(msg)}{"<br>fix: " + esc(fix) if fix else ""}</p>'

    def tfile(key):
        """(file, bundle) as the tools name a file: within its bundle for okf, from the collection root otherwise."""
        p = ROOT / key
        if kb.fmt_of(p) != "okf":
            return key, ""
        b = kb.enclosing(p.parent)
        return kb.rel(p, b), kb.kbpath(b)

    def call(name, **args):
        with LOCK:
            r = kb.REG[name](**args)
            return asyncio.run(r) if inspect.isawaitable(r) else r

    def post(action, inner, button="Go", hot=False):
        return (f'<form method=post action="{esc(action)}"><input type=hidden name=_t value="{TOKEN}">{inner}'
                f'<button class="go{" hot" if hot else ""}">{esc(button)}</button></form>')

    def hidden(vals):
        return "".join(f'<input type=hidden name="{esc(k)}" value="{esc(str(v))}">' for k, v in vals.items())

    def show(r):
        d = r.get("diff") if isinstance(r, dict) else None
        rest = {k: v for k, v in r.items() if k != "diff"} if isinstance(r, dict) else r
        out = f"<pre>{esc(json.dumps(rest, indent=1, default=str))}</pre>"
        if d:
            out += "<pre class=diff>" + "".join(
                f'<span class="{"a" if ln.startswith("+") and not ln.startswith("+++") else "d" if ln.startswith("-") and not ln.startswith("---") else ""}">{esc(ln)}</span>\n'
                for ln in d.splitlines()) + "</pre>"
        return out

    def tool_form(name, vals):
        params = inspect.signature(kb.REG[name]).parameters
        rows = []
        for k, p in params.items():
            if k in HIDE:
                continue
            v = vals.get(k, "")
            if kb.conv("1", p.annotation) is True:
                rows.append(f'<label><input type=checkbox name="{k}" {"checked" if v else ""} style="width:auto"> {k}</label>')
            else:
                hint = "JSON" if "dict" in str(p.annotation) else "a, b" if "list" in str(p.annotation) else "required" if p.default is p.empty else str(p.default)
                rows.append(f'<label>{k} <small>{esc(hint)}</small><input name="{k}" value="{esc(str(v))}"></label>')
        return post(f"/_tool/{name}", "".join(rows), "Preview" if "apply" in params else "Run", True)

    def run_tool(name, form):
        params = inspect.signature(kb.REG[name]).parameters
        vals, args = {}, {}
        for k, p in params.items():
            if k in HIDE:
                continue
            v = form.get(k, [""])[0].strip()
            vals[k] = v
            if v:
                args[k] = kb.conv(v, p.annotation)
        applied = "_apply" in form
        if "apply" in params:
            args["apply"] = applied
        r = call(name, **args)
        confirm = ""
        if "apply" in params and not applied:
            confirm = post(f"/_tool/{name}", hidden(vals) + "<input type=hidden name=_apply value=1>", "Confirm: apply this", True)
        return f'<h1>{name}{" (applied)" if applied else ""}</h1>{show(r)}{confirm}<p><a href="/_tool/{name}">Again</a></p>'

    def concepts():
        return kb.every(kb.KB_ROOT, "")

    def lint_body(key=""):
        kw = {"limit": 0}
        if key:
            kw["file"], kw["bundle"] = tfile(key)
        else:
            kw.update(all=True, bundle=".")
        r = call("lint", **kw)
        fs = r.get("findings", [])
        fix = post("/_tool/fix", hidden({"all": "on", "bundle": "."}), "Preview fixes", True) if any(x["fixable"] for x in fs) else ""
        return f'<h1>Lint{": " + esc(key) if key else ""}</h1><p>ok: {r.get("ok")} · {len(fs)} finding(s)</p>{fix}{ftable(fs)}'

    def ftable(fs, new_tab=False):
        row = lambda x: (lambda path: f'<tr><td>{esc(x["severity"])}</td><td>{esc(x["kind"])}</td><td><a href="{href(path)}"{" target=_blank" if new_tab else ""}>{esc(path)}</a></td>'
                         f'<td>{esc(x["message"])}<br><small>{esc(x["fix"])}</small></td><td>{"fix" if x["fixable"] else ""}</td></tr>')(
            x["file"] if x.get("bundle") in (None, "", ".") else f'{x["bundle"]}/{x["file"]}')
        return "<table><tr><th>severity<th>kind<th>file<th>finding<th></tr>" + "".join(map(row, fs)) + "</table>" if fs else "<p>No findings.</p>"

    def lint_text(key, text):
        """Lint a page as it is in the editor, unsaved: the tool reads the edited text for that one file, and nothing is written."""
        p = editable(key)
        if not p.exists():
            raise ValueError("a new page has nothing on disk to lint | fix: save it once, then lint")
        f, b = tfile(key)
        with LOCK:
            real = kb.read
            kb.read = lambda q: text if Path(q).resolve() == p else real(q)
            try:
                r = kb.REG["lint"](limit=0, file=f, bundle=b)
            finally:
                kb.read = real
        fs = r.get("findings", [])
        return f'<h3>Lint (this text, not saved): ok {r.get("ok")}, {len(fs)} finding(s)</h3>{ftable(fs, True)}'

    def tags_body(msg="", old=""):
        n = {}
        for _, x in concepts():
            for t in map(str, kb.tags_of(x)):
                n[t] = n.get(t, 0) + 1
        intro = ('<p>A tag is a word in a page\'s frontmatter, the <code>---</code> block at the top of the file: '
                 '<code>tags: [deploy, runbook]</code>. Bowerbird reads them for search (the Tags search type, and tags weigh into the '
                 'others), for <code>list</code> and <code>vocab</code>, and for lint (a tag spelled two ways is flagged). '
                 'Add or change a page\'s tags in the Tags field under that page, or edit its frontmatter. '
                 'This page lists every tag in use, and renames, merges or removes one across all pages at once.</p>')
        if not n:
            return f"<h1>Tags</h1>{msg}{intro}<p><b>No page has a tag yet.</b> Open a page that has frontmatter and fill in its Tags field.</p>"
        rows = "".join(f'<tr><td><a href="/_search?mode=tags&q={uq(t)}">{esc(t)}</a><td>{c}<td><a href="/_tags?old={uq(t)}">rename or remove</a></tr>'
                       for t, c in sorted(n.items(), key=lambda i: (-i[1], i[0])))
        form = post("/_retag", f'<label>tag <input name=old value="{esc(old)}"></label><label>becomes <small>(leave empty to remove it; the name of an existing tag merges them)</small><input name=new{" autofocus" if old else ""}></label>', "Preview the change", True)
        return f"<h1>Tags</h1>{msg}{intro}<h3>Rename, merge or remove</h3>{form}<h3>In use</h3><table><tr><th>tag<th>pages<th></tr>{rows}</table>"

    def retag(old, new, apply):
        outs = []
        with LOCK:
            for b, x in concepts():
                ts = [str(t) for t in kb.tags_of(x)]
                if old in ts:
                    nt = []
                    for t in ts:
                        t = new if t == old else t
                        if t and t not in nt:
                            nt.append(t)
                    outs.append(kb.set_(fields={"tags": nt}, file=x.rel, bundle=kb.kbpath(b), apply=apply))
        return outs

    def editable(key):
        p = (ROOT / key).resolve()
        if not key or not kb.inside(p, ROOT) or p.suffix != ".md" or any(x.startswith(".") for x in p.relative_to(ROOT).parts):
            raise ValueError(f"{key!r} is not a page | fix: pages are .md files inside the collection")  # shortcut: .md only, so no config or code file is editable here
        return p

    def sha(t):
        return hashlib.sha256((t or "").encode()).hexdigest()

    def edit_body(key, text=None, msg=""):
        p = editable(key)
        cur = kb.read(p) if p.exists() else None
        if p.exists() and cur is None:
            raise ValueError(f"{key} is not UTF-8 text")
        body = cur if text is None else text
        inner = (f'<input type=hidden name=file value="{esc(key)}"><input type=hidden name=base value="{sha(cur)}">'
                 f'<textarea name=text spellcheck=false>{esc(body or "")}</textarea>')
        return (f'<h1>{"Edit" if cur is not None else "New page"}: {esc(key)}</h1>{msg}<p><small>Saving a sealed page breaks its seal: '
                f'it reads "seal broken by edit" until you review it again.</small></p>'
                f'<form method=post action="/_save"><input type=hidden name=_t value="{TOKEN}">{inner}<div class=bar><button class="go hot">Save</button>'
                f'<button class=go formaction="/_editlint" title="lint this text without saving it">Lint</button>'
                f'<a href="{href(key) if cur is not None else "/"}">Cancel</a></div></form>')

    def new_body(d, name="", text="", msg=""):
        """The editor, for a page that does not exist yet: the folder is fixed, the name is typed, Save writes it."""
        inner = (f'<input type=hidden name=dir value="{esc(d)}"><textarea name=text spellcheck=false>{esc(text)}</textarea>')
        return (f'<h1>{esc(d + "/" if d else "")}<input form=newf name=name value="{esc(name)}" placeholder="name.md" autofocus style="width:auto;min-width:14rem;font:inherit"></h1>{msg}'
                f'<p><small>The folder is above; type a file name (.md is added), or a name ending in / to make a folder.</small></p>'
                f'<form id=newf method=post action="/_new"><input type=hidden name=_t value="{TOKEN}">{inner}'
                f'<div class=bar><button class="go hot">Save</button><a href="/">Cancel</a></div></form>')

    def backlinks(docs, key):
        return [src for src, o in docs.items() if src != key and any(resolve(src, link) == key for link in LINK.findall(o["body"]))]

    def seal_dialog(key):
        """The modal: what seal's MCP prompt shows, and asks the same two things (confirm, and your id)."""
        try:
            f, b = tfile(key)
            okf, p, r, t, d, label = kb.review_target(f, b, "")
        except (ValueError, OSError):
            return ""
        extra = ""
        if okf and d.get("status") == "draft":
            extra = '<label><input type=checkbox name=promote style="width:auto"> promote draft to stable (§5.4)</label>'
        elif not okf:
            extra = '<label>decision <small>(optional)</small><select name=decision><option value="">none<option>accepted<option>rejected</select></label>'
        msg = kb.review_message(label, okf, t, d, "", False)
        return (f'<dialog id=seal><form method=post action="/_seal"><input type=hidden name=_t value="{TOKEN}"><input type=hidden name=file value="{esc(key)}">'
                f'<input type=hidden name=sha value="{kb.content_hash(t, okf)}"><h3>Seal {esc(key)}</h3><p>{esc(msg)}</p>'
                f'<label><input type=checkbox name=confirm style="width:auto"> I reviewed this concept and confirm it is accurate</label>'
                f'<label>Your id <small>(recorded as human:&lt;id&gt;)</small><input name=reviewer value="{esc(kb.kb_user())}"></label>{extra}'
                f'<div class=bar><button class="go hot">Seal</button><button type=button class=go onclick="this.closest(\'dialog\').close()">Cancel</button></div></form></dialog>')

    def do_seal(form):
        key, rid = form["file"][0], form.get("reviewer", [""])[0].strip().removeprefix("human:")
        if "confirm" not in form:
            return "not confirmed; nothing written"
        if not rid or re.search(r"\s", rid):
            raise ValueError("reviewer id is empty or has spaces | fix: confirm again with your id")
        if kb.derived(ROOT / key):
            raise ValueError(f"{key} is derived from the code | fix: nothing to review; a `!` glob in seal.require leaves it out")
        f, b = tfile(key)
        decision = form.get("decision", [""])[0]
        with LOCK:
            okf, p, r, t, d, label = kb.review_target(f, b, decision)
            if kb.content_hash(t, okf) != form.get("sha", [""])[0]:
                raise ValueError(f"{key} changed while the prompt was open; nothing written | fix: review it again")
            kb.ATTEST = f"human:{rid}"  # the one place a human is recorded here: this click, with this typed id
            try:
                asyncio.run(kb.seal(file=f, bundle=b, promote="promote" in form, decision=decision))
            finally:
                kb.ATTEST = ""
        return f"sealed as human:{rid}"

    def go(h, where):
        h.send_response(303)
        h.send_header("Location", where)
        h.send_header("Content-Length", "0")
        h.end_headers()

    class H(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **{e: "text/plain; charset=utf-8" for e in (".yaml", ".yml", ".py", ".sh", ".conf", ".cf", ".toml", ".json", "")}}  # noqa: RUF012

        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(ROOT), **k)

        def send_bytes(self, data, ctype="text/html; charset=utf-8", code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def blocked(self, path):
            """A request path that must 404: a dot-prefixed part (decoded once, so `.%65nv`, `//.env` and `%2e%2e` are caught)
            or any symlinked component below the collection root."""
            parts = [x for x in urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0]).split("/") if x]
            cur = ROOT
            try:
                for x in parts:
                    cur = cur / x
                    if x.startswith(".") or cur.is_symlink():
                        return True
                return not kb.inside(cur, ROOT) or "/".join(parts) in SKIP[0]  # a seal-only file not shown (binary, oversized)
            except (ValueError, OSError):  # a NUL byte, a name too long: no such file
                return True

        def send_head(self):
            if self.command == "HEAD":
                scan()  # SKIP is rebuilt by a scan: a HEAD that comes first must not see it empty
            if self.blocked(self.path):
                return self.send_error(404)
            return super().send_head()

        def list_directory(self, path):
            """A listing without dotfiles or links (the stock one shows both)."""
            if self.blocked(self.path):
                return self.send_error(404)
            names = sorted((n for n in os.listdir(path) if not n.startswith(".") and not (Path(path) / n).is_symlink()), key=str.lower)
            li = "".join(f'<li><a href="{esc(uq(n))}{"/" if (Path(path) / n).is_dir() else ""}">{esc(n)}{"/" if (Path(path) / n).is_dir() else ""}</a>' for n in names)
            data = f"<!doctype html><meta charset=utf-8><title>{esc(self.path)}</title><h1>{esc(urllib.parse.unquote(self.path))}</h1><ul>{li}</ul>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return io.BytesIO(data)

        def guard(self, form=None):
            ok = self.headers.get("Host") in HOSTS
            o = self.headers.get("Origin")
            if form is not None:
                ok = ok and (o is None or o.removeprefix("http://") in HOSTS) and secrets.compare_digest(form.get("_t", [""])[0], TOKEN)
            return ok

        def fail(self, e, docs=None, code=400):
            self.send_bytes(page("Error", nav(docs if docs is not None else scan(), ""), err_box(e)), code=code)

        def admin(self, path, qs, docs, form=None):
            """The pages that act: GET shows a form or a result, POST (token checked) changes something."""
            one = lambda k: (qs.get(k) or (form or {}).get(k) or [""])[0]
            left = nav(docs, "")
            if path.startswith("/_tool/"):
                name = path[7:]
                if name not in FORMS:
                    raise ValueError(f"no form for {name!r} here | fix: it is a command-line tool: bowerbird-mcp help {name}")
                if form is not None:
                    return self.send_bytes(page(name, left, run_tool(name, form)))
                return self.send_bytes(page(name, left, f"<h1>{name}</h1><p>{esc(' '.join((kb.REG[name].__doc__ or '').split()))}</p>" + tool_form(name, {k: v[0] for k, v in qs.items()})))
            if path == "/_lint":
                return self.send_bytes(page("Lint", left, lint_body(one("f"))))
            if path == "/_tags":
                return self.send_bytes(page("Tags", left, tags_body(old=one("old"))))
            if path == "/_retag":
                old, new = one("old").strip(), one("new").strip()
                if not old:
                    raise ValueError("which tag? | fix: name the tag to rename")
                applied = "_apply" in (form or {})
                outs = retag(old, new, applied)
                if not outs:
                    return self.send_bytes(page("Tags", left, tags_body(f"<p>No page carries the tag {esc(old)}.</p>")))
                body = f"<h1>Rename tag {esc(old)} to {esc(new or '(nothing)')}{' (applied)' if applied else ''}</h1><p>{len(outs)} page(s).</p>" + (
                    "".join(show(o) for o in outs) if not applied else "")
                if not applied:
                    body += post("/_retag", hidden({"old": old, "new": new}) + "<input type=hidden name=_apply value=1>", "Confirm: apply this", True)
                return self.send_bytes(page("Tags", left, body))
            if path == "/_edit":
                return self.send_bytes(page("Edit", left, edit_body(one("f"))))
            if path == "/_editlint":
                key = one("file")
                text = one("text").replace("\r\n", "\n")
                try:
                    msg = lint_text(key, text)
                except ValueError as e:
                    msg = err_box(e)
                return self.send_bytes(page("Edit", left, edit_body(key, text, msg)))
            if path == "/_save":
                key = one("file")
                p = editable(key)
                text = one("text").replace("\r\n", "\n")
                text = text if text.endswith("\n") or not text else text + "\n"
                with LOCK:
                    cur = kb.read(p) if p.exists() else None
                    if sha(cur) != one("base"):
                        return self.send_bytes(page("Edit", left, edit_body(key, text, err_box("this page changed since you opened it | fix: copy your text, reload, and edit again; nothing was saved"))), code=409)
                    kb.commit(kb.enclosing(p.parent), {p: text}, True)
                return go(self, href(key))
            if path == "/_new":
                d = one("dir").strip().strip("/")
                lf = nav(docs, d + "/" if d else "")
                if form is None:
                    return self.send_bytes(page("New", lf, new_body(d)))
                name, text = one("name").strip().lstrip("/"), one("text").replace("\r\n", "\n")
                if not name:
                    return self.send_bytes(page("New", lf, new_body(d, name, text, err_box("name it | fix: type a file name, or a name ending in / for a folder"))), code=400)
                key = f"{d}/{name}" if d else name
                if name.endswith("/"):  # shortcut: a trailing / makes a folder, instead of a second form
                    p = (ROOT / key).resolve()
                    if not kb.inside(p, ROOT) or any(x.startswith(".") for x in p.relative_to(ROOT).parts):
                        raise ValueError(f"{key!r} is not a folder here | fix: a relative path inside the collection, not starting with .")
                    p.mkdir(parents=True, exist_ok=True)  # git keeps a folder once it holds a file
                    return go(self, f"/_new?dir={uq(key.rstrip('/'))}")
                key = key if key.endswith(".md") else key + ".md"
                p = editable(key)
                if p.exists():
                    return self.send_bytes(page("New", lf, new_body(d, name, text, err_box(f"{key} already exists | fix: pick another name, or edit it from the tree"))), code=409)
                with LOCK:
                    kb.commit(kb.enclosing(p.parent), {p: text if text.endswith("\n") or not text else text + "\n"}, True)
                return go(self, href(key))
            if path == "/_delete":
                key = one("f")
                p = editable(key)
                if not p.is_file():
                    raise ValueError(f"{key} is not a page")
                back = backlinks(docs, key)
                if form is None:
                    tf, tb = tfile(key)
                    lst = "<ul>" + "".join(f'<li><a href="{href(x)}">{esc(x)}</a>' for x in back) + "</ul>"
                    body = (f"<h1>Delete {esc(key)}</h1>" + (f'<p>Refused while these pages link to it. Fix or move them first, or <a href="/_tool/archive?file={uq(tf)}&bundle={uq(tb)}">archive it</a>.</p>{lst}'
                            if back else "<p>This removes the file (git is your undo) and its seal entry.</p>" + post("/_delete", hidden({"f": key}), "Delete", True)))
                    return self.send_bytes(page("Delete", left, body))
                if back:
                    raise ValueError(f"{len(back)} page(s) link to {key} | fix: unlink them first, or archive it")
                with LOCK:
                    changes = {p: None}
                    led = kb.ledger_read(kb.KB_ROOT / kb.LEDGER)
                    if led.pop(os.path.relpath(p, kb.KB_ROOT), None) is not None:
                        changes[kb.KB_ROOT / kb.LEDGER] = kb.ledger_text(led)
                    kb.commit(kb.enclosing(p.parent), changes, True)
                return go(self, "/")
            if path == "/_stop":
                if form is None:
                    raise ValueError("stop is a button, not a link")
                self.send_bytes(b"<!doctype html><meta charset=utf-8><title>stopped</title><p>The bowerbird server is stopped. Close this tab. Restart it with <code>bowerbird-mcp serve</code>.")
                return threading.Thread(target=srv.shutdown, daemon=True).start()  # from another thread: serve_forever waits on this one
            if path == "/_seal":
                if form is None:
                    raise ValueError("seal is a button on a page")
                do_seal(form)
                return go(self, href(one("file")))
            if path == "/_settags":
                key = one("file")
                f, b = tfile(key)
                call("set", fields={"tags": [t.strip() for t in one("tags").split(",") if t.strip()]}, file=f, bundle=b, apply=True)
                return go(self, href(key))
            raise ValueError(f"no page {path} | fix: see Tools")

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            if n > 8_000_000:
                return self.send_bytes(b"too large", "text/plain", 413)
            form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"), keep_blank_values=True)
            if not self.guard(form):
                return self.send_bytes(b"forbidden", "text/plain", 403)
            try:
                return self.admin(urllib.parse.unquote(u.path), {}, scan(), form)
            except (ValueError, TypeError, KeyError, OSError) as e:
                return self.fail(e)

        def do_GET(self):
            if not self.guard():
                return self.send_bytes(b"forbidden", "text/plain", 403)
            u = urllib.parse.urlparse(self.path)
            if u.path == "/_logo.svg":
                svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -173.5 1213 1213"><style>path{{fill:#1e2a4a}}@media(prefers-color-scheme:dark){{path{{fill:#e8ecf5}}}}</style>{PATHS}</svg>')
                return self.send_bytes(svg.encode(), "image/svg+xml")
            qs = urllib.parse.parse_qs(u.query)
            q, mode = qs.get("q", [""])[0].strip(), qs.get("mode", ["passages"])[0]
            if u.path == "/_search.json":
                hits, err = ask(q, mode) if q else ([], "")
                out = [{"error": esc(err)}] if err else [
                    {"href": href(h["path"]), "title": esc(h["title"]), "sub": esc(f'{h["path"]}:{h["line"]} · {h["extra"]}')} for h in hits[:8]]
                return self.send_bytes(json.dumps(out).encode(), "application/json")
            docs = scan()
            if u.path == "/_search":
                hits, err = ask(q, mode) if q else ([], "")
                items = "".join(
                    f'<div class=hit><a href="{href(h["path"])}">{esc(h["title"])}</a> <small>{esc(h["path"])}:{h["line"]} · {esc(h["heading"])}{" · " if h["heading"] else ""}{esc(h["extra"])}</small>'
                    f'<br><small>{esc(h["text"][:300])}</small></div>' for h in hits)
                none = f"<p>{esc(err)}</p>" if err else "<p>Nothing in the collection (gap).</p>"
                tabs = '<div class=bar>' + "".join(f'<a href="/_search?mode={m}&q={uq(q)}"{" class=cur" if m == mode else ""}>{m}</a>' for m, _ in modes()) + "</div>"
                return self.send_bytes(page("Search", nav(docs, ""), f"<h1>Search: {esc(q)}</h1>{tabs}" + (items or none)))
            if u.path.startswith("/_"):
                try:
                    return self.admin(urllib.parse.unquote(u.path), urllib.parse.parse_qs(u.query), docs)
                except (ValueError, TypeError, KeyError, OSError) as e:
                    return self.fail(e, docs)
            if self.blocked(u.path):
                return self.send_error(404)
            rel = urllib.parse.unquote(u.path).strip("/")
            p = (ROOT / rel).resolve()
            if p.is_dir() and (p / "index.md").exists():
                rel = (p / "index.md").relative_to(ROOT).as_posix()
            elif not rel and "index.md" in docs:
                rel = "index.md"
            if rel in SKIP[0]:
                return self.send_error(404)
            if rel in docs and docs[rel].get("code"):
                d = docs[rel]
                head = f'<div class=meta>{badge(d)}<br><small>{esc(rel)}</small></div>'
                made = d["state"] == "derived"  # built from the code: nothing for a person to seal
                bar = "" if made else ('<div class=bar><details class=menu><summary title="seal" aria-label="more">⚙</summary><div>'
                                       '<button onclick="document.getElementById(\'seal\').showModal()">Seal…</button></div></details></div>')
                return self.send_bytes(page(rel, nav(docs, rel), head + code_html(rel, d["text"]) + ("" if made else seal_dialog(rel)), bar, rel))
            if rel in docs:
                d = docs[rel]
                md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"toc_depth": "2-3"}})
                htm = md.convert(d["body"])
                out, back = [], []
                for src, o in docs.items():
                    if src != rel and src not in back and any(resolve(src, link) == rel for link in LINK.findall(o["body"])):
                        back.append(src)
                for link in LINK.findall(d["body"]):
                    t = resolve(rel, link)
                    if t is not None and t not in out:
                        out.append(t)

                def fix(m):  # mark links to missing files
                    t = resolve(rel, m.group(1))
                    return m.group(0) if t is None or t in docs or (ROOT / t).exists() else m.group(0).replace("<a ", '<a class="broken" ', 1)
                htm = re.sub(r'<a href="([^"#]+)[^"]*"', fix, htm)
                meta = d["meta"]
                head = (f'<div class=meta>{badge(d)}<span class=b>{esc(str(meta.get("type", "")))}</span><span class=b>{esc(str(meta.get("status", "")))}</span>'
                        f'<br>{esc(str(meta.get("description", "")))}<br><small>{esc(rel)}</small></div>')
                lst = lambda xs: ("<ul>" + "".join(
                    f'<li><a href="{href(x)}" class="{"" if x in docs or (ROOT / x).exists() else "broken"}">{esc(docs[x]["title"][:40] if x in docs else x)}</a></li>' for x in xs) + "</ul>") if xs else "<small>none</small>"
                right = f'<h4>On this page</h4>{md.toc}<h4>Linked from ({len(back)})</h4>{lst(back)}<h4>Links to ({len(out)})</h4>{lst(out)}'
                tf, tb = tfile(rel)
                made = d["state"] == "derived"  # built from the code: nothing for a person to seal
                bar = (f'<div class=bar><a href="/_edit?f={uq(rel)}" title="edit" aria-label="edit">✎</a>'
                       f'<details class=menu><summary title="move, delete, seal" aria-label="more">⚙</summary><div>'
                       f'<a href="/_tool/move?file={uq(tf)}&bundle={uq(tb)}">Move</a><a href="/_delete?f={uq(rel)}">Delete</a>'
                       + ("" if made else '<button onclick="document.getElementById(\'seal\').showModal()">Seal…</button>') + '</div></details></div>')
                tags = (post("/_settags", hidden({"file": rel}) + f'<label>tags <small>(comma separated)</small><input name=tags value="{esc(", ".join(map(str, meta.get("tags") or [])) if isinstance(meta.get("tags"), list) else "")}"></label>', "Set tags")
                        if d["fm"] else "")  # any page with frontmatter can carry tags, whatever its format
                return self.send_bytes(page(d["title"], nav(docs, rel), head + htm + ("" if made else seal_dialog(rel)) + tags, bar + right, rel))
            if not rel:  # no root index.md: the shell, with nothing in the reading or details panes
                return self.send_bytes(page(ROOT.name, nav(docs, ""), "<p><small>Pick a file from the tree, or search.</small></p>"))
            super().do_GET()

        def log_message(self, *a):
            pass

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), H)  # bound here so a busy port fails in front of the user
    except OSError as e:
        print(f"error: port {port}: {e.strerror} | fix: bowerbird serve stop {port}, or pick another port")
        return 1
    url = f"http://127.0.0.1:{port}/"
    if foreground or not hasattr(os, "fork"):  # shortcut: no fork on Windows, so it stays in the foreground there
        print(f"{url}  (serving {ROOT}; ctrl-c stops)")
        pf = pidfile(port)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(str(os.getpid()))  # so `serve status`, `serve stop` and the Stop button see it too
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            pf.unlink(missing_ok=True)
        return 0
    if os.fork():
        print(f"{url}  (serving {ROOT} in the background; `bowerbird serve stop{'' if port == PORT else f' {port}'}` ends it)")
        return 0
    os.setsid()
    if os.fork():
        os._exit(0)
    pf = pidfile(port)
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(os.getpid()))
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    srv.serve_forever()  # returns when the Stop button shuts it down
    pf.unlink(missing_ok=True)
    return 0
