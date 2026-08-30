# SETUP — for Claude Code

You (Claude Code) have been directed at this repository to install and verify the
`blogpost-knowledge-ingest` skill on a fresh machine or account. Follow these steps
in order. Do not skip the verification step — a skill that is installed but cannot
reach its Notion database will fail silently at the moment it matters.

This repo assumes the account you are running as **already has access, through the
Notion connector, to the "🧠 AI Knowledge Base" database** the skill writes into.
If it does not, stop and tell the human — the skill's target database ID is baked
into `skills/blogpost-knowledge-ingest/references/kb-schema.md`, and without access
to that database there is nothing to write to.

## Step 1 — Install the skill files

Run the bundled installer from the repo root:

```bash
./install.sh
```

It copies every directory under `skills/` into `~/.claude/skills/` (overwriting any
same-named copy), installs `pypdf`, and runs `fetch_article.py --help` as a smoke
test. If you cannot run the script, do the equivalent by hand: copy
`skills/blogpost-knowledge-ingest/` into `~/.claude/skills/`.

## Step 2 — Install the PDF dependency

HTML ingestion needs only the Python standard library. PDF ingestion needs at least
one text extractor; `install.sh` already tried `pip3 install -r requirements.txt`
(which installs `pypdf`). Confirm it took:

```bash
python3 -c "import pypdf; print('pypdf', pypdf.__version__)"
```

`pymupdf` and the `pdftotext` binary are optional — the script auto-detects and
scores whichever extractors are present, so `pypdf` alone reproduces every test in
this repo. See `requirements.txt` for the optional extras.

## Step 3 — Authorize the Notion connector

The skill uses the Notion MCP tools (`notion-fetch`, `notion-query-data-sources`,
`notion-search`, `notion-create-pages`, `notion-update-page`). These require an
authorized Notion connector on this account.

- In an interactive Claude Code terminal, run `/mcp` and complete the Notion
  authorization flow. (This cannot be done from a non-interactive session.)
- Then confirm the connector can actually see the target database — the surest
  check is to fetch its schema:

  > Fetch `collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3` and confirm the title
  > is "🧠 AI Knowledge Base".

  If that fetch fails, the database is not shared with this connector. The human
  needs to share it (Notion → the database → Connections → add the connector), or
  confirm this account is in the right workspace. Do not proceed until it resolves.

## Step 4 — Make the skill visible and smoke-test

Restart Claude Code (or start a new session) so it re-scans `~/.claude/skills/` and
picks up the new skill. Confirm it is listed, then run a dry, no-write smoke test of
the fetcher on a known-good article and a PDF:

```bash
# HTML — should print a title, word count, block count
python3 ~/.claude/skills/blogpost-knowledge-ingest/scripts/fetch_article.py \
  "https://www.anthropic.com/engineering/building-effective-agents" --md /tmp/smoke_html.md

# PDF — should report pages, the chosen extractor, and (for this file) an OCR warning
python3 ~/.claude/skills/blogpost-knowledge-ingest/scripts/fetch_article.py \
  "https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf" --md /tmp/smoke_pdf.md
```

Both should exit 0 and write a readable markdown file. The fetcher does not touch
Notion, so this is safe to run repeatedly.

Only after step 3 succeeds is a real ingest possible. To run one, invoke the skill
the way the human normally would — e.g. paste an article or PDF URL and ask to add
it to the knowledge base. The skill itself carries the full procedure (fetch → read
for the argument → distil → reconcile against existing rows → write in batches →
wire the graph). Do not front-run it; let the skill drive.

## What "exactly the same as we ran it" means

The skill is self-contained and deterministic in its procedure. Given the same
Notion database and an authorized connector, a new account runs it identically to
the reference session: same fetch script, same extractor-scoring logic, same
schema vocabulary, same reconciliation and batching discipline. The only inputs
that change the output are (a) which source URL you feed it and (b) what already
exists in the database at reconciliation time — both by design.
