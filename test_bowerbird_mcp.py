#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.10,<2", "pyyaml", "markdown"]
# ///
"""Self-check: throwaway bundles, every tool. Run: uv run test_bowerbird_mcp.py"""
import asyncio
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from pydantic import AnyUrl

HERE = Path(__file__).resolve().parent
coll = Path(tempfile.mkdtemp()) / "kb"
coll.mkdir()
os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
(coll / "bower.yaml").write_text("")  # the config file marks the collection root
sys.argv[1:] = ["--config", str(coll / "bower.yaml")]
sys.path.insert(0, str(HERE))
import bowerbird_mcp as bb
import importlib.util as _iu0

_se = _iu0.spec_from_file_location("bowerbird_seal_extensions", HERE / "addons" / "seal-extensions" / "bowerbird_seal_extensions.py")
seal_extensions = _iu0.module_from_spec(_se)
_se.loader.exec_module(seal_extensions)
seal_extensions.register(bb)  # what the `bowerbird.seal` entry point does when the add-on is installed


def create(**kw):
    return asyncio.run(bb.create(**kw))

del sys.argv[1:]
bb.CFG_DIR = None  # the tests swap ROOT around; keep each one's index inside its own root

TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def kinds(**kw):
    return {f["kind"] for f in bb.lint(limit=0, **kw)["findings"]}


def raises(fn, *a, **kw):
    try:
        out = fn(*a, **kw)
        if asyncio.iscoroutine(out):
            asyncio.run(out)
    except ValueError as e:
        return str(e)
    raise SystemExit(f"{fn.__name__} did not refuse")


def cli(*argv):
    bb.at_terminal = lambda: True  # tests stand in for a human at a terminal
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = bb.cli(list(argv))
    bb.CLI, bb.ATTEST = False, ""
    return code, buf.getvalue()


# init: a new bundle is conformant and clean; a second init refuses.
assert create()["would_edit"] == {".": ["index.md", "log.md"]}
create(apply=True)
assert bb.lint()["ok"] and bb.lint()["conformant"], bb.lint()
raises(bb.create, apply=True)

# A bundle with only a concept lints (no index, no log, no layout).
(coll / "bare").mkdir()
(coll / "bare/a.md").write_text("---\ntype: Note\n---\nhi\n")
assert bb.lint(bundle="bare")["ok"]

# SPEC.md's own examples: conformant, no okf errors. Their /tables/... links are dead here (house).
spec = (HERE / "docs-src" / "prompts" / "SPEC.md").read_text()
blocks = re.findall(r"```markdown\n(.*?)```", spec, re.DOTALL)
(coll / "spec").mkdir()
for i, b in enumerate(x for x in blocks if x.startswith("---\n")):
    (coll / f"spec/ex{i}.md").write_text(b)
(coll / "spec/log.md").write_text(next(b for b in blocks if b.startswith("# Directory Update Log")))
assert len(list((coll / "spec").glob("ex*.md"))) >= 6
L = bb.lint(scope="okf", bundle="spec", limit=0)
assert L["ok"] and L["conformant"], L
assert "dead_link" in kinds(bundle="spec")  # §6.1: / is the bundle root, and is checked
shutil.rmtree(coll / "spec")
shutil.rmtree(coll / "bare")

# One bad fixture per check.
(coll / "bad").mkdir()


def check(text, kind, name="x.md"):
    p = coll / "bad" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text) if isinstance(text, bytes) else p.write_text(text)
    got = kinds(bundle="bad")
    p.unlink()
    assert kind in got, (kind, got)


check("no frontmatter\n", "no_frontmatter")
check("---\na: b: c\n---\n", "bad_yaml")
check("---\ntype: x\nunclosed\n", "bad_yaml")
check("---\ntitle: x\n---\n", "no_type")
check(b"---\ntype: x\n---\n\xff\n", "non_utf8")
check("---\ntype: x\ngenerated: {by: drew}\n---\n", "okf_trust")
check("---\ntype: x\nverified: {by: human:a, at: 2026-10-27}\n---\n", "okf_trust")  # no UTC offset
check("---\ntype: x\nstatus: done\n---\n", "bad_status")
check("---\ntype: x\nstale_after: soon\n---\n", "bad_stale_after")
check("---\ntype: x\nsources:\n  - id: a\n---\n", "bad_source")
check("---\ntype: x\nsources: [{id: a, resource: r}, {id: a, resource: s}]\n---\n", "bad_source")
check("---\ntype: x\nsources: [{id: a, resource: r}]\n---\nclaim[^b]\n\n[^b]: x\n", "unknown_footnote")
check("---\ntype: x\n---\n[a](/nope.md) [b](./nope.md)\n", "dead_link")
check("---\ntitle: x\n---\n# I\n", "okf_index", "sub/index.md")
check("# Log\n\n## Recent\n", "okf_log", "log.md")
check("# Log\n\n## 2026-01-01\n\n## 2026-02-01\n", "okf_log", "log.md")
check("# Log\n\n## 2026-02-01\n\n* a\n\n## 2026-02-01\n\n* b\n", "okf_log", "log.md")  # after a union merge
assert bb.tidied("# Log\n\n## 2026-01-01\n\n* <!-- 1 --> old\n\n## 2026-02-01\n\n* <!-- 5 --> x\n\n"
                "## 2026-02-01\n\n* <!-- 9 --> y\n* <!-- 5 --> x\n") == (
    "# Log\n\n## 2026-02-01\n\n* <!-- 9 --> y\n* <!-- 5 --> x\n\n## 2026-01-01\n\n* <!-- 1 --> old\n")
check("---\nokf_version: '9.9'\n---\n", "okf_version", "index.md")
check("---\ntype: x\n---\n", "odd_filename", "a b.md")
check("---\ntype: x\n---\n", "no_description")
check("---\ntype: x\n---\n", "orphan")
check("---\ntype: Attested Computation\n---\n", "bad_computation")
check("---\ntype: x\n---\n# Real\n\n[a](#nope)\n", "dead_anchor")

# Wikilinks: [[Note]] resolves by file name (shortest path first), a missing one is a dead_link, #Heading is checked like a markdown anchor.
(coll / "wk" / "sub").mkdir(parents=True)
for n, body in {"a.md": "---\ntype: x\ndescription: d\n---\n# Top\n\n## My Heading\n\n[[Note]] [[sub/Deep#My Heading|alias]] ![[img.png]] [[Note#^b1]]\n",
                "Note.md": "---\ntype: x\ndescription: d\n---\n[[a]] [[a#my heading]]\n", "sub/Deep.md": "---\ntype: x\ndescription: d\n---\n# My Heading\n\n[[a]]\n",
                "sub/Note.md": "---\ntype: x\ndescription: d\n---\n[[a]]\n"}.items():
    (coll / "wk" / n).write_text(body)
(coll / "wk" / "img.png").write_bytes(b"x")
wk = {(f["file"], f["kind"]) for f in bb.lint(bundle="wk", limit=0)["findings"]}
assert not {k for k in wk if k[1] in ("dead_link", "dead_anchor", "self_link")}, wk  # every link above resolves
assert bb.links("a.md", bundle="wk")["out"][0]["link"] == "[[Note]]"  # a wikilink is a link, so links/backlinks see it
assert bb.target("[[note]]", coll / "wk" / "a.md", coll / "wk") == coll / "wk" / "Note.md"  # the shortest path wins, case ignored
(coll / "wk" / "b.md").write_text("---\ntype: x\ndescription: d\n---\n[[Missing]] [[a#nope]]\n")
wk = {(f["file"], f["kind"]) for f in bb.lint(bundle="wk", limit=0)["findings"]}
assert ("b.md", "dead_link") in wk and ("b.md", "dead_anchor") in wk, wk
shutil.rmtree(coll / "wk")
check("---\ntype: x\ntags: [Sales, sales]\n---\n", "tag_case")
check("---\ntype: x\ncomputation: nope/x.sql\n---\n", "dead_path")
check("---\ntype: x\ngenerated: {by: human:a, at: '2026-01-01T00:00:00Z'}\n"
      "sources: [{id: s, resource: r, last_modified: '2026-02-01T00:00:00Z'}]\n---\n", "source_changed")
check("---\ntype: x\nsources: [{resource: r, last_modified: yesterday}]\n---\n", "bad_source")  # §5.1 signals
check("---\ntype: x\nsources: [{resource: r, usage_count: many}]\n---\n", "bad_source")
check("---\ntype: x\nusage_window: {from: 2026-06-01}\nsources: [{resource: r}]\n---\n", "bad_source")
check("---\ntype: x\ntags: sales\n---\n", "bad_tags")
check("---\ntype: x\n---\nkey: AKIAIOSFODNN7EXAMPLE\n", "secret")  # AWS's documented example key
check("---\ntype: x\n---\n-----BEGIN OPENSSH PRIVATE KEY-----\n", "secret")
check("---\ntype: x\n---\npostgres://app:hunter2@db/prod\n", "secret")
assert bb.secrets("tok ghp_" + "a" * 36 + "\nfine\n") == [(1, "GitHub token")]
assert not bb.secrets("see https://example.com/a and ghp_short and sk-tiny\n")
(coll / "bad/leak.md").write_text("---\ntype: x\n---\nkey: AKIAIOSFODNN7EXAMPLE\n")
L = bb.lint(bundle="bad", limit=0)
assert not L["ok"] and "AKIAIOSFODNN7EXAMPLE" not in json.dumps(L)  # named by kind and line, never the value
(coll / "bad/leak.md").unlink()
sec = Path(tempfile.mkdtemp())  # ingest leaves a file with a credential behind, and says why
(sec / "ok.md").write_text("# Fine\n")
(sec / "leak.md").write_text("# Leak\n\ntoken: glpat-" + "x" * 20 + "\n")
plan = bb.ingest(str(sec), bundle="bad")
assert plan["ingest"] == 1 and plan["secrets"]["skipped"] == 1
assert any(f["file"] == "leak.md" and "GitLab token on line 3" in f["reason"] for f in plan["skipped_files"])
for c in ("parameters: [{name: year}]", "executor: {receipt: [job_id]}", "computation: x.sql\n---\n# Computation\n"):
    check(f"---\ntype: Attested Computation\nruntime: bigquery\n{c}" + ("" if "---" in c else "\n---\n# Computation\n"),
          "bad_computation")
check("---\ntype: x\ntimestamp: '2026-01-01T00:00:00Z'\n"  # §13.1: timestamp stands in for generated.at
      "sources: [{id: s, resource: r, last_modified: '2026-02-01T00:00:00Z'}]\n---\n", "source_changed")
(coll / "bad/dep.md").write_text("---\ntype: x\nstatus: deprecated\n---\n")
check("---\ntype: x\n---\n[o](dep.md)\n", "deprecated_link")
(coll / "bad/dep.md").unlink()
(coll / "bad/y.md").write_text("---\ntype: x\n---\n# Real Thing\n\n[a](#real-thing)\n")
assert "dead_anchor" not in kinds(bundle="bad")
(coll / "bad/y.md").unlink()
assert not kinds(bundle="bad")
(coll / "bad/e.md").write_text("---\ntype: x\n---")  # closing --- at end of file, no newline
assert bb.lint(bundle="bad")["ok"] and "bad_yaml" not in kinds(bundle="bad")
(coll / "bad/e.md").unlink()
(coll / "bad/w.md").write_text("---\ntype: x\n---\n")
(coll / "bad/W.md").write_text("---\ntype: x\n---\n")
if not (coll / "bad/w.md").samefile(coll / "bad/W.md"):  # case-sensitive file system
    assert "case_collision" in kinds(bundle="bad") and bb.lint(bundle="bad")["ok"]  # warnings do not fail
for p in (coll / "bad").glob("*.md"):
    p.unlink()

# baseline: old findings stop counting, new ones still fail.
(coll / "bad/old.md").write_text("no frontmatter\n")
assert not bb.lint(bundle="bad")["ok"]
bb.baseline(apply=True, bundle="bad")
assert bb.lint(bundle="bad", baseline=".okf-baseline.json")["ok"]
(coll / "bad/new.md").write_text("no frontmatter either\n")
L = bb.lint(bundle="bad", baseline=".okf-baseline.json")
assert not L["ok"] and L["total"] == 1 and L["baselined"] == 1

# bower.nolint: gitignore-style patterns; lint skips matching files. Cascades, last match wins, ! re-includes.
(coll / "bad/drafts/deep").mkdir(parents=True)
for f in ("drafts/a.md", "drafts/deep/b.md", "drafts/keep.md", "x1.md"):
    (coll / "bad" / f).write_text("no frontmatter\n")
(coll / "bad/bower.nolint").write_text("# old stuff\nold.md\nnew.md\ndrafts/\n!drafts/keep.md\nx[0-9].md\n")
assert {f["file"] for f in bb.lint(bundle="bad", limit=0)["findings"]} == {"drafts/keep.md"}
(coll / "bad/drafts/bower.nolint").write_text("/keep.md\n")
assert bb.lint(bundle="bad")["total"] == 0 and bb.lint(bundle="bad")["ok"]
assert bb.lint(bundle="bad", file="drafts/keep.md")["total"] == 0
(coll / "bad/inline.md").write_text("no frontmatter\n<!-- bower-nolint -->\n")
(coll / "bad/quoted.md").write_text("no frontmatter, mentions `<!-- bower-nolint -->`\n")
assert {f["file"] for f in bb.lint(bundle="bad", limit=0)["findings"]} == {"quoted.md"}
assert all(bb.glob_rx(p) for p in ("**/a", "a/**", "[!x]", r"\#x"))
shutil.rmtree(coll / "bad")

# fix: strips sub-index frontmatter, rebuilds the root list, re-lints; idempotent.
(coll / "note.md").write_text("---\ntype: Note\ntitle: Note\ndescription: A note.\ncustom: {a: [1, 2]}  # mine\n---\n"
                            "\n# Note\n\nBody.\n")
(coll / "sub").mkdir()
(coll / "sub/index.md").write_text("---\ntitle: Sub\n---\n# Sub\n")
assert {"okf_index", "index_stale"} <= kinds()
assert set(bb.fix()["would_edit"]["."]) == {"index.md", "sub/index.md"}
out = bb.fix(apply=True)
assert out["remaining"]["ok"], out
assert bb.fix()["would_edit"] == {}
assert "(./note.md)" in (coll / "index.md").read_text() and (coll / "sub/index.md").read_text() == "# Sub\n"
assert "Ran fix" in (coll / "log.md").read_text()

# set: text-level edits keep other lines byte for byte; CRLF and BOM survive; bad values refused.
raises(bb.set_, {"status": "done"}, file="note.md")
raises(bb.set_, {"verified": []}, file="note.md")
assert "+status: draft" in bb.set_({"status": "draft"}, file="note.md")["diff"]
bb.set_({"status": "draft", "tags": ["a", "b"]}, file="note.md", apply=True)
t = (coll / "note.md").read_text()
assert "custom: {a: [1, 2]}  # mine\n" in t and "status: draft\n" in t
bb.set_({"status": None}, file="note", apply=True)
assert "status:" not in (coll / "note.md").read_text()
(coll / "crlf.md").write_bytes(b"\xef\xbb\xbf---\r\ntype: Note\r\n---\r\nx\r\n")
bb.set_({"title": "C"}, file="crlf.md", apply=True)
raw = (coll / "crlf.md").read_bytes()
assert raw.startswith(b"\xef\xbb\xbf---\r\n") and b"title: C\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")

# verify: machine path; human: refused from an agent; elicitation path; changed body refused.
asyncio.run(bb.verify("note.md", by="claude-code/claude-opus-5-5"))
d = bb.meta((coll / "note.md").read_text())[0]
assert d["verified"][0]["by"] == "claude-code/claude-opus-5-5" and TS.fullmatch(d["verified"][0]["at"])
assert bb.trust_tier(d) == "machine-confirmed"
assert "only a human" in raises(bb.verify, "note.md", by="human:drew")
raises(bb.verify, "note.md", by="drew")


class Ctx:
    def __init__(self, action="accept", reviewer="tester", edit=None):
        self.action, self.reviewer, self.edit = action, reviewer, edit

    async def elicit(self, message, schema):
        assert "note.md" in message
        if self.edit:
            self.edit()
        return SimpleNamespace(action=self.action, data=SimpleNamespace(confirm=True, reviewer=self.reviewer))


assert asyncio.run(bb.verify("note.md", ctx=Ctx("decline")))["edited"] == []
assert asyncio.run(bb.verify("note.md", ctx=Ctx()))["tier"] == "human-reviewed"
sealed = (coll / "note.md").read_text()
e = bb.meta(sealed)[0]["verified"][-1]
assert e["by"] == "human:tester" and e["sha256"] == bb.content_hash(sealed, True)
assert bb.signed(bb.meta(sealed)[0], "note.md", {})["verified"][-1]["by"] == "human:tester"  # the seal holds
(coll / "note.md").write_text(sealed + "\nedited after review\n")
broken = bb.signed(bb.meta(sealed)[0], "note.md", {})
assert broken["verified"] == [e2 for e2 in broken["verified"] if "sha256" not in e2] and bb.is_stale(broken) and bb.trust_tier(broken) != "human-reviewed"
(coll / "note.md").write_text(sealed)
d = bb.meta((coll / "note.md").read_text())[0]
assert [e["by"] for e in d["verified"]] == ["claude-code/claude-opus-5-5", "human:tester"]
edit = lambda: (coll / "note.md").write_text((coll / "note.md").read_text() + "\nmore\n")
assert "changed" in raises(bb.verify, "note.md", ctx=Ctx(edit=edit))
os.environ["BOWERBIRD_USER"] = "drew"
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human at the terminal
assert bb.meta((coll / "note.md").read_text())[0]["verified"][-1]["by"] == "human:drew"
assert cli("verify", "file=note.md", "by=human:drew")[0] == 2 and cli("lint", "--attest")[0] == 2
bb.at_terminal = lambda: False  # a pipe or script is refused
with contextlib.redirect_stderr(io.StringIO()):
    assert bb.cli(["verify", "file=note.md", "--attest"]) == 2
assert bb.meta((coll / "note.md").read_text())[0]["verified"][-1]["by"] == "human:drew"
bb.CLI, bb.ATTEST = False, ""
assert all(cli(n)[0] == 2 for n in ("recheck_apply", "recheck_plan", "cite"))  # renamed in 2.2.0, with no alias: each says where it went

# fact / factcheck: a fact is a reproducible result: the recorded call, what it returned, and its fingerprint.
(coll / ".mcp.json").write_text(json.dumps({"mcpServers": {"jira": {"command": "x", "env": {"TOKEN": "secret"}}}}))
raises(bb.fact, "note.md", server="nope", tool="get_issue")
c = bb.fact("note.md", server="jira", tool="get_issue", args={"issue_key": "INFRA-1"}, result='{"status": "Open", "n": 1}',
           title="INFRA-1 status", stale_days=30)
assert c["footnote"] == "[^infra-1]"
(coll / "note.md").write_text((coll / "note.md").read_text().replace("Body.", "The ticket is open.[^infra-1]"))
d = bb.meta((coll / "note.md").read_text())[0]
assert d["sources"][0]["resource"] == "mcp://jira/get_issue?issue_key=INFRA-1" and TS.fullmatch(d["stale_after"])
assert d["sources"][0]["fact_sha256"] == bb.fact_sha256('{"n":1,   "status":"Open"}') != bb.fact_sha256('{"status": "Closed", "n": 1}')  # JSON: key order and spacing do not matter
assert bb.fact_sha256("a  b\n c") == bb.fact_sha256("a b c")  # other text: whitespace collapses
assert bb.lint()["ok"], bb.lint()
plan = bb.factcheck()  # no result: information only
assert plan["calls"][0]["call"] == {"server": "jira", "tool": "get_issue", "args": {"issue_key": "INFRA-1"}}
assert bb.factcheck(older_than_days=1)["calls"] == [] and bb.factcheck(file="note.md", id="nope")["calls"] == []
assert "The ticket is open" in plan["calls"][0]["cites"][0]
assert bb.meta((coll / "note.md").read_text())[0] == d  # and it wrote nothing
live = lambda: bb.trust_tier(bb.signed(bb.meta((coll / "note.md").read_text())[0], "note.md", {}))
os.environ["BOWERBIRD_USER"] = "drew"
bb.at_terminal = lambda: True
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human reviews the note with its fact
assert live() == "human-reviewed"
before = (coll / "note.md").read_bytes()
same = bb.factcheck(file="note.md", id="infra-1", result='{"n": 1, "status": "Open"}')  # the same fact: the check is recorded, nothing breaks
assert same["drift"] is False and live() == "human-reviewed" and (coll / "note.md").read_bytes() == before  # the sealed file is not touched by a clean check
assert "infra-1" in (coll / ".facts.yaml").read_text() and "drifted_at" not in (coll / ".facts.yaml").read_text()
assert "one fact" in raises(bb.factcheck, result="x") and "no fact" in raises(bb.factcheck, file="note.md", id="nope", result="x")
bad = bb.factcheck(file="note.md", id="infra-1", result='{"status": "Closed", "n": 1}')  # drift: the reviews before it stop holding
assert bad["drift"] is True and bad["was"] != bad["now"] and "The ticket is open" in bad["cites"][0], bad
assert (coll / "note.md").read_bytes() == before and "drifted_at" in (coll / ".facts.yaml").read_text()  # noted beside the file, the file itself unchanged
assert live() != "human-reviewed" and bb.drift_of("note.md", {}) is not None
bb.CLI = True
sk = bb.signatures("")["findings"]
assert any(f["kind"] == "stale_signature" and f["file"] == "note.md" and "fact drifted" in f["message"] for f in sk), sk
time.sleep(1.1)  # `at` has one-second resolution: the new review is later than the drift
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human reviews it again, after the drift: it holds
assert live() == "human-reviewed" and not any(f["file"] == "note.md" for f in bb.signatures("")["findings"])
bb.fact("note.md", resource="https://example.com/base", id="base", title="No result yet")  # no fact_sha256: the first result is the baseline
assert bb.factcheck(file="note.md", id="base", result="x")["drift"] is None
assert bb.factcheck(file="note.md", id="base", result="y")["drift"] is True
assert cli("fact", "file=note.md", "resource=https://x", "--attest")[0] == 2  # recording a fact is not confirming it
assert "secret" not in json.dumps(bb.lint(limit=0))
bb.fact("note.md", resource="https://example.com/page", title="Page")
assert bb.lint()["ok"]
assert bb.status()["by_tier"].get("human-reviewed", 0) == 0  # a new source changed the bytes: the review no longer holds, and status says so
time.sleep(1.1)  # a review counts only if it is made after the last drift: not in the same second
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human reviews it again

# Symlinks are never followed.
(coll / "alias.md").symlink_to(coll / "note.md")
assert "alias.md" not in json.dumps(bb.lint(limit=0)) and "alias" not in json.dumps(bb.list_())
(coll / "alias.md").unlink()

# Read tools.
st = bb.status()
assert st["by_tier"]["human-reviewed"] == 1 and st["by_status"]["stable"] >= 1 and st["okf_version"] == "0.2"
assert st["conformant"]
assert [x["id"] for x in bb.list_(tier="human-reviewed")["concepts"]] == ["note"]
(coll / "other.md").write_text("---\ntype: Note\n---\nSee [the note](/note.md).\n")
bb.index(apply=True)
assert bb.links("note.md")["in"] == ["other.md"] and bb.links("other.md")["out"][0]["exists"]
assert bb.search("ticket")["total"] == 1
assert bb.get("note.md", limit=1)["text"] == "---\n"
assert [f["file"] for f in bb.get(files=["note.md", "other.md"])["files"]] == ["note.md", "other.md"]

# create, move, log, per-directory indexes.
bb.new("guides/howto", type="Playbook", description="How to.", tags=["ops"], status="draft", body="Step one.",
         by="claude-code/claude-opus-5-5")
t = (coll / "guides/howto.md").read_text()
d = bb.meta(t)[0]
assert d["type"] == "Playbook" and d["generated"]["by"] == "claude-code/claude-opus-5-5" and "# howto\n\nStep one." in t
raises(bb.new, "guides/howto", type="Playbook")
raises(bb.new, "x", type=" ")
raises(bb.new, "index", type="Note")
(coll / "guides/ref.md").write_text("---\ntype: Note\ndescription: r.\nexecutor: {resource: note.md}\n"
                                  "sources:\n  - id: h\n    resource: howto.md\n---\n"
                                  "See [how](howto.md#howto), [note](../note.md) and [abs](/note.md).\n")
assert "playbooks/howto.md" in bb.move("guides/howto.md", "playbooks/howto.md")["would_edit"]["."]
bb.move("guides/howto.md", "playbooks/howto.md", apply=True)
assert (coll / "playbooks/howto.md").exists() and not (coll / "guides/howto.md").exists()
assert "](../playbooks/howto.md#howto)" in (coll / "guides/ref.md").read_text()
assert bb.meta((coll / "guides/ref.md").read_text())[0]["sources"][0]["resource"] == "../playbooks/howto.md"
bb.move("guides/ref", "a/b/ref", apply=True)
t = (coll / "a/b/ref.md").read_text()
assert "](../../playbooks/howto.md#howto)" in t and "](../../note.md)" in t and "](/note.md)" in t
d = bb.meta(t)[0]
assert d["sources"][0]["resource"] == "../../playbooks/howto.md" and d["executor"]["resource"] == "note.md"  # root-relative stays
bb.record("Reviewed the guides.")
assert re.search(r"^\* <!-- \d+ --> \*\*Update\*\*: Reviewed the guides\.$", (coll / "log.md").read_text(), re.MULTILINE)
raises(bb.log, "two\nlines")
bb.index(dirs=True, apply=True)
assert "(ref.md)" in (coll / "a/b/index.md").read_text() and "[b](b/)" in (coll / "a/index.md").read_text()
assert bb.lint()["ok"] and "index_stale" not in kinds() and "dead_anchor" not in kinds()

# upgrade (v0.1): Citations become sources; timestamp needs git for `by`.
(coll / "old").mkdir()
(coll / "old/index.md").write_text("# Old\n")
(coll / "old/m.md").write_text("---\ntype: Metric\ntimestamp: '2026-05-28T22:53:05+00:00'\n---\n# M\n\nText.\n\n"
                             "# Citations\n- https://wiki.acme/fpa-handbook\n- [Policy](https://wiki.acme/policy)\n")
out = bb.upgrade(apply=True, bundle="old")
assert out["needs_by"] == ["m.md"]
d = bb.meta((coll / "old/m.md").read_text())[0]
assert [e["id"] for e in d["sources"]] == ["fpa-handbook", "policy"] and d["sources"][1]["title"] == "Policy"
assert "# Citations" not in (coll / "old/m.md").read_text() and "timestamp" in d
assert bb.meta((coll / "old/index.md").read_text())[0]["okf_version"] == "0.2"
assert bb.lint(bundle="old", scope="okf")["ok"] and bb.upgrade(bundle="old")["would_edit"] == {}
assert {b["bundle"] for b in bb.bundles()["bundles"]} == {".", "old"}
shutil.rmtree(coll / "old")

# The spec as an MCP resource.
assert "okf://spec" in {str(x.uri) for x in asyncio.run(bb.mcp.list_resources())}
assert bb.spec().startswith("# Open Knowledge Format")

# verify promote: only a human review moves draft to stable.
bb.new("promo", type="Note", description="P.", status="draft")
assert "only a human" in raises(bb.verify, "promo.md", by="claude/x", promote=True)
assert cli("verify", "file=promo.md", "--attest", "promote=true")[0] == 0
assert bb.meta((coll / "promo.md").read_text())[0]["status"] == "stable"

# fix normalizes tag case to the most common spelling.
(coll / "tags").mkdir()
for n, tg in (("a", "Sales"), ("b", "Sales"), ("c", "sales")):
    (coll / f"tags/{n}.md").write_text(f"---\ntype: x\ndescription: d.\ntags: [{tg}]\n---\n")
assert "tag_case" in kinds(bundle="tags")
bb.fix(apply=True, bundle="tags")
assert "tag_case" not in kinds(bundle="tags") and bb.meta((coll / "tags/c.md").read_text())[0]["tags"] == ["Sales"]
shutil.rmtree(coll / "tags")

# Spec use cases: §6.1 broken links tolerated, §5.1 lineage edges and signals, §8 lists and synthesized
# indexes, §9 logs at any level, §5.4 deprecation logged by convention.
u, saved = coll.parent / "uses", bb.ROOT
u.mkdir()
bb.ROOT = coll.parent
create(apply=True, bundle="uses")
bb.new("t/src.md", type="Reference", description="s.", bundle="uses", resource="https://example.com/x")
bb.new("t/m.md", type="Metric", description="m.", body="[later](/t/unwritten.md)", bundle="uses")
(u / "t/m.md").write_text((u / "t/m.md").read_text().replace("type: Metric", "type: Metric\nsources: [{id: s, resource: /t/src.md}]"))
L = bb.lint(bundle="uses", limit=0)
assert L["ok"] and "dead_link" in L["counts"] and ("t/src.md", "orphan") not in {(f["file"], f["kind"]) for f in L["findings"]}
assert bb.links("t/src.md", bundle="uses")["in"] == ["t/m.md"]
assert {"field": "sources[0].resource", "path": "/t/src.md", "target": {"bundle": "uses", "file": "t/src.md"},
        "exists": True} in bb.links("t/m.md", bundle="uses")["out"]
assert "* [src](./t/src.md) - s." in (u / "index.md").read_text()
g = bb.get("t/index.md", bundle="uses")
assert g["synthesized"] and "* [m](m.md) - m." in g["text"] and not (u / "t/index.md").exists()
(u / "t/log.md").write_text("# Log\n")
bb.fact("t/m.md", resource="https://example.com/doc", author="team:docs", usage_count=0,
       last_modified="2026-05-30T00:00:00Z", bundle="uses")
e = bb.meta((u / "t/m.md").read_text())[0]["sources"][-1]
assert e["author"] == "team:docs" and e["usage_count"] == 0 and "Cited" in (u / "t/log.md").read_text()
bb.set_({"status": "deprecated"}, file="t/src.md", bundle="uses", apply=True)
assert "**Deprecation**: Deprecated [t/src.md](/t/src.md)." in (u / "t/log.md").read_text()
bb.record("Hand note on [m](/t/m.md).", dir="t", bundle="uses")
L = bb.log("t/m.md", bundle="uses")
assert [e["entry"] for e in L["entries"]][:1] == ["**Update**: Hand note on [m](/t/m.md)."] and L["entries"][0]["log"] == "t/log.md"
assert not any("src.md" in e["entry"] and "m.md" not in e["entry"] for e in L["entries"])
assert len(bb.log(bundle="uses")["entries"]) > len(L["entries"])
assert "Hand note" in (u / "t/log.md").read_text() and "Hand note" not in (u / "log.md").read_text()
assert "usage_window" in raises(bb.set_, {"usage_window": {"from": "x"}}, file="t/m.md", bundle="uses")
asyncio.run(bb.verify("t/m.md", by="process:nightly", bundle="uses"))
bb.new("t/d.md", type="Note", description="d.", status="draft", by="claude-code/x", bundle="uses")
bb.set_({"stale_after": bb.now(10)}, file="t/m.md", bundle="uses", apply=True)
st = bb.status(bundle="uses")
assert st["review"]["oldest"] == [{"file": "t/m.md", "days": 0}] and st["drafts"] == {"count": 1, "oldest": [{"file": "t/d.md", "days": 0}]}
assert [d["file"] for d in st["due"]] == ["t/m.md"] and not bb.status(due_days=5, bundle="uses")["due"]
# §6.2: a value naming a real file is a path, whatever its shape.
(u / "t/data").write_text("x")
assert bb.pathed("data", u / "t/m.md", u) == (u / "t/data", "doc") and bb.pathed("t/nothing", u / "t/m.md", u) is None


class Who:  # the person answering provenance's prompt
    def __init__(self, ok=True):
        self.ok = ok

    async def elicit(self, message, schema):
        assert "no history" in message
        return SimpleNamespace(action="accept" if self.ok else "decline", data=SimpleNamespace(confirm=True, author="ann"))


assert asyncio.run(bb.provenance(apply=True, ctx=Who(False), bundle="uses"))["unknown"]["count"] >= 1
asyncio.run(bb.provenance(apply=True, ctx=Who(), bundle="uses"))
g_ = bb.meta((u / "t/src.md").read_text())[0]["generated"]
assert g_["by"] == "human:ann" and g_["basis"] == "stated" and TS.fullmatch(g_["at"]), g_
shutil.rmtree(u)
bb.ROOT = saved

# The archive also works when the collection root is itself a bundle: it is set apart, not nested.
one = Path(tempfile.mkdtemp()) / "solo"
one.mkdir()
bb.ROOT = one
create(apply=True)
bb.new("x.md", type="Note", description="x.", bundle=".")
bb.archive("x.md", bundle=".", apply=True)
assert (one / "archive/solo/x.md").exists() and "nested_bundle" not in kinds() and not (one / "x.md").exists()
bb.unarchive("solo/x.md", apply=True)
assert (one / "x.md").exists() and not (one / "archive/solo/x.md").exists()
bb.ROOT = saved

# A collection of sibling bundles: tools follow where the user is; bundles do not nest.
saved, cwd, ws = bb.ROOT, os.getcwd(), (coll.parent / "ws").resolve()
ws.mkdir()
bb.ROOT = ws
create(apply=True, bundle="a")
create(apply=True, bundle="b")
assert (ws / ".gitattributes").read_text() == "log.md merge=union\nindex.md merge=union\n"
(ws / "a/sub").mkdir()
(ws / "a/sub/c.md").write_text("---\ntype: x\ndescription: c.\nsources: [{id: n, resource: /n.md}]\n---\n[n](/n.md)\n")
(ws / "a/n.md").write_text("---\ntype: x\ndescription: n.\n---\n[c](sub/c.md) [b](../b/m.md)\n")
(ws / "b/m.md").write_text("---\ntype: x\ndescription: m.\n---\n[n](../a/n.md) [m](m.md)\n")
bb.index(apply=True, bundle="a")
bb.index(apply=True, bundle="b")
os.chdir(ws / "a/sub")
L = bb.lint(limit=0, ignore=["stub"])
assert set(L["bundles"]) == {"a"} and {(f["bundle"], f["file"], f["kind"]) for f in L["findings"]} == {("a", "n.md", "cross_bundle")}, L
code, out = cli("get", "file=c.md")  # CLI paths are relative to where you are
assert code == 0 and (json.loads(out)["bundle"], json.loads(out)["file"]) == ("a", "sub/c.md")
os.chdir(ws)
L = bb.lint(limit=0)
assert set(L["bundles"]) == {".", "a", "b"} and L["ok"], L
assert {("a", "n.md"), ("b", "m.md")} <= {(c["bundle"], c["file"]) for c in bb.list_()["concepts"]} and any(h["bundle"] == "b" for h in bb.search("m.md")["hits"])
assert set(bb.status()["bundles"]) == {"a", "b"} and "bundles" not in bb.status(bundle="a")
st = bb.status(bundle="a")
assert st["sources"] == {"with": 1, "without": 1} and st["words"]["longest"][0]["words"] >= 1 and st["due"] == []
assert {(f["bundle"], f["file"]) for f in bb.lint(file="a/n.md", limit=0)["findings"]} == {("a", "n.md")}
assert {(f["bundle"], f["file"]) for f in bb.lint(files=["b"], limit=0)["findings"]} == {("b", "m.md")}
code, out = cli("lint", "a/n.md", "format=text")
assert code == 0 and out.startswith("a/n.md: warning: cross_bundle")
raises(bb.lint, file="nope.md")
bb.set_({"status": "draft"}, file="a/n.md", apply=True)  # routes to bundle a: its log, not a root one
assert "Set status" in (ws / "a/log.md").read_text() and not (ws / "log.md").exists()
assert bb.links("a/n.md")["in"] == ["sub/c.md"] and bb.links("n.md", bundle="a")["bundle"] == "a"
bb.baseline(apply=True)  # fingerprints are collection-relative, so they hold from any directory
os.chdir(ws / "a")
assert bb.lint(baseline=".okf-baseline.json")["total"] == 0 and bb.lint(baseline=".okf-baseline.json")["baselined"]
os.chdir(ws)
assert "migrate" in raises(bb.move, "a/sub/c.md", "b/c.md")
bb.migrate("a/sub/c.md", "b", apply=True)
assert (ws / "b/sub/c.md").exists() and not (ws / "a/sub/c.md").exists()
assert "[c](../b/sub/c.md)" in (ws / "a/n.md").read_text() and "[n](../../a/n.md)" in (ws / "b/sub/c.md").read_text()
assert bb.meta((ws / "b/sub/c.md").read_text())[0]["sources"][0]["resource"] == "../../a/n.md"
assert "Migrated" in (ws / "a/log.md").read_text() and "Migrated" in (ws / "b/log.md").read_text()
assert "nest" in raises(bb.create, bundle="a/inner", apply=True)
(ws / "a/inner").mkdir()
(ws / "a/inner/index.md").write_text('---\nokf_version: "0.2"\n---\n# Inner\n')
assert "nested_bundle" in kinds(bundle="a")
shutil.rmtree(ws / "a/inner")
assert bb.fix(apply=True)["remaining"]["ok"]  # every bundle here, re-linted the same way
(ws / "area").mkdir()
(ws / "area/y.md").write_text("---\ntype: x\ndescription: y.\n---\n")
(ws / "area/x.md").write_text("---\ntype: x\ndescription: x.\n---\n[n](/a/n.md) [y](/area/y.md)\n")
out = bb.split_off("area", apply=True)
t = (ws / "area/x.md").read_text()
assert "[n](../a/n.md)" in t and "[y](/y.md)" in t and out["crossing"]["count"] == 1
assert bb.declares(ws / "area/index.md") and bb.lint(bundle="area")["ok"]
assert "nest" in raises(bb.split_off, "b/sub")
# rename, archive, unarchive: whole directories move and every link follows.
(ws / "b/m.md").write_text("---\ntype: x\ndescription: m.\n---\n[n](../a/n.md) [m](/m.md)\n")
assert "-> d" in bb.rename_bundle("d", bundle="b")["move"] and (ws / "b").exists()
bb.rename_bundle("d", bundle="b", apply=True)
assert not (ws / "b").exists() and "[m](/m.md)" in (ws / "d/m.md").read_text()
assert "../d/m.md" in (ws / "a/n.md").read_text() and "Renamed the bundle" in (ws / "d/log.md").read_text()
bb.archive("n.md", bundle="a", apply=True)  # one concept
assert (ws / "archive/a/n.md").exists() and bb.declares(ws / "archive/a/index.md")  # archive/a: an archived bundle
assert not bb.declares(ws / "archive/index.md") and "* [a](a/)" in (ws / "archive/index.md").read_text()
assert "archive/a" not in bb.lint()["bundles"] and "n.md" not in json.dumps(bb.list_())  # set apart from the live one
assert "../archive/a/n.md" in (ws / "d/m.md").read_text() and "archived_link" in kinds(bundle="d")
assert "archived" in raises(bb.set_, {"status": "draft"}, file="a/n.md", bundle="archive")
bb.unarchive("a/n.md", apply=True)
assert (ws / "a/n.md").exists() and "../a/n.md" in (ws / "d/m.md").read_text()
assert "explicitly" in raises(bb.archive)
bb.archive(bundle="d", apply=True)  # a whole bundle: its log comes along, it stops being a bundle
assert not (ws / "d").exists() and bb.declares(ws / "archive/d/index.md") and (ws / "archive/d/log.md").exists()
assert "../archive/d/m.md" in (ws / "a/n.md").read_text() and "nested_bundle" not in kinds(bundle="archive")
bb.unarchive("d", apply=True)
assert bb.declares(ws / "d/index.md") and "../d/m.md" in (ws / "a/n.md").read_text() and bb.lint(bundle="d")["ok"]
bb.rename_bundle("b", bundle="d", apply=True)
shutil.rmtree(ws / "archive")
w = bb.web()  # at the collection root: bundles, edges counted
assert w["level"] == "bundles" and {"from": "a", "to": "b", "kind": "link", "count": 2} in w["edges"], w
assert bb.web(bundle="a")["level"] == "concepts" and bb.graph(w).startswith("graph LR\n")
code, out = cli("web", "format=mermaid")
assert code == 0 and "-->|link|" in out
assert bb.collection(ws / "a/sub") == ws / "a"  # no index above yet: the bundle is the collection
assert "index_stale" not in kinds() and bb.index(apply=True)["edited"] == {".": ["index.md"]}
assert bb.upgrade()["would_edit"] == {} and not bb.declares(ws / "index.md")  # the collection root stays no bundle
assert (ws / "index.md").read_text().count("* [") == 3 and "* [b](b/)" in (ws / "index.md").read_text()
assert bb.collection(ws / "a/sub") == ws and bb.collection(ws) == ws
(ws / "c").mkdir()
create(apply=True, bundle="c")
assert "index_stale" in kinds() and bb.fix(apply=True)["remaining"]["ok"] and "* [c](c/)" in (ws / "index.md").read_text()
os.chdir(cwd)
bb.ROOT = saved

# §6.2: a path field is a path only if it looks like one; git-ignored files are not scanned.
assert bb.pathed("dashboards/exec-revenue", coll / "x.md", coll) is None
assert bb.pathed("./nope", coll / "x.md", coll) == (None, "missing")
g = Path(tempfile.mkdtemp())
subprocess.run(["git", "init", "-q", str(g)], check=True)
(g / ".gitignore").write_text("node_modules/\n")
(g / "node_modules").mkdir()
(g / "node_modules/README.md").write_text("x\n")
(g / "a.md").write_text("x\n")
assert bb.walk(g) == [g / "a.md"]

# CLI: exit codes and CI formats.
assert cli("lint")[0] == 0
(coll / "bad").mkdir()
(coll / "bad/x.md").write_text("no frontmatter\n")
code, out = cli("lint", "bundle=bad", "format=github")
assert code == 1 and out.startswith("::error file=")
code, out = cli("lint", "bundle=bad", "format=sarif")
assert code == 1 and json.loads(out)["runs"][0]["results"]
assert cli("lint", "nonsense=1")[0] == 2
assert cli("fix", "bundle=bad")[0] == 0
assert cli("help")[0] == 0
fmt0, bb.OPTS["format"] = bb.OPTS["format"], "markdown"  # help is short and follows the format; `help all` lists everything
short, full = cli("help")[1], cli("help", "all")[1]
assert "seal" in short and "create" not in short and "create" in full and "bowerbird-mcp (format: markdown)" in short
bb.OPTS["format"] = fmt0
assert cli("nope")[0] == 2
assert bb.flags_to_words("seal", bb.REG["seal"], ["-cp"]) == ["promote=true", "check=true"]  # combined short flags
for n, m in bb.SHORTS.items():  # pinned letters: real arguments, none repeated, none of the reserved -h -F -O
    ps = {p for p in bb.inspect.signature(bb.REG[n]).parameters} - {"ctx"}
    assert set(m) <= ps and len(set(m.values())) == len(m) and not set(m.values()) & {"h", "F", "O"}, n
assert sorted(bb.flags_to_words("create", bb.REG["create"], ["-t", "markdown", "-a", "Docs", "--apply"])) == ["about=Docs", "apply=true", "holds=markdown"]
assert cli("bundles", "-O", "text")[1] == cli("bundles", "-F", "text")[1] == cli("bundles", "output=text")[1] and cli("lint", "--nope")[0] == 2
assert cli("lint", "--sca", "all")[0] == 2  # no abbreviations
(coll / "bare.md").write_text("---\ntype: x\n---\n")
assert cli("set", "bare.md", "status=draft", "tags=[a, b]", "apply=true")[0] == 0  # frontmatter as key=value
assert bb.meta((coll / "bare.md").read_text())[0] | {} == {"type": "x", "status": "draft", "tags": ["a", "b"]}
assert cli("set", "bare.md", "status=stable", "--apply")[0] == 0 and bb.meta((coll / "bare.md").read_text())[0]["status"] == "stable"  # a flag beside name=value
assert cli("move", "bare.md", "bare2.md", "apply=true")[0] == 0 and (coll / "bare2.md").exists()  # bare arguments
(coll / "bare2.md").unlink()
assert set(bb.EXAMPLES) == set(bb.REG)  # every tool has an example
code, out = cli("help", "move")
assert code == 0 and "-t, --to TO" in out and "str, required" in out and cli("move", "--help")[1] == out
import shlex  # every example, typed as flags, means what its name=value form means; `-a` is a bare switch, not `-a VALUE`

for n, exs in bb.EXAMPLES.items():
    for e in exs:
        fl = [w for w in shlex.split(bb.flag_example(n, e))[1:] if w != "--attest"]
        assert set(bb.flags_to_words(n, bb.REG[n], fl)) == {w for w in shlex.split(e)[1:] if w != "--attest"}, (n, e)
assert bb.flags_to_words("lint", bb.REG["lint"], ["-a"]) == ["all=true"] and bb.flags_to_words("lint", bb.REG["lint"], ["--no-all"]) == ["all=false"]
c1, o1 = cli("bundles", "output=text")
c2, o2 = cli("bundles", "format=text")  # the older name for output still works
assert c1 == c2 == 0 and o1 == o2 and not o1.lstrip().startswith("{"), (o1, o2)
assert cli("bundles", "output=json")[1].lstrip().startswith("{") and cli("bundles", "output=nope")[0] == 2
code, out = cli("bundles", "format=text")
assert code == 0 and out.startswith("bundles:")
assert cli("bundles")[1].lstrip().startswith("{")  # CI contract: piped output is JSON by default
bb.out_terminal = lambda: True  # a person at a terminal gets text by default; output=json still wins
assert cli("bundles")[1].startswith("bundles:") and cli("bundles", "output=json")[1].lstrip().startswith("{")
bb.out_terminal = lambda: False
shutil.rmtree(coll / "bad")

# MCP surface: annotations, and the context parameter is not a tool argument.
tools = {t.name: t for t in asyncio.run(bb.mcp.list_tools())}
assert tools["lint"].annotations.readOnlyHint and not tools["fix"].annotations.readOnlyHint
assert "ctx" not in tools["seal"].inputSchema["properties"]

# Git: history, provenance, ingest (copy, then in place).
src = coll / "src"
(src / "docs").mkdir(parents=True)


def g(*a):
    subprocess.run(["git", "-c", "commit.gpgsign=false", *a], cwd=src, check=True, capture_output=True)


g("init", "-q")
g("config", "user.name", "Ann")
g("config", "user.email", "ann@example.com")
(src / "docs/guide.md").write_text("# Guide\n\nHow to do it. [home](../index.md) ![i](../img.png)\n")
(src / "README.md").write_text("# Readme\n\nSee [g](/docs/guide.md).\n")
(src / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")
(src / "img.png").write_bytes(b"\x89PNG")
g("add", ".")
g("commit", "-qm", "init")
(src / "docs/guide.md").write_text("---\ntags: [x]\n---\n# Guide\n\nHow to do it. [home](../index.md) ![i](../img.png)\n")  # frontmatter only
g("-c", "user.name=Bob", "commit", "-qam", "tags")
(src / "README.md").write_text("# Readme\n\nSee [g](/docs/guide.md). Updated.\n")
g("commit", "-qam", "edit\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
(src / "bot.md").write_text("# Bot\n\nBumped.\n")
g("add", "bot.md")
g("-c", "user.name=dependabot[bot]", "-c", "user.email=49699333+dependabot[bot]@users.noreply.github.com",
  "commit", "-qm", "bot")
g("remote", "add", "origin", "https://user:tok@github.com/o/r.git")

hm = bb.heatmap(bundle="src", limit=0)  # most changed first; README and guide changed twice
assert [(f["file"], f["changes"]) for f in hm["files"][:2]] == [("src/README.md", 2), ("src/docs/guide.md", 2)], hm
assert sum(f["changes"] for f in hm["files"]) == hm["bundles"][0]["changes"] == 5  # index.md left out
assert {(f["file"], f["authors"]) for f in hm["files"]} >= {("src/docs/guide.md", 2), ("src/README.md", 1)}
assert {a["author"] for a in hm["authors"]} == {"Ann", "Bob", "dependabot[bot]"} and hm["authors"][0] == {
    "author": "Ann", "changes": 3, "concepts": 2}
assert {(f["file"], f["author"]) for f in hm["single_author"]} == {("src/README.md", "Ann"), ("src/bot.md", "dependabot[bot]")}
h = bb.history(src, [src / "docs/guide.md", src / "README.md", src / "bot.md"])
assert h[src / "docs/guide.md"]["by"] == "human:ann@example.com"  # Bob's frontmatter edit does not count
assert h[src / "README.md"]["by"] == "claude/claude-opus-5.5"
assert h[src / "bot.md"]["by"] == "process:dependabot"
assert asyncio.run(bb.provenance(bundle="src"))["would_edit"] == {"src": ["docs/guide.md"]}

plan = bb.ingest("src", bundle="imported", rules={"docs/*": "Guide"})
assert plan["ingest"] == 4 and plan["skipped"] == {"not markdown": 1}, plan
assert {i["to"] for i in plan["items"]} == {"docs/guide.md", "README.md", "src-index.md", "bot.md"}
assert plan["absolute_links"]["count"] == 1 and plan["provenance"] == {"full": 4}
assert plan["links_after_ingest"]["count"] == 2, plan["links_after_ingest"]
bb.ingest("src", bundle="imported", rules={"docs/*": "Guide"}, apply=True)
d = bb.meta((coll / "imported/docs/guide.md").read_text())[0]
assert d["type"] == "Guide" and d["status"] == "draft" and d["tags"] == ["x"]
assert d["generated"] == {"by": "human:ann@example.com", "at": d["generated"]["at"], "basis": "git-history"}
assert d["sources"][0]["resource"].startswith("https://github.com/o/r/blob/") and "tok" not in json.dumps(d)
assert bb.lint(bundle="imported", scope="okf")["ok"]
assert bb.ingest("src", bundle="imported")["ingest"] == 0  # re-run is a no-op
assert "source_changed" not in kinds(bundle="imported")
m = bb.ingest("imported", bundle="merged", keep_okf=True, apply=True)  # merge an OKF bundle as is
assert m["ingest"] == 4 and (coll / "merged/docs/guide.md").read_text() == (coll / "imported/docs/guide.md").read_text()
assert bb.ingest("imported", bundle="merged", keep_okf=True)["ingest"] == 0

(src / "dirty.md").write_text("x\n")
assert "clean git tree" in raises(bb.ingest, "src", bundle="src", apply=True)
(src / "dirty.md").unlink()
assert bb.ingest("src", bundle="src", apply=True)["links_after_ingest"]["count"] == 1
assert not (src / "index.md").exists() and (src / "src-index.md").exists()
assert bb.lint(bundle="src", scope="okf")["ok"] and bb.ingest("src", bundle="src")["ingest"] == 0

# lint since: only files changed since a ref (committed, unstaged or untracked) count.
g("add", "-A")
g("commit", "-qm", "okf")
(src / "new.md").write_text("no frontmatter\n")
L = bb.lint(bundle="src", since="HEAD", limit=0)
assert {f["file"] for f in L["findings"]} == {"new.md"} and not L["ok"]
assert bb.lint(bundle="src", since="HEAD~1", limit=0)["total"] > L["total"]
assert "unknown ref" in raises(bb.lint, bundle="src", since="nope")
assert "git work tree" in raises(bb.lint, since="HEAD")
assert "warning" in bb.heatmap() and bb.heatmap()["files"] == []  # no git: says so, does not fail
(coll / "box.tar.gz").write_bytes(b"x")
assert "unpack it first" in raises(bb.ingest, "box.tar.gz")
(coll / "box.tar.gz").unlink()
(src / "new.md").unlink()

subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{src}", str(coll / "shallow")], check=True,
               capture_output=True)
assert "shallow" in raises(bb.provenance, bundle="shallow")
pl = bb.ingest("shallow", bundle="fromshallow", keep_okf=True)  # no history: origin only, said so
assert "shallow" in pl and set(pl["provenance"]) == {"partial"}, pl
up = Path(tempfile.mkdtemp())  # a plain repo, shallow-cloned: origin documents the repository and the commit
for c in (["init", "-q"], ["-c", "user.name=A", "-c", "user.email=a@x", "-c", "commit.gpgsign=false", "commit", "-q",
                           "--allow-empty", "-m", "x"]):
    subprocess.run(["git", *c], cwd=up, check=True, capture_output=True)
(up / "plain.md").write_text("# Plain\n")
subprocess.run(["git", "add", "."], cwd=up, check=True)
subprocess.run(["git", "-c", "user.name=A", "-c", "user.email=a@x", "-c", "commit.gpgsign=false", "commit", "-qm", "y"],
               cwd=up, check=True)
subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{up}", str(coll / "shallow2")], check=True, capture_output=True)
bb.ingest("shallow2", bundle="fromshallow2", apply=True)
o = bb.meta((coll / "fromshallow2/plain.md").read_text())[0]["sources"][0]
assert o["resource"] == f"file://{up}" and re.fullmatch(r"plain\.md at [0-9a-f]{12} of file://.+", o["title"]), o
g("remote", "set-url", "origin", "https://user:tok@github.com/o/r.git")
assert bb.remote(src) == "https://github.com/o/r.git"

# permalink: credentials and ports dropped; a local remote has no web URL.
g("remote", "set-url", "origin", "ssh://git@host.example:2222/o/r.git")
assert bb.permalink(src, src.resolve())(src / "bot.md", "abc") == "https://host.example/o/r/blob/abc/bot.md"
g("remote", "set-url", "origin", "git@github.com:o/r.git")
assert bb.permalink(src, src.resolve())(src / "bot.md", "abc") == "https://github.com/o/r/blob/abc/bot.md"
assert bb.web_base(src) == "https://github.com/o/r"  # the repository's address, for the link in `serve`
g("remote", "set-url", "origin", "https://user:secret@host.example:8443/o/mygit.git")
assert bb.web_base(src) == "https://host.example/o/mygit" and "secret" not in bb.web_base(src)  # no credentials or port; only a trailing .git goes
g("remote", "set-url", "origin", f"file://{src}")
assert bb.permalink(src, src.resolve()) is None and bb.web_base(src) is None

# Ranked search, dirs, vocab, demand; new lint kinds and only/ignore.
saved, rk = bb.ROOT, Path(tempfile.mkdtemp()).resolve()
bb.ROOT = rk
create(apply=True)
long = "Plenty of words here, comfortably past the stub threshold for body text."
(rk / "ops").mkdir()
(rk / "ops/deploy.md").write_text(f"---\ntype: Playbook\ntitle: Deploy\ndescription: How we ship.\ntags: [ops]\n---\n"
                                  f"{long}\nRollback with care. [r](rollback.md) [w](wanted.md) [me](deploy.md)\n")
(rk / "ops/rollback.md").write_text(f"---\ntype: Playbook\ntitle: Rollback\ndescription: Undo a deploy.\ntags: [ops]\n"
                                    f"---\n{long}\n[d](deploy.md) [w](wanted.md) [x][gone] [u]: http://u.example\n")
(rk / "faq.md").write_text(f"---\ntype: Note\ntitle: Deploy\ndescription: Questions.\n---\n{long} deploy [d](ops/deploy.md)\n")
(rk / "tiny.md").write_text("---\ntype: Note\ndescription: Tiny.\n---\n# Tiny\n\nShort.\n")
(rk / "seed.md").write_text("---\ntype: Note\nstatus: draft\ndescription: Seed.\n---\nShort.\n")
bb.index(apply=True)
h = bb.search("deploy")["hits"]
assert [x["file"] for x in h[:2]] == ["ops/deploy.md", "faq.md"] and h[0]["score"] > h[1]["score"] > h[-1]["score"], h
assert h[0]["matched"][:2] == ["title", "id"] and h[0]["line"] == 8 and "(deploy.md)" in h[0]["text"]  # body first
assert [x["file"] for x in bb.search("deploy care")["hits"]] == ["ops/deploy.md"]  # every word, any field
assert {x["file"] for x in bb.search("deploy", type="Playbook", dir="ops")["hits"]} == {"ops/deploy.md", "ops/rollback.md"}
assert [x["file"] for x in bb.search("deploy", fields=["title"])["hits"]] == ["faq.md", "ops/deploy.md"]
assert bb.search("deploy", tag="nope")["total"] == 0
raises(bb.search, "")
raises(bb.search, "x", fields=["nope"])
assert {(d["dir"], d["concepts"]) for d in bb.dirs()["dirs"]} == {(".", 4), ("ops", 2)}
assert bb.vocab() == {"tags": {"ops": 2}, "types": {"Note": 3, "guide": 1, "Playbook": 2}}
st = bb.status()
assert st["wanted"] == [{"file": "ops/wanted.md", "links": 2}] and {"file": "ops/rollback.md", "links": 1} in st["hubs"]
kinds_of = lambda **kw: {(f["file"], f["kind"]) for f in bb.lint(limit=0, **kw)["findings"]}
L = kinds_of()
assert {("tiny.md", "stub"), ("ops/deploy.md", "self_link"), ("ops/rollback.md", "undefined_ref"),
        ("faq.md", "duplicate_title"), ("ops/deploy.md", "duplicate_title")} <= L, L
assert ("seed.md", "stub") not in L and not any(x == "unused_ref" for _, x in L)  # [u]: mid-line is no definition
(rk / "island1.md").write_text(f"---\ntype: Note\ndescription: I.\n---\n{long} [2](island2.md)\n\n[u]: http://u.example\n")
(rk / "island2.md").write_text(f"---\ntype: Note\ndescription: I.\n---\n{long} [1](island1.md)\n")
L = kinds_of()
assert ("island1.md", "island") in L and ("island1.md", "unused_ref") in L and not any(x == "island" and f.startswith("ops") for f, x in L), L
assert {x for _, x in kinds_of(only=["stub"])} == {"stub"} and "stub" not in {x for _, x in kinds_of(ignore=["stub"])}
raises(bb.lint, only=["nope"])
(rk / "bower.yaml").write_text(bb.EXAMPLE_CONFIG)  # at the collection root: right
assert any(f.startswith("ops/") for f, _ in kinds_of())
(rk / "ops/bower.yaml").write_text("")  # a folder's own bower.yaml overrides the one above it; it is not another collection
assert any(f.startswith("ops/") for f, _ in kinds_of()) and not any(x == "nested_config" for _, x in kinds_of())
(rk / "ops/bower.yaml").unlink()
bb._SCOPES.clear()
(rk / "bower.yaml").unlink()
src = Path(bb.__file__).read_text()
assert set(re.findall(r'finding\(\s*"(\w+)"', src)) | set(bb.ERR) | {"island"} <= bb.KINDS
# passages: heading-level BM25, with trust shown; a miss is a gap.
(rk / "ops").mkdir(exist_ok=True)
(rk / "ops/runbook.md").write_text("---\ntype: Playbook\ndescription: Shipping.\ntags: [ops]\n---\n"
                                   "Intro text about shipping.\n\n## Rollback\n\nTo roll back, redeploy the previous tag.\n\n"
                                   "```\n# not a heading\n```\n\n## Deploy\n\nPush the tag. " + "filler " * 40 + "\n")
P = bb.passages("roll back previous tag")
top = P["hits"][0]
assert top["file"] == "ops/runbook.md" and top["heading"].endswith("Rollback") and top["line"] == 9, top
assert {"tier", "stale", "status", "text"} <= set(top) and not P["gap"]
assert [c[0].split(" > ")[-1] for c in bb.chunks((rk / "ops/runbook.md").read_text(), "T")] == ["T", "Rollback", "Deploy"]
long = "# T\n\n" + "\n\n".join(f"para{i} " + "x" * 200 for i in range(12)) + "\n"
cs = [c[2] for c in bb.chunks(long, "T")]
assert len(cs) > 1 and all(f"para{i} " in "".join(cs) for i in range(12))
assert all(cs[j].split("\n\n")[-1] in cs[j + 1] for j in range(len(cs) - 1)), "pieces overlap by one paragraph"
ls = [c[1] for c in bb.chunks(long, "T")]
assert ls[1] == ls[0] + 2 * (len(cs[0].split("\n\n")) - 1), "an overlapped piece starts at its repeated paragraph"
G = bb.passages("zzzunseen")
assert G["gap"] and G["total"] == 0 and bb.passages("tag", tag="nope")["total"] == 0
raises(bb.passages, "   ")

# bower.yaml: root, user, ai_producers; unknown keys refuse.
cfg = Path(tempfile.mkdtemp()).resolve()
(cfg / "sub").mkdir()
(cfg / "bower.yaml").write_text("user: drew\nai_producers: [zed]\n")
d, c = bb.load_config(cfg / "sub")
assert d == cfg and c == {"user": "drew", "ai_producers": ["zed"]}
assert bb.load_config(Path("/"))[0] is None
(cfg / "bower.yaml").write_text("bogus: 1\n")
try:
    bb.load_config(cfg)
    raise AssertionError("bad key accepted")
except SystemExit as e:
    assert "unknown key bogus" in str(e)
# flat passage settings: types and values are checked.
for bad, msg in (("semantic: 3", "semantic must be a bool"), ("seal: {nope: 1}", "seal takes exempt and exempt_status"), ("vector_index: faiss", "vector_index must be"), ("format: rst", "format must be okf, markdown, adr, skos"), ("build: sometimes", "must be auto or manual"),
                 ("min_similarity: high", "must be a float"), ("index: {path: x}", "index must be a str"), ("nope: 1", "unknown key nope")):
    (cfg / "bower.yaml").write_text(bad + "\n")
    try:
        bb.load_config(cfg)
        raise AssertionError(bad)
    except SystemExit as e:
        assert msg in str(e), (bad, str(e))
(cfg / "bower.yaml").write_text("semantic: true\nmin_similarity: 1\nhubs: false\n")
assert bb.load_config(cfg)[1] == {"semantic": True, "min_similarity": 1, "hubs": False}

# passages: false: no passages tool, no example, the instructions send you to search.
(cfg / "bower.yaml").write_text("passages: false\n")
probe = "import bowerbird_mcp as k; print('passages' in k.REG, 'passages' in k.EXAMPLES, 'passages' in k.INSTRUCTIONS)"
env = dict(os.environ) | {"PYTHONPATH": str(HERE)}
off = subprocess.run([sys.executable, "-c", probe], cwd=cfg, env=env, capture_output=True, text=True, check=False)
assert off.stdout.split() == ["False", "False", "False"], off
(cfg / "bower.yaml").write_text("\n")
on = subprocess.run([sys.executable, "-c", probe], cwd=cfg, env=env, capture_output=True, text=True, check=False)
assert on.stdout.split() == ["True", "True", "True"], on

# hubs: the concept others link to ranks first on a tie, and shows its inbound count.
(rk / "hub").mkdir(exist_ok=True)
for n in ("a", "b"):
    (rk / f"hub/{n}.md").write_text(f"---\ntype: Note\ndescription: x\n---\nThe quokka protocol {n}.\n")
for n in range(3):
    (rk / f"hub/l{n}.md").write_text("---\ntype: Note\ndescription: x\n---\nSee [b](b.md).\n")
H = bb.passages("quokka", dir="hub")["hits"]
assert [h["file"] for h in H][:2] == ["hub/b.md", "hub/a.md"] and H[0]["links"] == 3 and H[1]["links"] == 0, H
bb.OPTS["hubs"] = False
assert [h["file"] for h in bb.passages("quokka", dir="hub")["hits"]] == ["hub/a.md", "hub/b.md"]
bb.OPTS["hubs"] = True

# semantic: a fake embedder finds a passage that shares no word with the query; the cache is reused.
calls = []
def fake(texts):
    calls.append(len(texts))
    return [[1.0, 0.0] if ("release" in t.lower() or "reverse" in t.lower()) else [0.0, 0.0] for t in texts]
(rk / "sem.md").write_text("---\ntype: Note\ndescription: x\n---\n## Release\n\nShip the release.\n")
bb.EMBEDDERS["fake"] = fake
bb.OPTS |= {"semantic": True, "semantic_model": "fake", "min_similarity": 0.5}
S = bb.passages("reverse")
assert [h["file"] for h in S["hits"]] == ["sem.md"], S
n_first = sum(calls)
bb.passages("reverse")
assert sum(calls) == n_first + 1 and (rk / ".bower/.gitignore").is_file()  # only the query was embedded again
assert bb.passages("zzzunseen")["gap"]
# vector_index: each backend that is installed returns what scan returns (hnsw is approximate, but exact at this size).
bb.EMBEDDERS["unit"] = lambda texts: [[1.0, 0.1] if ("release" in t.lower() or "reverse" in t.lower()) else [0.1, 1.0] for t in texts]
bb.OPTS |= {"semantic_model": "unit", "min_similarity": 0.5, "vector_index": "scan"}
want = [(h["file"], h["match"]) for h in bb.passages("reverse")["hits"]]
assert want and want[0][0] == "sem.md", want
for mode, mod in (("sqlite-vec", "sqlite_vec"), ("hnsw", "hnswlib")):
    try:
        __import__(mod)
        assert bb.sqlite3.connect(":memory:").enable_load_extension
    except (ImportError, AttributeError):
        print(f"skipped vector_index={mode}: {mod} not usable")
        continue
    bb.OPTS["vector_index"] = mode
    assert [(h["file"], h["match"]) for h in bb.passages("reverse")["hits"]] == want, mode
    assert [(h["file"], h["match"]) for h in bb.passages("reverse", dir="nope")["hits"]] == [], mode
    bb.reindex()
bb.OPTS |= {"vector_index": "scan", "semantic_model": "fake", "min_similarity": 0.5}
bb.OPTS["semantic"] = False
assert bb.passages("reverse")["gap"]
# reindex builds the one file at the chosen path; build: manual makes passages read it and nothing else.
default = {x: bb.OPTS[x] for x in ("index", "build", "min_similarity", "semantic_model")}
idx = Path(tempfile.mkdtemp()) / "x" / "my.db"
bb.OPTS["index"] = str(idx)
out = bb.reindex()
assert idx.is_file() and out["passages"] > 0 and out["vectors"] == 0 and out["path"] == str(idx) and not out["semantic"], out
bb.OPTS["build"] = "manual"
(rk / "late.md").write_text("---\ntype: Note\ndescription: x\n---\nThe zorblax arrived late.\n")
assert bb.passages("zorblax")["gap"]  # manual: the new file is not read until reindex
assert bb.reindex()["passages"] == out["passages"] + 1 and [h["file"] for h in bb.passages("zorblax")["hits"]] == ["late.md"]
bb.OPTS["index"] = str(idx.parent / "missing.db")
assert "reindex" in raises(bb.passages, "zorblax")
bb.OPTS |= {"index": str(idx), "build": "auto"}
assert bb.reindex(full=True)["passages"] == out["passages"] + 1
code, text = cli("reindex", "format=text")
assert code == 0 and "passages" in text, (code, text)
# reindex info and drop: manage the file from the tool.
bb.OPTS["index"] = str(idx)
I = bb.reindex(info=True)
assert I["exists"] and I["files"] > 0 and I["behind"] == 0 and I["bytes"] > 0 and I["vectors"] == 0 and I["build"] == "auto", I
(rk / "late2.md").write_text("---\ntype: Note\ndescription: x\n---\nAnother.\n")
assert bb.reindex(info=True)["behind"] == 1 and bb.reindex(info=True)["files"] == I["files"]  # info never builds
bb.reindex()
assert bb.reindex(info=True)["behind"] == 0 and bb.reindex(info=True)["files"] == I["files"] + 1
assert "pass one" in raises(bb.reindex, full=True, drop=True)
assert bb.reindex(drop=True)["dropped"] and not idx.exists() and not bb.reindex(drop=True)["dropped"]
assert bb.reindex(info=True)["exists"] is False and not idx.exists()
idx.parent.mkdir(exist_ok=True); idx.write_text("not a database")
assert bb.reindex(info=True)["usable"] is False
(rk / "late2.md").unlink()
bb.OPTS["index"] = ""
assert "bower.yaml" in raises(bb.reindex) and bb.passages("zorblax")["hits"]  # in memory: passages still works
bb.OPTS.update(default)
(rk / "late.md").unlink()
# roles: every tool has a home; the server offers the union of the roles asked for and enabled; the CLI has all.
assert set().union(*bb.ROLES.values()) == set(bb.REG) and bb.offered() == set(bb.REG)
list_tools = ("import sys, asyncio; sys.argv = ['x', *sys.argv[1:]]; import bowerbird_mcp as k; "
              "print(' '.join(sorted(t.name for t in asyncio.run(k.mcp.list_tools()))))")
def server(yaml_text="", *argv, **env):
    (cfg / "bower.yaml").write_text(yaml_text)
    e = {kk: v for kk, v in os.environ.items() if kk != "BOWERBIRD_ROLE"} | {"PYTHONPATH": str(HERE)} | env
    return subprocess.run([sys.executable, "-c", list_tools, *argv], cwd=cfg, env=e, capture_output=True, text=True, check=False)
r = server("", "--role", "read")
assert set(r.stdout.split()) == bb.ROLES["read"] and {"passages", "get", "dirs"} <= bb.ROLES["read"], r
r = server("", BOWERBIRD_ROLE="write,lifecycle")
assert set(r.stdout.split()) == bb.ROLES["write"] | bb.ROLES["lifecycle"], r
r = server("roles: [read]\n")  # the others are off: only read is offered
assert set(r.stdout.split()) == bb.ROLES["read"], r
r = server("roles: [read]\n", "--role=lifecycle")  # asking for a role that is off refuses
assert r.returncode and "off in bower.yaml" in r.stderr, r
r = server("roles: [wizard]\n")
assert r.returncode and "unknown role wizard" in r.stderr, r
assert bb.opt_arg(["--role", "write", "lint"], "--role") == ("write", ["lint"]) and bb.opt_arg(["--role=a"], "--role") == ("a", [])
# the config file marks the collection: found from the working directory or named by --config; ROOT is refused.
probe = "import sys; sys.argv = ['x', *sys.argv[1:]]; import bowerbird_mcp as k; print(k.ROOT); print(k.INSTRUCTIONS)"
def where(cwd, *argv, **env):
    e = {kk: v for kk, v in os.environ.items() if kk != "BOWERBIRD_ROLE"} | {"PYTHONPATH": str(HERE)} | env
    return subprocess.run([sys.executable, "-c", probe, *argv], cwd=cwd, env=e, capture_output=True, text=True, check=False)
base = Path(tempfile.mkdtemp()).resolve()
(base / "eng/deep").mkdir(parents=True)
(base / "eng/bower.yaml").write_text("about: Engineering runbooks.\n")
r = where(base / "eng/deep")  # found from below: the file's own folder is the collection
assert r.stdout.splitlines()[0] == str(base / "eng") and "This collection: Engineering runbooks." in r.stdout, r
assert where(base / "eng").stdout.splitlines()[0] == str(base / "eng")
(base / "other").mkdir()
r = where(base / "other", "--config", str(base / "eng/bower.yaml"))  # --config wins over where we are
assert r.stdout.splitlines()[0] == str(base / "eng") and "Engineering runbooks" in r.stdout, r
r = where(base / "other", "--config", str(base / "nope.yaml"))
assert r.returncode and "--config takes either" in r.stderr, r
for gone in ("KB_ROOT", "BOWERBIRD_ROOT"):
    r = where(base / "other", **{gone: str(base)})
    assert r.returncode and f"{gone} is no longer read" in r.stderr, r
# config: writes the commented example once, never over a file; the example tracks the real keys and defaults.
_y = bb.yaml
eg = bb.EXAMPLE_CONFIG
assert _y.safe_load(eg) is None  # all comments: valid, and marks the base
for key in bb.CONFIG_KEYS:
    line = next((ln for ln in eg.splitlines() if ln.startswith(f"# {key}: ")), None)
    assert line, f"{key} missing from the example"
    if key in bb.DEFAULTS and key != "about":  # about is only illustrated
        assert _y.safe_load(line[2:])[key] == bb.DEFAULTS[key], (key, line)
cf, ck, bb.CFG_DIR = bb.CFG_DIR, bb.ROOT, None
bb.ROOT = Path(tempfile.mkdtemp()).resolve()
C = bb.config()
assert not C["written"] and not (bb.ROOT / "bower.yaml").exists() and C["content"] == {"bower.yaml": eg, "env.example": bb.ENV_EXAMPLE}
assert bb.config(apply=True)["written"] and (bb.ROOT / "bower.yaml").read_text() == eg
assert "exist" in raises(bb.config)
assert bb.load_config(bb.ROOT) == (bb.ROOT, {}) and C["gitignore"] == "not a git work tree"
code, text = cli("config")
assert code == 2, (code, text)  # the CLI refuses too: both exist now
# in a git work tree: init writes a filled bower.yaml and env.example, lists .env in .gitignore, and asks for what it lacks.
gr = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(gr)], check=True)
(gr / ".gitignore").write_text("build/")  # no trailing newline: kept
bb.ROOT = gr
P = create()
assert P["config"]["files"][0] == "bower.yaml" and {"env.example", ".mcp.json"} <= set(P["config"]["files"]) and P["config"]["gitignore"] == ".gitignore gets .env", P  # .env too if a user id is known
assert "about" in P["config"]["missing"] and not (gr / "bower.yaml").exists(), P  # apply=false writes nothing
P = create(apply=True)
assert (gr / ".gitignore").read_text() == "build/\n.env\n" and (gr / "env.example").read_text() == bb.ENV_EXAMPLE
got = bb.load_config(gr)[1]
assert got == {"format": "okf", "passages": True, "hubs": True, "semantic": False, "semantic_model": bb.DEFAULTS["semantic_model"],
               "min_similarity": bb.DEFAULTS["min_similarity"], "index": bb.DEFAULTS["index"]}, got
assert bb.declares(gr / "index.md") and (gr / "log.md").is_file()  # okf: a bundle too
# init also writes a .mcp.json (commit it: a clone has the tools with nothing to register), and never overwrites one.
mj = json.loads((gr / ".mcp.json").read_text())
assert mj == bb.MCP_JSON and mj["mcpServers"]["bowerbird"]["command"] == "uvx" and "--role" not in mj["mcpServers"]["bowerbird"]["args"]
# a folder that already has its bower.yaml still gets the files it lacks, and that file is left alone.
ex = Path(tempfile.mkdtemp()).resolve()
(ex / "bower.yaml").write_text("format: adr\n")
bb.ROOT = ex
P = create(apply=True, holds="adr")
assert "bower.yaml" not in P["config"]["files"] and {"env.example", ".mcp.json", "BOWERBIRD.md"} <= set(P["config"]["files"]), P
assert (ex / "bower.yaml").read_text() == "format: adr\n" and json.loads((ex / ".mcp.json").read_text()) == bb.MCP_JSON
# init writes BOWERBIRD.md (agent rules), names only tools that exist, never overwrites it, and the docs page carries the same text.
assert (ex / "BOWERBIRD.md").read_text() == bb.AGENTS_MD
_pick = [ln for ln in bb.AGENTS_MD.split("## Picking a tool")[1].splitlines() if ln.startswith(("|", "Rare"))]
_use = [ln.strip("|").split("|")[1] if ln.startswith("|") else ln for ln in _pick]  # the Use column and the rare list name tools; the prose and the Not column name settings and arguments too
assert len(_use) > 20
for t in re.findall(r"`([a-z_]+)`", "\n".join(_use)):
    assert t in bb.REG, t
(ex / "BOWERBIRD.md").write_text("mine\n")
assert "BOWERBIRD.md" not in create(apply=True, holds="adr").get("config", {}).get("files", [])
assert (ex / "BOWERBIRD.md").read_text() == "mine\n"
assert bb.AGENTS_MD in (Path(bb.__file__).parent / "docs-src" / "agents.md").read_text(), "docs-src/agents.md drifted from AGENTS_MD"
# the rules also reach an agent with no file: a resource and a prompt serve the same text
assert [str(r.uri) for r in asyncio.run(bb.mcp.list_resources())].count("bowerbird://agent-rules") == 1
assert asyncio.run(bb.mcp.read_resource("bowerbird://agent-rules"))[0].content == bb.AGENTS_MD
assert asyncio.run(bb.mcp.get_prompt("rules")).messages[0].content.text == bb.AGENTS_MD
bb.ROOT = gr
# given values fill it in; markdown and skos start no bundle; nothing is overwritten.
md = Path(tempfile.mkdtemp()).resolve()
bb.ROOT = md
P = create(apply=True, about="Decisions.", holds="markdown", user="dfoulks")
assert bb.load_config(md)[1]["about"] == "Decisions." and bb.load_config(md)[1]["format"] == "markdown", P
assert (md / ".env").read_text() == "BOWERBIRD_USER=dfoulks\n" and not (md / "index.md").exists() and P["config"]["missing"] == []
raises(create, holds="rst")
# guessing: thesaurus files mean skos, markdown without OKF types means markdown, an empty folder means okf.
g = Path(tempfile.mkdtemp()).resolve()
assert bb.detect_holds(g) == "okf"
(g / "t.ttl").write_text("@prefix : <http://x/> .\n")
assert bb.detect_holds(g) == "skos"
(g / "adr").mkdir()
(g / "adr/0001-x.md").write_text("# Use x\n")
assert bb.detect_holds(g) == "adr"
(g / "adr/0001-x.md").rename(g / "adr/x.md")
(g / "adr").rename(g / "docs")
assert bb.detect_holds(g) == "markdown"
(g / "docs").rename(g / "adr")
(g / "adr/x.md").rename(g / "adr/0001-x.md")
(g / "adr/0001-x.md").write_text("---\ntype: Note\n---\nx\n")
assert bb.detect_holds(g) == "okf"
# init asks a human (elicitation) for what it could not know, and goes on without an answer.
class Ask:
    def __init__(self, action="accept", **data):
        self.action, self.data = action, data
        self.asked = []

    async def elicit(self, message, schema):
        self.asked.append(message)
        return SimpleNamespace(action=self.action, data=schema(**{"about": "", "holds": "markdown", "user": "", **self.data}))
a1 = Path(tempfile.mkdtemp()).resolve()
bb.ROOT = a1
ask = Ask(about="Ops notes.", holds="markdown", user="me")
asyncio.run(bb.create(apply=True, ctx=ask))
assert len(ask.asked) == 1 and "about" in ask.asked[0]
assert bb.load_config(a1)[1]["about"] == "Ops notes." and (a1 / ".env").read_text() == "BOWERBIRD_USER=me\n"
a2 = Path(tempfile.mkdtemp()).resolve()
bb.ROOT = a2
assert asyncio.run(bb.create(apply=True, ctx=Ask("decline")))["config"]["missing"]  # no answer: written with what it has
assert "about" not in bb.load_config(a2)[1]
# a folder holding its own bower.yaml overrides the one above it: the parent's lint still sees inside it.
bb.ROOT = gr
(gr / "sub").mkdir()
(gr / "sub/bower.yaml").write_text("")
(gr / "sub/n.md").write_text("---\ntype: Note\n---\nx\n")
assert any(f["file"].startswith("sub/") for f in bb.lint(limit=0)["findings"])
bb.ROOT, bb.CFG_DIR = ck, cf
# lint always says it ran: a verdict line (with what it checked) on success and failure, text and github.
L = bb.lint()
assert L["checked"]["concepts"] > 0 and L["checked"]["bundles"] >= 1, L
code, text = cli("lint", "format=text")
assert text.splitlines()[-1].startswith(f"bowerbird-mcp lint: {'ok' if code == 0 else 'FAILED'}: ") and "concept(s) in" in text, text
code, text = cli("lint", "format=github")
assert text.splitlines()[-1].startswith("::notice title=bowerbird-mcp lint::bowerbird-mcp lint: "), text
assert "checked" not in bb.lint(file="faq.md")  # a named file has no bundle count
good = Path(tempfile.mkdtemp()).resolve()
(good / "index.md").write_text('---\nokf_version: "0.2"\n---\n# kb\n')
(good / "log.md").write_text("# Log\n")
saved_root = bb.ROOT
bb.ROOT = good
code, text = cli("lint", "format=text")
assert code == 0 and text.splitlines()[-1] == "bowerbird-mcp lint: ok: 0 concept(s) in 1 bundle(s) checked, 0 finding(s), conformant: True", (code, text)
bb.ROOT = saved_root
# a file with no frontmatter that links to a concept must not crash lint (islands once raised KeyError).
(rk / "plain.md").write_text("No frontmatter here, but it links [to a concept](seed.md).\n")
assert ("plain.md", "no_frontmatter") in kinds_of()
(rk / "plain.md").unlink()
# passages: match is a percent of the best hit (a lone hit is 100); the "land it by PR" hint needs a git work tree.
M = bb.passages("quokka", dir="hub")["hits"]
assert M[0]["match"] == 100 and all(isinstance(h["match"], int) and 0 <= h["match"] <= 100 for h in M) and "score" not in M[0], M
assert [h["match"] for h in bb.passages("zorblax nothingelse")["hits"]] in ([], [100])
(rk / "solo.md").write_text("---\ntype: Note\ndescription: x\n---\nA lone ocelot sentence.\n")
assert [h["match"] for h in bb.passages("ocelot")["hits"]] == [100]
(rk / "solo.md").unlink()
assert "next" not in bb.new("hintless", type="Note")  # rk is not a git work tree
(rk / "hintless.md").unlink()
gr2 = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(gr2)], check=True)
bb.ROOT = gr2
assert "next" in create(apply=True)  # a git work tree: there is a diff to review
bb.ROOT = rk
# format: markdown indexes ADRs and MADR records with no OKF frontmatter, and offers only passages and reindex.
ar, was = Path(tempfile.mkdtemp()).resolve(), (bb.ROOT, dict(bb.OPTS))
(ar / "docs/adr").mkdir(parents=True)
(ar / "docs/adr/0001-record-decisions.md").write_text("# 1. Record architecture decisions\n\nDate: 2016-02-12\n\n## Status\n\n"
                                                      "Accepted\n\n## Context\n\nWe need to record zebra decisions.\n")
(ar / "docs/adr/0002-use-postgres.md").write_text("---\nstatus: superseded by [ADR-0005](0005-x.md)\ndate: 2024-05-01\n---\n"
                                                  "# Use PostgreSQL\n\n## Context and Problem Statement\n\nWhich database for the narwhal?\n")
(ar / "docs/adr/0003-use-queue.md").write_text("# Use a queue\n\n* Status: proposed\n* Date: 2020-01-01\n\n## Context\n\nThe platypus needs a queue.\n")
(ar / "docs/index.md").write_text("# Docs home\n\nWelcome, wombat readers.\n")
bb.ROOT = ar
bb.OPTS |= {"format": "markdown", "semantic": False, "index": ""}
got = {h["file"]: h for q in ("zebra", "narwhal", "platypus", "wombat") for h in bb.passages(q)["hits"]}
assert set(got) == {"docs/adr/0001-record-decisions.md", "docs/adr/0002-use-postgres.md", "docs/adr/0003-use-queue.md",
                    "docs/index.md"}, set(got)
assert [got[f"docs/adr/000{n}-" + x + ".md"]["status"] for n, x in ((1, "record-decisions"), (2, "use-postgres"), (3, "use-queue"))] \
    == ["Accepted", "superseded by ADR-0005", "proposed"], got
assert got["docs/adr/0001-record-decisions.md"]["type"] == "adr" and got["docs/index.md"]["type"] is None
assert got["docs/index.md"]["status"] == "stable" and got["docs/index.md"]["tier"] == "unverified"
assert bb.offered() == bb.MARKDOWN == {"passages", "reindex", "seal", "get", "search", "dirs", "links", "list", "status", "heatmap", "create", "config", "new", "lint", "fact", "factcheck"}
for f, want in (("adr", bb.MARKDOWN | {"move"}), ("skos", bb.BASE), ("asciidoc", bb.ADOC), ("seal-only", {"seal"})):  # the tiers
    bb.OPTS["format"] = f
    assert bb.offered() == want, (f, bb.offered())
bb.OPTS["format"] = "markdown"
# format: adr: every markdown file but README.md and index.md is a decision record, whatever its name or folder.
(ar / "notes").mkdir(exist_ok=True)
(ar / "notes/queue-choice.md").write_text("# Queue choice\n\n* Status: accepted\n\nThe okapi service needs a queue.\n")
(ar / "notes/README.md").write_text("# Notes\n\nThe okapi readme.\n")
bb.OPTS["format"] = "markdown"
assert {h["file"]: h["type"] for h in bb.passages("okapi")["hits"]} == {"notes/queue-choice.md": None, "notes/README.md": None}
bb.OPTS["format"] = "adr"
A = {h["file"]: h for h in bb.passages("okapi")["hits"]}
assert A["notes/queue-choice.md"]["type"] == "adr" and A["notes/queue-choice.md"]["status"] == "accepted" and A["notes/README.md"]["type"] is None, A
assert bb.offered() == bb.MARKDOWN | {"move"} and bb.detect_holds(ar) == "adr"
bb.OPTS["format"] = "markdown"
(ar / "notes/queue-choice.md").unlink()
(ar / "notes/README.md").unlink()
# list and status outside OKF: proposed and accepted are stable (a seal is what says accepted), superseded is final.
k0 = "docs/adr/0001-record-decisions.md"
text0 = (ar / k0).read_text()
bb.ledger_put(k0, {"file": k0, "sha256": bb.content_hash(text0, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
L = {c["file"]: c for c in bb.list_(limit=0)["concepts"]}
assert (L[k0]["status"], L[k0]["tier"]) == ("stable", "human-reviewed") and L["docs/adr/0002-use-postgres.md"]["status"] == "superseded", L
assert [c["file"] for c in bb.list_(status="proposed", tier="unverified")["concepts"]] == ["docs/adr/0003-use-queue.md"]  # the word the file wrote
assert {c["file"] for c in bb.list_(status="STABLE", tier="unverified")["concepts"]} == {"docs/adr/0003-use-queue.md", "docs/index.md"}
st = bb.status()
assert (st["concepts"], st["by_status"], st["by_tier"], st["stale"]) == (4, {"stable": 3, "superseded": 1}, {"human-reviewed": 1, "unverified": 3}, 0), st
assert st["by_state"] == {"accepted": 1, "proposed": 1, "stable": 1, "superseded": 1}, st  # the index note is no decision record
(ar / k0).write_text(text0 + "\nEdited.\n")  # an edit breaks the seal: unreviewed again, and counted stale
st = bb.status()
assert st["by_tier"] == {"unverified": 4} and st["stale"] == 1, st
assert st["by_state"] == {"proposed": 2, "stable": 1, "superseded": 1}, st
(ar / k0).write_text(text0)
# move carries a seal along when the file's text does not change, and leaves it when the file had to be edited.
bb.ledger_put(k0, {"file": k0, "sha256": bb.content_hash(text0, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
k1 = "docs/adr/0001-record-it.md"
bb.move(k0, "docs/adr/0001-record-it", apply=True)
assert set(bb.ledger_by_file()) == {k1} and {c["file"]: c["tier"] for c in bb.list_(limit=0)["concepts"]}[k1] == "human-reviewed"
assert bb.status()["by_state"]["accepted"] == 1
bb.move(k1, k0[:-3], apply=True)  # back again, so the other records keep their names
k9, t9 = "docs/adr/0009-linked.md", "# Linked\n\nSee [home](../index.md).\n"
(ar / k9).write_text(t9)
bb.ledger_put(k9, {"file": k9, "sha256": bb.content_hash(t9, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
bb.move(k9, "docs/0009-linked", apply=True)  # its own relative link had to change, so its text did and the seal stays behind
assert set(bb.ledger_by_file()) == {k0, k9} and {c["file"]: c["tier"] for c in bb.list_(limit=0)["concepts"]}["docs/0009-linked.md"] == "unverified"
(ar / "docs/0009-linked.md").unlink()
[f.unlink() for f in bb.ledger_files()]  # the ledgers now sit beside their files
# format: seal-only: nothing is indexed, one tool; every text file is checked except what seal.exempt leaves out (code included).
prev = (bb.ROOT, bb.OPTS["format"], dict(bb.OPTS["seal"]))
so = Path(tempfile.mkdtemp()).resolve()
(so / "src").mkdir()
(so / "src/app.py").write_text("def add(a, b):\n    return a + b\n")
(so / "src/util.py").write_text("X = 1\n")
(so / "src/blob.py").write_bytes(b"\xff\xfe\x00")
(so / "docs.md").write_text("# not in the policy\n")
bb.ROOT, bb.OPTS["format"], bb.OPTS["seal"] = so, "seal-only", {"exempt": ["docs.md"], "exempt_status": []}
assert bb.offered() == {"seal"} and bb.passages("add")["gap"]
C = bb.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"]} == {("src/app.py", "unsigned"), ("src/util.py", "unsigned"), ("src/blob.py", "unreadable")} and C["files_checked"] == 2, C
code, out = cli("seal", "check=true")  # CI contract: unsigned files exit 1, and the output is JSON
assert code == 1 and json.loads(out)["findings"], (code, out)
bb.OPTS["seal"] = {"exempt": ["docs.md", "src/util.py"], "exempt_status": []}  # an exempt file is left out
C = bb.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"]} == {("src/app.py", "unsigned"), ("src/blob.py", "unreadable")} and C["files_checked"] == 1, C
bb.OPTS["seal"] = {"exempt": ["docs.md"], "exempt_status": []}
class AnyFile(Ctx):
    async def elicit(self, message, schema):
        assert "src/app.py" in message and "sha256" in message
        return SimpleNamespace(action="accept", data=SimpleNamespace(confirm=True, reviewer="tester"))
asyncio.run(bb.seal("src/app.py", by="process:ci"))  # a machine's review does not satisfy a policy that wants a human
assert ("src/app.py", "unsigned") in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
asyncio.run(bb.seal("src/app.py", ctx=AnyFile(), decision="accepted"))
assert ("src/app.py", "unsigned") not in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
(so / "src/app.py").write_text("def add(a, b):\n    return a - b\n")  # edited after review: the seal is broken
assert ("src/app.py", "stale_signature") in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
asyncio.run(bb.seal("src/util.py", by="process:ci"))
(so / "src/util.py").unlink()
assert [f["file"] for f in bb.signatures()["findings"] if f["kind"] == "orphan_signature"] == ["src/util.py"]
bb.OPTS["seal"] = {"exempt": [], "exempt_status": []}  # no list at all: every text file is checked, and a binary one is reported
(so / "src/util.py").write_text("X = 1\n")
C = bb.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"] if f["kind"] != "orphan_signature"} == {
    ("src/app.py", "stale_signature"), ("src/util.py", "unsigned"), ("src/blob.py", "unreadable"), ("docs.md", "unsigned")}, C
bb.OPTS["seal"] = {"exempt": ["docs.md", "src/blob.py", "src/util.py"], "exempt_status": []}  # exemptions are the only list
C = bb.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"] if f["kind"] != "orphan_signature"} == {("src/app.py", "stale_signature")}, C
bb.OPTS["format"] = "markdown"  # in any format, a file sealed by path outside it is checked for edits and is not an orphan
bb.OPTS["seal"] = {"exempt": [], "exempt_status": []}
assert not any(f["kind"] == "orphan_signature" and f["file"] == "src/app.py" for f in bb.signatures()["findings"])
assert ("src/app.py", "stale_signature") in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
d1 = Path(tempfile.mkdtemp()).resolve()
bb.ROOT = d1
P = create(apply=True, holds="seal-only", about="Reviewed code.", user="you")
assert bb.load_config(d1)[1]["format"] == "seal-only" and not any(l.startswith("seal:") for l in (d1 / "bower.yaml").read_text().splitlines()), P  # no list to fill in
bb.ROOT, bb.OPTS["format"], bb.OPTS["seal"] = prev

# seal, in markdown mode: the ledger binds a review to exact bytes; `check` finds what lacks one; a decision is the status.
bb.OPTS["seal"] = {"exempt": ["docs/index.md"], "exempt_status": ["proposed"]}
adr1 = "docs/adr/0001-record-decisions.md"
C = bb.signatures()
assert not C["ok"] and C["files_checked"] == 4 and {(f["file"], f["kind"]) for f in C["findings"]} == {
    (adr1, "unsigned"), ("docs/adr/0002-use-postgres.md", "unsigned")}, C  # 0003 is proposed (exempt); index.md is not required
asyncio.run(bb.seal(adr1, by="process:ci"))  # a machine's review is recorded, but policy wants a human
assert (adr1, "unsigned") in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
assert "accepted or rejected" in raises(bb.seal, adr1, decision="maybe")
class Any(Ctx):  # a human who confirms whatever file is shown
    async def elicit(self, message, schema):
        assert "adr/0001" in message and "sha256" in message and "decision: accepted" in message
        return SimpleNamespace(action="accept", data=SimpleNamespace(confirm=True, reviewer="tester"))
asyncio.run(bb.seal(adr1, ctx=Any(), decision="accepted"))
adr_led = (ar / adr1).parent / ".waxseals.yaml"  # the ledger sits in the file's own folder, and names the file relative to it
led = adr_led.read_text()
line = next(ln for ln in led.splitlines() if Path(adr1).name in ln)  # one dense line per file
assert not (ar / ".waxseals.yaml").exists() and f"file: {Path(adr1).name}," in line
assert led.startswith("# .waxseals.yaml") and line.startswith("- {") and "sha256:" in line and "human:tester" in line and "decision: accepted" in line and f"bowerbird: {bb.VERSION}" in line, led
asyncio.run(bb.seal(adr1, ctx=Any(), decision="accepted"))  # sealing again replaces the line: only the last seal is kept
assert sum(Path(adr1).name in ln for ln in adr_led.read_text().splitlines()) == 1
assert (adr1, "unsigned") not in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
assert "sealed with its outcome" in raises(bb.seal, adr1, ctx=Any())  # a person sealing a decision record must say what they decided
assert bb.adr_meta(bb.meta((ar / adr1).read_text())[0] or {}, (ar / adr1).read_text(), ar / adr1)["status"] == "accepted" and (adr1, "stale_signature") not in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}  # the ruling is in the file, and the seal holds for it
# an ADR+ record: who ruled and when are written too, and History keeps the values it had
plus = ar / "docs/adr/0042-plus.md"
plus.write_text('---\nstatus: proposed\nstatus-note: "drafted"\nkind: process\nbuilt: not started\n---\n# ADR-042 Plus\n\n## Decision\n\nx\n\n## History\n\n- drafted.\n')
class Anyone(Ctx):
    async def elicit(self, message, schema):
        assert "-> accepted (written into the file)" in message  # the prompt says what the decision will write
        return SimpleNamespace(action="accept", data=SimpleNamespace(confirm=True, reviewer="tester"))
asyncio.run(bb.seal("docs/adr/0042-plus.md", ctx=Anyone(), decision="accepted"))
pt = plus.read_text()
assert "status: accepted" in pt and "ratified-by: tester" in pt and re.search(r'^ratified-on: "\d{4}-\d{2}-\d{2}"$', pt, re.MULTILINE) and isinstance(bb.meta(pt)[0]["ratified-on"], str) and "Earlier values, word for word: `status: proposed`, `status-note: \"drafted\"`" in pt, pt
plus.unlink()
bb.ledger_apply({"docs/adr/0042-plus.md": None})
h = bb.passages("zebra")["hits"][0]
assert h["tier"] == "human-reviewed" and h["status"] == "accepted" and not h["stale"], h
(ar / adr1).write_text((ar / adr1).read_text() + "\nAn edit after the review.\n")  # the seal is broken
assert (adr1, "stale_signature") in {(f["file"], f["kind"]) for f in bb.signatures()["findings"]}
h = bb.passages("zebra")["hits"][0]
assert h["tier"] == "unverified" and h["stale"], h
asyncio.run(bb.seal("docs/adr/0003-use-queue.md", by="process:ci"))
(ar / "docs/adr/0003-use-queue.md").unlink()
O = [f for f in bb.signatures()["findings"] if f["kind"] == "orphan_signature"]
assert [f["file"] for f in O] == ["docs/adr/0003-use-queue.md"] and O[0]["severity"] == "warning"
assert bb.ALIASES == {"verify": "seal", "ratify": "seal", "accepted": "seal"} and bb.verify is bb.seal
R = bb.signatures()
txt = bb.render(R, "text")
assert txt.splitlines()[-1].startswith("bowerbird-mcp seal: ") and "file(s) checked" in txt and "conformant" not in txt, txt
assert ": warning: orphan_signature:" in txt and "::warning file=" in bb.render(R, "github") and "title=orphan_signature" in bb.render(R, "github")
assert bb.render(bb.signatures(), "github").splitlines()[-1].startswith("::notice title=bowerbird-mcp seal::")
raises(bb.seal)  # no file and no check
bb.OPTS["format"] = "okf"
assert bb.passages("zebra")["gap"], "okf mode skips files without frontmatter"
bb.ROOT = was[0]
bb.OPTS.update(was[1])

# format: skos indexes a thesaurus: one passage per concept, headed by its broader chain.
try:
    import rdflib  # noqa: F401 (is it installed?)
except ImportError:
    print("skipped format=skos: rdflib not installed")
else:
    sr = Path(tempfile.mkdtemp()).resolve()
    (sr / "animals.ttl").write_text("""@prefix : <http://ex.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct: <http://purl.org/dc/terms/> .
:scheme a skos:ConceptScheme ; dct:title "Animals" .
:animal a skos:Concept ; skos:prefLabel "Animal"@en ; skos:narrower :dog .
:dog a skos:Concept ; skos:prefLabel "Dog"@en ; skos:altLabel "hound"@en ;
  skos:definition "A domesticated carnivore kept by humans."@en ; skos:broader :animal ; skos:related :wolf .
:wolf a skos:Concept ; skos:prefLabel "Wolf"@en .
""")
    (sr / "broken.ttl").write_text("this is not turtle {{{")
    bb.ROOT = sr
    bb.OPTS |= {"format": "skos", "semantic": False, "index": ""}
    P = bb.passages("hound")
    h = P["hits"][0]
    assert [x["file"] for x in P["hits"]] == ["animals.ttl"] and h["heading"] == "Animals > Animal > Dog", P
    assert h["type"] == "skos" and h["title"] == "Animals" and h["tier"] == "unverified" and h["line"] == 6, h
    assert "Broader: Animal" in h["text"] and "Related: Wolf" in h["text"] and "carnivore" in h["text"], h["text"]
    assert next(x["heading"] for x in bb.passages("animal")["hits"]).endswith("Animal")  # narrower links back to broader
    assert bb.passages("turtle")["gap"] and bb.offered() == {"passages", "reindex", "seal"}
    bb.ROOT = was[0]
    bb.OPTS.update(was[1])

# format: asciidoc indexes AsciiDoc: one passage per section, header attributes (or YAML front matter) as metadata.
ad = Path(tempfile.mkdtemp()).resolve()
(ad / "deploy.adoc").write_text("= Deploy guide\n:tags: ops, deploy\n:status: stable\n\nIntro text.\n\n== Rollback\n\nRun the okapi rollback.\n\n"
                                "----\n== not a heading\n----\n\nSee xref:other.adoc[other] and <<third.adoc#x,third>>.\n")
(ad / "other.adoc").write_text("---\ntitle: Other doc\ntype: runbook\n---\n= Ignored\n\nThe platypus page.\n")
(ad / "third.adoc").write_text("= Third\n\nThe wombat page.\n")
bb.ROOT = ad
bb.OPTS |= {"format": "asciidoc", "semantic": False, "index": ""}
t, m, tags, cs, dst = bb.load_adoc(ad / "deploy.adoc", ad, "deploy.adoc", "asciidoc")
assert (t, tags, m["status"], m["type"]) == ("Deploy guide", ["ops", "deploy"], "stable", "asciidoc"), (t, tags, m)
assert [c[0] for c in cs] == ["Deploy guide", "Deploy guide > Rollback"] and dst == {"other.adoc", "third.adoc"}, (cs, dst)
h = bb.passages("okapi")["hits"][0]
assert h["file"] == "deploy.adoc" and h["heading"] == "Deploy guide > Rollback" and h["tier"] == "unverified", h
o = bb.passages("platypus")["hits"][0]
assert o["title"] == "Other doc" and o["type"] == "runbook", o  # front matter wins over the `= Ignored` line
assert bb.offered() == bb.ADOC and bb.detect_holds(ad) == "asciidoc"
bb.ROOT = was[0]
bb.OPTS.update(was[1])

# heatmap outside OKF counts the format's own files; index.md is an ordinary note there.
hmd = Path(tempfile.mkdtemp()).resolve()
gh = lambda *a: subprocess.run(["git", "-C", str(hmd), "-c", "user.name=Ann", "-c", "user.email=a@example.com", *a], check=True, capture_output=True)
gh("init", "-q")
(hmd / "a.adoc").write_text("= A\n")
(hmd / "b.md").write_text("# B\n")
(hmd / "index.md").write_text("# I\n")
gh("add", ".")
gh("commit", "-qm", "x")
(hmd / "a.adoc").write_text("= A\n\nmore\n")
gh("commit", "-qam", "y")
bb.ROOT = hmd
for f, want in (("asciidoc", {"a.adoc"}), ("markdown", {"b.md", "index.md"}), ("adr", {"b.md", "index.md"})):
    bb.OPTS["format"] = f
    got = bb.heatmap(limit=0)
    assert {x["file"] for x in got["files"]} == want, (f, got)
assert {x["file"]: x["changes"] for x in (bb.OPTS.update(format="asciidoc") or bb.heatmap(limit=0))["files"]} == {"a.adoc": 2}
bb.ROOT = was[0]
bb.OPTS.update(was[1])

# BOWERBIRD_* overrides: bower.yaml < .env < the environment; `format` is never overridden; env.example lists every key.
assert bb.env_overrides({"BOWERBIRD_SEMANTIC": "true", "BOWERBIRD_MIN_SIMILARITY": "0.7", "BOWERBIRD_ROLES": "read, write", "BOWERBIRD_ABOUT": "x",
                        "BOWERBIRD_USER": "me", "BOWERBIRD_AI_PRODUCERS": "zed,foo", "BOWERBIRD_FORMAT": "skos"}) == {
    "semantic": True, "min_similarity": 0.7, "roles": ["read", "write"], "about": "x", "user": "me", "ai_producers": ["zed", "foo"]}
for bad in ({"BOWERBIRD_SEMANTIC": "maybe"}, {"BOWERBIRD_MIN_SIMILARITY": "high"}, {"BOWERBIRD_BUILD": "sometimes"}, {"BOWERBIRD_ROLES": "root"}):
    try:
        bb.env_overrides(bad)
        raise AssertionError(bad)
    except SystemExit as e:
        assert next(iter(bad)) in str(e) or "BOWERBIRD_* environment" in str(e), (bad, str(e))
de = Path(tempfile.mkdtemp()) / ".env"
de.write_text("# comment\nBOWERBIRD_ABOUT='quoted value'\nexport BOWERBIRD_BUILD=manual # inline\nOTHER=1\nBOWERBIRD_HUBS=\"false\"\nnot a line\n")
assert bb.read_dotenv(de) == {"BOWERBIRD_ABOUT": "quoted value", "BOWERBIRD_BUILD": "manual", "BOWERBIRD_HUBS": "false"} and bb.read_dotenv(de.parent / "x") == {}
ex = (HERE / "env.example").read_text()
assert ex == bb.ENV_EXAMPLE and all(f"# BOWERBIRD_{key.upper()}=" in ex for key in bb.CONFIG_KEYS - bb.SHARED_ONLY) and "BOWERBIRD_FORMAT" not in ex
pe = Path(tempfile.mkdtemp()).resolve()
(pe / "bower.yaml").write_text("about: from yaml\nbuild: auto\n")
(pe / ".env").write_text("BOWERBIRD_ABOUT=from dotenv\nBOWERBIRD_BUILD=manual\n")
probe = "import bowerbird_mcp as k; print(k.OPTS['about'], '|', k.OPTS['build'])"
env = {key: v for key, v in os.environ.items() if not key.startswith("BOWERBIRD_")} | {"PYTHONPATH": str(HERE)}
r1 = subprocess.run([sys.executable, "-c", probe], cwd=pe, env=env, capture_output=True, text=True, check=False)
assert r1.stdout.strip() == "from dotenv | manual", r1
r2 = subprocess.run([sys.executable, "-c", probe], cwd=pe, env=env | {"BOWERBIRD_ABOUT": "from env"}, capture_output=True, text=True, check=False)
assert r2.stdout.strip() == "from env | manual", r2

bb.ROOT = saved

# the token figures in the README follow the tools (same method as the text says: serialized definition chars / 4), within 10%.
_tl = {t.name: t for t in asyncio.run(bb.mcp.list_tools())}
_cost = lambda names: sum(len(json.dumps({"name": n, "description": _tl[n].description, "inputSchema": _tl[n].inputSchema}))
                          for n in names if n in _tl) // 4
_pp = (HERE / "pyproject.toml").read_text()  # semantic search (fastembed) is an add-on: not a base dependency, and an extra of its own
assert 'dependencies = ["mcp>=1.10,<2", "pyyaml"]' in _pp and 'semantic = ["fastembed"]' in _pp
assert set(bb.MCP_TEXT) == set(bb.REG), set(bb.MCP_TEXT) ^ set(bb.REG)  # every tool has its short MCP text; the docstring stays whole for help and the docs
for _n, _t in _tl.items():
    assert _t.description.startswith(bb.MCP_TEXT[_n]) and len(_t.description) < 600, _n
    assert ("apply=true" in _t.description) == ("apply" in bb.inspect.signature(bb.REG[_n]).parameters) or _n in bb.MCP_TEXT and "apply=true" in bb.MCP_TEXT[_n], _n
assert "never pass human:<id>" in _tl["seal"].description and "gap=true" in _tl["passages"].description  # the rules an agent must not lose
assert len(bb.REG["seal"].__doc__) > 1500 and "Never pass human:<id> yourself" in " ".join(bb.REG["seal"].__doc__.split())  # the full text lives on for help, the CLI and the docs
_rm = (HERE / "README.md").read_text()
_close = lambda doc, real: abs(doc - real) <= real * 0.1
assert f"All {len(_tl)} tools" in _rm and _close(int(re.search(r"about ([\d,]+) tokens of schema", _rm).group(1).replace(",", "")), _cost(_tl)), _cost(_tl)
for _role, _names in bb.ROLES.items():
    _m = re.search(rf"\| `{_role}` \|.*\| (\d+), ~([\d,]+) tokens \|", _rm)
    assert int(_m.group(1)) == len([n for n in _names if n in _tl]) and _close(int(_m.group(2).replace(",", "")), _cost(_names)), (_role, _cost(_names))

# a result whose `findings` is a count (baseline's) prints as text, not as a list of lint findings.
assert bb.render({"findings": 3, "path": ".okf-baseline.json", "written": True}, "text") == "findings: 3\npath: .okf-baseline.json\nwritten: true"
# --version: the running Bowerbird says what it is, including whether it is a development build.
assert bb.VERSION == re.search(r'^version = "(.*)"', (HERE / "pyproject.toml").read_text(), re.MULTILINE).group(1)  # one number, two files
ds = bb.describe_source
assert ds(None, True, None, False) == ("release", "")  # installed from an index such as PyPI
assert ds('{"url": "https://github.com/x/y", "vcs_info": {"vcs": "git", "commit_id": "0123456789abcdef"}}', True, None, False) == ("development", "git 0123456")
assert ds('{"url": "file:///src/y", "dir_info": {"editable": true}}', True, None, False) == ("development", "editable install")
assert ds('{"url": "file:///src/y", "dir_info": {}}', True, None, False) == ("development", "local build")
assert ds(None, False, "abc1234", False) == ("development", "git abc1234")  # run from a Bowerbird checkout
assert ds(None, False, None, False) == ("standalone", "") and ds(None, False, None, True) == ("standalone", "vendored")
b = bb.build_info()
assert b["version"] == bb.VERSION and b["kind"] == "development" and b["detail"].startswith("git "), b  # these tests run from the checkout
code, out = cli("--version")
assert code == 0 and out.strip().startswith(f"bowerbird-mcp {bb.VERSION} (development, git "), out
assert cli("-V")[1] == out
loose = Path(tempfile.mkdtemp()) / "bowerbird_mcp.py"
loose.write_text((HERE / "bowerbird_mcp.py").read_text())
r = subprocess.run([sys.executable, str(loose), "--version"], capture_output=True, text=True, check=False)
assert r.stdout.strip() == f"bowerbird-mcp {bb.VERSION} (standalone script)", r  # a lone copy, not a git checkout
vend = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(vend)], check=True)
(vend / "bowerbird_mcp.py").write_text(loose.read_text())
r = subprocess.run([sys.executable, str(vend / "bowerbird_mcp.py"), "--version"], capture_output=True, text=True, check=False)
assert r.stdout.strip() == f"bowerbird-mcp {bb.VERSION} (standalone script, vendored)", r  # vendored into someone else's repo
assert bb.mcp._mcp_server.create_initialization_options().server_version.startswith(f"{bb.VERSION}+development.")  # what the client sees

# Mixed formats: the nearest bower.yaml overrides the ones above it, like an inherited ACL. A markdown collection with an ADR
# folder, and an OKF collection with an ADR folder.
saved_root, saved_fmt, saved_cfg = bb.ROOT, bb.OPTS["format"], bb.CFG_DIR
ADR = "# Use Vault\n\n## Status\n\nAccepted\n\n## Context\n\nWe need one place for secrets, said plainly here.\n"
adr_cfg = "format: adr\nseal: {exempt: [], exempt_status: []}\n"  # its globs start at its own folder


def mixed(root_format, files):
    d = Path(tempfile.mkdtemp()).resolve()
    for n, x in {"bower.yaml": f"format: {root_format}\n", **files}.items():  # a collection has a root bower.yaml; what lies below it overrides
        (d / n).parent.mkdir(parents=True, exist_ok=True)
        (d / n).write_text(x)
    bb.ROOT, bb.CFG_DIR = d, None
    bb.OPTS["format"] = root_format
    bb._SCOPES.clear()
    bb._POLICY.clear()
    return d


mk = mixed("markdown", {"notes/runbook.md": "# Runbook\n\nHow we roll back a deploy, step by step, with care.\n",
                        "decisions/bower.yaml": adr_cfg, "decisions/0001-use-vault.md": ADR})
assert (bb.fmt_of(mk / "notes/runbook.md"), bb.fmt_of(mk / "decisions/0001-use-vault.md")) == ("markdown", "adr")
assert {os.path.relpath(p, mk) for p in bb.source_files(mk)} == {"notes/runbook.md", "decisions/0001-use-vault.md"}
h = bb.passages("vault secrets")["hits"]
assert h and h[0]["file"] == "decisions/0001-use-vault.md" and h[0]["status"] == "Accepted"  # read as an ADR, in a markdown collection
assert {(f["file"], f["kind"]) for f in bb.signatures()["findings"]} == {("decisions/0001-use-vault.md", "unsigned"),
                                                                       ("notes/runbook.md", "unsigned")}
(mk / "decisions/bower.yaml").write_text("index: other.db\n")  # a folder may override what it holds and who reviews it, not the server's settings
bb._SCOPES.clear()
try:
    bb.scopes()
    raise AssertionError("a folder's bower.yaml set index")
except SystemExit as e:
    assert "belongs to the whole collection" in str(e) and "index" in str(e)

ok = mixed("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n',
                   "db.md": "---\ntype: Note\ndescription: The database.\n---\n# DB\n\nPostgres, decided in [ADR 1](adr/0001-use-vault.md), body long enough.\n",
                   "adr/bower.yaml": adr_cfg, "adr/0001-use-vault.md": ADR + "\nSee [the DB](../db.md).\n"})
assert (bb.fmt_of(ok / "db.md"), bb.fmt_of(ok / "adr/0001-use-vault.md")) == ("okf", "adr")
L = bb.lint(limit=0)
assert L["ok"] and not any(f["file"].startswith("adr/") for f in L["findings"]), L  # lint does not judge ADRs as OKF concepts
assert {(f["file"], f["kind"]) for f in bb.signatures()["findings"]} == {("adr/0001-use-vault.md", "unsigned"), ("db.md", "unsigned")}
li = bb.links("db.md")
assert li["out"][0]["exists"] and li["in"] == ["adr/0001-use-vault.md"]  # links cross the boundary both ways
h = bb.passages("vault secrets")["hits"]
assert h and h[0]["file"] == "adr/0001-use-vault.md" and h[0]["status"] == "Accepted"
assert not any(f["kind"] == "orphan" for f in L["findings"]), L  # an ADR that links to a concept keeps it from being an orphan


def okf_with_adr():
    return mixed("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n',
                         "db.md": "---\ntype: Note\ndescription: The database.\n---\n# DB\n\nPostgres, decided in [ADR 1](adr/0001-use-vault.md), body long enough.\n",
                         "adr/bower.yaml": adr_cfg, "adr/0001-use-vault.md": ADR + "\nSee [the DB](../db.md).\n"})


ok = okf_with_adr()
bb.index(apply=True, dirs=True)  # lists OKF concepts only: the ADR folder gets no index.md and is not in the root one
assert "adr" not in (ok / "index.md").read_text() and not (ok / "adr/index.md").exists() and "[DB](./db.md)" in (ok / "index.md").read_text()
ok = okf_with_adr()
bb.move("db.md", "notes/db.md", apply=True)  # links in an ADR follow a moved concept
assert "(../notes/db.md)" in (ok / "adr/0001-use-vault.md").read_text() and "(../notes/db.md)" not in (ok / "adr/0001-use-vault.md").read_text().replace("(../notes/db.md)", "", 1)
ok = okf_with_adr()
txt = (ok / "adr/0001-use-vault.md").read_text()
bb.ledger_put("adr/0001-use-vault.md", {"file": "adr/0001-use-vault.md", "sha256": bb.content_hash(txt, False), "by": "human:me", "at": bb.now(), "bowerbird": bb.VERSION})
bb.move("adr/0001-use-vault.md", "adr/0002-vault.md", apply=True)  # a moved ADR keeps its review, and the concept's link follows it
assert "adr/0002-vault.md" in (ok / "db.md").read_text() and list(bb.ledger_by_file()) == ["adr/0002-vault.md"]
assert bb.reviews({}, "adr/0002-vault.md", (ok / "adr/0002-vault.md").read_text(), bb.ledger_by_file())[1]
ok = okf_with_adr()
(ok / "other").mkdir()
(ok / "other/index.md").write_text('---\nokf_version: "0.2"\n---\n# Other\n')
bb._SCOPES.clear()
bb.migrate("db.md", "other", apply=True)  # a concept moved to another bundle: the ADR's link follows it
assert (ok / "other/db.md").exists() and "(../other/db.md)" in (ok / "adr/0001-use-vault.md").read_text()
bb.ROOT, bb.CFG_DIR = saved_root, saved_cfg
bb.OPTS["format"] = saved_fmt
bb._SCOPES.clear()
bb._POLICY.clear()

# serve: a human's front end. Real HTTP against a throwaway okf collection.
try:
    import http.client
    import socket
    import threading
    import urllib.parse

    import markdown

    import bowerbird_serve
except ImportError:
    print("skipped serve: markdown not installed")
else:
    sv = mixed("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n',
                       "a.md": "---\ntype: Note\ndescription: A.\ntags: [old, keep]\n---\n# A\n\nSee [B](b.md), body long enough.\n",
                       "b.md": "---\ntype: Note\ndescription: B.\ntags: [old]\n---\n# B\n\nBody.\n",
                       "c.md": "---\ntype: Note\ndescription: C.\n---\n# C\n\nAlone.\n"})
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        port = so.getsockname()[1]
    here_ = os.getcwd()  # serve moves to the collection root, and the tests go on from where they were
    os.environ["XDG_CACHE_HOME"] = tempfile.mkdtemp()  # the pid file, kept out of the real cache
    threading.Thread(target=bowerbird_serve.run, args=(bb, port, True), daemon=True).start()
    import time
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)

    def hit(method, path, form=None, host=None, origin=None):
        c = http.client.HTTPConnection("127.0.0.1", port)
        h = {"Host": host or f"127.0.0.1:{port}", **({"Origin": origin} if origin else {})}
        body = None
        if form is not None:
            body = urllib.parse.urlencode(form)
            h["Content-Type"] = "application/x-www-form-urlencoded"
        c.request(method, path, body, h)
        r = c.getresponse()
        return r.status, r.read().decode(), r.getheader("Location")

    def token():
        return re.search(r'name=_t value="([^"]+)"', hit("GET", "/a.md")[1]).group(1)

    def put_(path, **form):
        return hit("POST", path, {"_t": token(), **form})

    assert hit("GET", "/a.md")[0] == 200 and "✎" in hit("GET", "/a.md")[1]
    assert hit("GET", "/a.md", host="evil.example:80")[0] == 403  # DNS rebinding
    mk_ = lambda dir, name: put_("/_new", dir=dir, name=name + "/")  # a trailing / makes a folder
    assert hit("POST", "/_new", {"dir": "", "name": "x/"})[0] == 403 and not (sv / "x").exists()  # no token
    assert hit("POST", "/_new", {"_t": token(), "dir": "", "name": "x/"}, origin="http://evil.example")[0] == 403
    assert mk_("", "../out")[0] == 400 and mk_("", ".git")[0] == 400 and put_("/_new", dir="", name="")[0] == 400
    assert mk_("notes", "sub")[0] == 303 and (sv / "notes/sub").is_dir()
    home = hit("GET", "/")[1]
    assert "notes/" in home and "/_new?dir=notes/sub" in home.replace("%2F", "/") and "/_new?dir=\"" in home  # an empty folder shows, each folder ends in + New file
    npg = hit("GET", "/_new?dir=notes")[1]
    assert "notes/" in npg and "form=newf" in npg and "<textarea" in npg and ">Save</button>" in npg and ">Cancel</a>" in npg
    t = bb.new_template(sv / "notes")  # the box starts as the folder's template, by its format
    assert t in {bb.TEMPLATES["okf"], bb.TEMPLATES["markdown"], bb.TEMPLATES["adr"].replace("{today}", __import__("datetime").date.today().isoformat()), ""} and "{today}" not in t
    assert bb.new_template(sv / "decisions") .startswith("---\nstatus: proposed") or bb.OPTS["format"] != "markdown"  # a path through decisions is an ADR
    st, tp, _ = put_("/_new", dir="notes", name="keep", tpl="adr", use="1")  # Use template: refills the box, keeps the name, saves nothing
    assert st == 200 and "Considered Options" in tp and 'value="keep"' in tp and not (sv / "notes/keep.md").exists()
    assert put_("/_new", dir="notes", name="fresh", text="---\ntype: Note\n---\n# Fresh\n")[0] == 303 and (sv / "notes/fresh.md").exists()  # Save writes dir/name.md
    assert put_("/_new", dir="notes", name="folder2/")[0] == 303 and (sv / "notes/folder2").is_dir()  # a trailing / is a folder
    assert put_("/_new", dir="", name="a", text="x")[0] == 409 and "x" not in (sv / "a.md").read_text()[:5]  # a.md exists
    assert put_("/_new", dir="", name="", text="x")[0] == 400
    pg = hit("GET", "/a.md")[1]
    aside = pg[pg.index("<aside>"):]
    # a fact block is its claim and a badge that links to a Facts tab, which holds the bibliography; a page's signers and "N of M" are shown
    (sv / "facts.md").write_text("---\ntype: Note\ndescription: F.\n---\n# Facts\n\nOne-liner: [fact.url](https://x.test/b) short claim [fact.end] and [fact.until](2999-01-01) the freeze is on [fact.end].\n")
    fpg_ = hit("GET", "/facts.md")[1]
    assert 'class="fact-badge" data-state="unchecked" href="#fact-1"' in fpg_ and "Facts (2)" in fpg_ and 'id=t-facts' in fpg_ and 'id="fact-2"' in fpg_ and "not yet checked" in fpg_
    assert "[fact." not in fpg_.split("<aside>")[0].split("<main>")[1] and "Facts (" not in pg  # no tag shows, and no tab on a page with no facts
    st_, js_, _ = hit("GET", "/_api/status?f=facts.md")  # the same as data, for a tool that draws its own badges
    api = json.loads(js_)
    assert st_ == 200 and api["file"] == "facts.md" and api["seal"]["state"] == "unsealed" and [f["kind"] for f in api["facts"]] == ["url", "until"]
    assert hit("GET", "/_api/status?f=../x.md")[0] == 400 and hit("GET", "/_api/status?f=.env")[0] == 400 and hit("GET", "/_api/status", host="evil.example:80")[0] == 403
    (sv / "signed.md").write_text("---\ntype: Note\ndescription: S.\nverified:\n  - {by: human:ann, at: '2026-11-23T10:00:00Z', comment: checked the steps}\n"
                                  "  - {by: human:bo, at: '2026-11-23T10:00:05Z'}\n---\n# S\n\nBody.\n")
    saved_seal = dict(bb.OPTS["seal"])
    bb.OPTS["seal"] = {**saved_seal, "extensions": True, "quorum": 3}
    bb._POLICY.clear()
    spg_ = hit("GET", "/signed.md")[1]
    assert "signed 2 of 3: ann (checked the steps), bo" in spg_ and "signed: 2 of 3 (ann, bo)" in spg_, spg_[spg_.find("signed"):][:200]  # the page's head and the modal
    bb.OPTS["seal"] = saved_seal
    bb._POLICY.clear()
    (sv / "facts.md").unlink()
    (sv / "signed.md").unlink()
    assert "✎" in aside and "⚙" in aside and "✎" not in pg[:pg.index("<aside>")].split("<main>")[1]  # the pencil and gear live in the right pane

    # edit: saves, and refuses to overwrite a page that changed under the editor
    base = re.search(r'name=base value="([^"]+)"', hit("GET", "/_edit?f=c.md")[1]).group(1)
    assert put_("/_save", file="c.md", base=base, text=(sv / "c.md").read_text().replace("Alone", "Edited"))[0] == 303
    assert "Edited" in (sv / "c.md").read_text() and "generated" not in (sv / "c.md").read_text()
    assert put_("/_save", file="c.md", base=base, text="lost")[0] == 409 and "lost" not in (sv / "c.md").read_text()
    assert put_("/_save", file="../escape.md", base="", text="x")[0] == 400 and put_("/_save", file="x.txt", base="", text="x")[0] == 400
    assert put_("/_save", file="notes/new.md", base=bb.hashlib.sha256(b"").hexdigest(), text="---\ntype: Note\n---\n# New\n")[0] == 303 and (sv / "notes/new.md").exists()

    # the editor: Save, Lint (the unsaved text, nothing written) and Cancel
    ed = hit("GET", "/_edit?f=a.md")[1]
    assert ">Save</button>" in ed and ">Lint</button>" in ed and ">Cancel</a>" in ed
    before = (sv / "a.md").read_text()
    bad = before.replace("type: Note", "type: ")  # no type: the unsaved text is wrong, the file on disk is not
    lt = put_("/_editlint", file="a.md", text=bad)
    assert lt[0] == 200 and "not saved" in lt[1] and "type" in lt[1] and (sv / "a.md").read_text() == before and bb.read is not None
    assert "ok True" in put_("/_editlint", file="a.md", text=before)[1]  # its own warnings (orphan, stub), no errors
    assert "save it once" in put_("/_editlint", file="notes/brandnew.md", text="# x")[1]

    # a form built from a tool: preview writes nothing, Confirm writes; only the few tools a button leads to are offered
    (sv / "made.md").write_text("---\ntype: Note\ndescription: By hand.\n---\n# Made\n")
    st, page_, _ = put_("/_tool/move", file="made.md", to="moved.md")
    assert st == 200 and "Confirm" in page_ and (sv / "made.md").exists() and not (sv / "moved.md").exists()
    put_("/_tool/move", file="made.md", to="moved.md", _apply="1")
    assert (sv / "moved.md").exists() and not (sv / "made.md").exists()
    put_("/_tool/move", file="moved.md", to="made.md", _apply="1")
    assert all(x not in "".join(p.read_text() for p in sv.rglob("*.md")) for x in ("generated:",))  # nothing here stamps `generated`
    assert "class=repo" not in hit("GET", "/")[1]  # no web remote here: no repository link
    assert hit("GET", "/_tool/create")[0] == 200 and "New knowledgebase" in hit("GET", "/")[1]  # the one tool every other surface had
    assert hit("GET", "/_tool/move")[0] == 200 and hit("GET", "/_tool/archive")[0] == 200 and hit("GET", "/_tool/unarchive")[0] == 200 and "Unarchive" in hit("GET", "/")[1]
    assert all(put_(f"/_tool/{n}", file="made.md")[0] == 400 for n in ("seal", "by", "create", "set", "provenance"))  # the CLI's, not offered
    assert hit("GET", "/_tools")[0] == 400  # the page is gone
    assert "Lint all" in hit("GET", "/a.md")[1] and "/_tags" in hit("GET", "/a.md")[1]

    # delete: refused while linked, ledger entry goes with the file
    assert put_("/_delete", f="b.md")[0] == 400 and (sv / "b.md").exists()
    assert put_("/_delete", f="c.md")[0] == 303 and not (sv / "c.md").exists()
    (sv / "d.md").write_text("---\ntype: Note\ndescription: Only the index lists it.\n---\n# D\n")
    with open(sv / "index.md", "a") as f_:
        f_.write("\n* [d](./d.md)\n")
    assert put_("/_delete", f="d.md")[0] == 303 and not (sv / "d.md").exists()  # index.md and log.md links do not block a delete

    # tags: rename previews, then applies across pages
    assert "old" in hit("GET", "/_tags")[1]
    assert "+tags" in put_("/_retag", old="old", new="new")[1].replace(" ", "") or "new" in put_("/_retag", old="old", new="new")[1]
    assert "tags: [old, keep]" in (sv / "a.md").read_text()
    put_("/_retag", old="old", new="new", _apply="1")
    assert "old" not in (sv / "a.md").read_text() and "new" in (sv / "b.md").read_text()
    assert put_("/_settags", file="b.md", tags="x, y")[0] == 303 and "x" in (sv / "b.md").read_text()

    # lint
    assert hit("GET", "/_lint")[0] == 200 and hit("GET", "/_lint?f=a.md")[0] == 200

    # seal: the modal, with the MCP prompt's own words; nothing is recorded unless the box is ticked, and the text has not moved
    dlg = hit("GET", "/a.md")[1]
    assert "I reviewed this concept and confirm it is accurate" in dlg and "Confirm seal: a.md" in dlg
    shaw = re.search(r'name=sha value="([^"]+)"', dlg).group(1)
    assert put_("/_seal", file="a.md", sha=shaw, reviewer="me")[0] == 303 and "verified" not in (sv / "a.md").read_text()  # not confirmed
    assert put_("/_seal", file="a.md", sha="0" * 64, reviewer="me", confirm="on")[0] == 400  # changed while open
    assert put_("/_seal", file="a.md", sha=shaw, reviewer="has space", confirm="on")[0] == 400
    assert put_("/_seal", file="a.md", sha=shaw, reviewer="me", confirm="on")[0] == 303
    assert "human:me" in (sv / "a.md").read_text() and bb.ATTEST == ""
    assert "sealed" in hit("GET", "/a.md")[1]
    put_("/_save", file="a.md", base=re.search(r'name=base value="([^"]+)"', hit("GET", "/_edit?f=a.md")[1]).group(1), text=(sv / "a.md").read_text() + "\nMore.\n")
    assert "seal broken by edit" in hit("GET", "/a.md")[1]  # an edit stales the seal, as anywhere

    # search: passages, concepts, meaning and tags, each its own mode
    sj = lambda mode, q: json.loads(hit("GET", f"/_search.json?mode={mode}&q={urllib.parse.quote(q)}")[1])
    assert any(r.get("href") == "/a.md" for r in sj("passages", "enough")) and any(r.get("href") == "/made.md" for r in sj("concepts", "Made"))  # a page with no body has no passage
    assert "matched" in sj("concepts", "Made")[0]["sub"] and "title" in sj("concepts", "Made")[0]["sub"]
    assert [r["href"] for r in sj("tags", "x")] == ["/b.md"] and "tags: x" in sj("tags", "x")[0]["sub"]  # a substring of a tag
    assert sj("tags", "zzz") == []
    assert "meaning search is off" in sj("semantic", "Made")[0]["error"]  # semantic: false here
    assert bb.OPTS["semantic"] is False  # the keyword mode's switch is put back
    assert "value=semantic" not in hit("GET", "/a.md")[1] and "mode=semantic" not in hit("GET", "/_search?q=x")[1]  # off: not offered
    bb.OPTS["semantic"] = True
    assert "value=semantic" in hit("GET", "/a.md")[1] and "mode=semantic" in hit("GET", "/_search?q=x")[1]  # on: offered
    bb.OPTS["semantic"] = False
    assert hit("GET", "/_search?mode=concepts&q=Made")[0] == 200 and "mode=tags" in hit("GET", "/_search?mode=concepts&q=Made")[1]
    assert 'id=mode' in hit("GET", "/a.md")[1] and sj("nonsense", "enough")  # an unknown mode is passages

    # status and the Stop button: no token, no stop; with one the server goes and the pid file with it
    with contextlib.redirect_stdout(io.StringIO()) as out_:
        assert bowerbird_serve.status(port) == 0
    assert "running" in out_.getvalue() and f":{port}/" in out_.getvalue()
    assert hit("POST", "/_stop", {})[0] == 403 and bowerbird_serve.listening(port)
    assert put_("/_stop")[0] == 200
    for _ in range(50):
        if not bowerbird_serve.listening(port):
            break
        time.sleep(0.1)
    assert not bowerbird_serve.listening(port) and not bowerbird_serve.pidfile(port).exists()
    with contextlib.redirect_stdout(io.StringIO()) as out_:
        assert bowerbird_serve.status(port) == 1
    assert "not running" in out_.getvalue()
    # the verbs: stop with nothing there is not an error; start refuses a port something else holds, and leaves it alone
    with contextlib.redirect_stdout(io.StringIO()) as out_:
        assert bowerbird_serve.stop(port) == 0 and bb.cli(["serve", "stop", str(port)]) == 0
        assert bb.cli(["serve", "status", str(port)]) == 1
        assert bb.cli(["serve"]) == 0 and bb.cli(["serve", str(port)]) == 0  # bare: help, and nothing is started
    assert "nothing running" in out_.getvalue() and "not running" in out_.getvalue() and "serve start|stop|restart|status [port]" in out_.getvalue() and "--config" in out_.getvalue()
    assert not bowerbird_serve.listening(port)
    with socket.socket() as other_:
        other_.bind(("127.0.0.1", 0))
        other_.listen(1)
        op_ = other_.getsockname()[1]
        with contextlib.redirect_stdout(io.StringIO()) as out_:
            assert bowerbird_serve.start(bb, op_) == 1 and bowerbird_serve.stop(op_) == 0
        assert "in use by something else" in out_.getvalue() and bowerbird_serve.listening(op_)
    with contextlib.redirect_stderr(io.StringIO()) as err_:
        assert bb.cli(["serve", "bogus"]) == 2
    assert "start|stop|restart|status" in err_.getvalue()
    assert os.getcwd() == str(sv)  # started from the repo, searched the throwaway collection: not the cwd's bundle
    os.chdir(here_)

    # serve over a seal-only collection: hidden files and links are 404 (GET and HEAD), and `/` is a shell without an index.md
    prev_ = (bb.ROOT, bb.OPTS["format"], dict(bb.OPTS["seal"]))
    so_ = mixed("seal-only", {"bower.yaml": 'format: seal-only\nseal: {exempt: ["docs/gen.md", "src/gen_*.py"]}\n', ".env": "SECRET=1\n",
                              "docs/gen.md": "# Generated\n\nBuilt from the code.\n", "docs/hand.md": "# Hand\n\nWritten by a person.\n",
                              ".waxseals.yaml": "[]\n", "sub/.hidden": "x\n", "sub/ok.txt": "fine\n", "src/app.py": "def add(a, b):\n    return a + b\n"})
    bb.OPTS["seal"] = {"exempt": ["docs/gen.md", "src/gen_*.py"], "exempt_status": []}
    (so_ / "src/blob.py").write_bytes(b"\xff\xfe\x00")
    (so_ / "src/big.py").write_text("x = 1\n" * 100_000)  # over the 512 KB cap
    (so_ / "link.py").symlink_to(so_ / "src/app.py")
    (so_ / "linkdir").symlink_to(so_ / "src", target_is_directory=True)
    assert bb.mark_derived(so_ / "docs/gen.md", "gen.py") and not bb.mark_derived(so_ / "docs/gen.md", "gen.py")  # a generator records it, once
    with socket.socket() as so2:
        so2.bind(("127.0.0.1", 0))
        port = so2.getsockname()[1]
    threading.Thread(target=bowerbird_serve.run, args=(bb, port, True), daemon=True).start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    assert hit("HEAD", "/src/blob.py")[0] == 404 and hit("HEAD", "/src/big.py")[0] == 404  # a HEAD first, before any scan: no leak of a skipped file
    for path in ("/.env", "/sub/.hidden", "//.env", "/.%65nv", "/%2e%2e/etc/passwd", "/.waxseals.yaml", "/.git/config", "/link.py", "/linkdir/app.py", "/linkdir/"):
        assert hit("GET", path)[0] == 404 and hit("HEAD", path)[0] == 404, path
    assert hit("GET", "/sub/ok.txt")[0] == 200 and "ok.txt" in hit("GET", "/sub/")[1] and ".hidden" not in hit("GET", "/sub/")[1]  # a listing drops dotfiles
    assert hit("GET", "/")[0] == 200 and "<nav>" in hit("GET", "/")[1]  # no index.md: the shell, not a bare listing
    assert "link.py" not in hit("GET", "/")[1] and "linkdir" not in hit("GET", "/")[1]  # a link is not listed
    # a seal-only .py is listed, and renders read-only with line numbers and the Seal modal
    home_ = hit("GET", "/")[1]
    assert "app.py" in home_ and 'data-seal="unsealed"' in home_ and "blob.py" not in home_ and "big.py" not in home_
    st_, pg_, _ = hit("GET", "/src/app.py")
    assert st_ == 200 and "<dialog id=sealdlg>" in pg_ and "Confirm seal: src/app.py" in pg_ and "unsealed" in pg_ and "✎" not in pg_  # no editor for code
    assert hit("GET", "/src/blob.py")[0] == 404 and hit("GET", "/src/big.py")[0] == 404  # not shown; the CLI still covers them
    # derived from the code (a generator's ledger line): a fourth state, with nothing to seal; `seal.exempt` alone says nothing about who made a file
    assert bb.derived(so_ / "docs/gen.md") and not bb.derived(so_ / "docs/hand.md") and not bb.derived(so_ / "src/app.py")
    assert 'data-seal="derived"' in home_ and 'data-seal="unsealed"' in home_
    gen_ = hit("GET", "/docs/gen.md")[1]
    assert "derived from the code" in gen_ and "<dialog id=sealdlg>" not in gen_ and "Seal…" not in gen_
    assert "<dialog id=sealdlg>" in hit("GET", "/docs/hand.md")[1]  # a page the policy requires still has its modal
    (so_ / "src/gen_tbl.py").write_text("T = {}\n")  # a non-markdown file built from the code: shown, marked, never sealed
    (so_ / "src/gen_other.py").write_text("U = {}\n")  # exempt too, but no generator recorded it: not derived, not listed
    assert not bb.derived(so_ / "src/gen_tbl.py") and bb.mark_derived(so_ / "src/gen_tbl.py", "gen.py") and not bb.derived(so_ / "src/gen_other.py")
    st_, gp_, _ = hit("GET", "/src/gen_tbl.py")
    assert bb.derived(so_ / "src/gen_tbl.py") and st_ == 200 and "derived from the code" in gp_ and "<dialog id=sealdlg>" not in gp_ and "Seal…" not in gp_
    assert "gen_tbl.py" not in [p.name for p in bb.sealonly_files()] and "gen_tbl.py" in [p.name for p in bb.derived_files()]
    assert "gen_other.py" not in [p.name for p in bb.sealonly_files() + bb.derived_files()]
    assert [e["derived"] for e in bb.ledger_by_file()["src/gen_tbl.py"]] == ["gen.py"] and all(e["by"] == "generator:gen.py" for e in bb.ledger_by_file()["src/gen_tbl.py"])  # `by`: an older reader needs one
    assert not bb.reviews({}, "src/gen_tbl.py", "T = {}\n", bb.ledger_by_file())[0]  # a generator's line is no review
    (so_ / "src/gen_tbl.py").write_text("T = {'edited': 1}\n")  # edited by hand: the line no longer matches
    assert not bb.derived(so_ / "src/gen_tbl.py")
    (so_ / "src/gen_tbl.py").write_text("T = {}\n")
    tok_ = re.search(r'name=_t value="([^"]+)"', home_).group(1)
    st_, body_, _ = hit("POST", "/_seal", {"_t": tok_, "file": "docs/gen.md", "confirm": "on", "reviewer": "you", "sha": "x"})
    assert st_ == 400 and "derived from the code" in body_  # refused: no seal is recorded for it
    try:
        import pygments  # noqa: F401
    except ImportError:
        pass
    else:
        assert 'class="highlight"' in pg_ and pg_.count('class="linenos"') == 2 and "prefers-color-scheme:dark" in pg_
    sys.modules["pygments"] = None  # pygments absent: plain numbered <pre>
    try:
        plain_ = hit("GET", "/src/app.py")[1]
    finally:
        del sys.modules["pygments"]
    assert "highlight" not in plain_ and plain_.count("<span class=l>") == 2 and "return a + b" in plain_
    with contextlib.redirect_stdout(io.StringIO()) as out_:
        assert bowerbird_serve.start(bb, port) == 0  # ours is already there: a no-op that says so
    assert "running" in out_.getvalue()
    assert hit("POST", "/_stop", {"_t": re.search(r'name=_t value="([^"]+)"', hit("GET", "/")[1]).group(1)})[0] == 200
    os.chdir(here_)
    bb.ROOT, bb.OPTS["format"], bb.OPTS["seal"] = prev_

# bowers: the root lists the folders that carry their own bower.yaml, and only those are its overrides. A bower run on its own is
# its own collection; one run inside the collection finds the root that lists it. --config takes a folder, a relative path and `~`.
def tree(files):
    d = Path(tempfile.mkdtemp()).resolve()
    for n, x in files.items():
        (d / n).parent.mkdir(parents=True, exist_ok=True)
        (d / n).write_text(x)
    return d


bw_saved = (bb.ROOT, bb.CFG_DIR, bb.OPTS["format"], os.getcwd(), os.environ.get("HOME"))
bw = tree({"bower.yaml": "format: markdown\nbowers: [docs, adr/*]\n", "docs/bower.yaml": "format: okf\nroles: [read]\n", "docs/a.md": "# A\n",
           "adr/one/bower.yaml": "format: adr\n", "adr/two/x.md": "# no config\n", "stray/bower.yaml": "format: skos\n", "stray/b.md": "# B\n"})
assert bb.load_config(bw / "docs")[0] == bw and bb.load_config(bw / "adr/one")[0] == bw  # a listed bower finds the root that lists it
assert bb.load_config(bw / "stray")[0] == bw / "stray"  # an unlisted one is its own collection
bb.ROOT, bb.CFG_DIR, bb.OPTS["format"] = bw, bw, "markdown"
bb._SCOPES.clear()
assert {d for d, _ in bb.scopes()} == {bw / "docs", bw / "adr/one"} and "roles" not in dict(bb.scopes())[bw / "docs"]  # the root decides roles
assert (bb.fmt_of(bw / "docs/a.md"), bb.fmt_of(bw / "adr/one/y.md"), bb.fmt_of(bw / "stray/b.md")) == ("okf", "adr", "markdown")
(bw / "bower.yaml").write_text("format: markdown\nbowers: [docs, nope]\n")
bb._SCOPES.clear()
try:
    bb.scopes()
    raise AssertionError("a bowers entry that names nothing must stop")
except SystemExit as e_:
    assert "bowers entry 'nope'" in str(e_)
(bw / "bower.yaml").write_text("format: markdown\n")  # no bowers key: the older rule, every bower.yaml below is an override
bb._SCOPES.clear()
try:
    bb.scopes()  # the older rule still refuses a whole-collection key in a nested file (docs/bower.yaml sets roles)
    raise AssertionError("roles in a nested bower.yaml must stop the older rule")
except SystemExit as e_:
    assert "belongs to the whole collection" in str(e_)
bb._SCOPES.clear()
(bw / "docs/bower.yaml").write_text("format: okf\n")
assert {d for d, _ in bb.scopes()} == {bw / "docs", bw / "adr/one", bw / "stray"}
for given in (str(bw), str(bw / "bower.yaml")):
    assert bb.load_config(Path("/"), given)[0] == bw
os.chdir(bw.parent)
os.environ["HOME"] = str(bw.parent)
assert bb.load_config(Path("/"), bw.name)[0] == bw and bb.load_config(Path("/"), f"~/{bw.name}")[0] == bw  # relative, and ~
os.chdir(bw_saved[3])
if bw_saved[4] is None:
    del os.environ["HOME"]
else:
    os.environ["HOME"] = bw_saved[4]
bb.ROOT, bb.CFG_DIR, bb.OPTS["format"] = bw_saved[:3]
bb._SCOPES.clear()
bb._POLICY.clear()
# with no root file and no repository, what lies below is not ours: nothing is scanned
lone = tree({"deep/bower.yaml": "format: skos\n", "deep/c.md": "# C\n"})
bb.ROOT = lone
bb._SCOPES.clear()
assert bb.scopes() == []
bb.ROOT = bw_saved[0]
bb._SCOPES.clear()

# new: a document from a template. The folder's bower.yaml picks it, template= overrides, and an existing file is refused.
nw_saved = (bb.ROOT, bb.CFG_DIR, bb.OPTS["format"])
nw = mixed("markdown", {"decisions/bower.yaml": "format: adr\n", "notes/a.md": "# A\n"})
R = bb.new("notes/b")
assert R["template"] == "markdown" and R["file"] == "notes/b.md" and (nw / "notes/b.md").read_text() == "---\ntitle: b\ntags: []\n---\n\n# b\n", R
R = bb.new("decisions/0002-use-x", title="Use X")
t_ = (nw / "decisions/0002-use-x.md").read_text()
assert R["template"] == "adr" and "# Use X" in t_ and "## Context and Problem Statement" in t_ and "status: proposed" in t_ and "{today}" not in t_, t_
assert "type: Reference" in (nw / "notes/c.md").read_text() if bb.new("notes/c", template="okf")["template"] == "okf" else False
assert "exists" in raises(bb.new, "notes/b") and "template 'rst'" in raises(bb.new, "notes/z", template="rst")
with contextlib.redirect_stdout(io.StringIO()):
    assert bb.cli(["new", "notes/d", "-t", "adr", "-T", "Dee"]) == 0  # the short flags: -t template, -T title
assert "# Dee" in (nw / "notes/d.md").read_text() and "decision-makers" in (nw / "notes/d.md").read_text()
bb.ROOT, bb.CFG_DIR, bb.OPTS["format"] = nw_saved
bb._SCOPES.clear()
bb._POLICY.clear()

# A bare `bowerbird-mcp` at a terminal: the help, then an offer to make a knowledgebase where there is none; "n" writes nothing.
class Tty(io.StringIO):
    def isatty(self):
        return True


wz_saved = (bb.ROOT, bb.CFG_DIR, bb.OPTS["format"], sys.stdin, bb.out_terminal, bb.user_id)
wz = Path(tempfile.mkdtemp()).resolve()
(wz / "a.md").write_text("# A\n\nHello there.\n")
bb.ROOT, bb.CFG_DIR, bb.OPTS["format"], bb.out_terminal, bb.user_id = wz, None, "markdown", (lambda: True), (lambda: "tester")
bb._SCOPES.clear()
bb._POLICY.clear()
sys.stdin = Tty("n\n")
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert bb.welcome() == 0
assert "not a knowledgebase yet" in wo.getvalue() and "Knowledge" in wo.getvalue() and not (wz / "bower.yaml").exists()
sys.stdin = Tty("y\nTest notes.\nmarkdown\n")  # create it: about, then the format (the folder's guess is offered)
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert bb.welcome() == 0
wc = (wz / "bower.yaml").read_text()
assert "about: Test notes." in wc and "format: markdown" in wc and (wz / ".mcp.json").is_file() and "Done." in wo.getvalue(), wo.getvalue()
bb.CFG_DIR = wz  # now it is a collection: the help only, no offer
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert bb.welcome() == 0
assert "not a knowledgebase yet" not in wo.getvalue()
bb.ROOT, bb.CFG_DIR, bb.OPTS["format"], sys.stdin, bb.out_terminal, bb.user_id = wz_saved
bb._SCOPES.clear()
bb._POLICY.clear()


# fact blocks: [fact.url](address) and [fact.mcp](server key) spans in a document, the state of checking them in .facts.yaml beside it, a drift ending
# the reviews before it, and `factcheck --fetch` fetching a page and calling a declared MCP tool for a fresh result.
import builtins
import functools
import http.server
import threading

import bowerbird_facts as F

fb, fp = F.parse("[fact.url](https://x.test/p)\n\nWords  here.\n\n[fact.end] and [fact.mcp](jira K-1) is open [fact.end]\n```\n[fact.url](hidden) x [fact.end]\n```\n")
assert [(b.kind, b.source) for b in fb] == [("url", "https://x.test/p"), ("mcp", "jira K-1")] and fp == []
assert fb[0].claim == "Words  here." and (fb[0].line, fb[0].end_line) == (1, 5) and fb[1].claim == "is open"  # the source is not part of the claim
for bad, why in (("[fact.url](https://x)\nwords", "unclosed_fact"), ("words [fact.end]", "stray_fact_end"), ("[fact.zip](a) b c [fact.end]", "unknown_fact_kind"),
                 ("[fact.url](nope)\n\nw\n\n[fact.end]", "bad_fact"), ("[fact.url](https://x)\n[fact.end]", "bad_fact"), ("[fact.mcp](jira) is open [fact.end]", "bad_fact"),
                 ("[fact.url] https://x w [fact.end]", "bad_fact"),  # the older form, with the address after the tag: the parentheses are required now
                 ("[fact.url](https://x)\nw\n[fact.url](https://y)\nv\n[fact.end]", "unclosed_fact")):
    assert why in {p[1] for p in F.parse(bad)[1]}, (bad, F.parse(bad)[1])
assert F.norm("`A`  b\n**C**") == "a b c" and F.fact_id("url", "u", "A  b") == F.fact_id("url", "u", "a b") != F.fact_id("url", "u", "a c")
assert F.check_literal("One.\n\nTwo.", "x ONE. y") == (1, 2) and F.check_literal("`one`", "One") == (1, 1)
lk, lk_saved = Path(tempfile.mkdtemp()).resolve(), bb.ROOT
bb.ROOT = lk
create(apply=True, holds="okf", about="facts", user="u")
(lk / "a.md").write_text("---\ntype: Note\ndescription: d\n---\n# A\n\n[fact.url](https://x.test/p)\n\nwords\n")  # never closed
assert any(f["kind"] == "unclosed_fact" and f["severity"] == "error" for f in bb.lint(bundle=".", limit=0)["findings"])
(lk / "a.md").write_text("---\ntype: Note\ndescription: d\n---\n# A\n\n[fact.url](https://x.test/p)\n\nwords\n\n[fact.end]\n\n[fact.mcp](jira K-1) is open [fact.end]\n")
undeclared = [f for f in bb.lint(bundle=".", limit=0)["findings"] if f["file"] == "a.md" and f["kind"] == "undeclared_fact_source"]
assert undeclared and undeclared[0]["severity"] == "warning" and "jira" in undeclared[0]["message"]
assert not any(f["kind"].endswith("_fact") or f["kind"].startswith(("unclosed", "stray")) for f in bb.lint(bundle=".", limit=0)["findings"])
bb.ROOT = lk_saved

fk = Path(tempfile.mkdtemp()).resolve()
site = fk / "site"
site.mkdir()
(site / "page.html").write_text("<html><style>x{}</style><body><p>(jenkins_url)/safeRestart - Allows all   running jobs to complete.</p>"
                                "<p>(jenkins_url)/restart - Forces a restart without waiting for builds to complete.</p></body></html>")
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
(fk / "status.txt").write_text("Open\n")
(fk / "fakejira.py").write_text("import json, os\nfrom mcp.server.fastmcp import FastMCP\nm = FastMCP('fakejira')\n@m.tool()\n"
                                "def get_issue(issue_key: str) -> str:\n    n = open(os.environ['STATUS_FILE']).read().strip()\n"
                                "    return json.dumps({'key': issue_key, 'fields': {'status': {'name': n}, 'updated': os.urandom(4).hex()}})\nm.run()\n")
(fk / ".mcp.json").write_text(json.dumps({"mcpServers": {"jira": {"command": sys.executable, "args": [str(fk / "fakejira.py")],
                                                                  "env": {"STATUS_FILE": str(fk / "status.txt")}}}}))
(fk / "bower.yaml").write_text("format: markdown\n")
doc = (f"# Jenkins\n\n[fact.url](http://127.0.0.1:{srv.server_address[1]}/page.html)\n\n`(jenkins_url)/safeRestart` - Allows all running jobs to complete.\n\n"
       "(jenkins_url)/restart - Forces a restart without waiting for builds to complete.\n\n[fact.end]\n\nThe ticket: [fact.mcp](jira INFRA-1) is open [fact.end]\n")
(fk / "notes.md").write_text(doc)
saved = (bb.ROOT, bb.CFG, bb.CLI, bb.at_terminal, builtins.input, dict(bb.OPTS))
bb.ROOT, bb.CLI, bb.OPTS["format"] = fk, True, "markdown"
bb.CFG = {"facts": {"mcp": {"jira": {"tool": "get_issue", "arg": "issue_key", "watch": "fields.status.name"}}}}
try:
    assert [(r["line"], r["kind"], r["status"]) for r in bb.factcheck()["blocks"]] == [(3, "url", "unchecked"), (11, "mcp", "unchecked")]  # information only
    assert not (fk / ".facts.yaml").exists()
    bb.at_terminal, builtins.input = (lambda: True), (lambda *a: "n")
    assert bb.factcheck(fetch=True)["note"] == "nothing run" and not (fk / ".facts.yaml").exists()  # shown, asked, declined
    builtins.input = lambda *a: "y"
    r = bb.factcheck(fetch=True)
    assert [(x["kind"], x["status"], x["method"]) for x in r["checked"]] == [("url", "checked", "same words"), ("mcp", "checked", "baseline recorded")] and r["drifted"] == 0, r
    assert [x["status"] for x in bb.factcheck()["blocks"]] == ["checked", "checked"] and "value: Open" in (fk / ".facts.yaml").read_text()
    assert [x["method"] for x in bb.factcheck(fetch=True)["checked"]] == ["same words", "same value"]  # the result's other fields (updated) are not watched
    # an agent (no terminal) runs the same checks: no question is asked, and the plan comes back with the result
    bb.at_terminal, builtins.input = (lambda: False), (lambda *a: (_ for _ in ()).throw(AssertionError("an agent was asked")))
    r = bb.factcheck(fetch=True)
    assert [x["method"] for x in r["checked"]] == ["same words", "same value"] and len(r["ran"]) == 2 and "notes.md:3" in r["ran"][0], r
    assert bb.factcheck(file="notes.md", id=bb.fact_rows("notes.md")[0]["id"])["checked"][0]["status"] == "checked"  # one fact by id, a page: fine for an agent too
    bb.at_terminal, builtins.input = (lambda: True), (lambda *a: "y")
    # a seal on the file, then a drift: the seal stops holding; one made after the drift holds
    text = (fk / "notes.md").read_text()
    sealed = {"file": "notes.md", "sha256": bb.content_hash(text, False), "by": "human:t", "at": bb.now(), "bowerbird": bb.VERSION}
    bb.ledger_put("notes.md", sealed)
    assert len(bb.reviews({}, "notes.md", text, bb.ledger_by_file())[1]) == 1
    (fk / "status.txt").write_text("Closed\n")
    r = bb.factcheck(fetch=True)
    assert [(x["kind"], x["status"]) for x in r["checked"]] == [("url", "checked"), ("mcp", "drifted")] and r["drifted"] == 1 and "Closed" in r["checked"][1]["method"], r
    assert bb.REG["factcheck"].exit(r) == 1 and bb.REG["factcheck"].exit({"drifted": 0}) == 0
    assert bb.reviews({}, "notes.md", text, bb.ledger_by_file())[1] == [] and bb.drift_of("notes.md", {}) is not None
    assert any(f["kind"] == "stale_signature" and "fact drifted" in f["message"] for f in bb.signatures("")["findings"])
    time.sleep(1.1)
    bb.ledger_put("notes.md", {**sealed, "at": bb.now()})  # a human reviews it again, after the drift
    assert len(bb.reviews({}, "notes.md", text, bb.ledger_by_file())[1]) == 1
    # the page changes: the block drifts, and the same check by meaning needs the extra and `semantic: true`
    (site / "page.html").write_text((site / "page.html").read_text().replace("Forces a restart without waiting", "Does something else"))
    assert bb.factcheck(fetch=True)["checked"][0]["status"] == "drifted"
    bb.EMBEDDERS["facts-test"] = lambda texts: [[1.0, 0.0] if "restart" in t.lower() or "complete" in t.lower() else [0.0, 1.0] for t in texts]
    bb.OPTS.update(semantic=True, semantic_model="facts-test", min_similarity=0.6)
    r = bb.factcheck(fetch=True)["checked"][0]
    assert (r["status"], r["method"]) == ("checked", "similar meaning"), r
    (fk / "notes.md").write_text(doc.replace("is open", "is closed"))  # editing the words makes a new fact: unchecked until it is checked
    assert [x["status"] for x in bb.factcheck()["blocks"]] == ["checked", "unchecked"]
    bb.CFG = {"facts": {}}
    assert [x["status"] for x in bb.factcheck(fetch=True)["checked"]][1] == "skipped"  # not declared in bower.yaml: never called
finally:
    bb.ROOT, bb.CFG, bb.CLI, bb.at_terminal, builtins.input = saved[:5]
    bb.OPTS.clear()
    bb.OPTS.update(saved[5])
    srv.shutdown()


# seals carry a comment by default; the seal extensions (seal.extensions, seal.quorum) let several people seal one version.
sk = Path(tempfile.mkdtemp()).resolve()
(sk / "bower.yaml").write_text("format: markdown\n")
(sk / "a.md").write_text("# A\n\nbody\n")
seal_saved = (bb.ROOT, bb.CLI, bb.ATTEST, dict(bb.OPTS))
bb.ROOT, bb.CLI, bb.OPTS["format"] = sk, True, "markdown"
bb.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": False, "quorum": 1}
bb._SCOPES.clear()
bb._POLICY.clear()
human = lambda who, **kw: (setattr(bb, "ATTEST", f"human:{who}"), asyncio.run(bb.seal(file="a.md", **kw)), setattr(bb, "ATTEST", ""))[1]
try:
    out = human("ann", comment="  checked   the steps\n")  # a default seal: a comment, no extension needed
    led = (sk / ".waxseals.yaml").read_text()
    assert "comment: checked the steps" in led and "by: 'human:ann'" in led and "seals:" not in led and out["tier"] == "human-reviewed", led
    assert bb.ledger_by_file()["a.md"][0]["comment"] == "checked the steps"
    assert "280" in raises(human, "ann", comment="x" * 281)
    human("bo")  # without the extension a second seal replaces the first: one line, the latest
    assert len(bb.ledger_by_file()["a.md"]) == 1 and bb.ledger_by_file()["a.md"][0]["by"] == "human:bo" and "comment" not in (sk / ".waxseals.yaml").read_text()
    # the extensions on, quorum 2, on a new version of the file (the earlier seals bound the old bytes)
    (sk / "a.md").write_text("# A\n\nbody, second version\n")
    bb.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": True, "quorum": 2}
    bb._POLICY.clear()
    out = human("ann", comment="steps match the runbook")
    assert out["tier"] == "unverified" and out["quorum"] == "1 of 2", out  # one person is short of two
    short = [f for f in bb.signatures("")["findings"] if f["file"] == "a.md"]
    assert [f["kind"] for f in short] == ["short_of_quorum"] and "1 of 2" in short[0]["message"], short
    assert bb.trust_tier(bb.signed({}, "a.md", bb.ledger_by_file())) == "unverified"
    human("ann", comment="again")  # the same person replaces their own seal, they do not count twice
    assert len(bb.ledger_by_file()["a.md"]) == 1
    asyncio.run(bb.seal(file="a.md", by="process:ci"))  # a machine check is not a signer
    assert [f["kind"] for f in bb.signatures("")["findings"] if f["file"] == "a.md"] == ["short_of_quorum"]
    out = human("bo", comment="agreed")
    assert out["tier"] == "human-reviewed" and "quorum" not in out, out
    line = [ln for ln in (sk / ".waxseals.yaml").read_text().splitlines() if "a.md" in ln]
    assert len(line) == 1 and line[0].count("by:") == 3 and "comment: again" in line[0] and "comment: agreed" in line[0], line  # one line for the file, every seal on it
    assert not [f for f in bb.signatures("")["findings"] if f["file"] == "a.md"]
    assert bb.trust_tier(bb.signed({}, "a.md", bb.ledger_by_file())) == "human-reviewed"
    (sk / "a.md").write_text("# A\n\nbody, edited\n")  # an edit ends every seal of the old version
    assert [f["kind"] for f in bb.signatures("")["findings"] if f["file"] == "a.md"] == ["stale_signature"]
    human("cy")
    assert [e["by"] for e in bb.ledger_by_file()["a.md"]] == ["human:cy"]  # the old version's seals are not carried over
    bb.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": False, "quorum": 1}  # off again: the line still reads, the latest counts
    bb._POLICY.clear()
    assert [e["by"] for e in bb.ledger_by_file()["a.md"]] == ["human:cy"]
    for bad, why in (("seal: {quorum: 2}\n", "needs extensions"), ("seal: {extensions: true, quorum: 0}\n", "whole number"), ("seal: {extensions: 1}\n", "true or false")):
        (sk / "bower.yaml").write_text(bad)
        try:
            bb.load_config(sk)
            raise AssertionError(bad)
        except SystemExit as e:
            assert why in str(e), (bad, str(e))
    (sk / "bower.yaml").write_text("format: markdown\nseal: {extensions: true, quorum: 3}\n")
    assert bb.load_config(sk)[1]["seal"] == {"extensions": True, "quorum": 3}
finally:
    bb.ROOT, bb.CLI, bb.ATTEST = seal_saved[:3]
    bb.OPTS.clear()
    bb.OPTS.update(seal_saved[3])
    bb._SCOPES.clear()
    bb._POLICY.clear()


# create: a collection, or a bower of one; --mcp and --env as steps; .mcp.json merged, not replaced; settings it ignores are said.
assert bb.with_bower("# c\nbowers: [a]\nx: 1\n", "b") == "# c\nbowers: [a, b]\nx: 1\n" and bb.with_bower("bowers: []\n", "b") == "bowers: [b]\n"
assert bb.with_bower("bowers:\n  - a\nx: 1\n", "b") == "bowers:\n  - a\n  - b\nx: 1\n" and bb.with_bower("bowers: [a]\n", "a") == "bowers: [a]\n"
assert bb.with_bower("format: markdown\n", "b") is None and "comment" in raises(bb.with_bower, "bowers: [a]  # why\n", "b") + "comment"
cr, cr_saved = Path(tempfile.mkdtemp()).resolve(), bb.ROOT
(cr / "bower.yaml").write_text("# the root\nformat: markdown\nbowers: [docs]\n")
(cr / "docs").mkdir()
(cr / "docs/bower.yaml").write_text("format: markdown\n")
bb.ROOT = cr
try:
    P = create(path=str(cr / "notes"), holds="markdown", about="Notes.", user="u")  # a preview writes nothing
    assert not (cr / "notes").exists() and P["bower"]["listed"] == "notes" and "would_edit" in P
    P = create(path=str(cr / "notes"), holds="markdown", about="Notes.", user="u", apply=True)  # inside a collection with a list: a bower
    assert (cr / "bower.yaml").read_text() == "# the root\nformat: markdown\nbowers: [docs, notes]\n", (cr / "bower.yaml").read_text()
    bt = (cr / "notes/bower.yaml").read_text()  # a bower gets the whole commented template, with only the answers uncommented
    assert bt == bb.filled_config({"about": "Notes.", "format": "markdown"}).replace("\n\n", "\n# This is a bower of bower.yaml: only format, seal, about, hubs and min_similarity are read here.\n# The rest are the root's to decide; they are listed below for reference.\n\n", 1), bt
    assert len(bt.splitlines()) > 60 and bb.yaml.safe_load(bt) == {"about": "Notes.", "format": "markdown"} and sorted(p.name for p in (cr / "notes").iterdir()) == ["bower.yaml"]
    assert bb.load_config(cr)[1]["bowers"] == ["docs", "notes"]  # and the root still reads it as a bower, not as a second root
    assert "is a bower" in raises(create, path=str(cr / "notes"))
    P = create(path=str(cr / "more"), holds="adr", about="a", user="u", mcp=True, apply=True)  # a bower shares the root's files
    assert "mcp and env were not used" in P["ignored"][0] and not (cr / "more/.mcp.json").exists()
    assert bb.load_config(cr)[1]["bowers"] == ["docs", "notes", "more"]
    nr = Path(tempfile.mkdtemp()).resolve()  # a new root, with only the assistant's part
    P = create(path=str(nr), holds="markdown", about="A.", user="u", mcp=True, apply=True)
    assert sorted(p.name for p in nr.iterdir()) == [".mcp.json", "BOWERBIRD.md", "bower.yaml"] and P["mcp"] == "written" and P["agent"] == {"file": os.path.relpath(nr / "BOWERBIRD.md", cr), "state": "written"}
    P = create(path=str(nr), mcp=True)
    assert P["mcp"] == "up to date" and P["agent"]["state"] == "exists"
    (nr / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": {"command": "y"}}}))  # another server: kept; bowerbird added
    assert "bowerbird added" in create(path=str(nr), mcp=True, apply=True)["mcp"]
    assert set(json.loads((nr / ".mcp.json").read_text())["mcpServers"]) == {"x", "bowerbird"}
    (nr / ".mcp.json").write_text(json.dumps({"mcpServers": {"bowerbird": {"command": "mine"}}}))  # one the person set up: left alone
    assert "left alone" in create(path=str(nr), mcp=True, apply=True)["mcp"] and json.loads((nr / ".mcp.json").read_text())["mcpServers"]["bowerbird"] == {"command": "mine"}
    (nr / ".mcp.json").write_text("{nope")
    assert "valid JSON" in raises(create, path=str(nr), mcp=True, apply=True)
    (nr / ".mcp.json").unlink()
    P = create(path=str(nr), about="zzz", holds="adr")  # settings for a folder that has its bower.yaml are not used, and it says so
    assert "were not used" in P["ignored"][0] and "format: markdown" in (nr / "bower.yaml").read_text()
    er = Path(tempfile.mkdtemp()).resolve()  # the other step
    create(path=str(er), holds="markdown", about="E.", user="u", env=True, apply=True)
    assert sorted(p.name for p in er.iterdir()) == [".env", "bower.yaml", "env.example"] and (er / ".env").read_text() == "BOWERBIRD_USER=u\n"
    assert all(cli(n)[0] == 2 for n in ("init", "cite", "recheck_plan"))  # renamed in 2.2.0: each says where it went
    assert cli("create", "file=x.md", "type=Note")[0] == 2  # a document is `new`
finally:
    bb.ROOT = cr_saved


# the docs hook reads only the ledger: a person's seal, an edit, a generator's line, and nothing
import importlib.util

hk_spec = importlib.util.spec_from_file_location("seal_banner", HERE / "hooks" / "seal_banner.py")
hk = importlib.util.module_from_spec(hk_spec)
hk_spec.loader.exec_module(hk)
hd = Path(tempfile.mkdtemp()).resolve()
(hd / "docs").mkdir()
pages = {n: (hd / "docs" / n) for n in ("sealed.md", "edited.md", "made.md", "none.md", "exempt.md")}
for n, p in pages.items():
    p.write_text(f"# {n}\r\nbody\r\n")  # CRLF on disk: the tool hashes it as LF, and so does the hook
sha = lambda n: bb.content_hash(pages[n].read_text(), False)
(hd / ".waxseals.yaml").write_text("\n".join([
    f"- {{file: docs/sealed.md, sha256: {sha('sealed.md')}, by: 'human:ann', at: '2026-11-20T10:00:00Z'}}",
    "- {file: docs/edited.md, sha256: 0000, by: 'human:ann', at: '2026-11-19T10:00:00Z'}",
    f"- {{file: docs/made.md, sha256: {sha('made.md')}, derived: gen.py, at: '2026-11-20T10:00:00Z'}}",
    f"- {{file: docs/exempt.md, sha256: {sha('exempt.md')}, seals: [{{by: 'human:ann', at: '2026-11-18T10:00:00Z'}}, {{by: 'human:bo', at: '2026-11-20T11:00:00Z'}}]}}"]) + "\n")
(hd / "docs" / "bower.yaml").write_text("seal: {exempt: ['/exempt.md', '/none.md']}\n")  # a policy the hook does not read
hk_cwd = os.getcwd()
os.chdir(hd)
try:
    state = lambda n: re.search(r'data-state="(\w+)"', hk.banner(pages[n], n, hd / "docs", "", False)).group(1)
    assert [state(n) for n in ("sealed.md", "edited.md", "made.md", "none.md", "exempt.md")] == ["reviewed", "edited", "derived", "unreviewed", "reviewed"]
    assert "2026-11-20T11:00:00Z" in hk.banner(pages["exempt.md"], "exempt.md", hd / "docs", "", False)  # several seals on a line: the latest
    pages["made.md"].write_text("# made by hand\n")
    assert state("made.md") == "unreviewed"  # edited since the generator wrote it: no longer derived
finally:
    os.chdir(hk_cwd)


# `serve restart`, as a person runs it: a new process each time, the pid file under XDG_CACHE_HOME, and always a running server after.
try:
    import markdown  # noqa: F401 (serve needs it)
except ImportError:
    print("skipped serve restart: markdown not installed")
else:
    import urllib.request

    rs = Path(tempfile.mkdtemp()).resolve()
    (rs / "bower.yaml").write_text("format: markdown\n")
    (rs / "a.md").write_text("# A\n\nbody\n")
    with socket.socket() as so3:
        so3.bind(("127.0.0.1", 0))
        rport = so3.getsockname()[1]
    renv = {**os.environ, "XDG_CACHE_HOME": str(rs / "cache"), "PYTHONPATH": str(HERE)}
    pf3 = rs / "cache" / "bowerbird-mcp" / f"serve-{rport}.pid"
    serve_cmd = lambda *a: subprocess.run([sys.executable, str(HERE / "bowerbird_mcp.py"), "serve", *a, str(rport)], cwd=rs, env=renv,
                                          capture_output=True, text=True, timeout=90, check=False)
    page = lambda: urllib.request.urlopen(f"http://127.0.0.1:{rport}/", timeout=10).status
    alive = lambda pid: (os.kill(pid, 0), True)[1] if Path(f"/proc/{pid}").exists() else False
    try:
        r = serve_cmd("status")
        assert r.returncode == 1 and "not running" in r.stdout, r
        r = serve_cmd("restart")  # nothing to stop: it just starts
        assert r.returncode == 0 and "in the background" in r.stdout, r
        pid1 = int(pf3.read_text())
        assert page() == 200 and serve_cmd("status").returncode == 0 and alive(pid1)
        r = serve_cmd("restart")  # stops the one it finds, waits for the port, starts a new one
        assert r.returncode == 0 and "stopped the server" in r.stdout and "in the background" in r.stdout, r
        pid2 = int(pf3.read_text())
        assert pid2 != pid1 and page() == 200 and serve_cmd("status").returncode == 0
        for _ in range(50):
            if not alive(pid1):
                break
            time.sleep(0.1)
        assert not alive(pid1) and alive(pid2)  # the old process is gone, the new one answers
        r = serve_cmd("stop")
        assert r.returncode == 0 and "stopped the server" in r.stdout and not pf3.exists(), r
        assert serve_cmd("status").returncode == 1 and serve_cmd("stop").returncode == 0  # nothing running is not an error
        # something else on the port: restart refuses, and never touches it
        with socket.socket() as foreign:
            foreign.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            foreign.bind(("127.0.0.1", rport))
            foreign.listen()
            r = serve_cmd("restart")
            assert r.returncode == 1 and "in use by something else" in r.stdout, r
            assert not pf3.exists()
    finally:
        serve_cmd("stop")


# marking a file derived also leaves it out of the review check: it goes into seal.exempt of the bower.yaml that covers it.
assert bb.with_exempt('# c\nseal: {exempt: ["/a.md"], exempt_status: []}\nx: 1\n', "/b.md") == "# c\nseal: {exempt: [/a.md, /b.md], exempt_status: []}\nx: 1\n"
assert bb.with_exempt('seal: {exempt: ["/a.md"]}\n', "/a.md") == 'seal: {exempt: ["/a.md"]}\n'
assert bb.with_exempt("# nothing set\nformat: markdown\n", "/g.md") == '# nothing set\nformat: markdown\nseal: {exempt: ["/g.md"]}\n'
assert bb.with_exempt("seal:\n  exempt: []\n", "/g.md") is None and bb.with_exempt("seal: {exempt: []}  # why\n", "/g.md") is None
dx, dx_saved = Path(tempfile.mkdtemp()).resolve(), (bb.ROOT, bb.CLI, dict(bb.OPTS))
(dx / "bower.yaml").write_text("# docs\nformat: markdown\n")
(dx / "gen.md").write_text("# Generated\n\ntable\n")
(dx / "hand.md").write_text("# Hand\n\nwords\n")
bb.ROOT, bb.CLI, bb.OPTS["format"], bb.OPTS["seal"] = dx, True, "markdown", {"exempt": [], "exempt_status": []}
bb._SCOPES.clear()
bb._POLICY.clear()
try:
    assert {f["file"] for f in bb.signatures("")["findings"]} >= {"gen.md", "hand.md"}  # unreviewed, both
    done = bb.mark_derived(dx / "gen.md", "gen.py")
    assert done[0] == ".waxseals.yaml" and "seal.exempt gets /gen.md" in done[1], done
    assert (dx / "bower.yaml").read_text() == '# docs\nformat: markdown\nseal: {exempt: ["/gen.md"]}\n'  # comments kept, one line added
    assert bb.derived(dx / "gen.md") and {f["file"] for f in bb.signatures("")["findings"]} == {"hand.md"}  # nobody seals it: no finding
    assert bb.mark_derived(dx / "gen.md", "gen.py") == []  # nothing to change the second time
    (dx / "bower.yaml").write_text("format: markdown\nseal:\n  exempt: []\n")  # a block: said, not rewritten
    bb._SCOPES.clear()
    bb._POLICY.clear()
    bb.OPTS["seal"] = {"exempt": [], "exempt_status": []}
    (dx / "gen2.md").write_text("# G2\n")
    assert "by hand" in bb.mark_derived(dx / "gen2.md", "gen.py")[-1] and (dx / "bower.yaml").read_text() == "format: markdown\nseal:\n  exempt: []\n"
finally:
    bb.ROOT, bb.CLI = dx_saved[:2]
    bb.OPTS.clear()
    bb.OPTS.update(dx_saved[2])
    bb._SCOPES.clear()
    bb._POLICY.clear()


# the old names are gone (2.3): a kbmcp.yaml with no bower.yaml stops the run, and KB_* variables, kbmcp.nolint and kb-index markers are not read.
lg = Path(tempfile.mkdtemp()).resolve()
(lg / "kbmcp.yaml").write_text("format: adr\nabout: Old name.\n")
try:
    bb.load_config(lg)
    msg = "did not stop"
except SystemExit as e:
    msg = str(e)
assert "kbmcp.yaml is no longer read" in msg and "git mv kbmcp.yaml bower.yaml" in msg, msg
(lg / "bower.yaml").write_text("format: markdown\nabout: New name.\n")  # with a bower.yaml beside it, the old file is just a file
assert bb.load_config(lg)[1]["about"] == "New name." and bb.config_file(lg).name == "bower.yaml"
(lg / "bower.yaml").unlink()
ov = bb.env_overrides({"BOWERBIRD_ABOUT": "new", "KB_ABOUT": "old", "KB_HUBS": "false"})
assert ov == {"about": "new"}, ov
assert bb.envvar("USER", {"KB_USER": "me"}) is None and bb.envvar("USER", {"BOWERBIRD_USER": "you", "KB_USER": "me"}) == "you"
(lg / ".env").write_text("KB_ABOUT=old\nBOWERBIRD_BUILD=manual\n")
assert bb.read_dotenv(lg / ".env") == {"BOWERBIRD_BUILD": "manual"}
old_block = "<!-- kb-index:start (generated by KnowledgeBaseMCP index; do not edit between the markers) -->\n\nstale\n\n<!-- kb-index:end -->"
assert not bb.BLOCK.search(f"# Index\n\n{old_block}\n") and bb.BLOCK.search(f"{bb.INDEX_BEGIN}\nx\n{bb.INDEX_END}")  # only the current marker is found
nl, nl_saved = Path(tempfile.mkdtemp()).resolve(), bb.ROOT
bb.ROOT = nl
(nl / "kbmcp.nolint").write_text("drafts/\n")
(nl / "bower.nolint").write_text("keep.md\n")
skip = bb.nolint(nl)
assert skip("keep.md") and not skip("drafts/a.md")  # kbmcp.nolint is not read
bb.ROOT = nl_saved


# purge_seals: the ledger lines of the files the globs name go, the others stay; a person runs it, it is not a tool.
pg, pg_saved = Path(tempfile.mkdtemp()).resolve(), bb.ROOT
bb.ROOT = pg
(pg / ".waxseals.yaml").write_text(
    "- {file: docs/a.html, sha256: 11, by: 'human:ann', at: '2026-11-20T10:00:00Z'}\n"
    "- {file: docs/img/b.png, sha256: 22, by: 'human:ann', at: '2026-11-20T10:00:00Z'}\n"
    "- {file: src/keep.py, sha256: 33, by: 'human:ann', at: '2026-11-20T10:00:00Z'}\n")
try:
    assert bb.purge_seals(["/docs/**"]) == ["docs/a.html", "docs/img/b.png"] and list(bb.ledger_all(pg / ".waxseals.yaml")) == ["src/keep.py"]
    assert bb.purge_seals(["/docs/**"]) == [] and "purge_seals" not in bb.REG  # nothing left to purge; and no agent can call it
finally:
    bb.ROOT = pg_saved


# distributed ledgers (2.3): a seal goes into the ledger of the file's own folder, a root ledger from before still holds, and the nearest wins.
dl2, dl2_saved = Path(tempfile.mkdtemp()).resolve(), bb.ROOT
bb.ROOT = dl2
(dl2 / "docs/adr").mkdir(parents=True)
(dl2 / "docs/other").mkdir()
(dl2 / ".waxseals.yaml").write_text("- {file: docs/adr/a.md, sha256: 11, by: 'human:old', at: '2026-01-01T00:00:00Z'}\n"
                                  "- {file: docs/keep.md, sha256: 22, by: 'human:old', at: '2026-01-01T00:00:00Z'}\n")
try:
    assert set(bb.ledger_by_file()) == {"docs/adr/a.md", "docs/keep.md"}  # the old root ledger is read as it was
    wrote = bb.ledger_put("docs/adr/a.md", {"file": "docs/adr/a.md", "sha256": "33", "by": "human:new", "at": "2026-02-01T00:00:00Z"})
    assert wrote == [".waxseals.yaml", "docs/adr/.waxseals.yaml"], wrote  # one line left the root ledger, one went beside the file
    assert "file: a.md," in (dl2 / "docs/adr/.waxseals.yaml").read_text() and "a.md" not in (dl2 / ".waxseals.yaml").read_text()
    seen = bb.ledger_by_file()
    assert set(seen) == {"docs/adr/a.md", "docs/keep.md"} and seen["docs/adr/a.md"][-1]["by"] == "human:new" and seen["docs/adr/a.md"][-1]["file"] == "docs/adr/a.md"
    (dl2 / "docs/adr/.waxseals.yaml").write_text(  # a stray old line in the root for the same file: the nearer ledger wins
        "- {file: a.md, sha256: 33, by: 'human:new', at: '2026-02-01T00:00:00Z'}\n")
    (dl2 / ".waxseals.yaml").write_text("- {file: docs/adr/a.md, sha256: 11, by: 'human:old', at: '2026-01-01T00:00:00Z'}\n")
    assert bb.ledger_by_file()["docs/adr/a.md"][-1]["by"] == "human:new"
    for k, v in bb.ledger_changes({"docs/adr/a.md": None, "docs/other/a.md": bb.ledger_by_file()["docs/adr/a.md"]}).items():  # a move carries the seal to the new folder
        (k.unlink() if v is None else k.write_text(v))
    assert not (dl2 / "docs/adr/.waxseals.yaml").exists() and "file: a.md," in (dl2 / "docs/other/.waxseals.yaml").read_text() and list(bb.ledger_by_file()) == ["docs/other/a.md"]
    assert hk.entries(dl2, "docs/other/a.md")[0]["by"] == "human:new" and hk.entries(dl2, "docs/adr/a.md") == []  # the docs hook finds the nearest ledger too
finally:
    bb.ROOT = dl2_saved


# format add-ons (2.3): obsidian, foam, dendron and logseq each register a profile of the markdown family; the shared resolver reads their links.
import importlib.metadata as _im
import importlib.util as _iu


def addon(n):
    s = _iu.spec_from_file_location(f"bowerbird_{n}", HERE / "addons" / n / f"bowerbird_{n}.py")
    m = _iu.module_from_spec(s)
    s.loader.exec_module(m)
    m.register(bb)


class _EP:  # an entry point, as importlib.metadata hands one out
    def __init__(self, name, fn):
        self.name, self.load = name, lambda: fn


def _boom(_bb):
    raise RuntimeError("broken add-on")


_orig_eps, err = _im.entry_points, io.StringIO()
_im.entry_points = lambda group=None: [_EP("fake", lambda m: m.register_format("fake", about="a fake")), _EP("bad", _boom)]
try:
    with contextlib.redirect_stderr(err):
        bb.load_plugins()
finally:
    _im.entry_points = _orig_eps
assert "fake" in bb.PROFILES and bb.base("fake") == "markdown" and bb.base("okf") == "okf"  # a profile is read as markdown
assert "the add-on bad did not load (RuntimeError: broken add-on)" in err.getvalue()  # a broken add-on is said, and left out
del bb.PROFILES["fake"]
for n in ("obsidian", "foam", "dendron", "logseq"):
    addon(n)
assert {"obsidian", "foam", "dendron", "logseq"} <= set(bb.PROFILES)


def vault(fmt, files):
    """A throwaway collection of `fmt` holding files; (root, a function giving the (file, kind) lint findings)."""
    d = Path(tempfile.mkdtemp()).resolve()
    (d / "bower.yaml").write_text(f"format: {fmt}\n")
    for n, body in files.items():
        (d / n).parent.mkdir(parents=True, exist_ok=True)
        (d / n).write_text(body)
    return d


def in_vault(fmt, files, fn):
    saved = (bb.ROOT, bb.OPTS["format"], bb.CFG_DIR)
    d = vault(fmt, files)
    bb.ROOT, bb.OPTS["format"], bb.CFG_DIR = d, fmt, d
    bb._SCOPES.clear()
    bb._POLICY.clear()
    bb.WIKI.clear()
    try:
        return fn(d)
    finally:
        bb.ROOT, bb.OPTS["format"], bb.CFG_DIR = saved
        bb._SCOPES.clear()
        bb._POLICY.clear()
        bb.WIKI.clear()


def dead(d):
    return {(f["file"], f["message"].split(" ")[2]) for f in bb.lint(limit=0)["findings"] if f["kind"] == "dead_link"}


# Obsidian: [[Note]] by name or alias, the vault's own folders skipped, %%comments%% and embeds of files handled, inline #tags
def obs(d):
    a = d / "a.md"
    assert bb.hrefs(a.read_text()) == ["[[b]]", "[[Missing]]", "[[img.png]]", "[[b]]", "[[Alt Name]]"], bb.hrefs(a.read_text())  # %% [[Hidden]] %% is a comment; [[b#^blk]] keeps the note
    assert bb.target("[[b]]", a, d) == d / "sub/b.md" and bb.target("[[img.png]]", a, d) == d / "img.png"
    assert bb.target("[[alt name]]", a, d) == d / "sub/b.md"  # a note's `aliases` find it
    assert not any(".obsidian" in str(p) for p in bb.walk(d)) and dead(d) == {("a.md", "[[Missing]]")}, dead(d)
    assert bb.fmt_of(a) == "markdown" and bb.profile().name == "obsidian"
    tg = bb.adr_meta(bb.meta((d / "t.md").read_text())[0] or {}, (d / "t.md").read_text(), d / "t.md")["tags"]
    assert tg == ["fm", "alpha", "beta/sub", "x_1"], tg  # the frontmatter's first; not #1984, a comment's, a code span's or a URL's
in_vault("obsidian", {"a.md": "[[b]] [[Missing]] %% [[Hidden]] %% ![[img.png]] [[b#^blk]] [[Alt Name]]\n", "sub/b.md": "---\naliases: [Alt Name]\n---\nb\n", "img.png": "x",
                      ".obsidian/workspace.md": "[[Nope]]\n", "t.md": "---\ntags: [fm]\n---\n# Heading\n\n#alpha #beta/sub #1984 %% #hidden %% `#code` http://x.y/#frag #x_1\n"}, obs)


# Foam: [[projects]] is projects/index.md, a sibling projects.md would win; ./ and / paths; the editor's folders are skipped; `alias` as a comma list
def foam(d):
    a, deep = d / "a.md", d / "projects/house/todo.md"
    assert bb.target("[[projects]]", a, d) == d / "projects/index.md" and bb.target("[[house/todo]]", a, d) == deep
    assert bb.target("[[./sib]]", deep, d) == d / "projects/house/sib.md" and bb.target("[[../index]]", deep, d) == d / "projects/index.md" and bb.target("[[/a]]", deep, d) == a
    assert bb.target("[[Plan B]]", a, d) == d / "projects/index.md" and bb.target("[[plan c]]", a, d) == d / "projects/index.md"  # `alias: Plan B, Plan C`
    assert dead(d) == {("a.md", "[[nope]]"), ("a.md", "[[./gone]]")} and not any(".foam" in str(p) for p in bb.walk(d)), dead(d)
    assert bb.adr_meta({}, "#one and #two/x\n", a)["tags"] == ["one", "two/x"]
in_vault("foam", {"a.md": "[[projects]] [[house/todo]] [[nope]] [[./gone]] [[/a]]\n", "projects/index.md": "---\nalias: Plan B, Plan C\n---\ni\n", "projects/house/todo.md": "t\n", "projects/house/sib.md": "s\n",
                  ".foam/templates/n.md": "[[$FOAM_X]]\n"}, foam)


# Dendron: the alias is on the left, dotted names are the hierarchy, a stub parent exists, a vault link stays in its vault, #tags and @user are not broken links
def den(d):
    a = d / "x.md"
    assert bb.hrefs(a.read_text()) == ["[[a.b.c#head]]", "[[a.b]]", "[[dendron://v1/a.b.c]]", "[[gone.x]]", "[[tags.proj.x]]", "[[user.ann]]"], bb.hrefs(a.read_text())
    assert bb.target("[[a.b.c]]", a, d) == d / "v2/a.b.c.md" or bb.target("[[a.b.c]]", a, d) == d / "v1/a.b.c.md"  # an unscoped link: the shortest path (both are one deep; the first by name)
    assert bb.target("[[a.b]]", a, d) is None  # a.b is a stub: no file, not a broken link
    assert bb.target("[[dendron://v1/a.b.c]]", a, d) == d / "v1/a.b.c.md" and bb.target("[[dendron://v2/a.b.c]]", a, d) == d / "v2/a.b.c.md"  # the vault says which
    assert bb.target("[[tags.proj.x]]", a, d) is None and bb.target("[[user.ann]]", a, d) is None
    assert dead(d) == {("x.md", "[[gone.x]]")}, dead(d)
    assert bb.adr_meta({}, "#proj.x and #other\n", a)["tags"] == ["proj.x", "other"]
in_vault("dendron", {"x.md": "[[alias|a.b.c#head]] [[a.b]] [[dendron://v1/a.b.c]] [[gone.x]] #proj.x @ann\n", "v1/a.b.c.md": "c1\n", "v2/a.b.c.md": "c2\n",
                     "dendron.yml": "workspace:\n  vaults:\n    - fsPath: v1\n      name: v1\n    - fsPath: v2\n      name: v2\n"}, den)


# Logseq: a___b.md is page a/b, `title::` and `alias::` name a page, ((uuid)) finds its block, a journal page needs no file, config.edn sets the formats
def lsq(d):
    a = d / "pages/z.md"
    assert bb.target("[[a/b]]", a, d) == d / "pages/a___b.md" and bb.target("[[Sep 14th, 2020]]", a, d) is None
    assert bb.target("[[A Better Title]]", a, d) == d / "pages/titled.md" and bb.target("[[tl]]", a, d) == d / "pages/titled.md"
    assert bb.target("[[block:6700a8c1-aaaa-bbbb-cccc-000000000001]]", a, d) == d / "pages/titled.md"
    assert "[[block:6700a8c1-aaaa-bbbb-cccc-000000000001]]" in bb.hrefs(a.read_text())
    assert dead(d) == set() and not any("logseq" in p.relative_to(d).parts for p in bb.walk(d))
    assert bb.adr_meta({}, a.read_text(), a)["tags"] == ["tag1", "two words", "plain", "x", "y"]
    (d / "logseq/config.edn").write_text('{:journal/page-title-format "yyyy-MM-dd"}\n')  # a config with no :file/name-format is a legacy graph: `.` is `/`; and the journal title is its own
    assert bb.target("[[2020-09-14]]", a, d) is None and bb.target("[[Sep 14th, 2020]]", a, d) != None
    assert bb.PROFILES["logseq"].page("a.b") == "a/b"
in_vault("logseq", {"pages/z.md": "- [[a/b]] [[Sep 14th, 2020]] [[nowhere]] [[A Better Title]] [[tl]] ((6700a8c1-aaaa-bbbb-cccc-000000000001)) #tag1 #[[two words]] #plain\ntags:: x, y\n",
                    "pages/a___b.md": "- b\n", "pages/titled.md": "title:: A Better Title\nalias:: tl, [[tt]]\n\n- a block\n  id:: 6700a8c1-aaaa-bbbb-cccc-000000000001\n",
                    "logseq/bak/old.md": "[[x]]\n", "logseq/config.edn": "{:file/name-format :triple-lowbar}\n"}, lsq)
for n in ("obsidian", "foam", "dendron", "logseq"):
    del bb.PROFILES[n]


# fact kinds file and internal (ADR-001): read here, no network; an agent may run the check, and a drift is recorded beside the document.
outside = Path(tempfile.mkdtemp()).resolve() / "limits.txt"  # a file outside the collection
outside.write_text("alpha\nbeta\ngamma\ndelta\n")


def facts_vault(d):
    def row(text, i=0):
        (d / "n.md").write_text(text)
        return bb.fact_rows("n.md")[i]

    def run(r):
        return bb.factcheck(file="n.md", id=r["id"])["checked"][0]
    r = row(f"[fact.file]({outside}#L2-3) beta gamma [fact.end]\n")
    assert r["status"] == "unchecked" and run(r)["status"] == "checked"  # an agent checks it with no prompt, and it is recorded
    assert bb.fact_rows("n.md")[0]["status"] == "checked"
    assert run(row(f"[fact.file]({outside}#L2-3) alpha [fact.end]\n"))["status"] == "drifted"  # alpha is in the file, not in the lines the fact names
    got = run(row(f"[fact.file]({outside}#L9-10) beta [fact.end]\n"))
    assert got["status"] == "drifted" and "past the end" in got["method"]
    assert run(row(f"[fact.file]({outside.parent}/gone.txt) beta [fact.end]\n"))["status"] == "drifted"
    (d / "data.txt").write_text("one\ntwo\n")
    assert run(row("[fact.file](data.txt#L2) two [fact.end]\n"))["status"] == "checked"  # relative to the document's folder
    assert run(row("[fact.file](data.txt) one two [fact.end]\n"))["status"] == "checked"  # no lines: the whole file
    (d / "other.md").write_text("# Top\n\n## Part One\nfoo\n\n## Part Two\nthe second part says x\n\n### Sub\nsub text\n\n## Part Three\nbar\n")
    assert run(row("[fact.internal](other.md#Part Two) the second part says x [fact.end]\n"))["status"] == "checked"
    assert run(row("[fact.internal](other.md#part-two) sub text [fact.end]\n"))["status"] == "checked"  # a sub-section is in its section; the heading is matched by anchor
    assert run(row("[fact.internal](other.md#Part Two) foo [fact.end]\n"))["status"] == "drifted"  # foo is on the page, in another section
    assert run(row("[fact.internal](other.md#Part Two) bar [fact.end]\n"))["status"] == "drifted"
    got = run(row("[fact.internal](other.md#Nope) foo [fact.end]\n"))
    assert got["status"] == "drifted" and "no heading" in got["method"]
    assert run(row("[fact.internal](nope.md) foo [fact.end]\n"))["status"] == "drifted"
    assert run(row("[fact.internal](other.md) foo [fact.end]\n"))["status"] == "checked"  # no heading: the whole page
    (d / "n.md").write_text("[fact.file](x#frag) a [fact.end] [fact.file](x#L3-1) a [fact.end] [fact.internal]() a [fact.end] [fact.file](https://a.b/c) a [fact.end]\n")
    assert {f["kind"] for f in bb.lint(limit=0)["findings"]} >= {"bad_fact"} and sum(f["kind"] == "bad_fact" for f in bb.lint(limit=0)["findings"]) == 4
in_vault("markdown", {"n.md": "x\n"}, facts_vault)


# the fact pack (ADR-001): key, git, until, manual and script, registered through the `bowerbird.fact_types` entry point.
_fp = _iu.spec_from_file_location("bowerbird_fact_pack", HERE / "addons" / "fact-pack" / "bowerbird_fact_pack.py")
fact_pack = _iu.module_from_spec(_fp)
_fp.loader.exec_module(fact_pack)
FF = bb.facts_mod()
assert "pip install 'bowerbird-mcp[fact-pack]'" in FF.parse("[fact.key](a b) x [fact.end]")[1][0][2]  # without the pack: told what to install
_im.entry_points = lambda group=None: [_EP("fact-pack", fact_pack.register)] if group == "bowerbird.fact_types" else []
try:
    bb.load_plugins("bowerbird.fact_types")
finally:
    _im.entry_points = _orig_eps
assert {"key", "git", "until", "manual", "script"} <= set(FF.FACT_TYPES) and FF.FACT_TYPES["key"].local and not FF.FACT_TYPES["script"].local and not FF.FACT_TYPES["manual"].local
assert "install the fact pack" not in str(FF.parse("[fact.key](a.json x) x [fact.end]")[1])


def pack_vault(d):
    def row(text, i=0):
        (d / "n.md").write_text(text)
        return bb.fact_rows("n.md")[i]

    def run(text):
        r = row(text)
        return bb.fact_run(d / "n.md", next(b for _, b in bb.fact_blocks("n.md") if b.id == r["id"]), bb.CFG.get("facts", {}).get("mcp", {}))
    # key: the first check records the value, the next ones compare, a missing key is a drift
    (d / "v.json").write_text(json.dumps({"project": {"version": "2.3.0", "list": [1, 2]}}))
    (d / "v.yaml").write_text("project:\n  version: '2.3.0'\n")
    claim = "[fact.key](v.json project.version) is 2.3.0 [fact.end]\n"
    assert run(claim)["method"] == "baseline recorded" and run(claim)["method"] == "same value"
    (d / "v.json").write_text(json.dumps({"project": {"version": "2.4.0"}}))
    got = run(claim)
    assert got["status"] == "drifted" and "2.3.0" in got["method"] and "2.4.0" in got["method"]
    assert run("[fact.key](v.json project.nope) x [fact.end]\n")["status"] == "drifted" and run("[fact.key](v.yaml project.version) x [fact.end]\n")["status"] == "checked"
    assert run("[fact.key](gone.json a) x [fact.end]\n")["status"] == "drifted"
    # until: a date
    assert run("[fact.until](2999-01-01) the freeze is on [fact.end]\n")["status"] == "checked" and run("[fact.until](2000-01-01) the freeze is on [fact.end]\n")["status"] == "drifted"
    (d / "n.md").write_text("[fact.until](soon) x [fact.end] [fact.git](tag) x [fact.end] [fact.git](file HEAD) x [fact.end] [fact.key](one) x [fact.end] [fact.script](a b c) x [fact.end]\n")
    assert sum(f["kind"] == "bad_fact" for f in bb.lint(limit=0)["findings"]) == 5
    # git: a tag, and a file at a revision
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    g = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, env=env)
    g("init", "-q")
    g("add", "-A")
    g("commit", "-q", "-m", "one")
    g("tag", "v1")
    tag = "[fact.git](tag v1) tagged [fact.end]\n"
    assert run(tag)["method"] == "baseline recorded" and run(tag)["method"] == "same value"
    (d / "x.txt").write_text("changed\n")
    g("add", "-A")
    g("commit", "-q", "-m", "two")
    g("tag", "-f", "v1")
    assert run(tag)["status"] == "drifted"  # the tag moved
    assert run("[fact.git](tag nope) x [fact.end]\n")["status"] == "drifted"
    f1 = "[fact.git](file HEAD x.txt) x.txt is unchanged [fact.end]\n"
    assert run(f1)["method"] == "baseline recorded"
    (d / "x.txt").write_text("changed again\n")
    g("add", "-A")
    g("commit", "-q", "-m", "three")
    assert run(f1)["status"] == "drifted"
    # manual: a person at a terminal answers; no prompt for an agent; an opted-in interval skips a fresh confirmation
    import builtins
    saved_in, saved_term = builtins.input, bb.at_terminal
    try:
        bb.at_terminal = lambda: False
        assert run("[fact.manual](ops standup) the rota moved to Tuesdays [fact.end]\n")["status"] == "skipped"  # asking a person is for a person: an agent's run leaves it
        bb.at_terminal = lambda: True
        builtins.input = lambda _="": "y"
        m = "[fact.manual](ops standup) the rota moved to Tuesdays [fact.end]\n"
        assert run(m)["status"] == "checked" and "confirmed by" in run(m)["method"]
        bb.CFG["facts"] = {"manual_days": 30}
        assert run(m)["status"] == "skipped"  # confirmed a moment ago, and an interval is on
        bb.CFG.pop("facts")
        builtins.input = lambda _="": "n"
        assert run(m)["status"] == "drifted"
    finally:
        builtins.input, bb.at_terminal = saved_in, saved_term
        bb.CFG.pop("facts", None)
    # script: declared in the root bower.yaml, an argument list, no shell; output is the value; a failing command is skipped
    s = "[fact.script](show) the file says one [fact.end]\n"
    assert run(s)["status"] == "skipped" and "not declared" in run(s)["method"]
    bb.CFG["facts"] = {"scripts": {"show": {"cmd": ["cat", "{key}"]}, "bad": {"cmd": ["false"]}, "inj": {"cmd": ["echo", "{key}"]}}}
    try:
        (d / "data.txt").write_text("one\n")
        s2 = "[fact.script](show data.txt) the file says one [fact.end]\n"
        assert run(s2)["method"] == "baseline recorded" and run(s2)["method"] == "same value"
        (d / "data.txt").write_text("two\n")
        assert run(s2)["status"] == "drifted"
        assert run("[fact.script](bad) x [fact.end]\n")["status"] == "skipped"
        (d / "n.md").write_text("[fact.script](inj ;touch-pwned) x [fact.end] [fact.script](inj --upload-pack=x) y [fact.end]\n")
        assert bb.fact_rows("n.md") == [] and sum(f["kind"] == "bad_fact" for f in bb.lint(limit=0)["findings"]) == 2  # a key with shell characters, or one that starts with -, is not a fact
        assert run("[fact.script](inj a.b-c) x [fact.end]\n")["status"] == "checked" and not (d / "touch-pwned").exists()  # an ordinary key goes in as one argument
    finally:
        bb.CFG.pop("facts", None)
in_vault("markdown", {"n.md": "x\n"}, pack_vault)
for _k in ("key", "git", "until", "manual", "script"):
    del FF.FACT_TYPES[_k]


# seal extensions: a move carries every person's seal, not only the last
def seals_move(d):
    saved = dict(bb.OPTS["seal"])
    bb.OPTS["seal"] = {**saved, "extensions": True, "quorum": 2}
    bb._POLICY.clear()
    try:
        text = (d / "a.md").read_text()
        for i, who in enumerate(("ann", "bo"), 1):
            bb.ledger_put("a.md", {"file": "a.md", "sha256": bb.content_hash(text, False), "by": f"human:{who}", "at": f"2026-11-23T10:00:0{i}Z", "comment": f"{who} read it"})
        assert [e["by"] for e in bb.ledger_by_file()["a.md"]] == ["human:ann", "human:bo"]
        bb.move("a.md", "sub/a", apply=True)
        moved = bb.ledger_by_file()
        assert set(moved) == {"sub/a.md"} and [e["by"] for e in moved["sub/a.md"]] == ["human:ann", "human:bo"] and moved["sub/a.md"][0]["comment"] == "ann read it"
        assert not (d / ".waxseals.yaml").read_text().count("a.md") if (d / ".waxseals.yaml").exists() else True
    finally:
        bb.OPTS["seal"] = saved
        bb._POLICY.clear()
in_vault("markdown", {"a.md": "# A\n\nbody\n", "sub/keep.md": "# K\n"}, seals_move)


# a heading that only exists once a MkDocs snippet is pulled in is still a heading (a link to it is not a dead anchor)
def snippets(d):
    got = {(f["file"], f["kind"]) for f in bb.lint(limit=0)["findings"]}
    assert ("guide.md", "dead_anchor") not in got and ("other.md", "dead_anchor") not in got and ("bad.md", "dead_anchor") in got, got
    assert bb.expanded('x\n--8<-- "src.md:part"\ny\n', d / "guide.md").count("## Pulled in") == 1 and "Other part" not in bb.expanded('--8<-- "src.md:part"', d / "guide.md")
in_vault("markdown", {"src.md": "<!-- --8<-- [start:part] -->\n## Pulled in\n\ntext\n<!-- --8<-- [end:part] -->\n## Other part\n", "guide.md": "# G\n\n--8<-- \"src.md:part\"\n",
                      "other.md": "[a](guide.md#pulled-in) [b](src.md#other-part)\n", "bad.md": "[c](guide.md#nope)\n"}, snippets)


# the `facts:` settings the pack reads are checked when bower.yaml loads
for bad in ("facts: {types: {key: {server: s, tool: t, arg: a}}}\n", "facts: {scripts: {a: {cmd: 'echo hi'}}}\n", "facts: {scripts: {a: {cmd: []}}}\n", "facts: {scripts: {a: {cmd: [echo], timeout: 0}}}\n",
            "facts: {scripts: {'a b': {cmd: [echo]}}}\n", "facts: {manual_days: 0}\n", "facts: {manual_days: true}\n"):
    (lg / "bower.yaml").write_text(bad)
    try:
        bb.load_config(lg)
        raise AssertionError(bad)
    except SystemExit as e:
        assert "facts takes" in str(e), (bad, str(e))
(lg / "bower.yaml").write_text("facts: {scripts: {uvver: {cmd: [uv, --version], timeout: 5}}, manual_days: 90}\n")
assert bb.load_config(lg)[1]["facts"]["manual_days"] == 90
(lg / "bower.yaml").unlink()


# the one grammar of a fact: [fact.KIND]{metadata}(source) claim [fact.end]; the metadata and the JSON source are optional, and neither is part of the fact's id
g0 = F.parse("[fact.url](https://x.test/a) The words. [fact.end]")[0][0]
g1 = F.parse('[fact.url]{by: ann, at: 2026-11-20, confidence: high, lastchecked: $DATETIME}(https://x.test/a) The words. [fact.end]')[0][0]
g2 = F.parse('[fact.url]{"by": "claude", "tags": ["a", "b"], "note": "has } brace"}(["https://x.test/a"]) The words. [fact.end]')[0][0]
g3 = F.parse('[fact.mcp]{}(["jira", "INFRA-1"]) is open [fact.end]')[0][0]
assert g0.id == g1.id == g2.id and g0.meta == {} and g1.meta["by"] == "ann" and g1.meta["lastchecked"] == "$DATETIME" and g2.meta["note"] == "has } brace" and g2.meta["tags"] == ["a", "b"]  # the same fact
assert (g3.kind, g3.source, g3.meta) == ("mcp", "jira INFRA-1", {}) and g2.source == "https://x.test/a"  # a JSON array of words is the words
for bad, why in (('[fact.url]{by: [ (https://x.test/a) x [fact.end]', "mapping that closes"), ('[fact.url]{a: 1}{b: 2}(https://x.test/a) x [fact.end]', "source in parentheses"),
                 ('[fact.url]("no) x [fact.end]', "JSON string or array"), ('[fact.url]{"a": 1} x [fact.end]', "source in parentheses")):
    assert why in F.parse(bad)[1][0][2], (bad, F.parse(bad)[1])
assert F.meta_problems({"by": 5, "confidence": 7, "tags": "x", "at": "soon", "stale_after": 0, "note": 1}) == ["by", "confidence", "tags", "at", "stale_after", "note"]
assert F.meta_problems({"by": "a", "at": "2026-11-20T10:00:00Z", "as_of": "2026-11-20", "confidence": 0.8, "tags": ["x"], "stale_after": 30, "note": "n", "free": {"any": 1}}) == []
assert F.meta_problems({"confidence": "high", "stale_after": "2026-12-31"}) == [] and F.due({"stale_after": 30}, {"status": "unchecked"}) and not F.due({}, {"status": "unchecked"})
assert F.due({"stale_after": 30}, {"status": "checked", "at": "2000-01-01T00:00:00Z"}) and not F.due({"stale_after": 30}, {"status": "checked", "at": bb.now()})
assert F.due({"stale_after": "2000-01-01"}, {"status": "checked", "at": bb.now()}) and not F.due({"stale_after": "2999-01-01"}, {"status": "checked", "at": bb.now()})
shown_meta, ents = F.render('[fact.url]{by: ann, confidence: high, note: "checked by hand", stale_after: 30}(https://x.test/a) The words. [fact.end]\n', Path(tempfile.mkdtemp()), "p.md")
bibm = F.bibliography(ents)
assert "by ann" in bibm and "confidence high" in bibm and "checked by hand" in bibm and "due for a check" in bibm and "{" not in shown_meta  # shown in the bibliography, and the braces are not in the text


def meta_vault(d):
    (d / "n.md").write_text('[fact.url]{by: ann, stale_after: 30}(https://x.test/z) the freeze is on [fact.end]\n\n[fact.url]{confidence: 7, tags: x}(https://x.test/a) a claim [fact.end]\n')
    rows = bb.fact_rows("n.md")
    assert rows[0]["meta"]["by"] == "ann" and rows[0]["due"] is True and "meta" in rows[1]
    got = [f for f in bb.lint(limit=0)["findings"] if f["kind"] == "bad_fact_meta"]
    assert len(got) == 1 and "confidence, tags" in got[0]["message"] and got[0]["severity"] == "warning", got
in_vault("markdown", {"n.md": "x\n"}, meta_vault)


# `fact` writes the block (ADR-003), in any format: checked first when the kind only reads files, placed where asked, the baseline recorded for an mcp fact
def writer(d):
    import builtins
    (d / "data.txt").write_text("alpha\nbeta\ngamma\n")
    (d / "n.md").write_text("# A\n\n## S1\n\ntext one\n\n## S2\n\ntext two\n")
    got = bb.fact(file="n.md", kind="file", source="data.txt#L2", claim="beta", meta={"by": "claude", "confidence": "high"}, after="S1")
    blk = f'[fact.file]{{"id": 1, "by": "claude", "confidence": "high", "at": "{bb.now()[:10]}", "last_checked": "{bb.now()[:10]}"}}(data.txt#L2) beta [fact.end]'  # the id first, the day it was checked last
    assert got["written"] and got["block"] == blk and got["checked"] == "checked", got
    body = (d / "n.md").read_text()
    assert body.index("## S1") < body.index(blk) < body.index("## S2") and "text one\n\n[fact.file]" in body  # at the end of S1's section
    assert [r["status"] for r in bb.fact_rows("n.md")] == ["checked"] and bb.fact_rows("n.md")[0]["meta"]["by"] == "claude"  # parsed back, and the check is recorded
    assert got["id"] == "1" and F.parse(blk)[0][0].id == "1" and F.parse(blk)[0][0].fp == F.parse("[fact.file](data.txt#L2) beta [fact.end]")[0][0].fp  # the id is the number; the fingerprint ignores the metadata
    assert bb.fact(file="n.md", kind="file", source="data.txt#L1", claim="alpha")["id"] == "2"  # the next number in this document
    refused = raises(bb.fact, file="n.md", kind="file", source="data.txt#L2", claim="alpha")  # alpha is on line 1: not what those lines say
    assert "not written" in refused and "gamma?" not in (d / "n.md").read_text()
    assert bb.fact(file="n.md", kind="file", source="data.txt#L2", claim="alpha", check=False)["written"]  # a person may say they know better
    # the other kinds: no check at write time; a `)` in the source, a JSON list of words, a line number, the end of the file
    assert "(https://x.test/a_(b%29) The words. [fact.end]" in bb.fact(file="n.md", kind="url", source="https://x.test/a_(b)", claim="The words.", after="line:1")["block"]  # a `)` is written %29
    w = bb.fact(file="n.md", kind="mcp", source=["jira", "INFRA-1"], claim="is open")
    assert w["block"].startswith("[fact.mcp]{") and "(jira INFRA-1) is open [fact.end]" in w["block"] and (d / "n.md").read_text().rstrip().endswith("[fact.end]")
    for bad, why in ((dict(kind="nope", source="x", claim="c"), "not a kind of fact"), (dict(kind="key", source="a b", claim="c"), "fact pack"), (dict(kind="url", source="no", claim="c"), "address"),
                     (dict(kind="url", source="https://x.test", claim="a [fact.end] b"), "claim"), (dict(kind="url", source="https://x.test", claim="c", meta={"confidence": 9}), "metadata confidence"),
                     (dict(kind="url", source="https://x.test", claim="c", after="Nope"), "no heading")):
        assert why in raises(bb.fact, file="n.md", **bad), (bad, why)
    assert "is not a file here" in raises(bb.fact, file="gone.md", kind="url", source="https://x.test", claim="c")
    # an mcp fact with its result: the watched value is the baseline, so a later check compares with it
    bb.CFG["facts"] = {"mcp": {"jira": {"tool": "get_issue", "arg": "issue_key", "watch": "fields.status.name"}}}
    try:
        w2 = bb.fact(file="n.md", kind="mcp", source="jira INFRA-2", claim="is in progress", result='{"fields": {"status": {"name": "In Progress"}}}')
        assert F.read_state(d).get(("n.md", w2["id"]), {}).get("value") == "In Progress" and w2["checked"] == "checked"
        # result=- and result=@file are the command line's; an agent over MCP is refused
        (d / "res.json").write_text('{"fields": {"status": {"name": "Done"}}}')
        assert "command line" in raises(bb.fact, file="n.md", kind="mcp", source="jira INFRA-3", claim="done", result="@res.json")
        bb.CLI = True
        try:
            w3 = bb.fact(file="n.md", kind="mcp", source="jira INFRA-3", claim="done", result=f"@{d / 'res.json'}")
            assert F.read_state(d)[("n.md", w3["id"])]["value"] == "Done"
            saved_in = sys.stdin
            sys.stdin = io.StringIO('{"fields": {"status": {"name": "Stdin"}}}')
            try:
                w4 = bb.fact(file="n.md", kind="mcp", source="jira INFRA-4", claim="stdin", result="-")
            finally:
                sys.stdin = saved_in
            assert F.read_state(d)[("n.md", w4["id"])]["value"] == "Stdin"
            # harvest: a person at a terminal picks a passage of a page; an agent cannot
            saved = (builtins.input, bb.at_terminal, F.page_text)
            F.page_text = lambda url, *a, **k: "First paragraph has enough words.\n\nSecond paragraph is the one we quote here.\n\nThird one is also long enough."
            bb.at_terminal = lambda: True
            answers = iter(["y", "2"])
            builtins.input = lambda _="": next(answers)
            try:
                h = bb.fact(file="n.md", kind="url", source="https://x.test/p", harvest=True)
                assert h["written"] and "Second paragraph is the one we quote here. [fact.end]" in h["block"] and "First paragraph" not in h["block"]
                bb.at_terminal = lambda: False
                assert "terminal" in raises(bb.fact, file="n.md", kind="url", source="https://x.test/p", harvest=True)
            finally:
                builtins.input, bb.at_terminal, F.page_text = saved
        finally:
            bb.CLI = False
    finally:
        bb.CFG.pop("facts", None)
    blocks_now = F.parse((d / "n.md").read_text())[0]
    assert not F.parse((d / "n.md").read_text())[1] and sorted(int(b.id) for b in blocks_now) == list(range(1, len(blocks_now) + 1)) and len(blocks_now) >= 8  # every block written reads back, numbered 1 up, nothing else wrong
in_vault("markdown", {"n.md": "x\n"}, writer)

# the same, in an OKF bundle (it goes through the bundle's commit and log), and the older form of `fact` is still there
def writer_okf(d):
    (d / "src.txt").write_text("one two three\n")
    w = bb.fact(file="a", kind="file", source="src.txt", claim="one two three")
    assert w["written"] and "[fact.file]" in (d / "a.md").read_text() and bb.fact_rows("a.md")[0]["status"] == "checked"
    old = bb.fact(file="a", resource="https://x.test/p", title="A page")
    assert old["footnote"] == "[^p]" and "sources" in (d / "a.md").read_text()
in_vault("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n', "a.md": "---\ntype: Note\ndescription: A.\n---\n# A\n\nBody text here.\n"}, writer_okf)


# a fact is its number (`id`, first in its metadata): factcheck takes it, a check stamps `last_checked`, `fix` numbers the old ones, and none of that breaks a seal
def numbered(d):
    (d / "data.txt").write_text("alpha\nbeta\ngamma\n")
    old = "# N\n\n[fact.file](data.txt#L1) alpha [fact.end]\n\n[fact.file]{by: ann}(data.txt#L2) beta [fact.end]\n"
    (d / "n.md").write_text(old)
    h0 = bb.content_hash(old, False)
    h_old = [b.id for b in F.parse(old)[0]]
    assert all(len(i) == 12 for i in h_old)  # no number: the fingerprint is the id, as in 2.2.0
    bb.factcheck(file="n.md", id=h_old[0])  # an agent checks it by its id; the old state is keyed by the fingerprint
    assert bb.fact_rows("n.md")[0]["status"] == "checked"
    stamped = (d / "n.md").read_text()
    assert "{last_checked: " + bb.now()[:10] + "}(data.txt#L1)" in stamped and "{by: ann}" in stamped  # the day is written in the block's own metadata, in its style
    assert bb.content_hash(stamped, False) == h0  # and a seal does not see it
    # fix numbers them, in the first place of the metadata, moves what was checked, and still no seal sees it
    out = bb.fix(apply=True)
    numbered_text = (d / "n.md").read_text()
    assert "{id: 1, last_checked: " in numbered_text and "{id: 2, by: ann}" in numbered_text, numbered_text
    assert [b.id for b in F.parse(numbered_text)[0]] == ["1", "2"] and bb.content_hash(numbered_text, False) == h0
    assert bb.fact_rows("n.md")[0]["status"] == "checked" and bb.fact_rows("n.md")[1]["status"] == "unchecked"  # fact 1 kept its history under its new number
    r = bb.factcheck(file="n.md", id=2)  # a number is fine, as an int or as text
    assert r["checked"][0]["status"] == "checked" and bb.factcheck(file="n.md", id="1")["checked"][0]["id"] == "1"
    # an edited claim keeps its number, and is unchecked until it is checked again; two with one number is an error
    edited = (d / "n.md").read_text().replace("alpha [fact.end]", "alpha beta [fact.end]")
    (d / "n.md").write_text(edited)
    assert bb.fact_rows("n.md")[0]["id"] == "1" and bb.fact_rows("n.md")[0]["status"] == "unchecked"
    assert bb.factcheck(file="n.md", id="1")["checked"][0]["status"] == "drifted"  # "alpha beta" is not what line 1 says
    (d / "n.md").write_text("[fact.url]{id: 1}(https://x.test/a) a [fact.end] [fact.url]{id: 1}(https://x.test/b) b [fact.end]\n")
    assert any(f["kind"] == "duplicate_fact_id" for f in bb.lint(limit=0)["findings"])
    assert "already used" in raises(bb.fact, file="n.md", kind="url", source="https://x.test/c", claim="c", meta={"id": 1})
in_vault("markdown", {"n.md": "x\n"}, numbered)


# seal-extensions is an add-on (addons/seal-extensions): registered through the `bowerbird.seal` entry point; without it a collection that turns extensions on is told what to install, and loses no seal
import importlib.metadata as _im2


def ext_vault(d):
    text = (d / "a.md").read_text()
    saved = (dict(bb.OPTS["seal"]), bb.SEAL_EXT)
    bb.OPTS["seal"] = {**saved[0], "extensions": True, "quorum": 3}
    bb._POLICY.clear()
    try:
        for i, who in enumerate(("ann", "bo"), 1):
            bb.ledger_put("a.md", {"file": "a.md", "sha256": bb.content_hash(text, False), "by": f"human:{who}", "at": f"2026-11-23T10:00:0{i}Z"})
        line = (d / ".waxseals.yaml").read_text()
        assert "quorum: 3" in line and "seals: [" in line, line  # the line says how many it wants, so a badge can say "2 of 3"
        assert [e["by"] for e in bb.ledger_by_file()["a.md"]] == ["human:ann", "human:bo"]
        # the docs hook: who signed, and how many are needed
        os.chdir(d)
        try:
            (d / "p.md").write_text("# P\n\n<!-- seal-banner: x -->\n")
            bb.ledger_put("p.md", {"file": "p.md", "sha256": bb.content_hash((d / "p.md").read_text(), False), "by": "human:ann", "at": "2026-11-23T10:00:01Z"})
            bb.ledger_put("p.md", {"file": "p.md", "sha256": bb.content_hash((d / "p.md").read_text(), False), "by": "human:bo", "at": "2026-11-23T10:00:02Z"})
            made = hk.banner(d / "p.md", "p.md", d, "x", False)
            assert "by ann, bo (2 of 3 needed)" in made and 'data-state="reviewed"' in made, made
        finally:
            os.chdir(HERE)
        # no add-on: writing would keep only the last seal and lose the rest, so it is refused, and the file is untouched
        bb.SEAL_EXT = None
        before = (d / ".waxseals.yaml").read_text()
        assert "seal-extensions add-on" in raises(bb.ledger_put, "a.md", {"file": "a.md", "sha256": bb.content_hash(text, False), "by": "human:cy", "at": "2026-11-23T10:00:09Z"})
        assert (d / ".waxseals.yaml").read_text() == before
        # the entry point registers it
        _orig = _im2.entry_points
        _im2.entry_points = lambda group=None: [_EP("seal-extensions", seal_extensions.register)] if group == "bowerbird.seal" else []
        try:
            bb.load_plugins("bowerbird.seal")
        finally:
            _im2.entry_points = _orig
        assert bb.seal_mod() is not None and bb.seal_mod().signers([{"by": "human:a"}, {"by": "process:x"}]) == {"human:a"}
    finally:
        bb.OPTS["seal"], bb.SEAL_EXT = saved
        bb._POLICY.clear()
in_vault("markdown", {"a.md": "# A\n\nbody\n"}, ext_vault)


# seal.count: the number of different people who hold a file is its importance: shown in list and passages, a little rank in a search, and the most sealed in `seal check`
def counted(d):
    saved = (dict(bb.OPTS["seal"]), bb.SEAL_EXT)
    try:
        for n in ("a", "b"):
            (d / f"{n}.md").write_text(f"# {n.upper()}\n\nThe quokka lives here.\n")
        bb.OPTS["seal"] = {**saved[0], "extensions": True, "quorum": 1}
        bb._POLICY.clear()
        for f, who in (("a.md", "ann"), ("b.md", "ann"), ("b.md", "bo")):
            bb.ledger_put(f, {"file": f, "sha256": bb.content_hash((d / f).read_text(), False), "by": f"human:{who}", "at": "2026-11-23T10:00:00Z"})
        order = lambda: [h["file"] for h in bb.passages("quokka")["hits"]]
        assert order() == ["a.md", "b.md"] and "seals" not in bb.passages("quokka")["hits"][0] and "most_sealed" not in bb.signatures()  # off: a tie, by path
        assert "seals" not in bb.list_(limit=0)["concepts"][0]
        bb.OPTS["seal"] = {**saved[0], "extensions": True, "quorum": 1, "count": True}
        bb._POLICY.clear()
        assert order() == ["b.md", "a.md"]  # on: two people hold b.md, one holds a.md
        assert {h["file"]: h["seals"] for h in bb.passages("quokka")["hits"]} == {"a.md": 1, "b.md": 2}
        assert {c["file"]: c["seals"] for c in bb.list_(limit=0)["concepts"]} == {"a.md": 1, "b.md": 2}
        assert bb.signatures()["most_sealed"] == [{"file": "b.md", "seals": 2}, {"file": "a.md", "seals": 1}]
        bb.ledger_put("a.md", {"file": "a.md", "sha256": bb.content_hash((d / "a.md").read_text(), False), "by": "process:ci", "at": "2026-11-23T11:00:00Z"})  # a machine's check is not a person
        assert {c["file"]: c["seals"] for c in bb.list_(limit=0)["concepts"]} == {"a.md": 1, "b.md": 2}  # the count is a human signal: process:ci is not in it
        (d / "b.md").write_text("# B\n\nThe quokka lives here, edited.\n")  # an edit ends the seals: only live ones count
        assert {c["file"]: c["seals"] for c in bb.list_(limit=0)["concepts"]} == {"a.md": 1, "b.md": 0} and bb.signatures()["most_sealed"] == [{"file": "a.md", "seals": 1}]
        bb.SEAL_EXT = None
        assert "seal-extensions add-on" in raises(bb.list_, limit=0)  # counting needs the add-on
    finally:
        bb.OPTS["seal"], bb.SEAL_EXT = saved
        bb._POLICY.clear()
    for bad in ("seal: {count: true}\n", "seal: {extensions: true, count: 3}\n"):  # counting needs extensions, and is true or false
        (lg / "bower.yaml").write_text(bad)
        try:
            bb.load_config(lg)
            raise AssertionError(bad)
        except SystemExit as e:
            assert "seal.count" in str(e), (bad, str(e))
    (lg / "bower.yaml").write_text("seal: {extensions: true, count: true}\n")
    assert bb.load_config(lg)[1]["seal"]["count"] is True
    (lg / "bower.yaml").unlink()
in_vault("markdown", {"a.md": "x\n"}, counted)


# an OKF concept's seal is in its frontmatter and goes stale when the text is edited: `list` says so, as a search and `seal check` do
def okf_stale(d):
    bb.ATTEST = "human:ann"
    try:
        asyncio.run(bb.seal(file="a"))
    finally:
        bb.ATTEST = ""
    tier = lambda: {c["file"]: c["tier"] for c in bb.list_(limit=0)["concepts"]}["a.md"]
    assert tier() == "human-reviewed"
    (d / "a.md").write_text((d / "a.md").read_text().replace("Body text", "Changed body text"))
    assert tier() == "unverified" and [h["tier"] for h in bb.passages("changed")["hits"]] == ["unverified"] and bb.status()["by_tier"].get("human-reviewed", 0) == 0
in_vault("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n', "a.md": "---\ntype: Note\ndescription: A.\n---\n# A\n\nBody text that is long enough to not be a stub here.\n"}, okf_stale)


# the review and the facts of one file as data (page_state; /_api/status in serve)
def state_vault(d):
    (d / "a.md").write_text("# A\n\nbody\n\n[fact.url]{id: 1, by: ann}(https://x.test/a) The words. [fact.end]\n")
    (d / ".hidden.md").write_text("x\n")
    s = bb.page_state("a.md")
    assert s["file"] == "a.md" and s["seal"]["state"] == "unsealed" and s["seal"]["signers"] == [] and s["seal"]["quorum"] is None
    assert [(f["id"], f["kind"], f["status"], f["meta"]["by"]) for f in s["facts"]] == [("1", "url", "unchecked", "ann")]
    bb.ledger_put("a.md", {"file": "a.md", "sha256": bb.content_hash((d / "a.md").read_text(), False), "by": "human:ann", "at": "2026-11-23T10:00:00Z", "comment": "read it"})
    s = bb.page_state("a.md")
    assert s["seal"]["state"] == "sealed" and s["seal"]["by"] == "human:ann" and s["seal"]["signers"] == [{"by": "human:ann", "at": "2026-11-23T10:00:00Z", "comment": "read it"}]
    (d / "a.md").write_text((d / "a.md").read_text() + "edited\n")
    assert bb.page_state("a.md")["seal"]["state"] == "broken-seal" and bb.page_state("a.md")["seal"]["signers"] == []
    for bad in (".hidden.md", "../x.md", "nope.md"):
        raises(bb.page_state, bad)
in_vault("markdown", {"a.md": "x\n"}, state_vault)


# an add-on found through its entry point as the module is imported, in a fresh interpreter (a hand registration in a test does not prove the loader works)
def entry_points_really():
    site = Path(tempfile.mkdtemp())
    (site / "fakeseal.py").write_text("import types\ndef register(bb):\n    bb.register_seal_extension(types.SimpleNamespace(merge=None, collapse=None, signers=lambda v: set(), expand=None, marker='real'))\n")
    di = site / "fakeseal-1.0.dist-info"
    di.mkdir()
    (di / "METADATA").write_text("Metadata-Version: 2.1\nName: fakeseal\nVersion: 1.0\n")
    (di / "entry_points.txt").write_text("[bowerbird.seal]\nfakeseal = fakeseal:register\n")
    r = subprocess.run([sys.executable, "-c", "import bowerbird_mcp as b; print(getattr(b.seal_mod(), 'marker', None))"], cwd=HERE, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(site)}, check=False)
    assert r.stdout.strip() == "real" and "did not load" not in r.stderr, (r.stdout, r.stderr[-300:])  # the add-on registered while the module was still being imported
entry_points_really()


def fact_sources(d):
    (d / "n.md").write_text("# N\n\n[fact.until](2999-01-01) the freeze is on [fact.end]\n\n[fact.url]{id: 2}(https://x.test/a) words [fact.end]\n\n[fact.file]{id: 3}(gone.txt#L1) words [fact.end]\n\nSee [real](nope.md).\n")
    got = [(f["kind"], f["message"]) for f in bb.lint(limit=0)["findings"] if f["kind"] == "dead_link"]
    assert got == [("dead_link", "link to nope.md does not resolve")], got  # a fact's source is not a link: only the real broken link is said
    assert bb.hrefs((d / "n.md").read_text()) == ["nope.md"]
in_vault("markdown", {"n.md": "x\n"}, fact_sources)


# the collection's files as resources: bowerbird://{bower}/{path}; the root is a bower, named by its folder; read-only, confined, no dotfiles.
rs2, rs2_saved = Path(tempfile.mkdtemp()).resolve() / "wiki", (bb.ROOT, dict(bb.OPTS))
(rs2 / "docs/sub").mkdir(parents=True)
(rs2 / "bower.yaml").write_text("format: markdown\nbowers: [docs]\n")
(rs2 / "docs/bower.yaml").write_text("format: markdown\n")
(rs2 / "a.md").write_text("# A\nline two\nline three\n")
(rs2 / "docs/sub/b c.md").write_text("# B\n")
(rs2 / ".env").write_text("SECRET=1\n")
(rs2 / "note.txt").write_text("not a concept\n")
(rs2 / "link.md").symlink_to(rs2 / "a.md")
bb.ROOT = rs2
bb.OPTS["format"] = "markdown"
bb._SCOPES.clear()
bb._POLICY.clear()
rd = lambda uri: asyncio.run(bb.read_resource(AnyUrl(uri)))
try:
    assert bb.resource_uri(rs2 / "a.md") == "bowerbird://wiki/a.md"  # the root bower, named by its folder
    assert bb.resource_uri(rs2 / "docs/sub/b c.md") == "bowerbird://docs/sub/b%20c.md"  # a bower below it: its path is the first segment
    listed = {str(r.uri) for r in asyncio.run(bb.list_resources())}
    assert {"bowerbird://wiki/a.md", "bowerbird://docs/sub/b%20c.md", "bowerbird://agent-rules", "okf://spec"} <= listed
    assert not any(".env" in u for u in listed)
    assert rd("bowerbird://wiki/a.md")[0].content == "# A\nline two\nline three\n" and rd("bowerbird://docs/sub/b%20c.md")[0].content == "# B\n"
    assert rd("bowerbird://wiki/a.md?lines=2-3")[0].content == "line two\nline three\n" and rd("bowerbird://wiki/a.md?lines=3-3")[0].content == "line three\n"
    assert rd("bowerbird://agent-rules")[0].content == bb.AGENTS_MD  # the static ones still go to FastMCP
    for bad in ("bowerbird://wiki/.env", "bowerbird://wiki/../outside.md", "bowerbird://wiki/link.md", "bowerbird://wiki/docs", "bowerbird://nope/a.md",
                "bowerbird://wiki/%2e%2e/x.md", "bowerbird://wiki/missing.md"):
        assert "ValueError" in raises(rd, bad) + "ValueError", bad
    assert "names no bower" in raises(rd, "bowerbird://nope/a.md") and "outside" in raises(rd, "bowerbird://wiki/../outside.md")
    bb.OPTS["roles"] = ["write"]  # without the read role the files are not offered, and not read
    assert not any("wiki" in str(r.uri) for r in asyncio.run(bb.list_resources()))
finally:
    bb.ROOT = rs2_saved[0]
    bb.OPTS.clear()
    bb.OPTS.update(rs2_saved[1])
    bb._SCOPES.clear()
    bb._POLICY.clear()


# the docs hook shows each fact block with its state, from the .facts.yaml beside the page, and leaves code alone.
fh = Path(tempfile.mkdtemp()).resolve()
fpage = fh / "p.md"
fsrc = ("Intro.\n\n[fact.url](https://x.test/a)\nThe page says this.\n\nAnd this.\n[fact.end]\n\nOne-liner: [fact.url](https://x.test/b) short claim [fact.end] and "
        "[fact.mcp](jira K-1) is open [fact.end].\n\n```\n[fact.url](https://x.test/c) in code [fact.end]\n```\n")
fpage.write_text(fsrc)
fblocks = F.parse(fsrc)[0]
F.record(fh, "p.md", fblocks[0].id, "url", fblocks[0].source, "checked", "same words", "2026-11-20T10:00:00Z")
F.record(fh, "p.md", fblocks[2].id, "mcp", fblocks[2].source, "drifted", "was 'Open', now 'Closed'", "2026-11-21T10:00:00Z", "Open")
shown = hk.facts(fsrc, fpage)
assert "[fact." not in shown.replace("[fact.url](https://x.test/c) in code [fact.end]", "")  # no tag survives outside the code block
assert '> The page says this.\n>\n> And this.\n>\n> <a class="fact-badge" data-state="checked" href="#fact-1">checked 2026-11-20 (same words)</a> <a href="https://x.test/a">source</a>' in shown
assert "[short claim](https://x.test/b) <a class=\"fact-badge\" data-state=\"unchecked\" href=\"#fact-2\">not yet checked</a>" in shown  # an address links the claim
assert 'jira K-1 is open <a class="fact-badge" data-state="drifted" href="#fact-3">drifted 2026-11-21' in shown  # a server and key read before it
assert "[fact.url](https://x.test/c) in code [fact.end]" in shown  # an example in code is not a fact
bib = shown[shown.index('<section class="fact-bib"'):]  # the bibliography: an entry for each block, each with the id its badge links to
assert [f'id="fact-{n}"' in bib for n in (1, 2, 3)] == [True] * 3 and 'id="fact-4"' not in bib and "https://x.test/a" in bib and "drifted 2026-11-21" in bib and "in code" not in bib
ents = F.render(fsrc, fh, "p.md")[1]
assert [(e["n"], e["kind"], e["status"], e["line"]) for e in ents] == [(1, "url", "checked", 3), (2, "url", "unchecked", 9), (3, "mcp", "drifted", 9)]  # the data both the hook and serve use
assert F.bibliography([]) == "" and "[fact." not in hk.facts("No facts here.\n", fpage)


# the registry of fact kinds: url, mcp, file and internal are registered; a new kind is one register() call, and parse, lint and the check all know it.
assert set(F.FACT_TYPES) == {"url", "mcp", "file", "internal"} and F.FACT_TYPES["url"].check is bb.fact_check_url and F.FACT_TYPES["mcp"].plan is bb.fact_plan_mcp
assert F.FACT_TYPES["file"].check is bb.fact_check_file and F.FACT_TYPES["internal"].check is bb.fact_check_internal and F.FACT_TYPES["file"].local and not F.FACT_TYPES["url"].local
assert F.parse("[fact.bogus](a.py#L1-2) x [fact.end]")[1][0][1] == "unknown_fact_kind" and "fact.url, fact.mcp, fact.file, fact.internal" in F.parse("[fact.bogus](a.py) x [fact.end]")[1][0][2]
F.register("doc", "src/app.py#L10-20", lambda s: None if re.fullmatch(r"[\w./-]+(#L\d+-\d+)?", s) else f"needs a path, got {s!r}")
try:
    fblk, fprob = F.parse("[fact.doc](src/app.py#L1-2) the limit is 5 [fact.end] and [fact.doc](a b) x [fact.end]")
    assert [(b.kind, b.source, b.claim) for b in fblk] == [("doc", "src/app.py#L1-2", "the limit is 5")] and fprob[0][1] == "bad_fact" and "src/app.py#L10-20" in fprob[0][2]
    assert "doc" in F.FACT_TYPES and F.FACT_TYPES["doc"].check is None  # registered, with no check yet: `factcheck --fetch` says so and records nothing
finally:
    del F.FACT_TYPES["doc"]
assert "doc" not in F.FACT_TYPES


# declared kinds of fact (facts: types: in the root bower.yaml) and `create --facts`.
for bad in ("facts: {types: {url: {server: s, tool: t, arg: a}}}\n", "facts: {types: {Bad1: {server: s, tool: t, arg: a}}}\n", "facts: {types: {ticket: {tool: t, arg: a}}}\n",
            "facts: {nope: 1}\n"):
    (lg / "bower.yaml").write_text(bad)
    try:
        bb.load_config(lg)
        raise AssertionError(bad)
    except SystemExit as e:
        assert "facts takes" in str(e), (bad, str(e))
(lg / "bower.yaml").write_text("facts: {types: {ticket: {server: jira, tool: get_issue, arg: issue_key, watch: fields.status.name}}}\n")
assert bb.load_config(lg)[1]["facts"]["types"]["ticket"]["server"] == "jira"
(lg / "bower.yaml").unlink()
fr, fr_saved = fk, (bb.ROOT, bb.CLI, bb.at_terminal, builtins.input, dict(bb.OPTS))
bb.ROOT, bb.CLI, bb.OPTS["format"], bb.at_terminal, builtins.input = fr, True, "markdown", (lambda: True), (lambda *a: "y")
bb.declared_type("ticket", {"server": "jira", "tool": "get_issue", "arg": "issue_key", "watch": "fields.status.name"})
(fr / "status.txt").write_text("Open\n")
(fr / "notes.md").write_text("The ticket: [fact.ticket](INFRA-9) is open [fact.end]\n")
try:
    assert [(b.kind, b.source, b.claim) for b in F.parse((fr / "notes.md").read_text())[0]] == [("ticket", "INFRA-9", "is open")]
    assert F.parse("[fact.ticket](a b) x [fact.end]")[1][0][1] == "bad_fact" and F.parse("[fact.ticket](INFRA-9) x")[1][0][1] == "unclosed_fact"
    r = bb.factcheck(fetch=True)["checked"]
    assert [(x["kind"], x["status"], x["method"]) for x in r] == [("ticket", "checked", "baseline recorded")], r  # no server in the source: the type names it
    (fr / "status.txt").write_text("Closed\n")
    r = bb.factcheck(fetch=True)
    assert r["drifted"] == 1 and "Closed" in r["checked"][0]["method"]
finally:
    del F.FACT_TYPES["ticket"]
    bb.ROOT, bb.CLI, bb.at_terminal, builtins.input = fr_saved[:4]
    bb.OPTS.clear()
    bb.OPTS.update(fr_saved[4])
assert [b.kind for b in F.parse("[fact.ticket](INFRA-9) x [fact.end]", strict=False)[0]] == ["ticket"] and F.parse("[fact.ticket](INFRA-9) x [fact.end]")[1][0][1] == "unknown_fact_kind"
servers = {"jira": {"command": "jira-mcp"}, "claude_ai_Slack": {"command": "x"}, "bowerbird": {"command": "uvx", "args": ["--from", "bowerbird-mcp>=2,<3", "bowerbird-mcp"]},
           "bowerbird-read": {"command": "uvx", "args": ["bowerbird-mcp", "--role", "read"]}, "mine": {"command": "uv", "args": ["run", "bowerbird_mcp.py"]},
           "docs": {"command": "uv", "args": ["run", "/home/me/bowerbird-mcp/other_server.py"]}}
mj = Path(tempfile.mkdtemp()).resolve()
(mj / ".mcp.json").write_text(json.dumps({"mcpServers": servers}))
assert set(bb.mcp_servers(mj)) == {"jira", "claude_ai_Slack", "docs"}  # Bowerbird itself, however it is started, is left out; a path that merely contains the name is not it
assert bb.mcp_servers(mj / "nowhere") == {} and "TOOL" in bb.facts_stub(bb.mcp_servers(mj)) and "bowerbird" not in bb.facts_stub(bb.mcp_servers(mj)).split("\n", 1)[1]
for sub_ in ("new", "partial"):
    (mj / sub_).mkdir()
    (mj / sub_ / ".mcp.json").write_text(json.dumps({"mcpServers": servers}))
(mj / "partial/bower.yaml").write_text("about: Partial.\nformat: markdown\n")
saved_root = bb.ROOT
try:
    P = create(path=str(mj / "new"), holds="markdown", about="N.", user="u", facts=True)  # a preview writes nothing
    assert P["facts"]["state"] == "would write" and not (mj / "new/bower.yaml").exists() and P["facts"]["servers"] == ["claude_ai_Slack", "docs", "jira"]
    create(path=str(mj / "new"), holds="markdown", about="N.", user="u", facts=True, apply=True)  # a new collection: only the facts step, and bower.yaml
    assert sorted(p.name for p in (mj / "new").iterdir()) == [".mcp.json", "bower.yaml"] and "claudeaislack: {server: claude_ai_Slack" in (mj / "new/bower.yaml").read_text()
    assert bb.yaml.safe_load((mj / "new/bower.yaml").read_text()) == {"about": "N.", "format": "markdown", "passages": True, "hubs": True, "semantic": False,
                                                                       "semantic_model": bb.DEFAULTS["semantic_model"], "min_similarity": bb.DEFAULTS["min_similarity"], "index": bb.DEFAULTS["index"]}  # still valid: it is all comments
    P = create(path=str(mj / "partial"), facts=True, apply=True)  # a partial bower.yaml gets the block added, nothing else touched
    assert P["facts"]["state"] == "written" and (mj / "partial/bower.yaml").read_text().startswith("about: Partial.\nformat: markdown\n\n# Found by `create --facts`")
    assert create(path=str(mj / "partial"), facts=True)["facts"]["state"] == "already there"  # again: nothing to add
    (mj / "partial/bower.yaml").write_text("about: Partial.\nfacts: {mcp: {}}\n")
    assert create(path=str(mj / "partial"), facts=True)["facts"]["state"] == "bower.yaml already declares facts"
    (mj / "partial/bower.yaml").write_text("format: [unclosed\n")  # a broken one is said, and left alone
    P = create(path=str(mj / "partial"), facts=True, apply=True)
    assert "does not parse" in P["ignored"][0] and (mj / "partial/bower.yaml").read_text() == "format: [unclosed\n"
finally:
    bb.ROOT = saved_root


# a generated folder: one ledger line for the folder, blue "derived" for everything under it (binaries included), exempt, and no orphan warning.
gd, gd_saved = Path(tempfile.mkdtemp()).resolve(), (bb.ROOT, bb.CLI, dict(bb.OPTS))
(gd / "bower.yaml").write_text("format: seal-only\n")
(gd / "site/img").mkdir(parents=True)
(gd / "site/index.html").write_text("<p>built</p>\n")
(gd / "site/img/logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff")
(gd / "hand.txt").write_text("written by a person\n")
bb.ROOT, bb.CLI, bb.OPTS["format"], bb.OPTS["seal"] = gd, True, "seal-only", {"exempt": [], "exempt_status": []}
bb._SCOPES.clear()
bb._POLICY.clear()
try:
    assert {f["file"] for f in bb.signatures("")["findings"]} >= {"site/index.html", "hand.txt"}  # unreviewed, both
    done = bb.mark_derived_dir(gd / "site", "mkdocs")
    assert done[0] == ".waxseals.yaml" and "seal.exempt gets /site/**" in done[1], done
    assert "seal: {exempt: [/site/**]}" in (gd / "bower.yaml").read_text().replace('"', "").replace("'", "") or "/site/**" in (gd / "bower.yaml").read_text()
    assert bb.derived(gd / "site/index.html") and bb.derived(gd / "site/img/logo.png") and not bb.derived(gd / "hand.txt")  # by location; a binary too
    assert {f["file"] for f in bb.signatures("")["findings"]} == {"hand.txt"}  # nobody seals it, and the folder's line is not an orphan
    assert [p.name for p in bb.derived_files()] == ["logo.png", "index.html"] or {p.name for p in bb.derived_files()} == {"index.html", "logo.png"}
    assert bb.mark_derived_dir(gd / "site", "mkdocs") == []  # nothing to change the second time
    assert [e["file"] for e in bb.ledger_all(gd / ".waxseals.yaml").get("site/", [])] == ["site/"] and not bb.reviews({}, "site/index.html", "x", bb.ledger_by_file())[0]
finally:
    bb.ROOT, bb.CLI = gd_saved[:2]
    bb.OPTS.clear()
    bb.OPTS.update(gd_saved[2])
    bb._SCOPES.clear()
    bb._POLICY.clear()


# okf export and import: a concept's reviews and sources between its frontmatter and the ledgers; a person's command, a preview until --apply.
import bowerbird_okf as O

ok_, ok_saved = Path(tempfile.mkdtemp()).resolve(), (bb.ROOT, bb.CLI, dict(bb.OPTS), bb.at_terminal)
(ok_ / "bower.yaml").write_text("format: okf\nseal: {extensions: true}\n")
(ok_ / "index.md").write_text('---\nokf_version: "0.2"\n---\n# T\n')
bb.ROOT, bb.CLI, bb.OPTS["format"], bb.OPTS["seal"], bb.at_terminal = ok_, True, "okf", {"exempt": [], "exempt_status": [], "extensions": True, "quorum": 1}, (lambda: True)
bb._SCOPES.clear()
bb._POLICY.clear()
try:
    note = ok_ / "note.md"
    note.write_text("---\ntype: Note\ndescription: d\nsources:\n- id: pg\n  resource: https://x.test/p\n  retrieved_at: 2026-11-18T10:00:00Z\n  fact_sha256: abc123\n---\n# N\n\nThe claim.[^pg]\n")
    h = bb.content_hash(note.read_text(), True)
    note.write_text(bb.put(note.read_text(), "verified", [
        {"by": "human:ann", "at": "2026-11-19T10:00:00Z", "sha256": h, "comment": "ok"}, {"by": "human:bo", "at": "2026-11-20T10:00:00Z", "sha256": h},
        {"by": "human:old", "at": "2026-11-01T10:00:00Z", "sha256": "0000"}]))
    before = note.read_bytes()
    out = O.export_(bb, "", False)  # a preview writes nothing
    assert len(out) == 1 and "2 review(s) to .waxseals.yaml" in out[0] and "1 stale review(s) stay behind" in out[0] and "source pg to .facts.yaml" in out[0], out
    assert not (ok_ / ".waxseals.yaml").exists() and not (ok_ / ".facts.yaml").exists()
    O.export_(bb, "", True)
    led = bb.ledger_all(ok_ / ".waxseals.yaml")["note.md"]
    assert [(e["by"], e.get("comment")) for e in led] == [("human:ann", "ok"), ("human:bo", None)] and all(e["sha256"] == bb.content_hash(note.read_text(), False) for e in led)
    st = F.read_state(ok_)[("note.md", "pg")]
    assert st["kind"] == "source" and st["value"] == "abc123" and st["at"].startswith("2026-11-18") and note.read_bytes() == before  # the document is untouched
    assert O.export_(bb, "", True) == []  # again: nothing to move
    # import into a fresh concept that has no frontmatter history: the ledgers fill it in
    fresh = ok_ / "fresh.md"
    fresh.write_text("---\ntype: Note\ndescription: d\n---\n# F\n")
    fh = bb.content_hash(fresh.read_text(), False)
    cur = bb.ledger_all(ok_ / ".waxseals.yaml")  # one line holds the seals of one set of bytes
    cur["fresh.md"] = [{"file": "fresh.md", "sha256": fh, "by": "human:cy", "at": "2026-11-20T11:00:00Z", "comment": "from the ledger"}]
    bb.write(ok_ / ".waxseals.yaml", bb.ledger_text(cur))
    F.record(ok_, "fresh.md", "abcdef123456", "url", "https://x.test/q", "checked", "same words", "2026-11-21T09:00:00Z")
    out = O.import_(bb, str(fresh), False)
    assert out and "+1 review(s)" in out[0] and fresh.read_text() == "---\ntype: Note\ndescription: d\n---\n# F\n"  # a preview writes nothing
    assert "end" in out[0], out  # the source it adds changes the bytes: the review that held would end
    O.import_(bb, str(fresh), True)
    d2 = bb.meta(fresh.read_text())[0]
    assert [(e["by"], e.get("comment")) for e in bb.entries(d2["verified"])] == [("human:cy", "from the ledger")]
    assert d2["sources"] == [{"id": "abcdef123456", "resource": "https://x.test/q", "retrieved_at": "2026-11-21T09:00:00Z"}]
    assert bb.trust_tier(bb.signed(d2, "fresh.md", {})) != "human-reviewed"  # the sources changed the bytes: a new seal verifies what loaded
    assert O.import_(bb, str(fresh), True) == []  # again: nothing to move
    # a review that is already stale loads as stale history, and nothing ends
    stale = ok_ / "stale.md"
    stale.write_text("---\ntype: Note\ndescription: d\n---\n# S\n")
    cur = bb.ledger_all(ok_ / ".waxseals.yaml")
    cur["stale.md"] = [{"file": "stale.md", "sha256": "dead", "by": "human:di", "at": "2026-11-10T11:00:00Z"}]
    bb.write(ok_ / ".waxseals.yaml", bb.ledger_text(cur))
    out = O.import_(bb, str(stale), True)
    assert out == ["stale.md: +1 review(s), 0 source(s) updated"], out
    assert [e["sha256"] for e in bb.entries(bb.meta(stale.read_text())[0]["verified"])] == ["dead"] and bb.trust_tier(bb.signed(bb.meta(stale.read_text())[0], "stale.md", {})) != "human-reviewed"
    # a concept whose bytes the import does not change keeps its review
    quiet = ok_ / "quiet.md"
    quiet.write_text("---\ntype: Note\ndescription: d\n---\n# Q\n")
    qh = bb.content_hash(quiet.read_text(), False)
    bb.ledger_put("quiet.md", {"file": "quiet.md", "sha256": qh, "by": "human:ed", "at": "2026-11-20T12:00:00Z"})
    O.import_(bb, str(quiet), True)
    assert bb.trust_tier(bb.signed(bb.meta(quiet.read_text())[0], "quiet.md", {})) == "human-reviewed"
    # the command: a person's, at a terminal, never a tool
    assert "okf" not in bb.REG and O.main(bb, ["nope"]) == 2 and O.main(bb, []) == 0
    bb.at_terminal = lambda: False
    assert O.main(bb, ["export"]) == 2
finally:
    bb.ROOT, bb.CLI, bb.at_terminal = ok_saved[0], ok_saved[1], ok_saved[3]
    bb.OPTS.clear()
    bb.OPTS.update(ok_saved[2])
    bb._SCOPES.clear()
    bb._POLICY.clear()


# sealing a folder says why it cannot be, and names a file to seal instead.
fd, fd_saved = Path(tempfile.mkdtemp()).resolve(), (bb.ROOT, bb.CLI, dict(bb.OPTS))
(fd / "bower.yaml").write_text("format: seal-only\n")
(fd / "formats").mkdir()
(fd / "formats/a.md").write_text("# a\n")
(fd / "formats/.hidden").write_text("x\n")
(fd / "empty").mkdir()
bb.ROOT, bb.CLI, bb.OPTS["format"] = fd, True, "seal-only"
bb._SCOPES.clear()
bb._POLICY.clear()
try:
    msg = raises(lambda: asyncio.run(bb.seal(file="formats", by="process:t")))
    assert "formats is a folder, and a seal covers one file" in msg and "such as formats/a.md (1 files here)" in msg, msg
    assert "holds no files" in raises(lambda: asyncio.run(bb.seal(file="empty", by="process:t")))
    assert asyncio.run(bb.seal(file="formats/a.md", by="process:t"))["file"] == "formats/a.md"
finally:
    bb.ROOT, bb.CLI = fd_saved[:2]
    bb.OPTS.clear()
    bb.OPTS.update(fd_saved[2])
    bb._SCOPES.clear()
    bb._POLICY.clear()

print("ok")
