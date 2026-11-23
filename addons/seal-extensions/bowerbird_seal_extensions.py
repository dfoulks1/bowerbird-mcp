"""bowerbird-mcp[seal-extensions]: the optional parts of sealing (`seal: {extensions: true}` in bower.yaml). Several people seal the same version of
a file, each with an optional comment, and `quorum` says how many different people a version needs.

Plain functions over ledger entries, registered with bowerbird-mcp through the `bowerbird.seal` entry point. A ledger line for a file with several seals
keeps them in one place, and says how many it wants:

    - {file: a.md, sha256: ..., quorum: 3, seals: [{by: 'human:ann', at: ..., bowerbird: 2.3.0, comment: "ok"}, {by: 'human:bo', at: ...}]}
"""
import types


def expand(line: dict) -> list:
    """The seals of a ledger line as flat entries: a `seals` list is several (each takes the line's file and sha256), else one."""
    if isinstance(line.get("seals"), list):
        return [{**s, "file": line["file"], "sha256": line.get("sha256")} for s in line["seals"] if isinstance(s, dict) and s.get("by")]
    return [line]


def collapse(entries: list, quorum: int = 1) -> dict:
    """One ledger line for a file's seals, which all bind the same bytes. A quorum above 1 is kept in the line, so a badge can say "2 of 3" without reading the policy."""
    first = entries[0]
    keep = ("by", "at", "bowerbird", "comment", "decision")
    return {"file": first["file"], "sha256": first.get("sha256"), **({"quorum": quorum} if quorum > 1 else {}),
            "seals": [{k: e[k] for k in keep if e.get(k) is not None} for e in entries]}


def merge(existing: list, new: dict) -> list:
    """A file's seals after `new`: other people's seals of the same bytes stay, the same person's earlier one is replaced, and
    a seal of different bytes is dropped (the file changed; git has it)."""
    return [e for e in existing if e.get("sha256") == new.get("sha256") and e.get("by") != new["by"]] + [new]


def signers(valid: list) -> set:
    """The different people (human:<id>) among a file's seals that still hold. A machine check is not a signer."""
    return {str(e["by"]) for e in valid if str(e.get("by", "")).startswith("human:")}


def register(bb):
    """The entry point: hand bowerbird-mcp these helpers."""
    bb.register_seal_extension(types.SimpleNamespace(expand=expand, collapse=collapse, merge=merge, signers=signers))
