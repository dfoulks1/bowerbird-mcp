#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.10,<2", "pyyaml"]
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
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
kb = Path(tempfile.mkdtemp()) / "kb"
kb.mkdir()
os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
(kb / "kbmcp.yaml").write_text("")  # the config file marks the knowledgebase root
sys.argv[1:] = ["--config", str(kb / "kbmcp.yaml")]
sys.path.insert(0, str(HERE))
import bowerbird_mcp as k


def init(**kw):
    return asyncio.run(k.init(**kw))

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
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = k.cli(list(argv))
    k.CLI, k.ATTEST = False, ""
    return code, buf.getvalue()


# init: a new bundle is conformant and clean; a second init refuses.
assert init()["would_edit"] == {".": ["index.md", "log.md"]}
init(apply=True)
assert k.lint()["ok"] and k.lint()["conformant"], k.lint()
raises(k.init, apply=True)

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
assert "only a human" in raises(k.recheck_apply, file="note.md", id="x", by="human:drew")

# cite / recheck: a recorded MCP call is the source and the re-check recipe.
(kb / ".mcp.json").write_text(json.dumps({"mcpServers": {"jira": {"command": "x", "env": {"TOKEN": "secret"}}}}))
raises(k.cite, "note.md", server="nope", tool="get_issue")
c = k.cite("note.md", server="jira", tool="get_issue", args={"issue_key": "INFRA-1"},
           title="INFRA-1 status", stale_days=30)
assert c["footnote"] == "[^infra-1]"
(kb / "note.md").write_text((kb / "note.md").read_text().replace("Body.", "The ticket is open.[^infra-1]"))
d = k.meta((kb / "note.md").read_text())[0]
assert d["sources"][0]["resource"] == "mcp://jira/get_issue?issue_key=INFRA-1" and TS.fullmatch(d["stale_after"])
assert k.lint()["ok"], k.lint()
plan = k.recheck_plan()
assert plan["calls"][0]["call"] == {"server": "jira", "tool": "get_issue", "args": {"issue_key": "INFRA-1"}}
assert k.recheck_plan(older_than_days=1)["calls"] == []
assert "The ticket is open" in plan["calls"][0]["cites"][0]
assert k.recheck_apply([{"file": "note.md", "id": "infra-1"}])[0]["checked"] == ["infra-1"]
n = len(k.entries(k.meta((kb / "note.md").read_text())[0]["verified"]))
assert k.recheck_apply(file="note.md", by="process:nightly")[0]["checked"] == ["infra-1"]  # no id: every source
assert k.entries(k.meta((kb / "note.md").read_text())[0]["verified"])[-1]["by"] == "process:nightly"
assert len(k.entries(k.meta((kb / "note.md").read_text())[0]["verified"])) == n + 1
assert k.recheck_apply(file="note.md", id="nope")[0]["result"] == "no such source"
assert cli("recheck_apply", "file=note.md", "--attest")[0] == 0  # a person: "I checked this concept's sources"
assert k.entries(k.meta((kb / "note.md").read_text())[0]["verified"])[-1]["by"] == "human:drew"
assert cli("cite", "file=note.md", "resource=https://x", "--attest")[0] == 2  # citing is not confirming
assert "secret" not in json.dumps(k.lint(limit=0))
k.cite("note.md", resource="https://example.com/page", title="Page")
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
k.create("guides/howto", "Playbook", description="How to.", tags=["ops"], status="draft", body="Step one.",
         by="claude-code/claude-opus-5-5")
t = (kb / "guides/howto.md").read_text()
d = k.meta(t)[0]
assert d["type"] == "Playbook" and d["generated"]["by"] == "claude-code/claude-opus-5-5" and "# howto\n\nStep one." in t
raises(k.create, "guides/howto", "Playbook")
raises(k.create, "x", " ")
raises(k.create, "index", "Note")
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
k.create("promo", "Note", description="P.", status="draft")
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
init(apply=True, bundle="uses")
k.create("t/src.md", "Reference", description="s.", bundle="uses", resource="https://example.com/x")
k.create("t/m.md", "Metric", description="m.", body="[later](/t/unwritten.md)", bundle="uses")
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
k.cite("t/m.md", resource="https://example.com/doc", author="team:docs", usage_count=0,
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
k.create("t/d.md", "Note", description="d.", status="draft", by="claude-code/x", bundle="uses")
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

# The archive also works when the knowledgebase root is itself a bundle: it is set apart, not nested.
one = Path(tempfile.mkdtemp()) / "solo"
one.mkdir()
k.KB_ROOT = one
init(apply=True)
k.create("x.md", "Note", description="x.", bundle=".")
k.archive("x.md", bundle=".", apply=True)
assert (one / "archive/solo/x.md").exists() and "nested_bundle" not in kinds() and not (one / "x.md").exists()
k.unarchive("solo/x.md", apply=True)
assert (one / "x.md").exists() and not (one / "archive/solo/x.md").exists()
k.KB_ROOT = saved

# A knowledgebase of sibling bundles: tools follow where the user is; bundles do not nest.
saved, cwd, ws = k.KB_ROOT, os.getcwd(), (kb.parent / "ws").resolve()
ws.mkdir()
k.KB_ROOT = ws
init(apply=True, bundle="a")
init(apply=True, bundle="b")
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
k.baseline(apply=True)  # fingerprints are knowledgebase-relative, so they hold from any directory
os.chdir(ws / "a")
assert k.lint(baseline=".okf-baseline.json")["total"] == 0 and k.lint(baseline=".okf-baseline.json")["baselined"]
os.chdir(ws)
assert "migrate" in raises(k.move, "a/sub/c.md", "b/c.md")
k.migrate("a/sub/c.md", "b", apply=True)
assert (ws / "b/sub/c.md").exists() and not (ws / "a/sub/c.md").exists()
assert "[c](../b/sub/c.md)" in (ws / "a/n.md").read_text() and "[n](../../a/n.md)" in (ws / "b/sub/c.md").read_text()
assert k.meta((ws / "b/sub/c.md").read_text())[0]["sources"][0]["resource"] == "../../a/n.md"
assert "Migrated" in (ws / "a/log.md").read_text() and "Migrated" in (ws / "b/log.md").read_text()
assert "nest" in raises(k.init, bundle="a/inner", apply=True)
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
w = k.web()  # at the knowledgebase root: bundles, edges counted
assert w["level"] == "bundles" and {"from": "a", "to": "b", "kind": "link", "count": 2} in w["edges"], w
assert k.web(bundle="a")["level"] == "concepts" and k.graph(w).startswith("graph LR\n")
code, out = cli("web", "format=mermaid")
assert code == 0 and "-->|link|" in out
assert k.knowledgebase(ws / "a/sub") == ws / "a"  # no index above yet: the bundle is the knowledgebase
assert "index_stale" not in kinds() and k.index(apply=True)["edited"] == {".": ["index.md"]}
assert k.upgrade()["would_edit"] == {} and not k.declares(ws / "index.md")  # the knowledgebase root stays no bundle
assert (ws / "index.md").read_text().count("* [") == 3 and "* [b](b/)" in (ws / "index.md").read_text()
assert k.knowledgebase(ws / "a/sub") == ws and k.knowledgebase(ws) == ws
(ws / "c").mkdir()
init(apply=True, bundle="c")
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
(kb / "bare.md").write_text("---\ntype: x\n---\n")
assert cli("set", "bare.md", "status=draft", "tags=[a, b]", "apply=true")[0] == 0  # frontmatter as key=value
assert k.meta((kb / "bare.md").read_text())[0] | {} == {"type": "x", "status": "draft", "tags": ["a", "b"]}
assert cli("move", "bare.md", "bare2.md", "apply=true")[0] == 0 and (kb / "bare2.md").exists()  # bare arguments
(kb / "bare2.md").unlink()
assert set(k.EXAMPLES) == set(k.REG)  # every tool has an example
code, out = cli("help", "move")
assert code == 0 and "to: str  (required)" in out and cli("move", "--help")[1] == out
code, out = cli("bundles", "format=text")
assert code == 0 and out.startswith("bundles:")
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
g("remote", "set-url", "origin", f"file://{src}")
assert k.permalink(src, src.resolve()) is None

# Ranked search, dirs, vocab, demand; new lint kinds and only/ignore.
saved, rk = k.KB_ROOT, Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = rk
init(apply=True)
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
assert {(d["dir"], d["concepts"]) for d in k.dirs()["dirs"]} == {(".", 3), ("ops", 2)}
assert k.vocab() == {"tags": {"ops": 2}, "types": {"Note": 3, "Playbook": 2}}
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
(rk / "kbmcp.yaml").write_text(k.EXAMPLE_CONFIG)  # at the knowledgebase root: right
assert any(f.startswith("ops/") for f, _ in kinds_of())
(rk / "ops/kbmcp.yaml").write_text("")  # any folder holding a kbmcp.yaml is its own knowledgebase: this one skips it
assert not any(f.startswith("ops/") for f, _ in kinds_of()) and not any(x == "nested_config" for _, x in kinds_of())
(rk / "ops/kbmcp.yaml").unlink()
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
for bad, msg in (("semantic: 3", "semantic must be a bool"), ("seal: {nope: 1}", "seal takes require and exempt_status"), ("vector_index: faiss", "vector_index must be"), ("format: rst", "format must be okf, markdown, adr, skos"), ("build: sometimes", "must be auto or manual"),
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
        k.sqlite3.connect(":memory:").enable_load_extension
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
# the config file marks the knowledgebase: found from the working directory or named by --config; KB_ROOT is refused.
probe = "import sys; sys.argv = ['x', *sys.argv[1:]]; import bowerbird_mcp as k; print(k.KB_ROOT); print(k.INSTRUCTIONS)"
def where(cwd, *argv, **env):
    e = {kk: v for kk, v in os.environ.items() if kk != "KB_ROLE"} | {"PYTHONPATH": str(HERE)} | env
    return subprocess.run([sys.executable, "-c", probe, *argv], cwd=cwd, env=e, capture_output=True, text=True, check=False)
base = Path(tempfile.mkdtemp()).resolve()
(base / "eng/deep").mkdir(parents=True)
(base / "eng/kbmcp.yaml").write_text("about: Engineering runbooks.\n")
r = where(base / "eng/deep")  # found from below: the file's own folder is the knowledgebase
assert r.stdout.splitlines()[0] == str(base / "eng") and "This knowledgebase: Engineering runbooks." in r.stdout, r
assert where(base / "eng").stdout.splitlines()[0] == str(base / "eng")
(base / "other").mkdir()
r = where(base / "other", "--config", str(base / "eng/kbmcp.yaml"))  # --config wins over where we are
assert r.stdout.splitlines()[0] == str(base / "eng") and "Engineering runbooks" in r.stdout, r
r = where(base / "other", "--config", str(base / "nope.yaml"))
assert r.returncode and "--config takes the path" in r.stderr, r
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
P = init()
assert P["config"]["files"][:2] == ["kbmcp.yaml", "env.example"] and P["config"]["gitignore"] == ".gitignore gets .env", P  # .env too if a user id is known
assert "about" in P["config"]["missing"] and not (gr / "kbmcp.yaml").exists(), P  # apply=false writes nothing
P = init(apply=True)
assert (gr / ".gitignore").read_text() == "build/\n.env\n" and (gr / "env.example").read_text() == k.ENV_EXAMPLE
got = k.load_config(gr)[1]
assert got == {"format": "okf", "passages": True, "hubs": True, "semantic": False, "semantic_model": k.DEFAULTS["semantic_model"],
               "min_similarity": k.DEFAULTS["min_similarity"], "index": k.DEFAULTS["index"]}, got
assert k.declares(gr / "index.md") and (gr / "log.md").is_file()  # okf: a bundle too
# init also writes a .mcp.json (commit it: a clone has the tools with nothing to register), and never overwrites one.
mj = json.loads((gr / ".mcp.json").read_text())
assert mj == k.MCP_JSON and mj["mcpServers"]["bowerbird"]["command"] == "uvx" and "--role" not in mj["mcpServers"]["bowerbird"]["args"]
# given values fill it in; markdown and skos start no bundle; nothing is overwritten.
md = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = md
P = init(apply=True, about="Decisions.", holds="markdown", user="dfoulks")
assert k.load_config(md)[1]["about"] == "Decisions." and k.load_config(md)[1]["format"] == "markdown", P
assert (md / ".env").read_text() == "KB_USER=dfoulks\n" and not (md / "index.md").exists() and P["config"]["missing"] == []
raises(init, holds="rst")
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
        return SimpleNamespace(action=self.action, data=schema(**{**{"about": "", "holds": "markdown", "user": ""}, **self.data}))
a1 = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = a1
ask = Ask(about="Ops notes.", holds="markdown", user="me")
asyncio.run(k.init(apply=True, ctx=ask))
assert len(ask.asked) == 1 and "about" in ask.asked[0]
assert k.load_config(a1)[1]["about"] == "Ops notes." and (a1 / ".env").read_text() == "KB_USER=me\n"
a2 = Path(tempfile.mkdtemp()).resolve()
k.KB_ROOT = a2
assert asyncio.run(k.init(apply=True, ctx=Ask("decline")))["config"]["missing"]  # no answer: written with what it has
assert "about" not in k.load_config(a2)[1]
# a folder holding its own kbmcp.yaml is another knowledgebase: the parent's lint does not see inside it.
k.KB_ROOT = gr
(gr / "sub").mkdir()
(gr / "sub/kbmcp.yaml").write_text("")
(gr / "sub/n.md").write_text("---\ntype: Note\n---\nx\n")
assert not any(f["file"].startswith("sub/") for f in k.lint(limit=0)["findings"])
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
assert "next" not in k.create("hintless", type="Note")  # rk is not a git work tree
(rk / "hintless.md").unlink()
gr2 = Path(tempfile.mkdtemp()).resolve()
subprocess.run(["git", "init", "-q", str(gr2)], check=True)
k.KB_ROOT = gr2
assert "next" in init(apply=True)  # a git work tree: there is a diff to review
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
assert k.offered() == {"passages", "reindex", "seal"}
# format: adr: every markdown file but README.md and index.md is a decision record, whatever its name or folder.
(ar / "notes").mkdir(exist_ok=True)
(ar / "notes/queue-choice.md").write_text("# Queue choice\n\n* Status: accepted\n\nThe okapi service needs a queue.\n")
(ar / "notes/README.md").write_text("# Notes\n\nThe okapi readme.\n")
k.OPTS["format"] = "markdown"
assert {h["file"]: h["type"] for h in k.passages("okapi")["hits"]} == {"notes/queue-choice.md": None, "notes/README.md": None}
k.OPTS["format"] = "adr"
A = {h["file"]: h for h in k.passages("okapi")["hits"]}
assert A["notes/queue-choice.md"]["type"] == "adr" and A["notes/queue-choice.md"]["status"] == "accepted" and A["notes/README.md"]["type"] is None, A
assert k.offered() == {"passages", "reindex", "seal"} and k.detect_holds(ar) == "adr"
k.OPTS["format"] = "markdown"
(ar / "notes/queue-choice.md").unlink()
(ar / "notes/README.md").unlink()
# seal, in markdown mode: the ledger binds a review to exact bytes; `check` finds what lacks one; a decision is the status.
k.OPTS["seal"] = {"require": ["docs/adr/*.md"], "exempt_status": ["proposed"]}
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
led = (ar / "verifications.yaml").read_text()
assert led.startswith("# verifications.yaml") and "sha256:" in led and "by: human:tester" in led and "decision: accepted" in led
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
assert k.ALIASES == {"verify": "seal", "ratify": "seal"} and k.verify is k.seal
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
    import rdflib
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
    assert [x["heading"] for x in k.passages("animal")["hits"]][0].endswith("Animal")  # narrower links back to broader
    assert k.passages("turtle")["gap"] and k.offered() == {"passages", "reindex", "seal"}
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
_rm = (HERE / "README.md").read_text()
_close = lambda doc, real: abs(doc - real) <= real * 0.1
assert f"All {len(_tl)} tools" in _rm and _close(int(re.search(r"about ([\d,]+) tokens of schema", _rm).group(1).replace(",", "")), _cost(_tl)), _cost(_tl)
for _role, _names in k.ROLES.items():
    _m = re.search(rf"\| `{_role}` \|.*\| (\d+), ~([\d,]+) tokens \|", _rm)
    assert int(_m.group(1)) == len([n for n in _names if n in _tl]) and _close(int(_m.group(2).replace(",", "")), _cost(_names)), (_role, _cost(_names))

print("ok")
