# Knowledge Base Ingest

A Claude Code skill that turns a **blog post, engineering write-up, essay,
newsletter, PDF report, whitepaper, or documentation page** into granular,
individually-retrievable rows in a Notion "🧠 AI Knowledge Base" database — each
row a self-contained knowledge unit carrying a deep link back to the exact
paragraph (or PDF page) the idea came from.

It is the article/PDF companion to a YouTube-ingest skill of the same design: read
the source for its *argument* first, distil one idea per row, reconcile every
candidate against what the database already holds (skip what is covered, enhance
what is partial), and write using the database's own controlled vocabulary. The
structure follows Google's Open Knowledge Format.

## What's in here

```
skills/blogpost-knowledge-ingest/
  SKILL.md                 the procedure Claude follows
  references/kb-schema.md  exact Notion property names, option values, call shapes
  references/extraction.md worked examples of good rows vs the rows they were nearly
  scripts/fetch_article.py zero-dependency HTML fetcher + PDF extractor + deep-linker
  evals/evals.json         trigger/behaviour evals
requirements.txt           the one Python dep the PDF path needs (pypdf)
install.sh                 copies the skill into ~/.claude/skills and installs deps
SETUP.md                   step-by-step setup, written for Claude Code to execute
```

## Install (point Claude Code here)

On the new machine or account, in an interactive Claude Code session:

```bash
git clone https://github.com/dusankolenovic/knowledge-base-ingest.git
cd knowledge-base-ingest
./install.sh
```

Then follow **[SETUP.md](SETUP.md)** — it walks through the two things the installer
can't do for you: authorizing the Notion connector (`/mcp`) and confirming the
knowledge-base database is shared with it. Or simply tell Claude Code:

> Set yourself up from this repo by following SETUP.md.

## Requirements

- **Claude Code** with skills enabled (skills live in `~/.claude/skills/`).
- **Python 3.8+**. HTML ingestion is standard-library only. PDF ingestion needs
  `pypdf` (installed by `install.sh`); `pymupdf` and the `pdftotext` binary are
  optional and auto-detected if present.
- **An authorized Notion connector** on the account, **with access to the target
  "🧠 AI Knowledge Base" database.** The database's ID is referenced inside
  `references/kb-schema.md`; this package assumes the account can already reach that
  database. (If you are pointing it at a *different* database, you would recreate the
  same nine-property schema and update the ID in `SKILL.md` and `kb-schema.md` — but
  that is out of scope for the standard install.)

## How the PDF path works (the one non-obvious part)

A YouTube transcript hands you `?t=742` for free; prose and PDFs do not. The fetch
script manufactures the equivalent:

- **HTML** → W3C text-fragment deep links (`#:~:text=…`) that scroll to and highlight
  the sentence, with a paragraph ordinal as a durable fallback.
- **PDF** → `#page=N` deep links (honoured by every major browser and Preview).

For PDFs it runs *every* extractor available (`pypdf`, `pymupdf`, `pdftotext`) and
picks the cleanest output **by score**, not by order — because OCR'd PDFs often carry
a doubled text layer that some extractors emit verbatim, which would silently corrupt
every quote. OCR'd text is flagged so quotes get a `Verbatim (OCR, p.N)` marker.
Scanned PDFs with no text layer fall back to reading the pages visually.

## License

MIT — see [LICENSE](LICENSE).
