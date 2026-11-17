"""bowerbird serve: browse the collection in a browser (localhost only, rereads files on every request).

Search is bowerbird's own `passages` (BM25 ranked sections, semantic too when kbmcp.yaml turns it on). Seal state comes
from bowerbird's own hash and ledger, so a page reads sealed, stale or unsealed exactly as `seal check=true` would.
Read-only: it never writes a seal.

Needs `markdown` (pip install 'bowerbird[serve]').
"""
import html
import json
import os
import re
import signal
import sys
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
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui}a{color:var(--acc)}
.wrap{display:grid;grid-template-columns:17rem minmax(0,1fr) 15rem;gap:1.5rem;max-width:100rem;margin:0 auto;padding:0 1rem}
nav,aside{position:sticky;top:3rem;align-self:start;max-height:calc(100vh - 3rem);overflow:auto;padding:1rem 0;font-size:13px}
nav details{margin:.1rem 0}nav summary{cursor:pointer;font-weight:600}nav a{display:block;padding:.1rem .4rem;text-decoration:none;color:var(--fg);border-radius:4px}
nav a:hover{background:var(--line)}nav a.cur{background:var(--acc);color:#fff}nav details details{margin-left:.7rem}
main{padding:1rem 0;min-width:0}h1{margin-top:.2rem}table{border-collapse:collapse;display:block;overflow:auto}
td,th{border:1px solid var(--line);padding:.25rem .5rem;vertical-align:top}code,pre{background:var(--line);border-radius:3px}code{padding:0 .2rem}pre{padding:.6rem;overflow:auto}pre code{background:none}
.meta{color:var(--mut);font-size:13px;border:1px solid var(--line);border-radius:6px;padding:.4rem .7rem;margin-bottom:1rem}
.b{display:inline-block;padding:0 .4rem;border-radius:9px;border:1px solid currentColor;font-size:12px;margin-right:.3rem}
.sealed{color:var(--ok)}.broken-seal{color:var(--bad)}.unsealed{color:var(--warn)}a.broken{color:var(--bad);text-decoration:line-through}
aside h4{margin:.8rem 0 .2rem;color:var(--mut);text-transform:uppercase;font-size:11px}aside ul{margin:0;padding-left:1rem}
input{width:100%;padding:.3rem;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}
#top{position:sticky;top:0;z-index:5;display:flex;gap:.5rem;align-items:center;height:3rem;padding:0 1rem;background:var(--bg);border-bottom:1px solid var(--line)}
#top a.brand{display:flex;align-items:center}.logo{height:1.35rem;width:auto;flex:none}.logo path{fill:var(--logo)}
#top button{background:none;border:1px solid var(--line);color:var(--fg);border-radius:4px;padding:.15rem .5rem;cursor:pointer}
#crumbs{color:var(--mut);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}#crumbs a{color:var(--mut)}
#sw{position:relative;width:20rem}#res{display:none;position:absolute;top:2.2rem;left:0;right:0;background:var(--bg);border:1px solid var(--line);border-radius:6px;max-height:70vh;overflow:auto;box-shadow:0 6px 20px #0004}
#res a{display:block;padding:.3rem .6rem;text-decoration:none;color:var(--fg)}#res a.sel,#res a:hover{background:var(--acc);color:#fff}#res small{color:inherit;opacity:.7}
.dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;margin-right:.35rem;background:var(--warn)}.dot.sealed{background:var(--ok)}.dot.broken-seal{background:var(--bad)}
aside li.act>a{font-weight:700}kbd{border:1px solid var(--line);border-radius:3px;padding:0 .3rem;font-size:12px}.dot.none{background:var(--line)}
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
const show=items=>{res.innerHTML=items.map(r=>r.error?`<a>${r.error}</a>`:`<a href="${r.href}"><b>${r.title}</b><br><small>${r.where} · ${r.tier} · ${r.match}%</small></a>`).join('')||'<a>nothing in the collection</a>';res.style.display='block';sel=-1;};
q.oninput=()=>{clearTimeout(tm);const v=q.value.trim();if(!v){res.style.display='none';return}tm=setTimeout(()=>fetch('/_search.json?q='+encodeURIComponent(v)).then(r=>r.json()).then(show),200)};
q.onkeydown=e=>{const a=$$('a[href]',res);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();sel=(sel+(e.key==='ArrowDown'?1:-1)+a.length)%a.length;a.forEach((x,i)=>x.classList.toggle('sel',i===sel))}
 else if(e.key==='Enter'){e.preventDefault();location=sel>=0?a[sel].href:'/_search?q='+encodeURIComponent(q.value)}else if(e.key==='Escape'){res.style.display='none';q.blur()}};
document.addEventListener('click',e=>{if(!e.target.closest('#sw'))res.style.display='none'});
const links=$$('nav a[data-seal]'), cur=links.findIndex(a=>a.classList.contains('cur'));
const jump=(d,unsealed)=>{for(let i=1;i<=links.length;i++){const a=links[(cur+d*i+links.length*2)%links.length];if(!unsealed||a.dataset.seal!=='sealed'){location=a.href;return}}};
document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea')||e.metaKey||e.ctrlKey||e.altKey)return;
 if(e.key==='/'){e.preventDefault();q.focus()}else if(e.key==='t')$('#theme').click();else if(e.key==='n')jump(1,true);else if(e.key==='p')jump(-1,true);else if(e.key==='j')jump(1,false);else if(e.key==='k')jump(-1,false);else if(e.key==='['){history.back()}else if(e.key===']'){history.forward()}});
const heads=$$('main h2[id],main h3[id]'), tl=new Map($$('aside a[href^="#"]').map(a=>[a.getAttribute('href').slice(1),a]));
if(heads.length&&'IntersectionObserver' in window){const io=new IntersectionObserver(es=>es.forEach(en=>{if(en.isIntersecting){$$('aside .act').forEach(x=>x.classList.remove('act'));const a=tl.get(en.target.id);if(a)a.parentElement.classList.add('act')}}),{rootMargin:'-10% 0px -80% 0px'});heads.forEach(h=>io.observe(h))}
const c=$('nav a.cur'); if(c)c.scrollIntoView({block:'center'});
})();
"""


def pidfile(port: int) -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "bowerbird-mcp" / f"serve-{port}.pid"


def stop(port: int = PORT) -> int:
    """Stop the background server on port."""
    f = pidfile(port)
    try:
        os.kill(int(f.read_text()), signal.SIGTERM)
    except (OSError, ValueError):
        print(f"nothing running on port {port}")
        f.unlink(missing_ok=True)
        return 1
    f.unlink(missing_ok=True)
    print(f"stopped the server on port {port}")
    return 0


def run(kb, port: int = PORT, foreground: bool = False) -> int:
    """Serve the collection kb (the bowerbird_mcp module) on localhost:port, in the background unless foreground."""
    try:
        import markdown
    except ImportError:
        print("error: serve needs the markdown package | fix: pip install 'bowerbird[serve]' (or uvx --from 'bowerbird[serve]' bowerbird serve)")
        return 2
    ROOT = kb.KB_ROOT
    href = lambda rel: "/" + urllib.parse.quote(rel)
    esc = html.escape

    def scan():
        """rel path -> {title, meta, body, state, by, at}, with seals checked by bowerbird's own hash and ledger."""
        try:
            ledger = kb.ledger_by_file()
        except ValueError:
            ledger = {}
        docs = {}
        for p in sorted(ROOT.rglob("*.md")):
            rel = p.relative_to(ROOT)
            if any(part.startswith(".") for part in rel.parts):
                continue
            key, text = rel.as_posix(), kb.read(p)
            if text is None:
                continue
            d = kb.meta(text)[0] or {}
            es, valid = kb.reviews(d, key, text, ledger)
            last = (valid or es or [{}])[-1]
            docs[key] = {"title": kb.title_of(d, text, p), "meta": d, "body": kb.split(text)[1],
                         "state": "unsealed" if not es else "sealed" if valid else "broken-seal",
                         "by": last.get("by", ""), "at": last.get("at", "")}
        return docs

    def resolve(src, url):
        if re.match(r"[a-z]+:", url):
            return None
        base = ROOT if url.startswith("/") else (ROOT / src).parent
        try:
            return (base / urllib.parse.unquote(url).lstrip("/")).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return None

    def badge(d):
        word = {"sealed": "sealed", "broken-seal": "seal broken by edit", "unsealed": "unsealed"}[d["state"]]
        who = f" {esc(str(d['by']))} {esc(str(d['at']))}" if d["by"] else ""
        return f'<span class="b {d["state"]}">{word}</span>{who}'

    def nav(docs, cur):
        """The whole directory under the collection's root folder."""
        tree = {}
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            if p.is_dir() or any(x.startswith(".") for x in rel.parts) or rel.parts[-1] == ".DS_Store":
                continue
            node = tree
            for part in rel.parts[:-1]:
                node = node.setdefault(part + "/", {})
            node[rel.parts[-1]] = rel.as_posix()

        def walk(node):
            out = []
            for k in sorted(node, key=lambda k: (not k.endswith("/"), k.lower())):
                v = node[k]
                if isinstance(v, dict):
                    out.append(f"<details open><summary>{esc(k)}</summary>{walk(v)}</details>")
                elif v in docs:
                    st = docs[v]["state"]
                    out.append(f'<a href="{href(v)}" data-seal="{st}" title="{esc(docs[v]["title"])}" class="{"cur" if v == cur else ""}"><span class="dot {st}"></span>{esc(k)}</a>')
                else:
                    out.append(f'<a href="{href(v)}"><span class="dot none"></span>{esc(k)}</a>')
            return "".join(out)
        return f"<details open><summary>{esc(ROOT.name)}/</summary>{walk(tree)}</details>"

    def page(title, left, body, right="", rel=""):
        parts = rel.split("/") if rel else []
        crumbs = [f'<a href="/">{esc(ROOT.name)}</a>'] + [
            f'<a href="{href("/".join(parts[:i + 1]))}">{esc(x)}</a>' if i < len(parts) - 1 and (ROOT / "/".join(parts[:i + 1]) / "index.md").exists() else esc(x)
            for i, x in enumerate(parts)]
        top = (f'<div id=top><a class=brand href="/" title="bowerbird">{LOGO}</a><button id=back title="back ([)">◀</button><button id=fwd title="forward (])">▶</button>'
               f'<span id=crumbs>{" / ".join(crumbs)}</span><div id=sw><input id=q placeholder="search ( / )" autocomplete=off><div id=res></div></div><button id=theme title="theme (t)">◐</button></div>')
        hint = '<h4>Keys</h4><small><kbd>/</kbd> search <kbd>n</kbd>/<kbd>p</kbd> next/prev unsealed<br><kbd>j</kbd>/<kbd>k</kbd> next/prev doc <kbd>t</kbd> theme <kbd>[</kbd><kbd>]</kbd> history</small>'
        return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>{esc(title)} · bowerbird</title>"
                f"<link rel=icon type=image/svg+xml href=/_logo.svg><script>try{{var t=localStorage.getItem('kbtheme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}}catch(e){{}}</script>"
                f"<style>{CSS}</style>{top}<div class=wrap><nav>{left}</nav><main>{body}</main><aside>{right}{hint}</aside></div><script>{JS}</script>").encode()

    def ask(q):
        """bowerbird's passages for q: (hits, error). Ranked, and semantic when kbmcp.yaml has it on."""
        try:
            r = kb.REG["passages"](q, limit=12)
        except (ValueError, KeyError, OSError) as e:
            return [], str(e).split(" | ")[0]
        for h in r["hits"]:
            h["path"] = h["file"] if h["bundle"] in (".", "") else f'{h["bundle"]}/{h["file"]}'
        return r["hits"], ""

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

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/_logo.svg":
                svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}"><style>path{{fill:#1e2a4a}}@media(prefers-color-scheme:dark){{path{{fill:#e8ecf5}}}}</style>{PATHS}</svg>')
                return self.send_bytes(svg.encode(), "image/svg+xml")
            q = urllib.parse.parse_qs(u.query).get("q", [""])[0].strip()
            if u.path == "/_search.json":
                hits, err = ask(q) if q else ([], "")
                out = [{"error": esc(err)}] if err else [
                    {"href": href(h["path"]), "title": esc(h["title"]), "where": esc(f'{h["path"]}:{h["line"]}'), "tier": esc(str(h["tier"])), "match": h["match"]} for h in hits[:8]]
                return self.send_bytes(json.dumps(out).encode(), "application/json")
            docs = scan()
            if u.path == "/_search":
                hits, err = ask(q) if q else ([], "")
                items = "".join(
                    f'<div class=hit><a href="{href(h["path"])}">{esc(h["title"])}</a> <small>{esc(h["path"])}:{h["line"]} · {esc(h["heading"] or "")} · {esc(str(h["tier"]))}{" · stale" if h["stale"] else ""} · {h["match"]}%</small>'
                    f'<br><small>{esc(h["text"][:300])}</small></div>' for h in hits)
                none = f"<p>{esc(err)}</p>" if err else "<p>Nothing in the collection (gap).</p>"
                return self.send_bytes(page("Search", nav(docs, ""), f"<h1>Search: {esc(q)}</h1>" + (items or none)))
            rel = urllib.parse.unquote(u.path).strip("/")
            p = (ROOT / rel).resolve()
            if p.is_dir() and (p / "index.md").exists():
                rel = (p / "index.md").relative_to(ROOT).as_posix()
            elif not rel and "index.md" in docs:
                rel = "index.md"
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
                return self.send_bytes(page(d["title"], nav(docs, rel), head + htm, right, rel))
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
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
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
    srv.serve_forever()
    return 0
