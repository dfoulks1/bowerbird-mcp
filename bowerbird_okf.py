"""okf: move an OKF concept's reviews and sources between its own frontmatter (`verified`, `sources`) and the two files Bowerbird keeps beside
documents (`.waxseals.yaml`, `.facts.yaml`).

    bowerbird-mcp okf export [path] [--apply]    frontmatter to the files: the reviews that still hold, and the facts' last checks
    bowerbird-mcp okf import [path] [--apply]    the files to frontmatter: every review (a stale one stays stale), and the facts' checks

A person's command, at a terminal, never a tool: it moves people's reviews. It previews until --apply. An import that changes a concept's
bytes (it adds `sources`) ends the reviews that bound the old bytes; a new seal is what verifies that the history loaded properly.
Like `serve`, it takes the core module as an argument, so this file imports nothing from it.
"""
import os
import sys
from pathlib import Path

import bowerbird_facts as F

HELP = __doc__.split("\n\n")[0].replace("okf: ", "", 1) + "\n\nA person's command (a terminal): it moves reviews. It previews until --apply."


def iso(x) -> str:
    """A timestamp as the ledgers write it (YAML may hand back a datetime)."""
    return x.isoformat().replace("+00:00", "Z") if hasattr(x, "isoformat") else str(x)


def concepts(bb, arg: str) -> list:
    """The OKF concept files under arg (a folder or a file; the collection by default)."""
    base = Path(arg).expanduser().resolve() if arg else bb.ROOT
    paths = bb.walk(base, "*.md") if base.is_dir() else [base]
    return [p for p in paths if bb.inside(p, bb.ROOT) and bb.fmt_of(p) == "okf" and p.name not in bb.RESERVED]


def export_(bb, arg: str, apply: bool) -> list:
    """Frontmatter to the files. A review that still holds goes into .waxseals.yaml (rebound to the file as it is, so it holds there too; a stale
    one stays behind), and each source's last check into .facts.yaml, unless the file already has a newer word on it. Reads the documents only."""
    led, lines, upd = bb.ledger_view(), [], {}
    for p in concepts(bb, arg):
        text = bb.read(p)
        d, err = bb.meta(text)
        if err or not d:
            continue
        rel, okf_h, full_h = os.path.relpath(p, bb.ROOT), bb.content_hash(text, True), bb.content_hash(text, False)
        ver = [e for e in bb.entries(d.get("verified")) if isinstance(e, dict) and e.get("by")]
        valid = [e for e in ver if not e.get("sha256") or e["sha256"] == okf_h]
        have = led.get(rel, [])
        seen = {(str(e["by"]), iso(e.get("at"))) for e in have}
        new = [{"file": rel, "sha256": full_h, "by": e["by"], "at": iso(e.get("at")), **{k: e[k] for k in ("bowerbird", "comment") if e.get(k)}}
               for e in valid if (str(e["by"]), iso(e.get("at"))) not in seen]
        kept = sorted(have + new, key=lambda e: str(e.get("at")))
        if not bb.seal_ext(p)[0]:
            kept = kept[-1:]  # without seal.extensions the ledger keeps one latest review per file
        parts = []
        if kept != have:
            led[rel] = upd[rel] = kept
            parts.append(f"{len(new)} review(s) to {bb.LEDGER}" + (f" ({len(have) + len(new) - len(kept)} left out: seal.extensions is off)" if len(have) + len(new) > len(kept) else ""))
        state = F.read_state(p.parent)
        for e in d.get("sources") if isinstance(d.get("sources"), list) else []:
            if not (isinstance(e, dict) and e.get("id") and (e.get("retrieved_at") or e.get("fact_sha256"))) or (p.name, str(e["id"])) in state:
                continue
            parts.append(f"source {e['id']} to {F.STATE}")
            if apply:
                F.record(p.parent, p.name, str(e["id"]), "source", str(e.get("resource", "")), "checked", "exported from the frontmatter",
                         iso(e.get("retrieved_at") or bb.now()), e.get("fact_sha256"))
        if parts:
            lines.append(f"{rel}: " + "; ".join(parts) + (f"; {len(ver) - len(valid)} stale review(s) stay behind" if len(ver) > len(valid) else ""))
    if apply and upd:
        bb.ledger_apply(upd)
    return lines


def import_(bb, arg: str, apply: bool) -> list:
    """The files to frontmatter. Every review in the ledger for the concept becomes a `verified` entry (one that held keeps holding, if the
    concept's bytes do not change; a stale one stays stale), and each fact's check updates its `sources` entry, or adds one for a block fact.
    Writing `sources` changes the bytes, which ends the reviews of the old ones: the preview says how many."""
    led, lines = bb.ledger_view(), []
    for p in concepts(bb, arg):
        text = bb.read(p)
        d, err = bb.meta(text)
        if err or not d:
            continue
        rel, okf_h, full_h = os.path.relpath(p, bb.ROOT), bb.content_hash(text, True), bb.content_hash(text, False)
        have = [e for e in bb.entries(d.get("verified")) if isinstance(e, dict) and e.get("by")]
        seen = {(str(e["by"]), iso(e.get("at"))) for e in have}
        add = [{"by": e["by"], "at": iso(e.get("at")), "sha256": okf_h if e.get("sha256") in (okf_h, full_h) else e.get("sha256"),
                **({"comment": e["comment"]} if e.get("comment") else {})}
               for e in led.get(rel, []) if e.get("by") and not e.get("derived") and (str(e["by"]), iso(e.get("at"))) not in seen]
        srcs = [dict(e) if isinstance(e, dict) else e for e in (d.get("sources") if isinstance(d.get("sources"), list) else [])]
        by_id, touched = {str(e["id"]): e for e in srcs if isinstance(e, dict) and e.get("id")}, 0
        for (name, fid), st in sorted(F.read_state(p.parent).items()):
            if name != p.name:
                continue
            at = iso(st.get("at"))
            if fid in by_id:
                e = by_id[fid]
                newer = bb.when(at) and (not bb.when(e.get("retrieved_at")) or bb.when(at) > bb.when(e.get("retrieved_at")))
                if st.get("kind") == "source" and newer and iso(e.get("retrieved_at")) != at:
                    e["retrieved_at"], touched = at, touched + 1
                if st.get("kind") == "source" and st.get("value") and not e.get("fact_sha256"):
                    e["fact_sha256"], touched = st["value"], touched + 1
            elif st.get("kind") != "source":  # a block fact: the page, or the tool's server and key, as a source
                server, _, key = str(st.get("source", "")).partition(" ")
                srcs.append({"id": fid, "resource": st["source"] if st.get("kind") == "url" else f"mcp://{server}/{key}", "retrieved_at": at})
                touched += 1
        new_text = text
        if touched:
            new_text = bb.put(new_text, "sources", srcs)
        if add:
            new_text = bb.put(new_text, "verified", have + add)
        if new_text == text:
            continue
        ends = [e for e in have + add if e.get("sha256") == okf_h] if bb.content_hash(new_text, True) != okf_h else []
        lines.append(f"{rel}: +{len(add)} review(s), {touched} source(s) updated" + (f"; {len(ends)} review(s) end, since the bytes change: seal it again to verify what loaded" if ends else ""))
        if apply:
            bb.commit(bb.enclosing(p.parent), {p: new_text}, True, f"**Update**: Imported reviews and sources of [{bb.title_of(d, text, p)}](/{rel}) from the ledgers.")
    return lines


def main(bb, argv: list) -> int:
    if not bb.at_terminal():
        print("error: okf is a person's command | fix: run it at a terminal; an agent cannot move people's reviews", file=sys.stderr)
        return 2
    args = [a for a in argv if a not in ("--apply", "-A")]
    apply = len(args) != len(argv)
    if not args:
        print(HELP)
        return 0
    if args[0] not in ("export", "import") or len(args) > 2:
        print(f"error: okf {' '.join(args)} | fix: okf export|import [path] [--apply]", file=sys.stderr)
        return 2
    lines = (export_ if args[0] == "export" else import_)(bb, args[1] if len(args) > 1 else "", apply)
    print("\n".join(lines) if lines else "nothing to move")
    print("done" if apply else "preview only: --apply writes")
    return 0
