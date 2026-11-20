# Serve

<!-- seal-banner: Written with Claude Sonnet 5.5. The commands were run against a throwaway collection and the pages were checked in a browser; a person has not reviewed it yet. -->

`serve` is Bowerbird in a browser, for a person. It browses a collection, searches it, edits it and seals it, with no AI
involved: it makes no model calls, and nothing it writes is stamped as machine-written. It runs on your machine, on
`127.0.0.1`, and rereads the files on every request, so a change on disk shows when you refresh.

## Start it

It needs one extra package (`markdown`):

```sh
pip install 'bowerbird-mcp[serve]'
# or, with no install:
uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp serve start
```

Run it from inside a collection (the folder holding `bower.yaml`, or below it):

```sh
bowerbird-mcp serve start       # in the background, at http://127.0.0.1:26937/
bowerbird-mcp serve start -f    # in the foreground; ctrl-c stops it
bowerbird-mcp serve start 8080  # another port
bowerbird-mcp serve             # a bare `serve` prints the help: every verb and option, `--config` included
bowerbird-mcp serve status      # information only (exit 0 if running, 1 if not)
bowerbird-mcp serve stop        # end it; nothing running is not an error
bowerbird-mcp serve restart     # stop what is found, then start
bowerbird-mcp --config ~/notes serve start   # another collection, from anywhere: a bower.yaml or its folder (a relative path, ~ or
                                             # a full path). --config goes BEFORE `serve`; without it, run inside the collection
```

Code highlighting is optional: add the `syntax` extra (`pip install 'bowerbird-mcp[serve,syntax]'`) and `serve` colours
code files by their file name, in a light and a dark set that follow the theme. Without it they show as plain numbered text.

`status` and `stop` take the port if it is not 26937. The port (26937) spells BOWER on a phone keypad.

**A different repository.** Run it from there, or name its config from anywhere:
`bowerbird-mcp --config /path/to/repo/bower.yaml serve start`. With no install, use an absolute path and the `serve` extra:

```sh
uvx --from 'bowerbird-mcp[serve]' bowerbird-mcp --config /path/to/repo/bower.yaml serve start
```

To serve several at once, give each its own port (`serve start 8081`) and use the same port with `status` and `stop`.

**Already running.** One server holds a port. If one is up, `serve start` prints its status and starts nothing, so
`--config` is not read and you keep seeing the old collection. Run `serve stop` first, or `serve restart`, or pick
another port.

**Stopping.** `serve stop`, or the **⏻** button at the right of the top bar. If you lose your shell, the button ends the
server, so you never have to hunt for the process.

**Restarting.** Refresh the page to see changed files. Run `serve restart` after you change
`bower.yaml` or update Bowerbird, because both are read once at start.

## What you see

- **Left:** the folder tree of the whole collection, with a dot on each page for its seal state (green sealed, amber
  unsealed, red broken by an edit, grey derived from the code and so never sealed). Every folder ends in **+ New file**. Under the root are **Lint all** and **Tags**.
- **Middle:** the page, with a badge saying who sealed it and when, or that it is unsealed or edited since review.
- **Right:** a pencil (edit) and a gear (Move, Delete, Seal), then the page's outline, the pages that link to it and the
  pages it links to.
- **Top:** back and forward, a path, the search box with its type menu, a theme button (system, light, dark) and **⏻**.

**Seal-only collections.** A file that `seal.exempt` does not leave out (code, YAML, config) is a page here: read-only, as numbered
text, with a badge and the same Seal button. It has no editor, no tags and no outline. A file that is not UTF-8 text, or is
over 512 KB, is not listed or shown; the command line still seals it. With no root `index.md`, `/` shows the empty shell
(tree and search) rather than a directory listing.

Keys: `/` search, `n` and `p` next and previous unsealed page, `j` and `k` next and previous page, `t` theme, `[` and `]`
history.

## Search

The menu beside the search box chooses what kind of search to run, and remembers your choice.

| Type | What it searches | Notes |
| --- | --- | --- |
| Passages | Ranked sections of pages, by keyword | The same `passages` an agent gets. Each hit shows its file and line, its trust tier and whether it is stale. |
| Concepts | Whole pages | The same as the `search` tool: a title match counts for more than a body match. |
| Meaning | Passages, matched by meaning as well as keyword | Offered only when `bower.yaml` sets `semantic: true` (it needs the `semantic` extra, `bowerbird-mcp[semantic]`). |
| Tags | Pages with a tag containing your text | Click a tag on the Tags page to jump here. |

Press **Enter** for a full results page, with the other types a click away.

## Change things

Every change goes through the same tools the command line runs. Where a tool can preview, you see its diff first and
nothing is written until you confirm.

- **Edit** (the pencil). The page's own text in a box, with **Save**, **Lint** and **Cancel**. Lint checks the text as you
  have typed it, without saving. Save refuses to overwrite a page that changed on disk while you were editing, so you
  never silently lose someone's work. Only `.md` files inside the collection can be edited here.
- **New file** (the link at the foot of each folder). The folder is fixed; type a name in the heading (`.md` is added),
  write the page, and Save. A name ending in `/` makes a folder instead. Git keeps a folder once it holds a file.
- **Move** (the gear). Moves or renames a page and rewrites every link to it, with a diff to confirm.
- **Delete** (the gear). Removes the file and its seal entry, and refuses while another page links to it. Git is your
  undo. For a reversible removal, use `archive` (the refusal page links to it).
- **Tags.** A tag is a word in a page's frontmatter: `tags: [deploy, runbook]`. Any page with frontmatter has a tags
  field under it (comma separated). The **Tags** page lists every tag in use, and renames, merges or removes one across
  all pages, with a diff first. A tag renamed to an existing tag merges them.
- **Lint all** lists every finding in the collection, with what to do about each, and previews `fix` for the ones it can
  clear.

## Seal from the browser

**Seal** (the gear) opens a dialog that shows what the MCP prompt shows: the file, its title, word count and
full sha256, under the heading "Confirm seal: <file>". You tick that you reviewed it, type your id, and Bowerbird records `human:<your id>` for
exactly that text. A draft concept can be promoted to stable in the same step, and a decision record can be marked accepted
or rejected. If the page changed while the dialog was open, nothing is written and you review it again.

The server never seals by itself. Editing a sealed page afterwards breaks its seal, and the badge says so until you
review it again. See [Sealing](sealing.md) for what a seal means.

## Safety

`serve` listens on `127.0.0.1` only, and refuses requests whose `Host` is not that address (a web page on another site
cannot reach it through your browser). Every change needs a token that is made fresh each time the server starts and
carries only in pages `serve` sends you. Paths are held inside the collection. Any path with a part that starts with a dot (`.env`, `.git/`,
`.waxseals.yaml`, `sub/.hidden`) is a 404, and so is any path through a symbolic link; listings leave both out.
Hidden files stay sealable from the command line.

It trusts the person at the machine, as the command line's `--attest` does: a program running as you could submit the
seal form too. A hardware key (FIDO2) is the planned way to close that. Do not put `serve` behind a public proxy: it has
no logins.

## If something goes wrong

- **`serve needs the markdown package`.** Install the extra: `pip install 'bowerbird-mcp[serve]'`.
- **`port 26937: Address already in use`.** It is already running (`serve status`), or something else has the port. Use
  `serve stop`, or pick a port: `serve start 8080`.
- **Meaning is not in the search menu.** `semantic` is off in `bower.yaml`. Turn it on, then restart `serve`.
- **A page you edited is not what you expected.** Check `git diff`. Edits are plain file writes, and Git has the history.
- **Not in the tools here.** `provenance`, `create` and the rest of the tools are the command line's:
  `bowerbird-mcp help`.
