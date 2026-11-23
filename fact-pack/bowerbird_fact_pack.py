"""bowerbird-mcp[fact-pack]: more kinds of fact, beyond the url, mcp, file and internal that bowerbird-mcp has.

    [fact.key](pyproject.toml project.version) is 2.3.0 [fact.end]     a value at a path in a JSON, YAML or TOML file
    [fact.git](tag v2.3.0) the release is tagged [fact.end]            a tag, or a file at a revision, in the document's repository
    [fact.until](2026-12-31) the freeze is on [fact.end]               a claim with an end date
    [fact.manual](ops standup) the rota moved to Tuesdays [fact.end]   what only a person can say: asked at a terminal
    [fact.script](uvver) uv 0.5 [fact.end]                             a command's output; the command is declared in the root bower.yaml

Registered through the `bowerbird.fact_types` entry point: bowerbird-mcp calls `register(bb)` with its own module.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def register(bb):
    F = bb.facts_mod()

    def where(token: str, doc: Path) -> Path:
        path = Path(os.path.expanduser(token))
        return path if path.is_absolute() else doc.parent / path

    def compare(old, value) -> tuple:
        """The same rule as an MCP fact: the first check records the value, later ones must match it (editing the claim makes a new fact)."""
        if old is None:
            return "checked", "baseline recorded", value
        if old == value:
            return "checked", "same value", value
        return "drifted", f"was {old!r}, now {value!r}", old

    def cfg(key):
        return (bb.CFG.get("facts") or {}).get(key)

    # ---- key: a value in a structured file
    def valid_key(s):
        return None if len(s.split()) == 2 else "needs a file and a key path: `pyproject.toml project.version`"

    def load(path: Path):
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        if suffix == ".json":
            return json.loads(text)
        if suffix in (".yaml", ".yml"):
            import yaml
            return yaml.safe_load(text)
        if suffix == ".toml":
            try:
                import tomllib
            except ModuleNotFoundError:
                try:
                    import tomli as tomllib
                except ModuleNotFoundError:
                    raise ValueError("reading .toml needs Python 3.11, or `pip install tomli`") from None
            return tomllib.loads(text)
        raise ValueError(f"{path.name}: key reads .json, .yaml and .toml files")

    def check_key(p, b, old, declared):
        token, key = b.source.split()
        path = where(token, p)
        if not path.is_file():
            return "drifted", f"{path} is not there", old
        try:
            value = F.dotted(load(path), key)
        except (KeyError, IndexError, ValueError, TypeError):
            return "drifted", f"{path.name} has nothing at {key!r}", old
        return compare(old, value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False))

    # ---- git: a tag, or a file at a revision
    def valid_git(s):
        t = s.split()
        if not t or t[0] not in ("tag", "file") or len(t) != (2 if t[0] == "tag" else 3):
            return "needs `tag NAME` or `file REVISION PATH`"
        return "a name cannot start with -" if any(x.startswith("-") for x in t[1:]) else None

    def git_ref(p, b) -> list:
        t = b.source.split()
        return [f"refs/tags/{t[1]}^{{commit}}"] if t[0] == "tag" else [f"{t[1]}:{t[2]}"]

    def check_git(p, b, old, declared):
        r = subprocess.run(["git", "-C", str(p.parent), "rev-parse", "--verify", "-q", *git_ref(p, b)], capture_output=True, text=True, check=False)
        if r.returncode == 1 and not r.stderr.strip():
            return "drifted", f"{b.source} is not in the repository", old
        if r.returncode:
            raise ValueError(r.stderr.strip()[:160] or f"git exited {r.returncode}")
        return compare(old, r.stdout.strip())

    # ---- until: an end date
    def valid_until(s):
        try:
            dt.date.fromisoformat(s)
        except ValueError:
            return "needs a date like 2026-12-31"
        return None

    def check_until(p, b, old, declared):
        end = dt.date.fromisoformat(b.source)
        return ("checked", f"holds until {end}", old) if dt.date.today() <= end else ("drifted", f"ended {end}", old)

    # ---- manual: a person says so
    def check_manual(p, b, old, declared):
        days = cfg("manual_days")
        last = F.read_state(p.parent).get((p.name, b.id), {})
        at = bb.when(str(last.get("at") or ""))
        if days and last.get("status") == "checked" and at and bb.now_dt() - at < dt.timedelta(days=days):
            return "skipped", f"confirmed {last['at']}; due after {days} days", old
        if not bb.at_terminal():
            raise ValueError("a manual fact is confirmed by a person at a terminal")
        print(f"\n  {b.source}\n  {b.claim}", file=sys.stderr)
        who = bb.user_id()
        if input("Still true? [y/N] ").strip().lower() == "y":
            return "checked", f"confirmed by {who}", old
        return "drifted", f"{who} says it no longer holds", old

    # ---- script: a command declared in the root bower.yaml
    def valid_script(s):
        t = s.split()
        if len(t) not in (1, 2) or not re.fullmatch(r"[A-Za-z0-9_-]+", t[0]):
            return "needs the name of a script, then optionally one key"
        return "a key cannot start with -" if len(t) == 2 and (t[1].startswith("-") or not re.fullmatch(r"[\w./:@=+-]+", t[1])) else None

    def argv_of(b):
        name, _, key = b.source.partition(" ")
        spec = (cfg("scripts") or {}).get(name)
        return name, (None if spec is None else [a.replace("{key}", key.strip()) for a in spec["cmd"]]), spec

    def plan_script(b, declared, p=None):
        name, argv, _ = argv_of(b)
        return f"run {argv}" if argv else f"skip {b.source}: {name!r} is not declared under facts.scripts in bower.yaml"

    def check_script(p, b, old, declared):
        name, argv, spec = argv_of(b)
        if argv is None:
            return "skipped", f"{name!r} is not declared under facts.scripts in bower.yaml", old
        r = subprocess.run(argv, capture_output=True, text=True, timeout=spec.get("timeout", 30), cwd=bb.ROOT, check=False)  # an argument list: no shell
        if r.returncode:
            return "skipped", f"{argv[0]} exited {r.returncode}: {r.stderr.strip()[:120]}", old
        return compare(old, r.stdout.strip())

    for name, sample, valid, plan, check, local in (
        ("key", "pyproject.toml project.version", valid_key, lambda b, d, p=None: f"read {b.source.split()[0]} at {b.source.split()[1]}", check_key, True),
        ("git", "tag v2.3.0", valid_git, lambda b, d, p=None: f"git rev-parse {' '.join(git_ref(p, b))}", check_git, True),
        ("until", "2026-12-31", valid_until, lambda b, d, p=None: f"compare today with {b.source}", check_until, True),
        ("manual", "ops standup", lambda s: None if s.strip() else "needs who or where it came from", lambda b, d, p=None: "ask you: still true?", check_manual, False),
        ("script", "uvver", valid_script, plan_script, check_script, False),
    ):
        F.register(name, sample, valid, plan, check, local)
