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

HERE = Path(__file__).resolve().parent
kb = Path(tempfile.mkdtemp()) / "kb"
kb.mkdir()
os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
(kb / "kbmcp.yaml").write_text("")  # the config file marks the collection root
sys.argv[1:] = ["--config", str(kb / "kbmcp.yaml")]
sys.path.insert(0, str(HERE))
import bowerbird_mcp as k


def create(**kw):
    return asyncio.run(k.create(**kw))

del sys.argv[1:]
k.CFG_DIR = None  # the tests swap KB_ROOT around; keep each one's index inside its own root

TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def kinds(**kw):
    return {f["kind"] for f in k.lint(limit=0, **kw)["findings"]}


def raises(fn, *a, **kw):
    try:
        out = fn(*a, **kw)
        if asyncio.iscoroutine(out):
            asyncio.run(out)
    except ValueError as e:
        return str(e)
    raise SystemExit(f"{fn.__name__} did not refuse")


def cli(*argv):
    k.at_terminal = lambda: True  # tests stand in for a human at a terminal
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = k.cli(list(argv))
    k.CLI, k.ATTEST = False, ""
    return code, buf.getvalue()


# init: a new bundle is conformant and clean; a second init refuses.
assert create()["would_edit"] == {".": ["index.md", "log.md"]}
create(apply=True)
assert k.lint()["ok"] and k.lint()["conformant"], k.lint()
raises(k.create, apply=True)

# A bundle with only a concept lints (no index, no log, no layout).
(kb / "bare").mkdir()
(kb / "bare/a.md").write_text("---\ntype: Note\n---\nhi\n")
assert k.lint(bundle="bare")["ok"]

# SPEC.md's own examples: conformant, no okf errors. Their /tables/... links are dead here (house).
spec = (HERE / "SPEC.md").read_text()
blocks = re.findall(r"```markdown\n(.*?)```", spec, re.DOTALL)
(kb / "spec").mkdir()
for i, b in enumerate(x for x in blocks if x.startswith("---\n")):
    (kb / f"spec/ex{i}.md").write_text(b)
(kb / "spec/log.md").write_text(next(b for b in blocks if b.startswith("# Directory Update Log")))
assert len(list((kb / "spec").glob("ex*.md"))) >= 6
L = k.lint(scope="okf", bundle="spec", limit=0)
assert L["ok"] and L["conformant"], L
assert "dead_link" in kinds(bundle="spec")  # §6.1: / is the bundle root, and is checked
shutil.rmtree(kb / "spec")
shutil.rmtree(kb / "bare")

# One bad fixture per check.
(kb / "bad").mkdir()


def check(text, kind, name="x.md"):
    p = kb / "bad" / name
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
assert k.tidied("# Log\n\n## 2026-01-01\n\n* <!-- 1 --> old\n\n## 2026-02-01\n\n* <!-- 5 --> x\n\n"
                "## 2026-02-01\n\n* <!-- 9 --> y\n* <!-- 5 --> x\n") == (
    "# Log\n\n## 2026-02-01\n\n* <!-- 9 --> y\n* <!-- 5 --> x\n\n## 2026-01-01\n\n* <!-- 1 --> old\n")
check("---\nokf_version: '9.9'\n---\n", "okf_version", "index.md")
check("---\ntype: x\n---\n", "odd_filename", "a b.md")
check("---\ntype: x\n---\n", "no_description")
check("---\ntype: x\n---\n", "orphan")
check("---\ntype: Attested Computation\n---\n", "bad_computation")
check("---\ntype: x\n---\n# Real\n\n[a](#nope)\n", "dead_anchor")
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
assert k.secrets("tok ghp_" + "a" * 36 + "\nfine\n") == [(1, "GitHub token")]
assert not k.secrets("see https://example.com/a and ghp_short and sk-tiny\n")
(kb / "bad/leak.md").write_text("---\ntype: x\n---\nkey: AKIAIOSFODNN7EXAMPLE\n")
L = k.lint(bundle="bad", limit=0)
assert not L["ok"] and "AKIAIOSFODNN7EXAMPLE" not in json.dumps(L)  # named by kind and line, never the value
(kb / "bad/leak.md").unlink()
sec = Path(tempfile.mkdtemp())  # ingest leaves a file with a credential behind, and says why
(sec / "ok.md").write_text("# Fine\n")
(sec / "leak.md").write_text("# Leak\n\ntoken: glpat-" + "x" * 20 + "\n")
plan = k.ingest(str(sec), bundle="bad")
assert plan["ingest"] == 1 and plan["secrets"]["skipped"] == 1
assert any(f["file"] == "leak.md" and "GitLab token on line 3" in f["reason"] for f in plan["skipped_files"])
for c in ("parameters: [{name: year}]", "executor: {receipt: [job_id]}", "computation: x.sql\n---\n# Computation\n"):
    check(f"---\ntype: Attested Computation\nruntime: bigquery\n{c}" + ("" if "---" in c else "\n---\n# Computation\n"),
          "bad_computation")
check("---\ntype: x\ntimestamp: '2026-01-01T00:00:00Z'\n"  # §13.1: timestamp stands in for generated.at
      "sources: [{id: s, resource: r, last_modified: '2026-02-01T00:00:00Z'}]\n---\n", "source_changed")
(kb / "bad/dep.md").write_text("---\ntype: x\nstatus: deprecated\n---\n")
check("---\ntype: x\n---\n[o](dep.md)\n", "deprecated_link")
(kb / "bad/dep.md").unlink()
(kb / "bad/y.md").write_text("---\ntype: x\n---\n# Real Thing\n\n[a](#real-thing)\n")
assert "dead_anchor" not in kinds(bundle="bad")
(kb / "bad/y.md").unlink()
assert not kinds(bundle="bad")
(kb / "bad/e.md").write_text("---\ntype: x\n---")  # closing --- at end of file, no newline
assert k.lint(bundle="bad")["ok"] and "bad_yaml" not in kinds(bundle="bad")
(kb / "bad/e.md").unlink()
(kb / "bad/w.md").write_text("---\ntype: x\n---\n")
(kb / "bad/W.md").write_text("---\ntype: x\n---\n")
if not (kb / "bad/w.md").samefile(kb / "bad/W.md"):  # case-sensitive file system
    assert "case_collision" in kinds(bundle="bad") and k.lint(bundle="bad")["ok"]  # warnings do not fail
for p in (kb / "bad").glob("*.md"):
    p.unlink()

# baseline: old findings stop counting, new ones still fail.
(kb / "bad/old.md").write_text("no frontmatter\n")
assert not k.lint(bundle="bad")["ok"]
k.baseline(apply=True, bundle="bad")
assert k.lint(bundle="bad", baseline=".okf-baseline.json")["ok"]
(kb / "bad/new.md").write_text("no frontmatter either\n")
L = k.lint(bundle="bad", baseline=".okf-baseline.json")
assert not L["ok"] and L["total"] == 1 and L["baselined"] == 1

# kbmcp.nolint: gitignore-style patterns; lint skips matching files. Cascades, last match wins, ! re-includes.
(kb / "bad/drafts/deep").mkdir(parents=True)
for f in ("drafts/a.md", "drafts/deep/b.md", "drafts/keep.md", "x1.md"):
    (kb / "bad" / f).write_text("no frontmatter\n")
(kb / "bad/kbmcp.nolint").write_text("# old stuff\nold.md\nnew.md\ndrafts/\n!drafts/keep.md\nx[0-9].md\n")
assert {f["file"] for f in k.lint(bundle="bad", limit=0)["findings"]} == {"drafts/keep.md"}
(kb / "bad/drafts/kbmcp.nolint").write_text("/keep.md\n")
assert k.lint(bundle="bad")["total"] == 0 and k.lint(bundle="bad")["ok"]
assert k.lint(bundle="bad", file="drafts/keep.md")["total"] == 0
(kb / "bad/inline.md").write_text("no frontmatter\n<!-- kbmcp-nolint -->\n")
(kb / "bad/quoted.md").write_text("no frontmatter, mentions `<!-- kbmcp-nolint -->`\n")
assert {f["file"] for f in k.lint(bundle="bad", limit=0)["findings"]} == {"quoted.md"}
assert all(k.glob_rx(p) for p in ("**/a", "a/**", "[!x]", r"\#x"))
shutil.rmtree(kb / "bad")

# fix: strips sub-index frontmatter, rebuilds the root list, re-lints; idempotent.
(kb / "note.md").write_text("---\ntype: Note\ntitle: Note\ndescription: A note.\ncustom: {a: [1, 2]}  # mine\n---\n"
                            "\n# Note\n\nBody.\n")
(kb / "sub").mkdir()
(kb / "sub/index.md").write_text("---\ntitle: Sub\n---\n# Sub\n")
assert {"okf_index", "index_stale"} <= kinds()
assert set(k.fix()["would_edit"]["."]) == {"index.md", "sub/index.md"}
out = k.fix(apply=True)
assert out["remaining"]["ok"], out
assert k.fix()["would_edit"] == {}
assert "(./note.md)" in (kb / "index.md").read_text() and (kb / "sub/index.md").read_text() == "# Sub\n"
assert "Ran fix" in (kb / "log.md").read_text()

# set: text-level edits keep other lines byte for byte; CRLF and BOM survive; bad values refused.
raises(k.set_, {"status": "done"}, file="note.md")
raises(k.set_, {"verified": []}, file="note.md")
assert "+status: draft" in k.set_({"status": "draft"}, file="note.md")["diff"]
k.set_({"status": "draft", "tags": ["a", "b"]}, file="note.md", apply=True)
t = (kb / "note.md").read_text()
assert "custom: {a: [1, 2]}  # mine\n" in t and "status: draft\n" in t
k.set_({"status": None}, file="note", apply=True)
assert "status:" not in (kb / "note.md").read_text()
(kb / "crlf.md").write_bytes(b"\xef\xbb\xbf---\r\ntype: Note\r\n---\r\nx\r\n")
k.set_({"title": "C"}, file="crlf.md", apply=True)
raw = (kb / "crlf.md").read_bytes()
assert raw.startswith(b"\xef\xbb\xbf---\r\n") and b"title: C\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")

# verify: machine path; human: refused from an agent; elicitation path; changed body refused.
asyncio.run(k.verify("note.md", by="claude-code/claude-opus-5-5"))
d = k.meta((kb / "note.md").read_text())[0]
assert d["verified"][0]["by"] == "claude-code/claude-opus-5-5" and TS.fullmatch(d["verified"][0]["at"])
assert k.trust_tier(d) == "machine-confirmed"
assert "only a human" in raises(k.verify, "note.md", by="human:drew")
raises(k.verify, "note.md", by="drew")


class Ctx:
    def __init__(self, action="accept", reviewer="tester", edit=None):
        self.action, self.reviewer, self.edit = action, reviewer, edit

    async def elicit(self, message, schema):
        assert "note.md" in message
        if self.edit:
            self.edit()
        return SimpleNamespace(action=self.action, data=SimpleNamespace(confirm=True, reviewer=self.reviewer))


assert asyncio.run(k.verify("note.md", ctx=Ctx("decline")))["edited"] == []
assert asyncio.run(k.verify("note.md", ctx=Ctx()))["tier"] == "human-reviewed"
sealed = (kb / "note.md").read_text()
e = k.meta(sealed)[0]["verified"][-1]
assert e["by"] == "human:tester" and e["sha256"] == k.content_hash(sealed, True)
assert k.signed(k.meta(sealed)[0], "note.md", {})["verified"][-1]["by"] == "human:tester"  # the seal holds
(kb / "note.md").write_text(sealed + "\nedited after review\n")
broken = k.signed(k.meta(sealed)[0], "note.md", {})
assert broken["verified"] == [e2 for e2 in broken["verified"] if "sha256" not in e2] and k.is_stale(broken) and k.trust_tier(broken) != "human-reviewed"
(kb / "note.md").write_text(sealed)
d = k.meta((kb / "note.md").read_text())[0]
assert [e["by"] for e in d["verified"]] == ["claude-code/claude-opus-5-5", "human:tester"]
edit = lambda: (kb / "note.md").write_text((kb / "note.md").read_text() + "\nmore\n")
assert "changed" in raises(k.verify, "note.md", ctx=Ctx(edit=edit))
os.environ["KB_USER"] = "drew"
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human at the terminal
assert k.meta((kb / "note.md").read_text())[0]["verified"][-1]["by"] == "human:drew"
assert cli("verify", "file=note.md", "by=human:drew")[0] == 2 and cli("lint", "--attest")[0] == 2
k.at_terminal = lambda: False  # a pipe or script is refused
with contextlib.redirect_stderr(io.StringIO()):
    assert k.cli(["verify", "file=note.md", "--attest"]) == 2
assert k.meta((kb / "note.md").read_text())[0]["verified"][-1]["by"] == "human:drew"
k.CLI, k.ATTEST = False, ""
assert all(cli(n)[0] == 2 for n in ("recheck_apply", "recheck_plan", "cite"))  # renamed in 2.2.0, with no alias: each says where it went

# fact / factcheck: a fact is a reproducible result: the recorded call, what it returned, and its fingerprint.
(kb / ".mcp.json").write_text(json.dumps({"mcpServers": {"jira": {"command": "x", "env": {"TOKEN": "secret"}}}}))
raises(k.fact, "note.md", server="nope", tool="get_issue")
c = k.fact("note.md", server="jira", tool="get_issue", args={"issue_key": "INFRA-1"}, result='{"status": "Open", "n": 1}',
           title="INFRA-1 status", stale_days=30)
assert c["footnote"] == "[^infra-1]"
(kb / "note.md").write_text((kb / "note.md").read_text().replace("Body.", "The ticket is open.[^infra-1]"))
d = k.meta((kb / "note.md").read_text())[0]
assert d["sources"][0]["resource"] == "mcp://jira/get_issue?issue_key=INFRA-1" and TS.fullmatch(d["stale_after"])
assert d["sources"][0]["fact_sha256"] == k.fact_sha256('{"n":1,   "status":"Open"}') != k.fact_sha256('{"status": "Closed", "n": 1}')  # JSON: key order and spacing do not matter
assert k.fact_sha256("a  b\n c") == k.fact_sha256("a b c")  # other text: whitespace collapses
assert k.lint()["ok"], k.lint()
plan = k.factcheck()  # no result: information only
assert plan["calls"][0]["call"] == {"server": "jira", "tool": "get_issue", "args": {"issue_key": "INFRA-1"}}
assert k.factcheck(older_than_days=1)["calls"] == [] and k.factcheck(file="note.md", id="nope")["calls"] == []
assert "The ticket is open" in plan["calls"][0]["cites"][0]
assert k.meta((kb / "note.md").read_text())[0] == d  # and it wrote nothing
live = lambda: k.trust_tier(k.signed(k.meta((kb / "note.md").read_text())[0], "note.md", {}))
os.environ["KB_USER"] = "drew"
k.at_terminal = lambda: True
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human reviews the note with its fact
assert live() == "human-reviewed"
before = (kb / "note.md").read_bytes()
same = k.factcheck(file="note.md", id="infra-1", result='{"n": 1, "status": "Open"}')  # the same fact: the check is recorded, nothing breaks
assert same["drift"] is False and live() == "human-reviewed" and (kb / "note.md").read_bytes() == before  # the sealed file is not touched by a clean check
assert "infra-1" in (kb / ".facts.yaml").read_text() and "drifted_at" not in (kb / ".facts.yaml").read_text()
assert "one fact" in raises(k.factcheck, result="x") and "no fact" in raises(k.factcheck, file="note.md", id="nope", result="x")
bad = k.factcheck(file="note.md", id="infra-1", result='{"status": "Closed", "n": 1}')  # drift: the reviews before it stop holding
assert bad["drift"] is True and bad["was"] != bad["now"] and "The ticket is open" in bad["cites"][0], bad
assert (kb / "note.md").read_bytes() == before and "drifted_at" in (kb / ".facts.yaml").read_text()  # noted beside the file, the file itself unchanged
assert live() != "human-reviewed" and k.drift_of("note.md", {}) is not None
k.CLI = True
sk = k.signatures("")["findings"]
assert any(f["kind"] == "stale_signature" and f["file"] == "note.md" and "fact drifted" in f["message"] for f in sk), sk
time.sleep(1.1)  # `at` has one-second resolution: the new review is later than the drift
assert cli("verify", "file=note.md", "--attest")[0] == 0  # a human reviews it again, after the drift: it holds
assert live() == "human-reviewed" and not any(f["file"] == "note.md" for f in k.signatures("")["findings"])
k.fact("note.md", resource="https://example.com/base", id="base", title="No result yet")  # no fact_sha256: the first result is the baseline
assert k.factcheck(file="note.md", id="base", result="x")["drift"] is None
assert k.factcheck(file="note.md", id="base", result="y")["drift"] is True
assert cli("fact", "file=note.md", "resource=https://x", "--attest")[0] == 2  # recording a fact is not confirming it
assert "secret" not in json.dumps(k.lint(limit=0))
k.fact("note.md", resource="https://example.com/page", title="Page")
assert k.lint()["ok"]

# Symlinks are never followed.
(kb / "alias.md").symlink_to(kb / "note.md")
assert "alias.md" not in json.dumps(k.lint(limit=0)) and "alias" not in json.dumps(k.list_())
(kb / "alias.md").unlink()

# Read tools.
st = k.status()
assert st["by_tier"]["human-reviewed"] == 1 and st["by_status"]["stable"] >= 1 and st["okf_version"] == "0.2"
assert st["conformant"]
assert [x["id"] for x in k.list_(tier="human-reviewed")["concepts"]] == ["note"]
(kb / "other.md").write_text("---\ntype: Note\n---\nSee [the note](/note.md).\n")
k.index(apply=True)
assert k.links("note.md")["in"] == ["other.md"] and k.links("other.md")["out"][0]["exists"]
assert k.search("ticket")["total"] == 1
assert k.get("note.md", limit=1)["text"] == "---\n"
assert [f["file"] for f in k.get(files=["note.md", "other.md"])["files"]] == ["note.md", "other.md"]

# create, move, log, per-directory indexes.
k.new("guides/howto", type="Playbook", description="How to.", tags=["ops"], status="draft", body="Step one.",
         by="claude-code/claude-opus-5-5")
t = (kb / "guides/howto.md").read_text()
d = k.meta(t)[0]
assert d["type"] == "Playbook" and d["generated"]["by"] == "claude-code/claude-opus-5-5" and "# howto\n\nStep one." in t
raises(k.new, "guides/howto", type="Playbook")
raises(k.new, "x", type=" ")
raises(k.new, "index", type="Note")
(kb / "guides/ref.md").write_text("---\ntype: Note\ndescription: r.\nexecutor: {resource: note.md}\n"
                                  "sources:\n  - id: h\n    resource: howto.md\n---\n"
                                  "See [how](howto.md#howto), [note](../note.md) and [abs](/note.md).\n")
assert "playbooks/howto.md" in k.move("guides/howto.md", "playbooks/howto.md")["would_edit"]["."]
k.move("guides/howto.md", "playbooks/howto.md", apply=True)
assert (kb / "playbooks/howto.md").exists() and not (kb / "guides/howto.md").exists()
assert "](../playbooks/howto.md#howto)" in (kb / "guides/ref.md").read_text()
assert k.meta((kb / "guides/ref.md").read_text())[0]["sources"][0]["resource"] == "../playbooks/howto.md"
k.move("guides/ref", "a/b/ref", apply=True)
t = (kb / "a/b/ref.md").read_text()
assert "](../../playbooks/howto.md#howto)" in t and "](../../note.md)" in t and "](/note.md)" in t
d = k.meta(t)[0]
assert d["sources"][0]["resource"] == "../../playbooks/howto.md" and d["executor"]["resource"] == "note.md"  # root-relative stays
k.record("Reviewed the guides.")
assert re.search(r"^\* <!-- \d+ --> \*\*Update\*\*: Reviewed the guides\.$", (kb / "log.md").read_text(), re.MULTILINE)
raises(k.log, "two\nlines")
k.index(dirs=True, apply=True)
assert "(ref.md)" in (kb / "a/b/index.md").read_text() and "[b](b/)" in (kb / "a/index.md").read_text()
assert k.lint()["ok"] and "index_stale" not in kinds() and "dead_anchor" not in kinds()

# upgrade (v0.1): Citations become sources; timestamp needs git for `by`.
(kb / "old").mkdir()
(kb / "old/index.md").write_text("# Old\n")
(kb / "old/m.md").write_text("---\ntype: Metric\ntimestamp: '2026-05-28T22:53:05+00:00'\n---\n# M\n\nText.\n\n"
                             "# Citations\n- https://wiki.acme/fpa-handbook\n- [Policy](https://wiki.acme/policy)\n")
out = k.upgrade(apply=True, bundle="old")
assert out["needs_by"] == ["m.md"]
d = k.meta((kb / "old/m.md").read_text())[0]
assert [e["id"] for e in d["sources"]] == ["fpa-handbook", "policy"] and d["sources"][1]["title"] == "Policy"
assert "# Citations" not in (kb / "old/m.md").read_text() and "timestamp" in d
assert k.meta((kb / "old/index.md").read_text())[0]["okf_version"] == "0.2"
assert k.lint(bundle="old", scope="okf")["ok"] and k.upgrade(bundle="old")["would_edit"] == {}
assert {b["bundle"] for b in k.bundles()["bundles"]} == {".", "old"}
shutil.rmtree(kb / "old")

# The spec as an MCP resource.
assert "okf://spec" in {str(x.uri) for x in asyncio.run(k.mcp.list_resources())}
assert k.spec().startswith("# Open Knowledge Format")

# verify promote: only a human review moves draft to stable.
k.new("promo", type="Note", description="P.", status="draft")
assert "only a human" in raises(k.verify, "promo.md", by="claude/x", promote=True)
assert cli("verify", "file=promo.md", "--attest", "promote=true")[0] == 0
assert k.meta((kb / "promo.md").read_text())[0]["status"] == "stable"

# fix normalizes tag case to the most common spelling.
(kb / "tags").mkdir()
for n, tg in (("a", "Sales"), ("b", "Sales"), ("c", "sales")):
    (kb / f"tags/{n}.md").write_text(f"---\ntype: x\ndescription: d.\ntags: [{tg}]\n---\n")
assert "tag_case" in kinds(bundle="tags")
k.fix(apply=True, bundle="tags")
assert "tag_case" not in kinds(bundle="tags") and k.meta((kb / "tags/c.md").read_text())[0]["tags"] == ["Sales"]
shutil.rmtree(kb / "tags")

# Spec use cases: §6.1 broken links tolerated, §5.1 lineage edges and signals, §8 lists and synthesized
# indexes, §9 logs at any level, §5.4 deprecation logged by convention.
u, saved = kb.parent / "uses", k.KB_ROOT
u.mkdir()
k.KB_ROOT = kb.parent
create(apply=True, bundle="uses")
k.new("t/src.md", type="Reference", description="s.", bundle="uses", resource="https://example.com/x")
k.new("t/m.md", type="Metric", description="m.", body="[later](/t/unwritten.md)", bundle="uses")
(u / "t/m.md").write_text((u / "t/m.md").read_text().replace("type: Metric", "type: Metric\nsources: [{id: s, resource: /t/src.md}]"))
L = k.lint(bundle="uses", limit=0)
assert L["ok"] and "dead_link" in L["counts"] and ("t/src.md", "orphan") not in {(f["file"], f["kind"]) for f in L["findings"]}
assert k.links("t/src.md", bundle="uses")["in"] == ["t/m.md"]
assert {"field": "sources[0].resource", "path": "/t/src.md", "target": {"bundle": "uses", "file": "t/src.md"},
        "exists": True} in k.links("t/m.md", bundle="uses")["out"]
assert "* [src](./t/src.md) - s." in (u / "index.md").read_text()
g = k.get("t/index.md", bundle="uses")
assert g["synthesized"] and "* [m](m.md) - m." in g["text"] and not (u / "t/index.md").exists()
(u / "t/log.md").write_text("# Log\n")
k.fact("t/m.md", resource="https://example.com/doc", author="team:docs", usage_count=0,
       last_modified="2026-05-30T00:00:00Z", bundle="uses")
e = k.meta((u / "t/m.md").read_text())[0]["sources"][-1]
assert e["author"] == "team:docs" and e["usage_count"] == 0 and "Cited" in (u / "t/log.md").read_text()
k.set_({"status": "deprecated"}, file="t/src.md", bundle="uses", apply=True)
assert "**Deprecation**: Deprecated [t/src.md](/t/src.md)." in (u / "t/log.md").read_text()
k.record("Hand note on [m](/t/m.md).", dir="t", bundle="uses")
L = k.log("t/m.md", bundle="uses")
assert [e["entry"] for e in L["entries"]][:1] == ["**Update**: Hand note on [m](/t/m.md)."] and L["entries"][0]["log"] == "t/log.md"
assert not any("src.md" in e["entry"] and "m.md" not in e["entry"] for e in L["entries"])
assert len(k.log(bundle="uses")["entries"]) > len(L["entries"])
assert "Hand note" in (u / "t/log.md").read_text() and "Hand note" not in (u / "log.md").read_text()
assert "usage_window" in raises(k.set_, {"usage_window": {"from": "x"}}, file="t/m.md", bundle="uses")
asyncio.run(k.verify("t/m.md", by="process:nightly", bundle="uses"))
k.new("t/d.md", type="Note", description="d.", status="draft", by="claude-code/x", bundle="uses")
k.set_({"stale_after": k.now(10)}, file="t/m.md", bundle="uses", apply=True)
st = k.status(bundle="uses")
assert st["review"]["oldest"] == [{"file": "t/m.md", "days": 0}] and st["drafts"] == {"count": 1, "oldest": [{"file": "t/d.md", "days": 0}]}
assert [d["file"] for d in st["due"]] == ["t/m.md"] and not k.status(due_days=5, bundle="uses")["due"]
# §6.2: a value naming a real file is a path, whatever its shape.
(u / "t/data").write_text("x")
assert k.pathed("data", u / "t/m.md", u) == (u / "t/data", "doc") and k.pathed("t/nothing", u / "t/m.md", u) is None


class Who:  # the person answering provenance's prompt
    def __init__(self, ok=True):
        self.ok = ok

    async def elicit(self, message, schema):
        assert "no history" in message
        return SimpleNamespace(action="accept" if self.ok else "decline", data=SimpleNamespace(confirm=True, author="ann"))


assert asyncio.run(k.provenance(apply=True, ctx=Who(False), bundle="uses"))["unknown"]["count"] >= 1
asyncio.run(k.provenance(apply=True, ctx=Who(), bundle="uses"))
g_ = k.meta((u / "t/src.md").read_text())[0]["generated"]
assert g_["by"] == "human:ann" and g_["basis"] == "stated" and TS.fullmatch(g_["at"]), g_
shutil.rmtree(u)
k.KB_ROOT = saved

# The archive also works when the collection root is itself a bundle: it is set apart, not nested.
one = Path(tempfile.mkdtemp()) / "solo"
one.mkdir()
k.KB_ROOT = one
create(apply=True)
k.new("x.md", type="Note", description="x.", bundle=".")
k.archive("x.md", bundle=".", apply=True)
assert (one / "archive/solo/x.md").exists() and "nested_bundle" not in kinds() and not (one / "x.md").exists()
k.unarchive("solo/x.md", apply=True)
assert (one / "x.md").exists() and not (one / "archive/solo/x.md").exists()
k.KB_ROOT = saved

# A collection of sibling bundles: tools follow where the user is; bundles do not nest.
saved, cwd, ws = k.KB_ROOT, os.getcwd(), (kb.parent / "ws").resolve()
ws.mkdir()
k.KB_ROOT = ws
create(apply=True, bundle="a")
create(apply=True, bundle="b")
assert (ws / ".gitattributes").read_text() == "log.md merge=union\nindex.md merge=union\n"
(ws / "a/sub").mkdir()
(ws / "a/sub/c.md").write_text("---\ntype: x\ndescription: c.\nsources: [{id: n, resource: /n.md}]\n---\n[n](/n.md)\n")
(ws / "a/n.md").write_text("---\ntype: x\ndescription: n.\n---\n[c](sub/c.md) [b](../b/m.md)\n")
(ws / "b/m.md").write_text("---\ntype: x\ndescription: m.\n---\n[n](../a/n.md) [m](m.md)\n")
k.index(apply=True, bundle="a")
k.index(apply=True, bundle="b")
os.chdir(ws / "a/sub")
L = k.lint(limit=0, ignore=["stub"])
assert set(L["bundles"]) == {"a"} and {(f["bundle"], f["file"], f["kind"]) for f in L["findings"]} == {("a", "n.md", "cross_bundle")}, L
code, out = cli("get", "file=c.md")  # CLI paths are relative to where you are
assert code == 0 and (json.loads(out)["bundle"], json.loads(out)["file"]) == ("a", "sub/c.md")
os.chdir(ws)
L = k.lint(limit=0)
assert set(L["bundles"]) == {".", "a", "b"} and L["ok"], L
assert {("a", "n.md"), ("b", "m.md")} <= {(c["bundle"], c["file"]) for c in k.list_()["concepts"]} and any(h["bundle"] == "b" for h in k.search("m.md")["hits"])
assert set(k.status()["bundles"]) == {"a", "b"} and "bundles" not in k.status(bundle="a")
st = k.status(bundle="a")
assert st["sources"] == {"with": 1, "without": 1} and st["words"]["longest"][0]["words"] >= 1 and st["due"] == []
assert {(f["bundle"], f["file"]) for f in k.lint(file="a/n.md", limit=0)["findings"]} == {("a", "n.md")}
assert {(f["bundle"], f["file"]) for f in k.lint(files=["b"], limit=0)["findings"]} == {("b", "m.md")}
code, out = cli("lint", "a/n.md", "format=text")
assert code == 0 and out.startswith("a/n.md: warning: cross_bundle")
raises(k.lint, file="nope.md")
k.set_({"status": "draft"}, file="a/n.md", apply=True)  # routes to bundle a: its log, not a root one
assert "Set status" in (ws / "a/log.md").read_text() and not (ws / "log.md").exists()
assert k.links("a/n.md")["in"] == ["sub/c.md"] and k.links("n.md", bundle="a")["bundle"] == "a"
k.baseline(apply=True)  # fingerprints are collection-relative, so they hold from any directory
os.chdir(ws / "a")
assert k.lint(baseline=".okf-baseline.json")["total"] == 0 and k.lint(baseline=".okf-baseline.json")["baselined"]
os.chdir(ws)
assert "migrate" in raises(k.move, "a/sub/c.md", "b/c.md")
k.migrate("a/sub/c.md", "b", apply=True)
assert (ws / "b/sub/c.md").exists() and not (ws / "a/sub/c.md").exists()
assert "[c](../b/sub/c.md)" in (ws / "a/n.md").read_text() and "[n](../../a/n.md)" in (ws / "b/sub/c.md").read_text()
assert k.meta((ws / "b/sub/c.md").read_text())[0]["sources"][0]["resource"] == "../../a/n.md"
assert "Migrated" in (ws / "a/log.md").read_text() and "Migrated" in (ws / "b/log.md").read_text()
assert "nest" in raises(k.create, bundle="a/inner", apply=True)
(ws / "a/inner").mkdir()
(ws / "a/inner/index.md").write_text('---\nokf_version: "0.2"\n---\n# Inner\n')
assert "nested_bundle" in kinds(bundle="a")
shutil.rmtree(ws / "a/inner")
assert k.fix(apply=True)["remaining"]["ok"]  # every bundle here, re-linted the same way
(ws / "area").mkdir()
(ws / "area/y.md").write_text("---\ntype: x\ndescription: y.\n---\n")
(ws / "area/x.md").write_text("---\ntype: x\ndescription: x.\n---\n[n](/a/n.md) [y](/area/y.md)\n")
out = k.split_off("area", apply=True)
t = (ws / "area/x.md").read_text()
assert "[n](../a/n.md)" in t and "[y](/y.md)" in t and out["crossing"]["count"] == 1
assert k.declares(ws / "area/index.md") and k.lint(bundle="area")["ok"]
assert "nest" in raises(k.split_off, "b/sub")
# rename, archive, unarchive: whole directories move and every link follows.
(ws / "b/m.md").write_text("---\ntype: x\ndescription: m.\n---\n[n](../a/n.md) [m](/m.md)\n")
assert "-> d" in k.rename_bundle("d", bundle="b")["move"] and (ws / "b").exists()
k.rename_bundle("d", bundle="b", apply=True)
assert not (ws / "b").exists() and "[m](/m.md)" in (ws / "d/m.md").read_text()
assert "../d/m.md" in (ws / "a/n.md").read_text() and "Renamed the bundle" in (ws / "d/log.md").read_text()
k.archive("n.md", bundle="a", apply=True)  # one concept
assert (ws / "archive/a/n.md").exists() and k.declares(ws / "archive/a/index.md")  # archive/a: an archived bundle
assert not k.declares(ws / "archive/index.md") and "* [a](a/)" in (ws / "archive/index.md").read_text()
assert "archive/a" not in k.lint()["bundles"] and "n.md" not in json.dumps(k.list_())  # set apart from the live one
assert "../archive/a/n.md" in (ws / "d/m.md").read_text() and "archived_link" in kinds(bundle="d")
assert "archived" in raises(k.set_, {"status": "draft"}, file="a/n.md", bundle="archive")
k.unarchive("a/n.md", apply=True)
assert (ws / "a/n.md").exists() and "../a/n.md" in (ws / "d/m.md").read_text()
assert "explicitly" in raises(k.archive)
k.archive(bundle="d", apply=True)  # a whole bundle: its log comes along, it stops being a bundle
assert not (ws / "d").exists() and k.declares(ws / "archive/d/index.md") and (ws / "archive/d/log.md").exists()
assert "../archive/d/m.md" in (ws / "a/n.md").read_text() and "nested_bundle" not in kinds(bundle="archive")
k.unarchive("d", apply=True)
assert k.declares(ws / "d/index.md") and "../d/m.md" in (ws / "a/n.md").read_text() and k.lint(bundle="d")["ok"]
k.rename_bundle("b", bundle="d", apply=True)
shutil.rmtree(ws / "archive")
w = k.web()  # at the collection root: bundles, edges counted
assert w["level"] == "bundles" and {"from": "a", "to": "b", "kind": "link", "count": 2} in w["edges"], w
assert k.web(bundle="a")["level"] == "concepts" and k.graph(w).startswith("graph LR\n")
code, out = cli("web", "format=mermaid")
assert code == 0 and "-->|link|" in out
assert k.collection(ws / "a/sub") == ws / "a"  # no index above yet: the bundle is the collection
assert "index_stale" not in kinds() and k.index(apply=True)["edited"] == {".": ["index.md"]}
assert k.upgrade()["would_edit"] == {} and not k.declares(ws / "index.md")  # the collection root stays no bundle
assert (ws / "index.md").read_text().count("* [") == 3 and "* [b](b/)" in (ws / "index.md").read_text()
assert k.collection(ws / "a/sub") == ws and k.collection(ws) == ws
(ws / "c").mkdir()
create(apply=True, bundle="c")
assert "index_stale" in kinds() and k.fix(apply=True)["remaining"]["ok"] and "* [c](c/)" in (ws / "index.md").read_text()
os.chdir(cwd)
k.KB_ROOT = saved

# §6.2: a path field is a path only if it looks like one; git-ignored files are not scanned.
assert k.pathed("dashboards/exec-revenue", kb / "x.md", kb) is None
assert k.pathed("./nope", kb / "x.md", kb) == (None, "missing")
g = Path(tempfile.mkdtemp())
subprocess.run(["git", "init", "-q", str(g)], check=True)
(g / ".gitignore").write_text("node_modules/\n")
(g / "node_modules").mkdir()
(g / "node_modules/README.md").write_text("x\n")
(g / "a.md").write_text("x\n")
assert k.walk(g) == [g / "a.md"]

# CLI: exit codes and CI formats.
assert cli("lint")[0] == 0
(kb / "bad").mkdir()
(kb / "bad/x.md").write_text("no frontmatter\n")
code, out = cli("lint", "bundle=bad", "format=github")
assert code == 1 and out.startswith("::error file=")
code, out = cli("lint", "bundle=bad", "format=sarif")
assert code == 1 and json.loads(out)["runs"][0]["results"]
assert cli("lint", "nonsense=1")[0] == 2
assert cli("fix", "bundle=bad")[0] == 0
assert cli("help")[0] == 0
fmt0, k.OPTS["format"] = k.OPTS["format"], "markdown"  # help is short and follows the format; `help all` lists everything
short, full = cli("help")[1], cli("help", "all")[1]
assert "seal" in short and "create" not in short and "create" in full and "bowerbird-mcp (format: markdown)" in short
k.OPTS["format"] = fmt0
assert cli("nope")[0] == 2
assert k.flags_to_words("seal", k.REG["seal"], ["-cp"]) == ["promote=true", "check=true"]  # combined short flags
for n, m in k.SHORTS.items():  # pinned letters: real arguments, none repeated, none of the reserved -h -F -O
    ps = {p for p in k.inspect.signature(k.REG[n]).parameters} - {"ctx"}
    assert set(m) <= ps and len(set(m.values())) == len(m) and not set(m.values()) & {"h", "F", "O"}, n
assert sorted(k.flags_to_words("create", k.REG["create"], ["-t", "markdown", "-a", "Docs", "--apply"])) == ["about=Docs", "apply=true", "holds=markdown"]
assert cli("bundles", "-O", "text")[1] == cli("bundles", "-F", "text")[1] == cli("bundles", "output=text")[1] and cli("lint", "--nope")[0] == 2
assert cli("lint", "--sca", "all")[0] == 2  # no abbreviations
(kb / "bare.md").write_text("---\ntype: x\n---\n")
assert cli("set", "bare.md", "status=draft", "tags=[a, b]", "apply=true")[0] == 0  # frontmatter as key=value
assert k.meta((kb / "bare.md").read_text())[0] | {} == {"type": "x", "status": "draft", "tags": ["a", "b"]}
assert cli("set", "bare.md", "status=stable", "--apply")[0] == 0 and k.meta((kb / "bare.md").read_text())[0]["status"] == "stable"  # a flag beside name=value
assert cli("move", "bare.md", "bare2.md", "apply=true")[0] == 0 and (kb / "bare2.md").exists()  # bare arguments
(kb / "bare2.md").unlink()
assert set(k.EXAMPLES) == set(k.REG)  # every tool has an example
code, out = cli("help", "move")
assert code == 0 and "-t, --to TO" in out and "str, required" in out and cli("move", "--help")[1] == out
import shlex  # every example, typed as flags, means what its name=value form means; `-a` is a bare switch, not `-a VALUE`

for n, exs in k.EXAMPLES.items():
    for e in exs:
        fl = [w for w in shlex.split(k.flag_example(n, e))[1:] if w != "--attest"]
        assert set(k.flags_to_words(n, k.REG[n], fl)) == {w for w in shlex.split(e)[1:] if w != "--attest"}, (n, e)
assert k.flags_to_words("lint", k.REG["lint"], ["-a"]) == ["all=true"] and k.flags_to_words("lint", k.REG["lint"], ["--no-all"]) == ["all=false"]
c1, o1 = cli("bundles", "output=text")
c2, o2 = cli("bundles", "format=text")  # the older name for output still works
assert c1 == c2 == 0 and o1 == o2 and not o1.lstrip().startswith("{"), (o1, o2)
assert cli("bundles", "output=json")[1].lstrip().startswith("{") and cli("bundles", "output=nope")[0] == 2
code, out = cli("bundles", "format=text")
assert code == 0 and out.startswith("bundles:")
assert cli("bundles")[1].lstrip().startswith("{")  # CI contract: piped output is JSON by default
k.out_terminal = lambda: True  # a person at a terminal gets text by default; output=json still wins
assert cli("bundles")[1].startswith("bundles:") and cli("bundles", "output=json")[1].lstrip().startswith("{")
k.out_terminal = lambda: False
shutil.rmtree(kb / "bad")

# MCP surface: annotations, and the context parameter is not a tool argument.
tools = {t.name: t for t in asyncio.run(k.mcp.list_tools())}
assert tools["lint"].annotations.readOnlyHint and not tools["fix"].annotations.readOnlyHint
assert "ctx" not in tools["seal"].inputSchema["properties"]

# Git: history, provenance, ingest (copy, then in place).
src = kb / "src"
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

hm = k.heatmap(bundle="src", limit=0)  # most changed first; README and guide changed twice
assert [(f["file"], f["changes"]) for f in hm["files"][:2]] == [("src/README.md", 2), ("src/docs/guide.md", 2)], hm
assert sum(f["changes"] for f in hm["files"]) == hm["bundles"][0]["changes"] == 5  # index.md left out
assert {(f["file"], f["authors"]) for f in hm["files"]} >= {("src/docs/guide.md", 2), ("src/README.md", 1)}
assert {a["author"] for a in hm["authors"]} == {"Ann", "Bob", "dependabot[bot]"} and hm["authors"][0] == {
    "author": "Ann", "changes": 3, "concepts": 2}
assert {(f["file"], f["author"]) for f in hm["single_author"]} == {("src/README.md", "Ann"), ("src/bot.md", "dependabot[bot]")}
h = k.history(src, [src / "docs/guide.md", src / "README.md", src / "bot.md"])
assert h[src / "docs/guide.md"]["by"] == "human:ann@example.com"  # Bob's frontmatter edit does not count
assert h[src / "README.md"]["by"] == "claude/claude-opus-5.5"
assert h[src / "bot.md"]["by"] == "process:dependabot"
assert asyncio.run(k.provenance(bundle="src"))["would_edit"] == {"src": ["docs/guide.md"]}

plan = k.ingest("src", bundle="imported", rules={"docs/*": "Guide"})
assert plan["ingest"] == 4 and plan["skipped"] == {"not markdown": 1}, plan
assert {i["to"] for i in plan["items"]} == {"docs/guide.md", "README.md", "src-index.md", "bot.md"}
assert plan["absolute_links"]["count"] == 1 and plan["provenance"] == {"full": 4}
assert plan["links_after_ingest"]["count"] == 2, plan["links_after_ingest"]
k.ingest("src", bundle="imported", rules={"docs/*": "Guide"}, apply=True)
d = k.meta((kb / "imported/docs/guide.md").read_text())[0]
assert d["type"] == "Guide" and d["status"] == "draft" and d["tags"] == ["x"]
assert d["generated"] == {"by": "human:ann@example.com", "at": d["generated"]["at"], "basis": "git-history"}
assert d["sources"][0]["resource"].startswith("https://github.com/o/r/blob/") and "tok" not in json.dumps(d)
assert k.lint(bundle="imported", scope="okf")["ok"]
assert k.ingest("src", bundle="imported")["ingest"] == 0  # re-run is a no-op
assert "source_changed" not in kinds(bundle="imported")
m = k.ingest("imported", bundle="merged", keep_okf=True, apply=True)  # merge an OKF bundle as is
assert m["ingest"] == 4 and (kb / "merged/docs/guide.md").read_text() == (kb / "imported/docs/guide.md").read_text()
assert k.ingest("imported", bundle="merged", keep_okf=True)["ingest"] == 0

(src / "dirty.md").write_text("x\n")
assert "clean git tree" in raises(k.ingest, "src", bundle="src", apply=True)
(src / "dirty.md").unlink()
assert k.ingest("src", bundle="src", apply=True)["links_after_ingest"]["count"] == 1
assert not (src / "index.md").exists() and (src / "src-index.md").exists()
assert k.lint(bundle="src", scope="okf")["ok"] and k.ingest("src", bundle="src")["ingest"] == 0

# lint since: only files changed since a ref (committed, unstaged or untracked) count.
g("add", "-A")
g("commit", "-qm", "okf")
(src / "new.md").write_text("no frontmatter\n")
L = k.lint(bundle="src", since="HEAD", limit=0)
assert {f["file"] for f in L["findings"]} == {"new.md"} and not L["ok"]
assert k.lint(bundle="src", since="HEAD~1", limit=0)["total"] > L["total"]
assert "unknown ref" in raises(k.lint, bundle="src", since="nope")
assert "git work tree" in raises(k.lint, since="HEAD")
assert "warning" in k.heatmap() and k.heatmap()["files"] == []  # no git: says so, does not fail
(kb / "box.tar.gz").write_bytes(b"x")
assert "unpack it first" in raises(k.ingest, "box.tar.gz")
(kb / "box.tar.gz").unlink()
(src / "new.md").unlink()

subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{src}", str(kb / "shallow")], check=True,
               capture_output=True)
assert "shallow" in raises(k.provenance, bundle="shallow")
pl = k.ingest("shallow", bundle="fromshallow", keep_okf=True)  # no history: origin only, said so
assert "shallow" in pl and set(pl["provenance"]) == {"partial"}, pl
up = Path(tempfile.mkdtemp())  # a plain repo, shallow-cloned: origin documents the repository and the commit
for c in (["init", "-q"], ["-c", "user.name=A", "-c", "user.email=a@x", "-c", "commit.gpgsign=false", "commit", "-q",
                           "--allow-empty", "-m", "x"]):
    subprocess.run(["git", *c], cwd=up, check=True, capture_output=True)
(up / "plain.md").write_text("# Plain\n")
subprocess.run(["git", "add", "."], cwd=up, check=True)
subprocess.run(["git", "-c", "user.name=A", "-c", "user.email=a@x", "-c", "commit.gpgsign=false", "commit", "-qm", "y"],
               cwd=up, check=True)
subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{up}", str(kb / "shallow2")], check=True, capture_output=True)
k.ingest("shallow2", bundle="fromshallow2", apply=True)
o = k.meta((kb / "fromshallow2/plain.md").read_text())[0]["sources"][0]
assert o["resource"] == f"file://{up}" and re.fullmatch(r"plain\.md at [0-9a-f]{12} of file://.+", o["title"]), o
g("remote", "set-url", "origin", "https://user:tok@github.com/o/r.git")
assert k.remote(src) == "https://github.com/o/r.git"

# permalink: credentials and ports dropped; a local remote has no web URL.
g("remote", "set-url", "origin", "ssh://git@host.example:2222/o/r.git")
assert k.permalink(src, src.resolve())(src / "bot.md", "abc") == "https://host.example/o/r/blob/abc/bot.md"
g("remote", "set-url", "origin", "git@github.com:o/r.git")
assert k.permalink(src, src.resolve())(src / "bot.md", "abc") == "https://github.com/o/r/blob/abc/bot.md"
assert k.web_base(src) == "https://github.com/o/r"  # the repository's address, for the link in `serve`
g("remote", "set-url", "origin", "https://user:secret@host.example:8443/o/mygit.git")
assert k.web_base(src) == "https://host.example/o/mygit" and "secret" not in k.web_base(src)  # no credentials or port; only a trailing .git goes
g("remote", "set-url", "origin", f"file://{src}")
assert k.permalink(src, src.resolve()) is None and k.web_base(src) is None

# Ranked search, dirs, vocab, demand; new lint kinds and only/ignore.
saved, rk = k.KB_ROOT, Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = rk
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
k.index(apply=True)
h = k.search("deploy")["hits"]
assert [x["file"] for x in h[:2]] == ["ops/deploy.md", "faq.md"] and h[0]["score"] > h[1]["score"] > h[-1]["score"], h
assert h[0]["matched"][:2] == ["title", "id"] and h[0]["line"] == 8 and "(deploy.md)" in h[0]["text"]  # body first
assert [x["file"] for x in k.search("deploy care")["hits"]] == ["ops/deploy.md"]  # every word, any field
assert {x["file"] for x in k.search("deploy", type="Playbook", dir="ops")["hits"]} == {"ops/deploy.md", "ops/rollback.md"}
assert [x["file"] for x in k.search("deploy", fields=["title"])["hits"]] == ["faq.md", "ops/deploy.md"]
assert k.search("deploy", tag="nope")["total"] == 0
raises(k.search, "")
raises(k.search, "x", fields=["nope"])
assert {(d["dir"], d["concepts"]) for d in k.dirs()["dirs"]} == {(".", 4), ("ops", 2)}
assert k.vocab() == {"tags": {"ops": 2}, "types": {"Note": 3, "guide": 1, "Playbook": 2}}
st = k.status()
assert st["wanted"] == [{"file": "ops/wanted.md", "links": 2}] and {"file": "ops/rollback.md", "links": 1} in st["hubs"]
kinds_of = lambda **kw: {(f["file"], f["kind"]) for f in k.lint(limit=0, **kw)["findings"]}
L = kinds_of()
assert {("tiny.md", "stub"), ("ops/deploy.md", "self_link"), ("ops/rollback.md", "undefined_ref"),
        ("faq.md", "duplicate_title"), ("ops/deploy.md", "duplicate_title")} <= L, L
assert ("seed.md", "stub") not in L and not any(x == "unused_ref" for _, x in L)  # [u]: mid-line is no definition
(rk / "island1.md").write_text(f"---\ntype: Note\ndescription: I.\n---\n{long} [2](island2.md)\n\n[u]: http://u.example\n")
(rk / "island2.md").write_text(f"---\ntype: Note\ndescription: I.\n---\n{long} [1](island1.md)\n")
L = kinds_of()
assert ("island1.md", "island") in L and ("island1.md", "unused_ref") in L and not any(x == "island" and f.startswith("ops") for f, x in L), L
assert {x for _, x in kinds_of(only=["stub"])} == {"stub"} and "stub" not in {x for _, x in kinds_of(ignore=["stub"])}
raises(k.lint, only=["nope"])
(rk / "kbmcp.yaml").write_text(k.EXAMPLE_CONFIG)  # at the collection root: right
assert any(f.startswith("ops/") for f, _ in kinds_of())
(rk / "ops/kbmcp.yaml").write_text("")  # a folder's own kbmcp.yaml overrides the one above it; it is not another collection
assert any(f.startswith("ops/") for f, _ in kinds_of()) and not any(x == "nested_config" for _, x in kinds_of())
(rk / "ops/kbmcp.yaml").unlink()
k._SCOPES.clear()
(rk / "kbmcp.yaml").unlink()
src = Path(k.__file__).read_text()
assert set(re.findall(r'finding\(\s*"(\w+)"', src)) | set(k.ERR) | {"island"} <= k.KINDS
# passages: heading-level BM25, with trust shown; a miss is a gap.
(rk / "ops").mkdir(exist_ok=True)
(rk / "ops/runbook.md").write_text("---\ntype: Playbook\ndescription: Shipping.\ntags: [ops]\n---\n"
                                   "Intro text about shipping.\n\n## Rollback\n\nTo roll back, redeploy the previous tag.\n\n"
                                   "```\n# not a heading\n```\n\n## Deploy\n\nPush the tag. " + "filler " * 40 + "\n")
P = k.passages("roll back previous tag")
top = P["hits"][0]
assert top["file"] == "ops/runbook.md" and top["heading"].endswith("Rollback") and top["line"] == 9, top
assert {"tier", "stale", "status", "text"} <= set(top) and not P["gap"]
assert [c[0].split(" > ")[-1] for c in k.chunks((rk / "ops/runbook.md").read_text(), "T")] == ["T", "Rollback", "Deploy"]
long = "# T\n\n" + "\n\n".join(f"para{i} " + "x" * 200 for i in range(12)) + "\n"
cs = [c[2] for c in k.chunks(long, "T")]
assert len(cs) > 1 and all(f"para{i} " in "".join(cs) for i in range(12))
assert all(cs[j].split("\n\n")[-1] in cs[j + 1] for j in range(len(cs) - 1)), "pieces overlap by one paragraph"
ls = [c[1] for c in k.chunks(long, "T")]
assert ls[1] == ls[0] + 2 * (len(cs[0].split("\n\n")) - 1), "an overlapped piece starts at its repeated paragraph"
G = k.passages("zzzunseen")
assert G["gap"] and G["total"] == 0 and k.passages("tag", tag="nope")["total"] == 0
raises(k.passages, "   ")

# kbmcp.yaml: root, user, ai_producers; unknown keys refuse.
cfg = Path(tempfile.mkdtemp()).resolve()
(cfg / "sub").mkdir()
(cfg / "kbmcp.yaml").write_text("user: drew\nai_producers: [zed]\n")
d, c = k.load_config(cfg / "sub")
assert d == cfg and c == {"user": "drew", "ai_producers": ["zed"]}
assert k.load_config(Path("/"))[0] is None
(cfg / "kbmcp.yaml").write_text("bogus: 1\n")
try:
    k.load_config(cfg)
    raise AssertionError("bad key accepted")
except SystemExit as e:
    assert "unknown key bogus" in str(e)
# flat passage settings: types and values are checked.
for bad, msg in (("semantic: 3", "semantic must be a bool"), ("seal: {nope: 1}", "seal takes exempt and exempt_status"), ("vector_index: faiss", "vector_index must be"), ("format: rst", "format must be okf, markdown, adr, skos"), ("build: sometimes", "must be auto or manual"),
                 ("min_similarity: high", "must be a float"), ("index: {path: x}", "index must be a str"), ("nope: 1", "unknown key nope")):
    (cfg / "kbmcp.yaml").write_text(bad + "\n")
    try:
        k.load_config(cfg)
        raise AssertionError(bad)
    except SystemExit as e:
        assert msg in str(e), (bad, str(e))
(cfg / "kbmcp.yaml").write_text("semantic: true\nmin_similarity: 1\nhubs: false\n")
assert k.load_config(cfg)[1] == {"semantic": True, "min_similarity": 1, "hubs": False}

# passages: false: no passages tool, no example, the instructions send you to search.
(cfg / "kbmcp.yaml").write_text("passages: false\n")
probe = "import bowerbird_mcp as k; print('passages' in k.REG, 'passages' in k.EXAMPLES, 'passages' in k.INSTRUCTIONS)"
env = dict(os.environ) | {"PYTHONPATH": str(HERE)}
off = subprocess.run([sys.executable, "-c", probe], cwd=cfg, env=env, capture_output=True, text=True, check=False)
assert off.stdout.split() == ["False", "False", "False"], off
(cfg / "kbmcp.yaml").write_text("\n")
on = subprocess.run([sys.executable, "-c", probe], cwd=cfg, env=env, capture_output=True, text=True, check=False)
assert on.stdout.split() == ["True", "True", "True"], on

# hubs: the concept others link to ranks first on a tie, and shows its inbound count.
(rk / "hub").mkdir(exist_ok=True)
for n in ("a", "b"):
    (rk / f"hub/{n}.md").write_text(f"---\ntype: Note\ndescription: x\n---\nThe quokka protocol {n}.\n")
for n in range(3):
    (rk / f"hub/l{n}.md").write_text("---\ntype: Note\ndescription: x\n---\nSee [b](b.md).\n")
H = k.passages("quokka", dir="hub")["hits"]
assert [h["file"] for h in H][:2] == ["hub/b.md", "hub/a.md"] and H[0]["links"] == 3 and H[1]["links"] == 0, H
k.OPTS["hubs"] = False
assert [h["file"] for h in k.passages("quokka", dir="hub")["hits"]] == ["hub/a.md", "hub/b.md"]
k.OPTS["hubs"] = True

# semantic: a fake embedder finds a passage that shares no word with the query; the cache is reused.
calls = []
def fake(texts):
    calls.append(len(texts))
    return [[1.0, 0.0] if ("release" in t.lower() or "reverse" in t.lower()) else [0.0, 0.0] for t in texts]
(rk / "sem.md").write_text("---\ntype: Note\ndescription: x\n---\n## Release\n\nShip the release.\n")
k.EMBEDDERS["fake"] = fake
k.OPTS |= {"semantic": True, "semantic_model": "fake", "min_similarity": 0.5}
S = k.passages("reverse")
assert [h["file"] for h in S["hits"]] == ["sem.md"], S
n_first = sum(calls)
k.passages("reverse")
assert sum(calls) == n_first + 1 and (rk / ".kbmcp/.gitignore").is_file()  # only the query was embedded again
assert k.passages("zzzunseen")["gap"]
# vector_index: each backend that is installed returns what scan returns (hnsw is approximate, but exact at this size).
k.EMBEDDERS["unit"] = lambda texts: [[1.0, 0.1] if ("release" in t.lower() or "reverse" in t.lower()) else [0.1, 1.0] for t in texts]
k.OPTS |= {"semantic_model": "unit", "min_similarity": 0.5, "vector_index": "scan"}
want = [(h["file"], h["match"]) for h in k.passages("reverse")["hits"]]
assert want and want[0][0] == "sem.md", want
for mode, mod in (("sqlite-vec", "sqlite_vec"), ("hnsw", "hnswlib")):
    try:
        __import__(mod)
        assert k.sqlite3.connect(":memory:").enable_load_extension
    except (ImportError, AttributeError):
        print(f"skipped vector_index={mode}: {mod} not usable")
        continue
    k.OPTS["vector_index"] = mode
    assert [(h["file"], h["match"]) for h in k.passages("reverse")["hits"]] == want, mode
    assert [(h["file"], h["match"]) for h in k.passages("reverse", dir="nope")["hits"]] == [], mode
    k.reindex()
k.OPTS |= {"vector_index": "scan", "semantic_model": "fake", "min_similarity": 0.5}
k.OPTS["semantic"] = False
assert k.passages("reverse")["gap"]
# reindex builds the one file at the chosen path; build: manual makes passages read it and nothing else.
default = {x: k.OPTS[x] for x in ("index", "build", "min_similarity", "semantic_model")}
idx = Path(tempfile.mkdtemp()) / "x" / "my.db"
k.OPTS["index"] = str(idx)
out = k.reindex()
assert idx.is_file() and out["passages"] > 0 and out["vectors"] == 0 and out["path"] == str(idx) and not out["semantic"], out
k.OPTS["build"] = "manual"
(rk / "late.md").write_text("---\ntype: Note\ndescription: x\n---\nThe zorblax arrived late.\n")
assert k.passages("zorblax")["gap"]  # manual: the new file is not read until reindex
assert k.reindex()["passages"] == out["passages"] + 1 and [h["file"] for h in k.passages("zorblax")["hits"]] == ["late.md"]
k.OPTS["index"] = str(idx.parent / "missing.db")
assert "reindex" in raises(k.passages, "zorblax")
k.OPTS |= {"index": str(idx), "build": "auto"}
assert k.reindex(full=True)["passages"] == out["passages"] + 1
code, text = cli("reindex", "format=text")
assert code == 0 and "passages" in text, (code, text)
# reindex info and drop: manage the file from the tool.
k.OPTS["index"] = str(idx)
I = k.reindex(info=True)
assert I["exists"] and I["files"] > 0 and I["behind"] == 0 and I["bytes"] > 0 and I["vectors"] == 0 and I["build"] == "auto", I
(rk / "late2.md").write_text("---\ntype: Note\ndescription: x\n---\nAnother.\n")
assert k.reindex(info=True)["behind"] == 1 and k.reindex(info=True)["files"] == I["files"]  # info never builds
k.reindex()
assert k.reindex(info=True)["behind"] == 0 and k.reindex(info=True)["files"] == I["files"] + 1
assert "pass one" in raises(k.reindex, full=True, drop=True)
assert k.reindex(drop=True)["dropped"] and not idx.exists() and not k.reindex(drop=True)["dropped"]
assert k.reindex(info=True)["exists"] is False and not idx.exists()
idx.parent.mkdir(exist_ok=True); idx.write_text("not a database")
assert k.reindex(info=True)["usable"] is False
(rk / "late2.md").unlink()
k.OPTS["index"] = ""
assert "kbmcp.yaml" in raises(k.reindex) and k.passages("zorblax")["hits"]  # in memory: passages still works
k.OPTS.update(default)
(rk / "late.md").unlink()
# roles: every tool has a home; the server offers the union of the roles asked for and enabled; the CLI has all.
assert set().union(*k.ROLES.values()) == set(k.REG) and k.offered() == set(k.REG)
list_tools = ("import sys, asyncio; sys.argv = ['x', *sys.argv[1:]]; import bowerbird_mcp as k; "
              "print(' '.join(sorted(t.name for t in asyncio.run(k.mcp.list_tools()))))")
def server(yaml_text="", *argv, **env):
    (cfg / "kbmcp.yaml").write_text(yaml_text)
    e = {kk: v for kk, v in os.environ.items() if kk != "KB_ROLE"} | {"PYTHONPATH": str(HERE)} | env
    return subprocess.run([sys.executable, "-c", list_tools, *argv], cwd=cfg, env=e, capture_output=True, text=True, check=False)
r = server("", "--role", "read")
assert set(r.stdout.split()) == k.ROLES["read"] and {"passages", "get", "dirs"} <= k.ROLES["read"], r
r = server("", KB_ROLE="write,lifecycle")
assert set(r.stdout.split()) == k.ROLES["write"] | k.ROLES["lifecycle"], r
r = server("roles: [read]\n")  # the others are off: only read is offered
assert set(r.stdout.split()) == k.ROLES["read"], r
r = server("roles: [read]\n", "--role=lifecycle")  # asking for a role that is off refuses
assert r.returncode and "off in kbmcp.yaml" in r.stderr, r
r = server("roles: [wizard]\n")
assert r.returncode and "unknown role wizard" in r.stderr, r
assert k.opt_arg(["--role", "write", "lint"], "--role") == ("write", ["lint"]) and k.opt_arg(["--role=a"], "--role") == ("a", [])
# the config file marks the collection: found from the working directory or named by --config; KB_ROOT is refused.
probe = "import sys; sys.argv = ['x', *sys.argv[1:]]; import bowerbird_mcp as k; print(k.KB_ROOT); print(k.INSTRUCTIONS)"
def where(cwd, *argv, **env):
    e = {kk: v for kk, v in os.environ.items() if kk != "KB_ROLE"} | {"PYTHONPATH": str(HERE)} | env
    return subprocess.run([sys.executable, "-c", probe, *argv], cwd=cwd, env=e, capture_output=True, text=True, check=False)
base = Path(tempfile.mkdtemp()).resolve()
(base / "eng/deep").mkdir(parents=True)
(base / "eng/kbmcp.yaml").write_text("about: Engineering runbooks.\n")
r = where(base / "eng/deep")  # found from below: the file's own folder is the collection
assert r.stdout.splitlines()[0] == str(base / "eng") and "This collection: Engineering runbooks." in r.stdout, r
assert where(base / "eng").stdout.splitlines()[0] == str(base / "eng")
(base / "other").mkdir()
r = where(base / "other", "--config", str(base / "eng/kbmcp.yaml"))  # --config wins over where we are
assert r.stdout.splitlines()[0] == str(base / "eng") and "Engineering runbooks" in r.stdout, r
r = where(base / "other", "--config", str(base / "nope.yaml"))
assert r.returncode and "--config takes either" in r.stderr, r
r = where(base / "other", KB_ROOT=str(base))
assert r.returncode and "KB_ROOT is no longer read" in r.stderr, r
# config: writes the commented example once, never over a file; the example tracks the real keys and defaults.
_y = k.yaml
eg = k.EXAMPLE_CONFIG
assert _y.safe_load(eg) is None  # all comments: valid, and marks the base
for key in k.CONFIG_KEYS:
    line = next((ln for ln in eg.splitlines() if ln.startswith(f"# {key}: ")), None)
    assert line, f"{key} missing from the example"
    if key in k.DEFAULTS and key != "about":  # about is only illustrated
        assert _y.safe_load(line[2:])[key] == k.DEFAULTS[key], (key, line)
cf, ck, k.CFG_DIR = k.CFG_DIR, k.KB_ROOT, None
k.KB_ROOT = Path(tempfile.mkdtemp()).resolve()
C = k.config()
assert not C["written"] and not (k.KB_ROOT / "kbmcp.yaml").exists() and C["content"] == {"kbmcp.yaml": eg, "env.example": k.ENV_EXAMPLE}
assert k.config(apply=True)["written"] and (k.KB_ROOT / "kbmcp.yaml").read_text() == eg
assert "exist" in raises(k.config)
assert k.load_config(k.KB_ROOT) == (k.KB_ROOT, {}) and C["gitignore"] == "not a git work tree"
code, text = cli("config")
assert code == 2, (code, text)  # the CLI refuses too: both exist now
# in a git work tree: init writes a filled kbmcp.yaml and env.example, lists .env in .gitignore, and asks for what it lacks.
gr = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(gr)], check=True)
(gr / ".gitignore").write_text("build/")  # no trailing newline: kept
k.KB_ROOT = gr
P = create()
assert P["config"]["files"][0] == "kbmcp.yaml" and {"env.example", ".mcp.json"} <= set(P["config"]["files"]) and P["config"]["gitignore"] == ".gitignore gets .env", P  # .env too if a user id is known
assert "about" in P["config"]["missing"] and not (gr / "kbmcp.yaml").exists(), P  # apply=false writes nothing
P = create(apply=True)
assert (gr / ".gitignore").read_text() == "build/\n.env\n" and (gr / "env.example").read_text() == k.ENV_EXAMPLE
got = k.load_config(gr)[1]
assert got == {"format": "okf", "passages": True, "hubs": True, "semantic": False, "semantic_model": k.DEFAULTS["semantic_model"],
               "min_similarity": k.DEFAULTS["min_similarity"], "index": k.DEFAULTS["index"]}, got
assert k.declares(gr / "index.md") and (gr / "log.md").is_file()  # okf: a bundle too
# init also writes a .mcp.json (commit it: a clone has the tools with nothing to register), and never overwrites one.
mj = json.loads((gr / ".mcp.json").read_text())
assert mj == k.MCP_JSON and mj["mcpServers"]["bowerbird"]["command"] == "uvx" and "--role" not in mj["mcpServers"]["bowerbird"]["args"]
# a folder that already has its kbmcp.yaml still gets the files it lacks, and that file is left alone.
ex = Path(tempfile.mkdtemp()).resolve()
(ex / "kbmcp.yaml").write_text("format: adr\n")
k.KB_ROOT = ex
P = create(apply=True, holds="adr")
assert "kbmcp.yaml" not in P["config"]["files"] and {"env.example", ".mcp.json", "BOWERBIRD.md"} <= set(P["config"]["files"]), P
assert (ex / "kbmcp.yaml").read_text() == "format: adr\n" and json.loads((ex / ".mcp.json").read_text()) == k.MCP_JSON
# init writes BOWERBIRD.md (agent rules), names only tools that exist, never overwrites it, and the docs page carries the same text.
assert (ex / "BOWERBIRD.md").read_text() == k.AGENTS_MD
_pick = [ln for ln in k.AGENTS_MD.split("## Picking a tool")[1].splitlines() if ln.startswith(("|", "Rare"))]
_use = [ln.strip("|").split("|")[1] if ln.startswith("|") else ln for ln in _pick]  # the Use column and the rare list name tools; the prose and the Not column name settings and arguments too
assert len(_use) > 20
for t in re.findall(r"`([a-z_]+)`", "\n".join(_use)):
    assert t in k.REG, t
(ex / "BOWERBIRD.md").write_text("mine\n")
assert "BOWERBIRD.md" not in create(apply=True, holds="adr").get("config", {}).get("files", [])
assert (ex / "BOWERBIRD.md").read_text() == "mine\n"
assert k.AGENTS_MD in (Path(k.__file__).parent / "docs-src" / "agents.md").read_text(), "docs-src/agents.md drifted from AGENTS_MD"
# the rules also reach an agent with no file: a resource and a prompt serve the same text
assert [str(r.uri) for r in asyncio.run(k.mcp.list_resources())].count("bowerbird://agent-rules") == 1
assert asyncio.run(k.mcp.read_resource("bowerbird://agent-rules"))[0].content == k.AGENTS_MD
assert asyncio.run(k.mcp.get_prompt("rules")).messages[0].content.text == k.AGENTS_MD
k.KB_ROOT = gr
# given values fill it in; markdown and skos start no bundle; nothing is overwritten.
md = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = md
P = create(apply=True, about="Decisions.", holds="markdown", user="dfoulks")
assert k.load_config(md)[1]["about"] == "Decisions." and k.load_config(md)[1]["format"] == "markdown", P
assert (md / ".env").read_text() == "KB_USER=dfoulks\n" and not (md / "index.md").exists() and P["config"]["missing"] == []
raises(create, holds="rst")
# guessing: thesaurus files mean skos, markdown without OKF types means markdown, an empty folder means okf.
g = Path(tempfile.mkdtemp()).resolve()
assert k.detect_holds(g) == "okf"
(g / "t.ttl").write_text("@prefix : <http://x/> .\n")
assert k.detect_holds(g) == "skos"
(g / "adr").mkdir()
(g / "adr/0001-x.md").write_text("# Use x\n")
assert k.detect_holds(g) == "adr"
(g / "adr/0001-x.md").rename(g / "adr/x.md")
(g / "adr").rename(g / "docs")
assert k.detect_holds(g) == "markdown"
(g / "docs").rename(g / "adr")
(g / "adr/x.md").rename(g / "adr/0001-x.md")
(g / "adr/0001-x.md").write_text("---\ntype: Note\n---\nx\n")
assert k.detect_holds(g) == "okf"
# init asks a human (elicitation) for what it could not know, and goes on without an answer.
class Ask:
    def __init__(self, action="accept", **data):
        self.action, self.data = action, data
        self.asked = []

    async def elicit(self, message, schema):
        self.asked.append(message)
        return SimpleNamespace(action=self.action, data=schema(**{"about": "", "holds": "markdown", "user": "", **self.data}))
a1 = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = a1
ask = Ask(about="Ops notes.", holds="markdown", user="me")
asyncio.run(k.create(apply=True, ctx=ask))
assert len(ask.asked) == 1 and "about" in ask.asked[0]
assert k.load_config(a1)[1]["about"] == "Ops notes." and (a1 / ".env").read_text() == "KB_USER=me\n"
a2 = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = a2
assert asyncio.run(k.create(apply=True, ctx=Ask("decline")))["config"]["missing"]  # no answer: written with what it has
assert "about" not in k.load_config(a2)[1]
# a folder holding its own kbmcp.yaml overrides the one above it: the parent's lint still sees inside it.
k.KB_ROOT = gr
(gr / "sub").mkdir()
(gr / "sub/kbmcp.yaml").write_text("")
(gr / "sub/n.md").write_text("---\ntype: Note\n---\nx\n")
assert any(f["file"].startswith("sub/") for f in k.lint(limit=0)["findings"])
k.KB_ROOT, k.CFG_DIR = ck, cf
# lint always says it ran: a verdict line (with what it checked) on success and failure, text and github.
L = k.lint()
assert L["checked"]["concepts"] > 0 and L["checked"]["bundles"] >= 1, L
code, text = cli("lint", "format=text")
assert text.splitlines()[-1].startswith(f"bowerbird-mcp lint: {'ok' if code == 0 else 'FAILED'}: ") and "concept(s) in" in text, text
code, text = cli("lint", "format=github")
assert text.splitlines()[-1].startswith("::notice title=bowerbird-mcp lint::bowerbird-mcp lint: "), text
assert "checked" not in k.lint(file="faq.md")  # a named file has no bundle count
good = Path(tempfile.mkdtemp()).resolve()
(good / "index.md").write_text('---\nokf_version: "0.2"\n---\n# kb\n')
(good / "log.md").write_text("# Log\n")
saved_root = k.KB_ROOT
k.KB_ROOT = good
code, text = cli("lint", "format=text")
assert code == 0 and text.splitlines()[-1] == "bowerbird-mcp lint: ok: 0 concept(s) in 1 bundle(s) checked, 0 finding(s), conformant: True", (code, text)
k.KB_ROOT = saved_root
# a file with no frontmatter that links to a concept must not crash lint (islands once raised KeyError).
(rk / "plain.md").write_text("No frontmatter here, but it links [to a concept](seed.md).\n")
assert ("plain.md", "no_frontmatter") in kinds_of()
(rk / "plain.md").unlink()
# passages: match is a percent of the best hit (a lone hit is 100); the "land it by PR" hint needs a git work tree.
M = k.passages("quokka", dir="hub")["hits"]
assert M[0]["match"] == 100 and all(isinstance(h["match"], int) and 0 <= h["match"] <= 100 for h in M) and "score" not in M[0], M
assert [h["match"] for h in k.passages("zorblax nothingelse")["hits"]] in ([], [100])
(rk / "solo.md").write_text("---\ntype: Note\ndescription: x\n---\nA lone ocelot sentence.\n")
assert [h["match"] for h in k.passages("ocelot")["hits"]] == [100]
(rk / "solo.md").unlink()
assert "next" not in k.new("hintless", type="Note")  # rk is not a git work tree
(rk / "hintless.md").unlink()
gr2 = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(gr2)], check=True)
k.KB_ROOT = gr2
assert "next" in create(apply=True)  # a git work tree: there is a diff to review
k.KB_ROOT = rk
# format: markdown indexes ADRs and MADR records with no OKF frontmatter, and offers only passages and reindex.
ar, was = Path(tempfile.mkdtemp()).resolve(), (k.KB_ROOT, dict(k.OPTS))
(ar / "docs/adr").mkdir(parents=True)
(ar / "docs/adr/0001-record-decisions.md").write_text("# 1. Record architecture decisions\n\nDate: 2016-02-12\n\n## Status\n\n"
                                                      "Accepted\n\n## Context\n\nWe need to record zebra decisions.\n")
(ar / "docs/adr/0002-use-postgres.md").write_text("---\nstatus: superseded by [ADR-0005](0005-x.md)\ndate: 2024-05-01\n---\n"
                                                  "# Use PostgreSQL\n\n## Context and Problem Statement\n\nWhich database for the narwhal?\n")
(ar / "docs/adr/0003-use-queue.md").write_text("# Use a queue\n\n* Status: proposed\n* Date: 2020-01-01\n\n## Context\n\nThe platypus needs a queue.\n")
(ar / "docs/index.md").write_text("# Docs home\n\nWelcome, wombat readers.\n")
k.KB_ROOT = ar
k.OPTS |= {"format": "markdown", "semantic": False, "index": ""}
got = {h["file"]: h for q in ("zebra", "narwhal", "platypus", "wombat") for h in k.passages(q)["hits"]}
assert set(got) == {"docs/adr/0001-record-decisions.md", "docs/adr/0002-use-postgres.md", "docs/adr/0003-use-queue.md",
                    "docs/index.md"}, set(got)
assert [got[f"docs/adr/000{n}-" + x + ".md"]["status"] for n, x in ((1, "record-decisions"), (2, "use-postgres"), (3, "use-queue"))] \
    == ["Accepted", "superseded by ADR-0005", "proposed"], got
assert got["docs/adr/0001-record-decisions.md"]["type"] == "adr" and got["docs/index.md"]["type"] is None
assert got["docs/index.md"]["status"] == "stable" and got["docs/index.md"]["tier"] == "unverified"
assert k.offered() == k.MARKDOWN == {"passages", "reindex", "seal", "get", "search", "dirs", "links", "list", "status", "heatmap", "create", "config", "new"}
for f, want in (("adr", k.MARKDOWN | {"move"}), ("skos", k.BASE), ("asciidoc", k.ADOC), ("seal-only", {"seal"})):  # the tiers
    k.OPTS["format"] = f
    assert k.offered() == want, (f, k.offered())
k.OPTS["format"] = "markdown"
# format: adr: every markdown file but README.md and index.md is a decision record, whatever its name or folder.
(ar / "notes").mkdir(exist_ok=True)
(ar / "notes/queue-choice.md").write_text("# Queue choice\n\n* Status: accepted\n\nThe okapi service needs a queue.\n")
(ar / "notes/README.md").write_text("# Notes\n\nThe okapi readme.\n")
k.OPTS["format"] = "markdown"
assert {h["file"]: h["type"] for h in k.passages("okapi")["hits"]} == {"notes/queue-choice.md": None, "notes/README.md": None}
k.OPTS["format"] = "adr"
A = {h["file"]: h for h in k.passages("okapi")["hits"]}
assert A["notes/queue-choice.md"]["type"] == "adr" and A["notes/queue-choice.md"]["status"] == "accepted" and A["notes/README.md"]["type"] is None, A
assert k.offered() == k.MARKDOWN | {"move"} and k.detect_holds(ar) == "adr"
k.OPTS["format"] = "markdown"
(ar / "notes/queue-choice.md").unlink()
(ar / "notes/README.md").unlink()
# list and status outside OKF: proposed and accepted are stable (a seal is what says accepted), superseded is final.
k0 = "docs/adr/0001-record-decisions.md"
text0 = (ar / k0).read_text()
k.ledger_put(k0, {"file": k0, "sha256": k.content_hash(text0, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
L = {c["file"]: c for c in k.list_(limit=0)["concepts"]}
assert (L[k0]["status"], L[k0]["tier"]) == ("stable", "human-reviewed") and L["docs/adr/0002-use-postgres.md"]["status"] == "superseded", L
assert [c["file"] for c in k.list_(status="proposed", tier="unverified")["concepts"]] == ["docs/adr/0003-use-queue.md"]  # the word the file wrote
assert {c["file"] for c in k.list_(status="STABLE", tier="unverified")["concepts"]} == {"docs/adr/0003-use-queue.md", "docs/index.md"}
st = k.status()
assert (st["concepts"], st["by_status"], st["by_tier"], st["stale"]) == (4, {"stable": 3, "superseded": 1}, {"human-reviewed": 1, "unverified": 3}, 0), st
assert st["by_state"] == {"accepted": 1, "proposed": 1, "stable": 1, "superseded": 1}, st  # the index note is no decision record
(ar / k0).write_text(text0 + "\nEdited.\n")  # an edit breaks the seal: unreviewed again, and counted stale
st = k.status()
assert st["by_tier"] == {"unverified": 4} and st["stale"] == 1, st
assert st["by_state"] == {"proposed": 2, "stable": 1, "superseded": 1}, st
(ar / k0).write_text(text0)
# move carries a seal along when the file's text does not change, and leaves it when the file had to be edited.
k.ledger_put(k0, {"file": k0, "sha256": k.content_hash(text0, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
k1 = "docs/adr/0001-record-it.md"
k.move(k0, "docs/adr/0001-record-it", apply=True)
assert set(k.ledger_by_file()) == {k1} and {c["file"]: c["tier"] for c in k.list_(limit=0)["concepts"]}[k1] == "human-reviewed"
assert k.status()["by_state"]["accepted"] == 1
k.move(k1, k0[:-3], apply=True)  # back again, so the other records keep their names
k9, t9 = "docs/adr/0009-linked.md", "# Linked\n\nSee [home](../index.md).\n"
(ar / k9).write_text(t9)
k.ledger_put(k9, {"file": k9, "sha256": k.content_hash(t9, False), "by": "human:ann", "at": "2026-01-01T00:00:00Z"})
k.move(k9, "docs/0009-linked", apply=True)  # its own relative link had to change, so its text did and the seal stays behind
assert set(k.ledger_by_file()) == {k0, k9} and {c["file"]: c["tier"] for c in k.list_(limit=0)["concepts"]}["docs/0009-linked.md"] == "unverified"
(ar / "docs/0009-linked.md").unlink()
(ar / ".waxseals.yaml").unlink()
# format: seal-only: nothing is indexed, one tool; every text file is checked except what seal.exempt leaves out (code included).
prev = (k.KB_ROOT, k.OPTS["format"], dict(k.OPTS["seal"]))
so = Path(tempfile.mkdtemp()).resolve()
(so / "src").mkdir()
(so / "src/app.py").write_text("def add(a, b):\n    return a + b\n")
(so / "src/util.py").write_text("X = 1\n")
(so / "src/blob.py").write_bytes(b"\xff\xfe\x00")
(so / "docs.md").write_text("# not in the policy\n")
k.KB_ROOT, k.OPTS["format"], k.OPTS["seal"] = so, "seal-only", {"exempt": ["docs.md"], "exempt_status": []}
assert k.offered() == {"seal"} and k.passages("add")["gap"]
C = k.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"]} == {("src/app.py", "unsigned"), ("src/util.py", "unsigned"), ("src/blob.py", "unreadable")} and C["files_checked"] == 2, C
code, out = cli("seal", "check=true")  # CI contract: unsigned files exit 1, and the output is JSON
assert code == 1 and json.loads(out)["findings"], (code, out)
k.OPTS["seal"] = {"exempt": ["docs.md", "src/util.py"], "exempt_status": []}  # an exempt file is left out
C = k.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"]} == {("src/app.py", "unsigned"), ("src/blob.py", "unreadable")} and C["files_checked"] == 1, C
k.OPTS["seal"] = {"exempt": ["docs.md"], "exempt_status": []}
class AnyFile(Ctx):
    async def elicit(self, message, schema):
        assert "src/app.py" in message and "sha256" in message
        return SimpleNamespace(action="accept", data=SimpleNamespace(confirm=True, reviewer="tester"))
asyncio.run(k.seal("src/app.py", by="process:ci"))  # a machine's review does not satisfy a policy that wants a human
assert ("src/app.py", "unsigned") in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
asyncio.run(k.seal("src/app.py", ctx=AnyFile(), decision="accepted"))
assert ("src/app.py", "unsigned") not in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
(so / "src/app.py").write_text("def add(a, b):\n    return a - b\n")  # edited after review: the seal is broken
assert ("src/app.py", "stale_signature") in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
asyncio.run(k.seal("src/util.py", by="process:ci"))
(so / "src/util.py").unlink()
assert [f["file"] for f in k.signatures()["findings"] if f["kind"] == "orphan_signature"] == ["src/util.py"]
k.OPTS["seal"] = {"exempt": [], "exempt_status": []}  # no list at all: every text file is checked, and a binary one is reported
(so / "src/util.py").write_text("X = 1\n")
C = k.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"] if f["kind"] != "orphan_signature"} == {
    ("src/app.py", "stale_signature"), ("src/util.py", "unsigned"), ("src/blob.py", "unreadable"), ("docs.md", "unsigned")}, C
k.OPTS["seal"] = {"exempt": ["docs.md", "src/blob.py", "src/util.py"], "exempt_status": []}  # exemptions are the only list
C = k.signatures()
assert {(f["file"], f["kind"]) for f in C["findings"] if f["kind"] != "orphan_signature"} == {("src/app.py", "stale_signature")}, C
k.OPTS["format"] = "markdown"  # in any format, a file sealed by path outside it is checked for edits and is not an orphan
k.OPTS["seal"] = {"exempt": [], "exempt_status": []}
assert not any(f["kind"] == "orphan_signature" and f["file"] == "src/app.py" for f in k.signatures()["findings"])
assert ("src/app.py", "stale_signature") in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
d1 = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = d1
P = create(apply=True, holds="seal-only", about="Reviewed code.", user="you")
assert k.load_config(d1)[1]["format"] == "seal-only" and not any(l.startswith("seal:") for l in (d1 / "kbmcp.yaml").read_text().splitlines()), P  # no list to fill in
k.KB_ROOT, k.OPTS["format"], k.OPTS["seal"] = prev

# seal, in markdown mode: the ledger binds a review to exact bytes; `check` finds what lacks one; a decision is the status.
k.OPTS["seal"] = {"exempt": ["docs/index.md"], "exempt_status": ["proposed"]}
adr1 = "docs/adr/0001-record-decisions.md"
C = k.signatures()
assert not C["ok"] and C["files_checked"] == 4 and {(f["file"], f["kind"]) for f in C["findings"]} == {
    (adr1, "unsigned"), ("docs/adr/0002-use-postgres.md", "unsigned")}, C  # 0003 is proposed (exempt); index.md is not required
asyncio.run(k.seal(adr1, by="process:ci"))  # a machine's review is recorded, but policy wants a human
assert (adr1, "unsigned") in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
assert "accepted or rejected" in raises(k.seal, adr1, decision="maybe")
class Any(Ctx):  # a human who confirms whatever file is shown
    async def elicit(self, message, schema):
        assert "adr/0001" in message and "sha256" in message and "decision: accepted" in message
        return SimpleNamespace(action="accept", data=SimpleNamespace(confirm=True, reviewer="tester"))
asyncio.run(k.seal(adr1, ctx=Any(), decision="accepted"))
led = (ar / ".waxseals.yaml").read_text()
line = next(ln for ln in led.splitlines() if adr1 in ln)  # one dense line per file
assert led.startswith("# .waxseals.yaml") and line.startswith("- {") and "sha256:" in line and "human:tester" in line and "decision: accepted" in line and f"bowerbird: {k.VERSION}" in line, led
asyncio.run(k.seal(adr1, ctx=Any(), decision="accepted"))  # sealing again replaces the line: only the last seal is kept
assert [ln for ln in (ar / ".waxseals.yaml").read_text().splitlines() if adr1 in ln] and sum(adr1 in ln for ln in (ar / ".waxseals.yaml").read_text().splitlines()) == 1
assert (adr1, "unsigned") not in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
h = k.passages("zebra")["hits"][0]
assert h["tier"] == "human-reviewed" and h["status"] == "accepted" and not h["stale"], h
(ar / adr1).write_text((ar / adr1).read_text() + "\nAn edit after the review.\n")  # the seal is broken
assert (adr1, "stale_signature") in {(f["file"], f["kind"]) for f in k.signatures()["findings"]}
h = k.passages("zebra")["hits"][0]
assert h["tier"] == "unverified" and h["stale"], h
asyncio.run(k.seal("docs/adr/0003-use-queue.md", by="process:ci"))
(ar / "docs/adr/0003-use-queue.md").unlink()
O = [f for f in k.signatures()["findings"] if f["kind"] == "orphan_signature"]
assert [f["file"] for f in O] == ["docs/adr/0003-use-queue.md"] and O[0]["severity"] == "warning"
assert k.ALIASES == {"verify": "seal", "ratify": "seal", "accepted": "seal"} and k.verify is k.seal
R = k.signatures()
txt = k.render(R, "text")
assert txt.splitlines()[-1].startswith("bowerbird-mcp seal: ") and "file(s) checked" in txt and "conformant" not in txt, txt
assert ": warning: orphan_signature:" in txt and "::warning file=" in k.render(R, "github") and "title=orphan_signature" in k.render(R, "github")
assert k.render(k.signatures(), "github").splitlines()[-1].startswith("::notice title=bowerbird-mcp seal::")
raises(k.seal)  # no file and no check
k.OPTS["format"] = "okf"
assert k.passages("zebra")["gap"], "okf mode skips files without frontmatter"
k.KB_ROOT = was[0]
k.OPTS.update(was[1])

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
    k.KB_ROOT = sr
    k.OPTS |= {"format": "skos", "semantic": False, "index": ""}
    P = k.passages("hound")
    h = P["hits"][0]
    assert [x["file"] for x in P["hits"]] == ["animals.ttl"] and h["heading"] == "Animals > Animal > Dog", P
    assert h["type"] == "skos" and h["title"] == "Animals" and h["tier"] == "unverified" and h["line"] == 6, h
    assert "Broader: Animal" in h["text"] and "Related: Wolf" in h["text"] and "carnivore" in h["text"], h["text"]
    assert next(x["heading"] for x in k.passages("animal")["hits"]).endswith("Animal")  # narrower links back to broader
    assert k.passages("turtle")["gap"] and k.offered() == {"passages", "reindex", "seal"}
    k.KB_ROOT = was[0]
    k.OPTS.update(was[1])

# format: asciidoc indexes AsciiDoc: one passage per section, header attributes (or YAML front matter) as metadata.
ad = Path(tempfile.mkdtemp()).resolve()
(ad / "deploy.adoc").write_text("= Deploy guide\n:tags: ops, deploy\n:status: stable\n\nIntro text.\n\n== Rollback\n\nRun the okapi rollback.\n\n"
                                "----\n== not a heading\n----\n\nSee xref:other.adoc[other] and <<third.adoc#x,third>>.\n")
(ad / "other.adoc").write_text("---\ntitle: Other doc\ntype: runbook\n---\n= Ignored\n\nThe platypus page.\n")
(ad / "third.adoc").write_text("= Third\n\nThe wombat page.\n")
k.KB_ROOT = ad
k.OPTS |= {"format": "asciidoc", "semantic": False, "index": ""}
t, m, tags, cs, dst = k.load_adoc(ad / "deploy.adoc", ad, "deploy.adoc", "asciidoc")
assert (t, tags, m["status"], m["type"]) == ("Deploy guide", ["ops", "deploy"], "stable", "asciidoc"), (t, tags, m)
assert [c[0] for c in cs] == ["Deploy guide", "Deploy guide > Rollback"] and dst == {"other.adoc", "third.adoc"}, (cs, dst)
h = k.passages("okapi")["hits"][0]
assert h["file"] == "deploy.adoc" and h["heading"] == "Deploy guide > Rollback" and h["tier"] == "unverified", h
o = k.passages("platypus")["hits"][0]
assert o["title"] == "Other doc" and o["type"] == "runbook", o  # front matter wins over the `= Ignored` line
assert k.offered() == k.ADOC and k.detect_holds(ad) == "asciidoc"
k.KB_ROOT = was[0]
k.OPTS.update(was[1])

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
k.KB_ROOT = hmd
for f, want in (("asciidoc", {"a.adoc"}), ("markdown", {"b.md", "index.md"}), ("adr", {"b.md", "index.md"})):
    k.OPTS["format"] = f
    got = k.heatmap(limit=0)
    assert {x["file"] for x in got["files"]} == want, (f, got)
assert {x["file"]: x["changes"] for x in (k.OPTS.update(format="asciidoc") or k.heatmap(limit=0))["files"]} == {"a.adoc": 2}
k.KB_ROOT = was[0]
k.OPTS.update(was[1])

# KB_* overrides: kbmcp.yaml < .env < the environment; `format` is never overridden; env.example lists every key.
assert k.env_overrides({"KB_SEMANTIC": "true", "KB_MIN_SIMILARITY": "0.7", "KB_ROLES": "read, write", "KB_ABOUT": "x",
                        "KB_USER": "me", "KB_AI_PRODUCERS": "zed,foo", "KB_FORMAT": "skos"}) == {
    "semantic": True, "min_similarity": 0.7, "roles": ["read", "write"], "about": "x", "user": "me", "ai_producers": ["zed", "foo"]}
for bad in ({"KB_SEMANTIC": "maybe"}, {"KB_MIN_SIMILARITY": "high"}, {"KB_BUILD": "sometimes"}, {"KB_ROLES": "root"}):
    try:
        k.env_overrides(bad)
        raise AssertionError(bad)
    except SystemExit as e:
        assert next(iter(bad)) in str(e) or "KB_* environment" in str(e), (bad, str(e))
de = Path(tempfile.mkdtemp()) / ".env"
de.write_text("# comment\nKB_ABOUT='quoted value'\nexport KB_BUILD=manual # inline\nOTHER=1\nKB_HUBS=\"false\"\nnot a line\n")
assert k.read_dotenv(de) == {"KB_ABOUT": "quoted value", "KB_BUILD": "manual", "KB_HUBS": "false"} and k.read_dotenv(de.parent / "x") == {}
ex = (HERE / "env.example").read_text()
assert ex == k.ENV_EXAMPLE and all(f"# KB_{key.upper()}=" in ex for key in k.CONFIG_KEYS - k.SHARED_ONLY) and "KB_FORMAT" not in ex
pe = Path(tempfile.mkdtemp()).resolve()
(pe / "kbmcp.yaml").write_text("about: from yaml\nbuild: auto\n")
(pe / ".env").write_text("KB_ABOUT=from dotenv\nKB_BUILD=manual\n")
probe = "import bowerbird_mcp as k; print(k.OPTS['about'], '|', k.OPTS['build'])"
env = {key: v for key, v in os.environ.items() if not key.startswith("KB_")} | {"PYTHONPATH": str(HERE)}
r1 = subprocess.run([sys.executable, "-c", probe], cwd=pe, env=env, capture_output=True, text=True, check=False)
assert r1.stdout.strip() == "from dotenv | manual", r1
r2 = subprocess.run([sys.executable, "-c", probe], cwd=pe, env=env | {"KB_ABOUT": "from env"}, capture_output=True, text=True, check=False)
assert r2.stdout.strip() == "from env | manual", r2

k.KB_ROOT = saved

# the token figures in the README follow the tools (same method as the text says: serialized definition chars / 4), within 10%.
_tl = {t.name: t for t in asyncio.run(k.mcp.list_tools())}
_cost = lambda names: sum(len(json.dumps({"name": n, "description": _tl[n].description, "inputSchema": _tl[n].inputSchema}))
                          for n in names if n in _tl) // 4
_pp = (HERE / "pyproject.toml").read_text()  # semantic search (fastembed) is an add-on: not a base dependency, and an extra of its own
assert 'dependencies = ["mcp>=1.10,<2", "pyyaml"]' in _pp and 'semantic = ["fastembed"]' in _pp
assert set(k.MCP_TEXT) == set(k.REG), set(k.MCP_TEXT) ^ set(k.REG)  # every tool has its short MCP text; the docstring stays whole for help and the docs
for _n, _t in _tl.items():
    assert _t.description.startswith(k.MCP_TEXT[_n]) and len(_t.description) < 600, _n
    assert ("apply=true" in _t.description) == ("apply" in k.inspect.signature(k.REG[_n]).parameters) or _n in k.MCP_TEXT and "apply=true" in k.MCP_TEXT[_n], _n
assert "never pass human:<id>" in _tl["seal"].description and "gap=true" in _tl["passages"].description  # the rules an agent must not lose
assert len(k.REG["seal"].__doc__) > 1500 and "Never pass human:<id> yourself" in " ".join(k.REG["seal"].__doc__.split())  # the full text lives on for help, the CLI and the docs
_rm = (HERE / "README.md").read_text()
_close = lambda doc, real: abs(doc - real) <= real * 0.1
assert f"All {len(_tl)} tools" in _rm and _close(int(re.search(r"about ([\d,]+) tokens of schema", _rm).group(1).replace(",", "")), _cost(_tl)), _cost(_tl)
for _role, _names in k.ROLES.items():
    _m = re.search(rf"\| `{_role}` \|.*\| (\d+), ~([\d,]+) tokens \|", _rm)
    assert int(_m.group(1)) == len([n for n in _names if n in _tl]) and _close(int(_m.group(2).replace(",", "")), _cost(_names)), (_role, _cost(_names))

# a result whose `findings` is a count (baseline's) prints as text, not as a list of lint findings.
assert k.render({"findings": 3, "path": ".okf-baseline.json", "written": True}, "text") == "findings: 3\npath: .okf-baseline.json\nwritten: true"
# --version: the running Bowerbird says what it is, including whether it is a development build.
assert k.VERSION == re.search(r'^version = "(.*)"', (HERE / "pyproject.toml").read_text(), re.MULTILINE).group(1)  # one number, two files
ds = k.describe_source
assert ds(None, True, None, False) == ("release", "")  # installed from an index such as PyPI
assert ds('{"url": "https://github.com/x/y", "vcs_info": {"vcs": "git", "commit_id": "0123456789abcdef"}}', True, None, False) == ("development", "git 0123456")
assert ds('{"url": "file:///src/y", "dir_info": {"editable": true}}', True, None, False) == ("development", "editable install")
assert ds('{"url": "file:///src/y", "dir_info": {}}', True, None, False) == ("development", "local build")
assert ds(None, False, "abc1234", False) == ("development", "git abc1234")  # run from a Bowerbird checkout
assert ds(None, False, None, False) == ("standalone", "") and ds(None, False, None, True) == ("standalone", "vendored")
b = k.build_info()
assert b["version"] == k.VERSION and b["kind"] == "development" and b["detail"].startswith("git "), b  # these tests run from the checkout
code, out = cli("--version")
assert code == 0 and out.strip().startswith(f"bowerbird-mcp {k.VERSION} (development, git "), out
assert cli("-V")[1] == out
loose = Path(tempfile.mkdtemp()) / "bowerbird_mcp.py"
loose.write_text((HERE / "bowerbird_mcp.py").read_text())
r = subprocess.run([sys.executable, str(loose), "--version"], capture_output=True, text=True, check=False)
assert r.stdout.strip() == f"bowerbird-mcp {k.VERSION} (standalone script)", r  # a lone copy, not a git checkout
vend = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(vend)], check=True)
(vend / "bowerbird_mcp.py").write_text(loose.read_text())
r = subprocess.run([sys.executable, str(vend / "bowerbird_mcp.py"), "--version"], capture_output=True, text=True, check=False)
assert r.stdout.strip() == f"bowerbird-mcp {k.VERSION} (standalone script, vendored)", r  # vendored into someone else's repo
assert k.mcp._mcp_server.create_initialization_options().server_version.startswith(f"{k.VERSION}+development.")  # what the client sees

# Mixed formats: the nearest kbmcp.yaml overrides the ones above it, like an inherited ACL. A markdown collection with an ADR
# folder, and an OKF collection with an ADR folder.
saved_root, saved_fmt, saved_cfg = k.KB_ROOT, k.OPTS["format"], k.CFG_DIR
ADR = "# Use Vault\n\n## Status\n\nAccepted\n\n## Context\n\nWe need one place for secrets, said plainly here.\n"
adr_cfg = "format: adr\nseal: {exempt: [], exempt_status: []}\n"  # its globs start at its own folder


def mixed(root_format, files):
    d = Path(tempfile.mkdtemp()).resolve()
    for n, x in {"kbmcp.yaml": f"format: {root_format}\n", **files}.items():  # a collection has a root kbmcp.yaml; what lies below it overrides
        (d / n).parent.mkdir(parents=True, exist_ok=True)
        (d / n).write_text(x)
    k.KB_ROOT, k.CFG_DIR = d, None
    k.OPTS["format"] = root_format
    k._SCOPES.clear()
    k._POLICY.clear()
    return d


mk = mixed("markdown", {"notes/runbook.md": "# Runbook\n\nHow we roll back a deploy, step by step, with care.\n",
                        "decisions/kbmcp.yaml": adr_cfg, "decisions/0001-use-vault.md": ADR})
assert (k.fmt_of(mk / "notes/runbook.md"), k.fmt_of(mk / "decisions/0001-use-vault.md")) == ("markdown", "adr")
assert {os.path.relpath(p, mk) for p in k.source_files(mk)} == {"notes/runbook.md", "decisions/0001-use-vault.md"}
h = k.passages("vault secrets")["hits"]
assert h and h[0]["file"] == "decisions/0001-use-vault.md" and h[0]["status"] == "Accepted"  # read as an ADR, in a markdown collection
assert {(f["file"], f["kind"]) for f in k.signatures()["findings"]} == {("decisions/0001-use-vault.md", "unsigned"),
                                                                       ("notes/runbook.md", "unsigned")}
(mk / "decisions/kbmcp.yaml").write_text("index: other.db\n")  # a folder may override what it holds and who reviews it, not the server's settings
k._SCOPES.clear()
try:
    k.scopes()
    raise AssertionError("a folder's kbmcp.yaml set index")
except SystemExit as e:
    assert "belongs to the whole collection" in str(e) and "index" in str(e)

ok = mixed("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n',
                   "db.md": "---\ntype: Note\ndescription: The database.\n---\n# DB\n\nPostgres, decided in [ADR 1](adr/0001-use-vault.md), body long enough.\n",
                   "adr/kbmcp.yaml": adr_cfg, "adr/0001-use-vault.md": ADR + "\nSee [the DB](../db.md).\n"})
assert (k.fmt_of(ok / "db.md"), k.fmt_of(ok / "adr/0001-use-vault.md")) == ("okf", "adr")
L = k.lint(limit=0)
assert L["ok"] and not any(f["file"].startswith("adr/") for f in L["findings"]), L  # lint does not judge ADRs as OKF concepts
assert {(f["file"], f["kind"]) for f in k.signatures()["findings"]} == {("adr/0001-use-vault.md", "unsigned"), ("db.md", "unsigned")}
li = k.links("db.md")
assert li["out"][0]["exists"] and li["in"] == ["adr/0001-use-vault.md"]  # links cross the boundary both ways
h = k.passages("vault secrets")["hits"]
assert h and h[0]["file"] == "adr/0001-use-vault.md" and h[0]["status"] == "Accepted"
assert not any(f["kind"] == "orphan" for f in L["findings"]), L  # an ADR that links to a concept keeps it from being an orphan


def okf_with_adr():
    return mixed("okf", {"index.md": '---\nokf_version: "0.2"\n---\n# KB\n',
                         "db.md": "---\ntype: Note\ndescription: The database.\n---\n# DB\n\nPostgres, decided in [ADR 1](adr/0001-use-vault.md), body long enough.\n",
                         "adr/kbmcp.yaml": adr_cfg, "adr/0001-use-vault.md": ADR + "\nSee [the DB](../db.md).\n"})


ok = okf_with_adr()
k.index(apply=True, dirs=True)  # lists OKF concepts only: the ADR folder gets no index.md and is not in the root one
assert "adr" not in (ok / "index.md").read_text() and not (ok / "adr/index.md").exists() and "[DB](./db.md)" in (ok / "index.md").read_text()
ok = okf_with_adr()
k.move("db.md", "notes/db.md", apply=True)  # links in an ADR follow a moved concept
assert "(../notes/db.md)" in (ok / "adr/0001-use-vault.md").read_text() and "(../notes/db.md)" not in (ok / "adr/0001-use-vault.md").read_text().replace("(../notes/db.md)", "", 1)
ok = okf_with_adr()
txt = (ok / "adr/0001-use-vault.md").read_text()
k.ledger_put("adr/0001-use-vault.md", {"file": "adr/0001-use-vault.md", "sha256": k.content_hash(txt, False), "by": "human:me", "at": k.now(), "bowerbird": k.VERSION})
k.move("adr/0001-use-vault.md", "adr/0002-vault.md", apply=True)  # a moved ADR keeps its review, and the concept's link follows it
assert "adr/0002-vault.md" in (ok / "db.md").read_text() and list(k.ledger_by_file()) == ["adr/0002-vault.md"]
assert k.reviews({}, "adr/0002-vault.md", (ok / "adr/0002-vault.md").read_text(), k.ledger_by_file())[1]
ok = okf_with_adr()
(ok / "other").mkdir()
(ok / "other/index.md").write_text('---\nokf_version: "0.2"\n---\n# Other\n')
k._SCOPES.clear()
k.migrate("db.md", "other", apply=True)  # a concept moved to another bundle: the ADR's link follows it
assert (ok / "other/db.md").exists() and "(../other/db.md)" in (ok / "adr/0001-use-vault.md").read_text()
k.KB_ROOT, k.CFG_DIR = saved_root, saved_cfg
k.OPTS["format"] = saved_fmt
k._SCOPES.clear()
k._POLICY.clear()

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
    threading.Thread(target=bowerbird_serve.run, args=(k, port, True), daemon=True).start()
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
    t = k.new_template(sv / "notes")  # the box starts as the folder's template, by its format
    assert t in {k.TEMPLATES["okf"], k.TEMPLATES["markdown"], k.TEMPLATES["adr"].replace("{today}", __import__("datetime").date.today().isoformat()), ""} and "{today}" not in t
    assert k.new_template(sv / "decisions") .startswith("---\nstatus: proposed") or k.OPTS["format"] != "markdown"  # a path through decisions is an ADR
    st, tp, _ = put_("/_new", dir="notes", name="keep", tpl="adr", use="1")  # Use template: refills the box, keeps the name, saves nothing
    assert st == 200 and "Considered Options" in tp and 'value="keep"' in tp and not (sv / "notes/keep.md").exists()
    assert put_("/_new", dir="notes", name="fresh", text="---\ntype: Note\n---\n# Fresh\n")[0] == 303 and (sv / "notes/fresh.md").exists()  # Save writes dir/name.md
    assert put_("/_new", dir="notes", name="folder2/")[0] == 303 and (sv / "notes/folder2").is_dir()  # a trailing / is a folder
    assert put_("/_new", dir="", name="a", text="x")[0] == 409 and "x" not in (sv / "a.md").read_text()[:5]  # a.md exists
    assert put_("/_new", dir="", name="", text="x")[0] == 400
    pg = hit("GET", "/a.md")[1]
    aside = pg[pg.index("<aside>"):]
    assert "✎" in aside and "⚙" in aside and "✎" not in pg[:pg.index("<aside>")].split("<main>")[1]  # the pencil and gear live in the right pane

    # edit: saves, and refuses to overwrite a page that changed under the editor
    base = re.search(r'name=base value="([^"]+)"', hit("GET", "/_edit?f=c.md")[1]).group(1)
    assert put_("/_save", file="c.md", base=base, text=(sv / "c.md").read_text().replace("Alone", "Edited"))[0] == 303
    assert "Edited" in (sv / "c.md").read_text() and "generated" not in (sv / "c.md").read_text()
    assert put_("/_save", file="c.md", base=base, text="lost")[0] == 409 and "lost" not in (sv / "c.md").read_text()
    assert put_("/_save", file="../escape.md", base="", text="x")[0] == 400 and put_("/_save", file="x.txt", base="", text="x")[0] == 400
    assert put_("/_save", file="notes/new.md", base=k.hashlib.sha256(b"").hexdigest(), text="---\ntype: Note\n---\n# New\n")[0] == 303 and (sv / "notes/new.md").exists()

    # the editor: Save, Lint (the unsaved text, nothing written) and Cancel
    ed = hit("GET", "/_edit?f=a.md")[1]
    assert ">Save</button>" in ed and ">Lint</button>" in ed and ">Cancel</a>" in ed
    before = (sv / "a.md").read_text()
    bad = before.replace("type: Note", "type: ")  # no type: the unsaved text is wrong, the file on disk is not
    lt = put_("/_editlint", file="a.md", text=bad)
    assert lt[0] == 200 and "not saved" in lt[1] and "type" in lt[1] and (sv / "a.md").read_text() == before and k.read is not None
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
    assert "human:me" in (sv / "a.md").read_text() and k.ATTEST == ""
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
    assert k.OPTS["semantic"] is False  # the keyword mode's switch is put back
    assert "value=semantic" not in hit("GET", "/a.md")[1] and "mode=semantic" not in hit("GET", "/_search?q=x")[1]  # off: not offered
    k.OPTS["semantic"] = True
    assert "value=semantic" in hit("GET", "/a.md")[1] and "mode=semantic" in hit("GET", "/_search?q=x")[1]  # on: offered
    k.OPTS["semantic"] = False
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
        assert bowerbird_serve.stop(port) == 0 and k.cli(["serve", "stop", str(port)]) == 0
        assert k.cli(["serve", "status", str(port)]) == 1
        assert k.cli(["serve"]) == 0 and k.cli(["serve", str(port)]) == 0  # bare: help, and nothing is started
    assert "nothing running" in out_.getvalue() and "not running" in out_.getvalue() and "serve start|stop|restart|status [port]" in out_.getvalue() and "--config" in out_.getvalue()
    assert not bowerbird_serve.listening(port)
    with socket.socket() as other_:
        other_.bind(("127.0.0.1", 0))
        other_.listen(1)
        op_ = other_.getsockname()[1]
        with contextlib.redirect_stdout(io.StringIO()) as out_:
            assert bowerbird_serve.start(k, op_) == 1 and bowerbird_serve.stop(op_) == 0
        assert "in use by something else" in out_.getvalue() and bowerbird_serve.listening(op_)
    with contextlib.redirect_stderr(io.StringIO()) as err_:
        assert k.cli(["serve", "bogus"]) == 2
    assert "start|stop|restart|status" in err_.getvalue()
    assert os.getcwd() == str(sv)  # started from the repo, searched the throwaway collection: not the cwd's bundle
    os.chdir(here_)

    # serve over a seal-only collection: hidden files and links are 404 (GET and HEAD), and `/` is a shell without an index.md
    prev_ = (k.KB_ROOT, k.OPTS["format"], dict(k.OPTS["seal"]))
    so_ = mixed("seal-only", {"kbmcp.yaml": 'format: seal-only\nseal: {exempt: ["docs/gen.md", "src/gen_*.py"]}\n', ".env": "SECRET=1\n",
                              "docs/gen.md": "# Generated\n\nBuilt from the code.\n", "docs/hand.md": "# Hand\n\nWritten by a person.\n",
                              ".waxseals.yaml": "[]\n", "sub/.hidden": "x\n", "sub/ok.txt": "fine\n", "src/app.py": "def add(a, b):\n    return a + b\n"})
    k.OPTS["seal"] = {"exempt": ["docs/gen.md", "src/gen_*.py"], "exempt_status": []}
    (so_ / "src/blob.py").write_bytes(b"\xff\xfe\x00")
    (so_ / "src/big.py").write_text("x = 1\n" * 100_000)  # over the 512 KB cap
    (so_ / "link.py").symlink_to(so_ / "src/app.py")
    (so_ / "linkdir").symlink_to(so_ / "src", target_is_directory=True)
    assert k.mark_derived(so_ / "docs/gen.md", "gen.py") and not k.mark_derived(so_ / "docs/gen.md", "gen.py")  # a generator records it, once
    with socket.socket() as so2:
        so2.bind(("127.0.0.1", 0))
        port = so2.getsockname()[1]
    threading.Thread(target=bowerbird_serve.run, args=(k, port, True), daemon=True).start()
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
    assert st_ == 200 and "<dialog id=seal>" in pg_ and "Confirm seal: src/app.py" in pg_ and "unsealed" in pg_ and "✎" not in pg_  # no editor for code
    assert hit("GET", "/src/blob.py")[0] == 404 and hit("GET", "/src/big.py")[0] == 404  # not shown; the CLI still covers them
    # derived from the code (a generator's ledger line): a fourth state, with nothing to seal; `seal.exempt` alone says nothing about who made a file
    assert k.derived(so_ / "docs/gen.md") and not k.derived(so_ / "docs/hand.md") and not k.derived(so_ / "src/app.py")
    assert 'data-seal="derived"' in home_ and 'data-seal="unsealed"' in home_
    gen_ = hit("GET", "/docs/gen.md")[1]
    assert "derived from the code" in gen_ and "<dialog id=seal>" not in gen_ and "Seal…" not in gen_
    assert "<dialog id=seal>" in hit("GET", "/docs/hand.md")[1]  # a page the policy requires still has its modal
    (so_ / "src/gen_tbl.py").write_text("T = {}\n")  # a non-markdown file built from the code: shown, marked, never sealed
    (so_ / "src/gen_other.py").write_text("U = {}\n")  # exempt too, but no generator recorded it: not derived, not listed
    assert not k.derived(so_ / "src/gen_tbl.py") and k.mark_derived(so_ / "src/gen_tbl.py", "gen.py") and not k.derived(so_ / "src/gen_other.py")
    st_, gp_, _ = hit("GET", "/src/gen_tbl.py")
    assert k.derived(so_ / "src/gen_tbl.py") and st_ == 200 and "derived from the code" in gp_ and "<dialog id=seal>" not in gp_ and "Seal…" not in gp_
    assert "gen_tbl.py" not in [p.name for p in k.sealonly_files()] and "gen_tbl.py" in [p.name for p in k.derived_files()]
    assert "gen_other.py" not in [p.name for p in k.sealonly_files() + k.derived_files()]
    assert [e["derived"] for e in k.ledger_by_file()["src/gen_tbl.py"]] == ["gen.py"] and not k.reviews({}, "src/gen_tbl.py", "T = {}\n", k.ledger_by_file())[0]  # a generator's line is no review
    (so_ / "src/gen_tbl.py").write_text("T = {'edited': 1}\n")  # edited by hand: the line no longer matches
    assert not k.derived(so_ / "src/gen_tbl.py")
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
        assert bowerbird_serve.start(k, port) == 0  # ours is already there: a no-op that says so
    assert "running" in out_.getvalue()
    assert hit("POST", "/_stop", {"_t": re.search(r'name=_t value="([^"]+)"', hit("GET", "/")[1]).group(1)})[0] == 200
    os.chdir(here_)
    k.KB_ROOT, k.OPTS["format"], k.OPTS["seal"] = prev_

# bowers: the root lists the folders that carry their own kbmcp.yaml, and only those are its overrides. A bower run on its own is
# its own collection; one run inside the collection finds the root that lists it. --config takes a folder, a relative path and `~`.
def tree(files):
    d = Path(tempfile.mkdtemp()).resolve()
    for n, x in files.items():
        (d / n).parent.mkdir(parents=True, exist_ok=True)
        (d / n).write_text(x)
    return d


bw_saved = (k.KB_ROOT, k.CFG_DIR, k.OPTS["format"], os.getcwd(), os.environ.get("HOME"))
bw = tree({"kbmcp.yaml": "format: markdown\nbowers: [docs, adr/*]\n", "docs/kbmcp.yaml": "format: okf\nroles: [read]\n", "docs/a.md": "# A\n",
           "adr/one/kbmcp.yaml": "format: adr\n", "adr/two/x.md": "# no config\n", "stray/kbmcp.yaml": "format: skos\n", "stray/b.md": "# B\n"})
assert k.load_config(bw / "docs")[0] == bw and k.load_config(bw / "adr/one")[0] == bw  # a listed bower finds the root that lists it
assert k.load_config(bw / "stray")[0] == bw / "stray"  # an unlisted one is its own collection
k.KB_ROOT, k.CFG_DIR, k.OPTS["format"] = bw, bw, "markdown"
k._SCOPES.clear()
assert {d for d, _ in k.scopes()} == {bw / "docs", bw / "adr/one"} and "roles" not in dict(k.scopes())[bw / "docs"]  # the root decides roles
assert (k.fmt_of(bw / "docs/a.md"), k.fmt_of(bw / "adr/one/y.md"), k.fmt_of(bw / "stray/b.md")) == ("okf", "adr", "markdown")
(bw / "kbmcp.yaml").write_text("format: markdown\nbowers: [docs, nope]\n")
k._SCOPES.clear()
try:
    k.scopes()
    raise AssertionError("a bowers entry that names nothing must stop")
except SystemExit as e_:
    assert "bowers entry 'nope'" in str(e_)
(bw / "kbmcp.yaml").write_text("format: markdown\n")  # no bowers key: the older rule, every kbmcp.yaml below is an override
k._SCOPES.clear()
try:
    k.scopes()  # the older rule still refuses a whole-collection key in a nested file (docs/kbmcp.yaml sets roles)
    raise AssertionError("roles in a nested kbmcp.yaml must stop the older rule")
except SystemExit as e_:
    assert "belongs to the whole collection" in str(e_)
k._SCOPES.clear()
(bw / "docs/kbmcp.yaml").write_text("format: okf\n")
assert {d for d, _ in k.scopes()} == {bw / "docs", bw / "adr/one", bw / "stray"}
for given in (str(bw), str(bw / "kbmcp.yaml")):
    assert k.load_config(Path("/"), given)[0] == bw
os.chdir(bw.parent)
os.environ["HOME"] = str(bw.parent)
assert k.load_config(Path("/"), bw.name)[0] == bw and k.load_config(Path("/"), f"~/{bw.name}")[0] == bw  # relative, and ~
os.chdir(bw_saved[3])
if bw_saved[4] is None:
    del os.environ["HOME"]
else:
    os.environ["HOME"] = bw_saved[4]
k.KB_ROOT, k.CFG_DIR, k.OPTS["format"] = bw_saved[:3]
k._SCOPES.clear()
k._POLICY.clear()
# with no root file and no repository, what lies below is not ours: nothing is scanned
lone = tree({"deep/kbmcp.yaml": "format: skos\n", "deep/c.md": "# C\n"})
k.KB_ROOT = lone
k._SCOPES.clear()
assert k.scopes() == []
k.KB_ROOT = bw_saved[0]
k._SCOPES.clear()

# new: a document from a template. The folder's kbmcp.yaml picks it, template= overrides, and an existing file is refused.
nw_saved = (k.KB_ROOT, k.CFG_DIR, k.OPTS["format"])
nw = mixed("markdown", {"decisions/kbmcp.yaml": "format: adr\n", "notes/a.md": "# A\n"})
R = k.new("notes/b")
assert R["template"] == "markdown" and R["file"] == "notes/b.md" and (nw / "notes/b.md").read_text() == "---\ntitle: b\ntags: []\n---\n\n# b\n", R
R = k.new("decisions/0002-use-x", title="Use X")
t_ = (nw / "decisions/0002-use-x.md").read_text()
assert R["template"] == "adr" and "# Use X" in t_ and "## Context and Problem Statement" in t_ and "status: proposed" in t_ and "{today}" not in t_, t_
assert "type: Reference" in (nw / "notes/c.md").read_text() if k.new("notes/c", template="okf")["template"] == "okf" else False
assert "exists" in raises(k.new, "notes/b") and "template 'rst'" in raises(k.new, "notes/z", template="rst")
with contextlib.redirect_stdout(io.StringIO()):
    assert k.cli(["new", "notes/d", "-t", "adr", "-T", "Dee"]) == 0  # the short flags: -t template, -T title
assert "# Dee" in (nw / "notes/d.md").read_text() and "decision-makers" in (nw / "notes/d.md").read_text()
k.KB_ROOT, k.CFG_DIR, k.OPTS["format"] = nw_saved
k._SCOPES.clear()
k._POLICY.clear()

# A bare `bowerbird-mcp` at a terminal: the help, then an offer to make a knowledgebase where there is none; "n" writes nothing.
class Tty(io.StringIO):
    def isatty(self):
        return True


wz_saved = (k.KB_ROOT, k.CFG_DIR, k.OPTS["format"], sys.stdin, k.out_terminal, k.kb_user)
wz = Path(tempfile.mkdtemp()).resolve()
(wz / "a.md").write_text("# A\n\nHello there.\n")
k.KB_ROOT, k.CFG_DIR, k.OPTS["format"], k.out_terminal, k.kb_user = wz, None, "markdown", (lambda: True), (lambda: "tester")
k._SCOPES.clear()
k._POLICY.clear()
sys.stdin = Tty("n\n")
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert k.welcome() == 0
assert "not a knowledgebase yet" in wo.getvalue() and "Knowledge" in wo.getvalue() and not (wz / "kbmcp.yaml").exists()
sys.stdin = Tty("y\nTest notes.\nmarkdown\n")  # create it: about, then the format (the folder's guess is offered)
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert k.welcome() == 0
wc = (wz / "kbmcp.yaml").read_text()
assert "about: Test notes." in wc and "format: markdown" in wc and (wz / ".mcp.json").is_file() and "Done." in wo.getvalue(), wo.getvalue()
k.CFG_DIR = wz  # now it is a collection: the help only, no offer
with contextlib.redirect_stdout(io.StringIO()) as wo:
    assert k.welcome() == 0
assert "not a knowledgebase yet" not in wo.getvalue()
k.KB_ROOT, k.CFG_DIR, k.OPTS["format"], sys.stdin, k.out_terminal, k.kb_user = wz_saved
k._SCOPES.clear()
k._POLICY.clear()


# fact blocks: [fact.url] and [fact.mcp] spans in a document, the state of checking them in .facts.yaml beside it, a drift ending
# the reviews before it, and `factcheck --fetch` fetching a page and calling a declared MCP tool for a fresh result.
import builtins
import functools
import http.server
import threading

import bowerbird_facts as F

fb, fp = F.parse("[fact.url] https://x.test/p\n\nWords  here.\n\n[fact.end] and [fact.mcp] jira K-1 is open [fact.end]\n```\n[fact.url] hidden\n```\n")
assert [(b.kind, b.source) for b in fb] == [("url", "https://x.test/p"), ("mcp", "jira K-1")] and fp == []
assert fb[0].claim == "Words  here." and (fb[0].line, fb[0].end_line) == (1, 5) and fb[1].claim == "jira K-1 is open" or fb[1].claim.startswith("jira K-1")
for bad, why in (("[fact.url] https://x\nwords", "unclosed_fact"), ("words [fact.end]", "stray_fact_end"), ("[fact.zip] a b c [fact.end]", "unknown_fact_kind"),
                 ("[fact.url] nope\n\nw\n\n[fact.end]", "bad_fact"), ("[fact.url] https://x\n[fact.end]", "bad_fact"), ("[fact.mcp] jira [fact.end]", "bad_fact"),
                 ("[fact.url] https://x\nw\n[fact.url] https://y\nv\n[fact.end]", "unclosed_fact")):
    assert why in {p[1] for p in F.parse(bad)[1]}, (bad, F.parse(bad)[1])
assert F.norm("`A`  b\n**C**") == "a b c" and F.fact_id("url", "u", "A  b") == F.fact_id("url", "u", "a b") != F.fact_id("url", "u", "a c")
assert F.check_literal("One.\n\nTwo.", "x ONE. y") == (1, 2) and F.check_literal("`one`", "One") == (1, 1)
lk, lk_saved = Path(tempfile.mkdtemp()).resolve(), k.KB_ROOT
k.KB_ROOT = lk
create(apply=True, holds="okf", about="facts", user="u")
(lk / "a.md").write_text("---\ntype: Note\ndescription: d\n---\n# A\n\n[fact.url] https://x.test/p\n\nwords\n")  # never closed
assert any(f["kind"] == "unclosed_fact" and f["severity"] == "error" for f in k.lint(bundle=".", limit=0)["findings"])
(lk / "a.md").write_text("---\ntype: Note\ndescription: d\n---\n# A\n\n[fact.url] https://x.test/p\n\nwords\n\n[fact.end]\n\n[fact.mcp] jira K-1 is open [fact.end]\n")
undeclared = [f for f in k.lint(bundle=".", limit=0)["findings"] if f["file"] == "a.md" and f["kind"] == "undeclared_fact_source"]
assert undeclared and undeclared[0]["severity"] == "warning" and "jira" in undeclared[0]["message"]
assert not any(f["kind"].endswith("_fact") or f["kind"].startswith(("unclosed", "stray")) for f in k.lint(bundle=".", limit=0)["findings"])
k.KB_ROOT = lk_saved

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
(fk / "kbmcp.yaml").write_text("format: markdown\n")
doc = (f"# Jenkins\n\n[fact.url] http://127.0.0.1:{srv.server_address[1]}/page.html\n\n`(jenkins_url)/safeRestart` - Allows all running jobs to complete.\n\n"
       "(jenkins_url)/restart - Forces a restart without waiting for builds to complete.\n\n[fact.end]\n\nThe ticket: [fact.mcp] jira INFRA-1 is open [fact.end]\n")
(fk / "notes.md").write_text(doc)
saved = (k.KB_ROOT, k.CFG, k.CLI, k.at_terminal, builtins.input, dict(k.OPTS))
k.KB_ROOT, k.CLI, k.OPTS["format"] = fk, True, "markdown"
k.CFG = {"facts": {"mcp": {"jira": {"tool": "get_issue", "arg": "issue_key", "watch": "fields.status.name"}}}}
try:
    assert [(r["line"], r["kind"], r["status"]) for r in k.factcheck()["blocks"]] == [(3, "url", "unchecked"), (11, "mcp", "unchecked")]  # information only
    assert not (fk / ".facts.yaml").exists()
    k.at_terminal = lambda: False
    assert "terminal-only" in raises(k.factcheck, fetch=True)  # a pipe, a script or an agent cannot run it
    k.at_terminal, builtins.input = (lambda: True), (lambda *a: "n")
    assert k.factcheck(fetch=True)["note"] == "nothing run" and not (fk / ".facts.yaml").exists()  # shown, asked, declined
    builtins.input = lambda *a: "y"
    r = k.factcheck(fetch=True)
    assert [(x["kind"], x["status"], x["method"]) for x in r["checked"]] == [("url", "checked", "same words"), ("mcp", "checked", "baseline recorded")] and r["drifted"] == 0, r
    assert [x["status"] for x in k.factcheck()["blocks"]] == ["checked", "checked"] and "value: Open" in (fk / ".facts.yaml").read_text()
    assert [x["method"] for x in k.factcheck(fetch=True)["checked"]] == ["same words", "same value"]  # the result's other fields (updated) are not watched
    # a seal on the file, then a drift: the seal stops holding; one made after the drift holds
    text = (fk / "notes.md").read_text()
    sealed = {"file": "notes.md", "sha256": k.content_hash(text, False), "by": "human:t", "at": k.now(), "bowerbird": k.VERSION}
    k.ledger_put("notes.md", sealed)
    assert len(k.reviews({}, "notes.md", text, k.ledger_by_file())[1]) == 1
    (fk / "status.txt").write_text("Closed\n")
    r = k.factcheck(fetch=True)
    assert [(x["kind"], x["status"]) for x in r["checked"]] == [("url", "checked"), ("mcp", "drifted")] and r["drifted"] == 1 and "Closed" in r["checked"][1]["method"], r
    assert k.REG["factcheck"].exit(r) == 1 and k.REG["factcheck"].exit({"drifted": 0}) == 0
    assert k.reviews({}, "notes.md", text, k.ledger_by_file())[1] == [] and k.drift_of("notes.md", {}) is not None
    assert any(f["kind"] == "stale_signature" and "fact drifted" in f["message"] for f in k.signatures("")["findings"])
    time.sleep(1.1)
    k.ledger_put("notes.md", {**sealed, "at": k.now()})  # a human reviews it again, after the drift
    assert len(k.reviews({}, "notes.md", text, k.ledger_by_file())[1]) == 1
    # the page changes: the block drifts, and the same check by meaning needs the extra and `semantic: true`
    (site / "page.html").write_text((site / "page.html").read_text().replace("Forces a restart without waiting", "Does something else"))
    assert k.factcheck(fetch=True)["checked"][0]["status"] == "drifted"
    k.EMBEDDERS["facts-test"] = lambda texts: [[1.0, 0.0] if "restart" in t.lower() or "complete" in t.lower() else [0.0, 1.0] for t in texts]
    k.OPTS.update(semantic=True, semantic_model="facts-test", min_similarity=0.6)
    r = k.factcheck(fetch=True)["checked"][0]
    assert (r["status"], r["method"]) == ("checked", "similar meaning"), r
    (fk / "notes.md").write_text(doc.replace("is open", "is closed"))  # editing the words makes a new fact: unchecked until it is checked
    assert [x["status"] for x in k.factcheck()["blocks"]] == ["checked", "unchecked"]
    k.CFG = {"facts": {}}
    assert [x["status"] for x in k.factcheck(fetch=True)["checked"]][1] == "skipped"  # not declared in kbmcp.yaml: never called
finally:
    k.KB_ROOT, k.CFG, k.CLI, k.at_terminal, builtins.input = saved[:5]
    k.OPTS.clear()
    k.OPTS.update(saved[5])
    srv.shutdown()


# seals carry a comment by default; the seal extensions (seal.extensions, seal.quorum) let several people seal one version.
sk = Path(tempfile.mkdtemp()).resolve()
(sk / "kbmcp.yaml").write_text("format: markdown\n")
(sk / "a.md").write_text("# A\n\nbody\n")
seal_saved = (k.KB_ROOT, k.CLI, k.ATTEST, dict(k.OPTS))
k.KB_ROOT, k.CLI, k.OPTS["format"] = sk, True, "markdown"
k.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": False, "quorum": 1}
k._SCOPES.clear()
k._POLICY.clear()
human = lambda who, **kw: (setattr(k, "ATTEST", f"human:{who}"), asyncio.run(k.seal(file="a.md", **kw)), setattr(k, "ATTEST", ""))[1]
try:
    out = human("ann", comment="  checked   the steps\n")  # a default seal: a comment, no extension needed
    led = (sk / ".waxseals.yaml").read_text()
    assert "comment: checked the steps" in led and "by: 'human:ann'" in led and "seals:" not in led and out["tier"] == "human-reviewed", led
    assert k.ledger_by_file()["a.md"][0]["comment"] == "checked the steps"
    assert "280" in raises(human, "ann", comment="x" * 281)
    human("bo")  # without the extension a second seal replaces the first: one line, the latest
    assert len(k.ledger_by_file()["a.md"]) == 1 and k.ledger_by_file()["a.md"][0]["by"] == "human:bo" and "comment" not in (sk / ".waxseals.yaml").read_text()
    # the extensions on, quorum 2, on a new version of the file (the earlier seals bound the old bytes)
    (sk / "a.md").write_text("# A\n\nbody, second version\n")
    k.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": True, "quorum": 2}
    k._POLICY.clear()
    out = human("ann", comment="steps match the runbook")
    assert out["tier"] == "unverified" and out["quorum"] == "1 of 2", out  # one person is short of two
    short = [f for f in k.signatures("")["findings"] if f["file"] == "a.md"]
    assert [f["kind"] for f in short] == ["short_of_quorum"] and "1 of 2" in short[0]["message"], short
    assert k.trust_tier(k.signed({}, "a.md", k.ledger_by_file())) == "unverified"
    human("ann", comment="again")  # the same person replaces their own seal, they do not count twice
    assert len(k.ledger_by_file()["a.md"]) == 1
    asyncio.run(k.seal(file="a.md", by="process:ci"))  # a machine check is not a signer
    assert [f["kind"] for f in k.signatures("")["findings"] if f["file"] == "a.md"] == ["short_of_quorum"]
    out = human("bo", comment="agreed")
    assert out["tier"] == "human-reviewed" and "quorum" not in out, out
    line = [ln for ln in (sk / ".waxseals.yaml").read_text().splitlines() if "a.md" in ln]
    assert len(line) == 1 and line[0].count("by:") == 3 and "comment: again" in line[0] and "comment: agreed" in line[0], line  # one line for the file, every seal on it
    assert not [f for f in k.signatures("")["findings"] if f["file"] == "a.md"]
    assert k.trust_tier(k.signed({}, "a.md", k.ledger_by_file())) == "human-reviewed"
    (sk / "a.md").write_text("# A\n\nbody, edited\n")  # an edit ends every seal of the old version
    assert [f["kind"] for f in k.signatures("")["findings"] if f["file"] == "a.md"] == ["stale_signature"]
    human("cy")
    assert [e["by"] for e in k.ledger_by_file()["a.md"]] == ["human:cy"]  # the old version's seals are not carried over
    k.OPTS["seal"] = {"exempt": [], "exempt_status": [], "extensions": False, "quorum": 1}  # off again: the line still reads, the latest counts
    k._POLICY.clear()
    assert [e["by"] for e in k.ledger_by_file()["a.md"]] == ["human:cy"]
    for bad, why in (("seal: {quorum: 2}\n", "needs extensions"), ("seal: {extensions: true, quorum: 0}\n", "whole number"), ("seal: {extensions: 1}\n", "true or false")):
        (sk / "kbmcp.yaml").write_text(bad)
        try:
            k.load_config(sk)
            raise AssertionError(bad)
        except SystemExit as e:
            assert why in str(e), (bad, str(e))
    (sk / "kbmcp.yaml").write_text("format: markdown\nseal: {extensions: true, quorum: 3}\n")
    assert k.load_config(sk)[1]["seal"] == {"extensions": True, "quorum": 3}
finally:
    k.KB_ROOT, k.CLI, k.ATTEST = seal_saved[:3]
    k.OPTS.clear()
    k.OPTS.update(seal_saved[3])
    k._SCOPES.clear()
    k._POLICY.clear()


# create: a collection, or a bower of one; --mcp and --env as steps; .mcp.json merged, not replaced; settings it ignores are said.
assert k.with_bower("# c\nbowers: [a]\nx: 1\n", "b") == "# c\nbowers: [a, b]\nx: 1\n" and k.with_bower("bowers: []\n", "b") == "bowers: [b]\n"
assert k.with_bower("bowers:\n  - a\nx: 1\n", "b") == "bowers:\n  - a\n  - b\nx: 1\n" and k.with_bower("bowers: [a]\n", "a") == "bowers: [a]\n"
assert k.with_bower("format: markdown\n", "b") is None and "comment" in raises(k.with_bower, "bowers: [a]  # why\n", "b") + "comment"
cr, cr_saved = Path(tempfile.mkdtemp()).resolve(), k.KB_ROOT
(cr / "kbmcp.yaml").write_text("# the root\nformat: markdown\nbowers: [docs]\n")
(cr / "docs").mkdir()
(cr / "docs/kbmcp.yaml").write_text("format: markdown\n")
k.KB_ROOT = cr
try:
    P = create(path=str(cr / "notes"), holds="markdown", about="Notes.", user="u")  # a preview writes nothing
    assert not (cr / "notes").exists() and P["bower"]["listed"] == "notes" and "would_edit" in P
    P = create(path=str(cr / "notes"), holds="markdown", about="Notes.", user="u", apply=True)  # inside a collection with a list: a bower
    assert (cr / "kbmcp.yaml").read_text() == "# the root\nformat: markdown\nbowers: [docs, notes]\n", (cr / "kbmcp.yaml").read_text()
    bt = (cr / "notes/kbmcp.yaml").read_text()  # a bower gets the whole commented template, with only the answers uncommented
    assert bt == k.filled_config({"about": "Notes.", "format": "markdown"}).replace("\n\n", "\n# This is a bower of kbmcp.yaml: only format, seal, about, hubs and min_similarity are read here.\n# The rest are the root's to decide; they are listed below for reference.\n\n", 1), bt
    assert len(bt.splitlines()) > 60 and k.yaml.safe_load(bt) == {"about": "Notes.", "format": "markdown"} and sorted(p.name for p in (cr / "notes").iterdir()) == ["kbmcp.yaml"]
    assert k.load_config(cr)[1]["bowers"] == ["docs", "notes"]  # and the root still reads it as a bower, not as a second root
    assert "is a bower" in raises(create, path=str(cr / "notes"))
    P = create(path=str(cr / "more"), holds="adr", about="a", user="u", mcp=True, apply=True)  # a bower shares the root's files
    assert "mcp and env were not used" in P["ignored"][0] and not (cr / "more/.mcp.json").exists()
    assert k.load_config(cr)[1]["bowers"] == ["docs", "notes", "more"]
    nr = Path(tempfile.mkdtemp()).resolve()  # a new root, with only the assistant's part
    P = create(path=str(nr), holds="markdown", about="A.", user="u", mcp=True, apply=True)
    assert sorted(p.name for p in nr.iterdir()) == [".mcp.json", "BOWERBIRD.md", "kbmcp.yaml"] and P["mcp"] == "written" and P["agent"] == {"file": os.path.relpath(nr / "BOWERBIRD.md", cr), "state": "written"}
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
    P = create(path=str(nr), about="zzz", holds="adr")  # settings for a folder that has its kbmcp.yaml are not used, and it says so
    assert "were not used" in P["ignored"][0] and "format: markdown" in (nr / "kbmcp.yaml").read_text()
    er = Path(tempfile.mkdtemp()).resolve()  # the other step
    create(path=str(er), holds="markdown", about="E.", user="u", env=True, apply=True)
    assert sorted(p.name for p in er.iterdir()) == [".env", "env.example", "kbmcp.yaml"] and (er / ".env").read_text() == "KB_USER=u\n"
    assert all(cli(n)[0] == 2 for n in ("init", "cite", "recheck_plan"))  # renamed in 2.2.0: each says where it went
    assert cli("create", "file=x.md", "type=Note")[0] == 2  # a document is `new`
finally:
    k.KB_ROOT = cr_saved


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
sha = lambda n: k.content_hash(pages[n].read_text(), False)
(hd / ".waxseals.yaml").write_text("\n".join([
    f"- {{file: docs/sealed.md, sha256: {sha('sealed.md')}, by: 'human:ann', at: '2026-11-20T10:00:00Z'}}",
    "- {file: docs/edited.md, sha256: 0000, by: 'human:ann', at: '2026-11-19T10:00:00Z'}",
    f"- {{file: docs/made.md, sha256: {sha('made.md')}, derived: gen.py, at: '2026-11-20T10:00:00Z'}}",
    f"- {{file: docs/exempt.md, sha256: {sha('exempt.md')}, seals: [{{by: 'human:ann', at: '2026-11-18T10:00:00Z'}}, {{by: 'human:bo', at: '2026-11-20T11:00:00Z'}}]}}"]) + "\n")
(hd / "docs" / "kbmcp.yaml").write_text("seal: {exempt: ['/exempt.md', '/none.md']}\n")  # a policy the hook does not read
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
    (rs / "kbmcp.yaml").write_text("format: markdown\n")
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

print("ok")
