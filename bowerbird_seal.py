"""Seal extensions (`seal: {extensions: true}` in bower.yaml; the `seal-extensions` extra): several people seal the same version of
a file, each with an optional comment, and `quorum` says how many different people a version needs.

Plain functions over ledger entries. A ledger line for a file with several seals keeps them in one place:

    - {file: a.md, sha256: ..., seals: [{by: 'human:ann', at: ..., bowerbird: 2.2.0, comment: "ok"}, {by: 'human:bo', at: ...}]}
"""


def expand(line: dict) -> list:
    """The seals of a ledger line as flat entries: a `seals` list is several (each takes the line's file and sha256), else one."""
    if isinstance(line.get("seals"), list):
        return [{**s, "file": line["file"], "sha256": line.get("sha256")} for s in line["seals"] if isinstance(s, dict) and s.get("by")]
    return [line]


def collapse(entries: list) -> dict:
    """One ledger line for a file's seals, which all bind the same bytes."""
    first = entries[0]
    keep = ("by", "at", "bowerbird", "comment", "decision")
    return {"file": first["file"], "sha256": first.get("sha256"), "seals": [{k: e[k] for k in keep if e.get(k) is not None} for e in entries]}


def merge(existing: list, new: dict) -> list:
    """A file's seals after `new`: other people's seals of the same bytes stay, the same person's earlier one is replaced, and
    a seal of different bytes is dropped (the file changed; git has it)."""
    return [e for e in existing if e.get("sha256") == new.get("sha256") and e.get("by") != new["by"]] + [new]


def signers(valid: list) -> set:
    """The different people (human:<id>) among a file's seals that still hold. A machine check is not a signer."""
    return {str(e["by"]) for e in valid if str(e.get("by", "")).startswith("human:")}
