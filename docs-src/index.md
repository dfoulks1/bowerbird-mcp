<div class="hero">
  <img class="logo-light" src="img/logo-v2.svg" alt="Bowerbird: a bower of sticks rising from an open book, with a small bird" width="240" height="175">
  <img class="logo-dark" src="img/logo-dark-v2.svg" alt="Bowerbird: a bower of sticks rising from an open book, with a small bird" width="240" height="175">
  <h1 id="bowerbird-mcp">Bowerbird</h1>
  <p class="lead">Curate a collection of files, and know a human looked at them. Bowerbird keeps notes, decisions, vocabularies or code searchable and in order, for agents and people alike. Guarantee integrity across <a href="formats/">formats</a> with one tool.</p>
  <p>
    <a class="btn btn-brand me-2" href="getting-started/">Get started</a>
    <a class="btn btn-outline-secondary" href="https://github.com/dfoulks1/bowerbird-mcp">View on GitHub</a>
  </p>
</div>

<div class="row g-3 users my-4">
  <div class="col-md-4"><div class="card p-3">
    <h3>An agent, over MCP</h3>
    <p>Every tool, with a diff before each write and a confirmation prompt before anything records a person.</p>
  </div></div>
  <div class="col-md-4"><div class="card p-3">
    <h3>CI</h3>
    <p><code>lint</code> as GitHub annotations or SARIF, a baseline for old findings, <code>since=</code> for pull requests, and <code>seal check=true</code> to fail a commit that has no human review.</p>
  </div></div>
  <div class="col-md-4"><div class="card p-3">
    <h3>A person, at a terminal or in a browser</h3>
    <p>No AI needed: <code>help</code>, ranked <code>search</code>, <code>passages</code> for questions, readable text output, <code>--attest</code> to sign your own reviews, and <a href="serve/"><code>serve</code></a> to browse, edit and seal in a browser.</p>
  </div></div>
</div>

<p class="note">Local files only. No network, except the one-time model download if you turn on semantic search. Never writes to git. One Python file, installed or run with <a href="https://docs.astral.sh/uv/">uv</a>. These pages were written with Claude Opus 5.5 and Claude Sonnet 5.5 and are sealed with Bowerbird.</p>

## Pick the format that fits

A `format:` line in `bower.yaml` says what a folder holds. Each exists for a reason:

- **Markdown**: notes, runbooks, wikis, docs. Nothing to write but Markdown.
- **ADR**: decision records (ADR or MADR), with each record's status.
- **OKF**: knowledge that says where it came from, who checked it and when it expires, with the full toolset.
- **SKOS**: glossaries, vocabularies and thesauri.
- **Seal-only**: code and other files, with nothing searched: just a guaranteed human review of each one.

[Formats](formats.md) shows what each one looks like, side by side.

Use whatever type is right for you: plain Markdown needs no header and no conversion, ADR reads decision records, OKF adds
sources and trust, SKOS holds vocabularies, and seal-only does no searching at all, just a guaranteed human review of each
file you name.

## Quickstart

Nothing to clone. [uv](https://docs.astral.sh/uv/) installs it from PyPI, with its dependencies, on the fly:

```sh
uvx bowerbird-mcp help
```

No uv yet? `curl -LsSf https://astral.sh/uv/install.sh | sh`

Then add it to your MCP client's servers file (`.mcp.json` for Claude Code;
[other clients](guide.md#register-with-an-mcp-client)):

```json
{
  "mcpServers": {
    "bowerbird": {
      "command": "uvx",
      "args": ["bowerbird-mcp"]
    }
  }
}
```

Or work from the terminal, no AI needed. In any folder, with the format that fits what you keep (Markdown here, as an example):

```sh
# make it a collection: settings files only, your files are not touched
# holds= is markdown, adr, okf, skos or seal-only
uvx bowerbird-mcp create holds=markdown about="Team notes." apply=true

# ask a question: the best sections, each with the file and line to cite
uvx bowerbird-mcp passages 'how do we deploy' output=text

# any tool: what it does, its arguments
uvx bowerbird-mcp help passages
```

Next: [getting started](getting-started.md) for a ten-minute walkthrough, [formats](formats.md) for what each kind of
collection looks like, the [guide](guide.md) for settings and workflows, the [tools](tools.md) for every command,
[serve](serve.md) to browse, edit and seal a collection in your browser, and
[OKF](formats/okf.md) for the richest format, with its [specification][okf].

[okf]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/bad9bdbafa82c672b00d437d4f2cc8f17e9e5f58/okf/SPEC.md
