---
name: blogpost-knowledge-ingest
description: >-
  Turn a blog post, engineering write-up, essay, newsletter issue, PDF report,
  whitepaper, or documentation page into granular, individually-retrievable rows in the "🧠 AI Knowledge Base"
  Notion database. Fetches and de-chromes the article with a bundled zero-dependency
  script, reads it for its argument, distills self-contained knowledge units that each
  carry a deep link back to the exact paragraph the idea was written in, checks every
  candidate against the rows already in the database (skip what is already covered,
  enhance what is only partly covered), and writes them using the database's own
  Type/Theme/Domain/Lens vocabulary and body conventions, structured along Google's
  Open Knowledge Format. Use this whenever an article URL appears together with any
  intent to keep what is in it — "add this to the knowledge base", "ingest this post",
  "capture this article", "file this write-up", "save what's in here", "put this in
  Notion" — and also when asked to pull the frameworks, lessons, patterns, or
  takeaways out of a written piece about AI, agents, product, data, evals, prompting,
  engineering practice, or ways of working, because those belong in the knowledge base
  rather than in a chat summary that disappears. Not for articles the user only wants
  read, summarized once, fact-checked, or quoted in passing with no intent to store.
---

# Blog post → AI Knowledge Base

You are extending a hand-curated knowledge base of ~430 rows that its owner queries
during real AI work. The measure of success is not how much you extracted. It is
whether, six months from now, a question asked in the middle of a client engagement
surfaces exactly the right row — and whether that row can be traced back to the
paragraph it came from.

That standard rules out two failure modes at once. A post crushed into four summary
rows is unretrievable because nothing is specific enough to match a real question. A
post sliced along its own headings is unretrievable because the rows are a table of
contents, not ideas. Aim between them, and let the post's actual idea density decide
the count — never a quota.

## What is different about prose, and why it changes the work

The YouTube version of this skill fights a transcript: 8,000 spoken words of which
maybe 1,500 carry ideas, with no structure and no punctuation you can trust. Prose is
the opposite problem, and it is the more dangerous one.

**A blog post arrives pre-chunked, and the chunking is not yours.** The author already
wrote headings, already numbered their three principles, already bolded the takeaway.
Following that structure feels like extraction and is not — it produces a set of rows
that reproduce the article's outline, answer no question a person would type, and are
unretrievable for exactly the reason a transcript-sliced video is. **An author's
heading is a claim about how to read the post, not a claim about the world.** Your
rows are units of knowledge; their headings are units of navigation. When those
coincide it should be because you checked, not because you inherited.

Three more consequences worth holding while you read:

- **There are no asides.** In a talk, the unrehearsed aside is where the speaker's real
  experience leaks out, and it is the highest-value row. Written prose is deliberate,
  so that value hides elsewhere: in **parentheticals, footnotes, the caveat paragraph
  near the end, the hedge a reviewer forced in, comments inside code blocks, and the
  outbound links**. A sentence starting "in practice", "the exception is", or "we tried
  X first" is doing the same job the spoken aside did.
- **The words are exact, and they are someone's work.** Auto-captions were approximate,
  which licensed paraphrase. Here a quote must be reproduced faithfully — and kept
  short. See "Quoting" below; it is a harder constraint than the video version's.
- **The source can change under you.** A video is immutable. A post gets silently
  edited, and the URL you cited may serve different text next year. Record the
  retrieval date, and prefer text-fragment links that break loudly over page links
  that rot quietly.

## The three ground rules

**One idea, one row, one question it answers.** A candidate earns a row only if you
can state a question a working practitioner would actually type, which this row
answers better than any sibling and better than anything already in the database. If
two candidates answer the same question, they are one row.

**Every row stands alone.** It must make sense to someone who never read the post. If
the body only parses with the article open beside it, it is not a knowledge unit — it
is a highlight.

**Every claim is traceable.** Each row body carries a deep link to the paragraph the
idea was written in. This is the whole point: the owner must be able to check you.

## Step 0 — Confirm the target

Fetch the database schema before writing anything, so you use current property names
and current option values rather than remembered ones:

```
notion-fetch  id="collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
```

If that ID no longer resolves, find it with `notion-search` for "AI Knowledge Base"
and take the `collection://` URL from the `<data-source>` tag. Read
`references/kb-schema.md` for the exact vocabularies, body templates, and the Notion
call shapes — do not improvise property values, and never invent a new `Theme`
option (see "Vocabulary is closed" in that file).

Then check whether this article is already in the database. **This is harder than the
video case and needs two probes**, because a post has no unique ID the way a video
does: the same piece routinely lives at a personal domain, a Medium mirror, a
newsletter archive, and an aggregator, and the URL you were handed may not be the one
that was ingested.

```sql
-- 1. URL probe: match on the path slug, not the full URL, to catch mirrors
SELECT "Title", "Type", "Source" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Source" LIKE '%<distinctive-path-slug>%'
```

Then a semantic probe with `notion-search` for the post's title and its central claim,
scoped to this data source. A mirror under a different domain will not match the SQL
and will match this. Rows coming back means it was ingested before — stop and say so,
naming the URL already recorded. Offer to top up instead: extract as normal, then
reconcile against the existing subtree and add only what is new.

## Step 1 — Fetch the source

```bash
SLUG=$(python3 -c "import sys,re,urllib.parse as u; p=u.urlsplit(sys.argv[1]).path.strip('/'); print(re.sub(r'[^a-z0-9]+','-',p.split('/')[-1].lower())[:40] or 'article')" "<url-or-path>")
python3 scripts/fetch_article.py "<url-or-path>" --json "article-$SLUG.json" --md "article-$SLUG.md"
```

Stdlib only for HTML; PDFs use whichever of `pypdf` / `pymupdf` / `pdftotext` is
already installed, auto-detected. Accepts a URL **or a local file path**. It sniffs
the format from the magic bytes, not the extension, and dispatches. Read the `.md`.

### HTML sources

Follows redirects, resolves the canonical URL and strips tracking parameters, pulls
title/author/dates from `<meta>` and JSON-LD, scores the page's containers to find the
article body and drop nav/share/related furniture, and converts what survives to
markdown as numbered blocks.

### PDF sources

Reports, whitepapers, and conference PDFs are a large share of what is worth ingesting,
and they behave differently enough to matter:

- **Deep links are `url#page=N`.** Chrome, Safari, Firefox, and Preview all honour it.
  There is no text-fragment tier — the page number *is* the citation, so it never
  silently rots, but it is also coarser than a paragraph anchor. Cite as `p.20`.
- **The extractor is chosen by output quality, not availability.** The script runs every
  extractor it can and scores each on `dupe_rate` — the fraction of adjacent identical
  words. OCR'd PDFs often carry a doubled text layer that some extractors emit verbatim;
  on a real Anthropic report `pdftotext` scored 0.332 while `pypdf` scored 0.001 on the
  same file. Taking the first tool that returns something would have poisoned every
  quote in the ingest. Check the reported extractor and dupe rate in `--debug`.
- **OCR text is approximate — this is the auto-caption rule again.** When the producer
  is a capture/OCR pipeline the script sets `text_is_ocr` and prints a banner. Treat the
  text as evidence of what was written, not as a printed quote: silently fix obvious
  recognition artifacts (`T op tips` → `Top tips`, mangled product names), and where a
  passage is too garbled to trust, paraphrase with the page cite rather than quoting.
  Mark bodies `**Verbatim (OCR, p.20):**` so a future reader knows before they requote.
- **No text layer at all** (scanned without OCR, image-only decks): the script exits 2,
  caches the file, and tells you to read the pages **visually with the Read tool**
  (`pages: "1-20"`, max 20 per call), citing the same `#page=N` links and marking bodies
  `**Verbatim (page image, p.N):**`. Steps 2–6 are unchanged. Do not guess contents.
- **Bookmarks are often fake structure.** Export pipelines emit one bookmark per page
  named `Report-name-01`, `-02`. The script detects the sequence pattern and discards
  them as headings — but recovers the document title from their common stem, which is
  frequently the only place a title exists when `/Info` is empty.
- **A PDF's own headings are still the heading trap**, and worse: a report with ten
  templated sections invites ten rows named after the sections. See Step 3.

Three checks before you read further:

- **Word count.** Under ~6,000 words, work the whole piece at once. Above that (long
  essays, documentation pages, most PDF reports), work in spans of roughly 2,000 words
  or by top-level section, completing Steps 2–5 per span so the report arrives steadily.
- **The warnings.** If the script flags `paywall_suspected`, `js_shell_suspected`, or a
  surviving high dupe rate, the body you have may be a teaser, an empty shell, or
  doubled. Do not extract from it. For HTML, the browser tools (`preview_start` +
  `get_page_text`) render JavaScript and use the user's own session. For PDFs, fall back
  to reading pages visually.
- **`outbound_links`** (HTML only). In a well-argued post the links are the citations:
  where a claim is borrowed, where the evidence lives, whom the author is arguing
  against. A link is often the tell that a paragraph is summarising someone else's idea,
  which changes whether the row belongs to this source at all. PDFs give you no such
  signal — for a PDF, watch instead for "reported by", "according to", and named
  third-party benchmarks.

If the fetch fails, the script prints what it tried and what to do. Do not guess at the
source's contents from its title, its URL slug, its filename, or its meta description.

## Step 2 — Read for the argument, before extracting anything

Read the article end to end and write down, for yourself, the spine: what is this post
arguing, through what moves, in what order? Three to ten sentences.

Do this first because it changes what you extract, and because it is your defence
against the heading trap. A post's spine is frequently *not* its outline: the setup
section carries no ideas, two headings develop one idea, and the real claim arrives in
a paragraph under a heading about something else. If your spine can be written by
transcribing the H2s, you have not found the argument yet.

While reading, note where the register changes: a claim repeated in different words, a
number, a worked example, a thing warned against, a concession, a place where the
author disagrees with a named position. Note the parentheticals and the footnotes
specifically. These are where the units are.

## Step 3 — Extract candidates

Walk the article and list candidates. For each: a working title, the block ordinal and
its deep link, the one-line claim, and which `Type` it looks like.

What earns a row:

- a named structure you reason **with** — parts, dimensions, stages → `Framework`
- an ordered procedure executed 1→N → `Playbook`
- one self-contained claim plus the reason it holds → `Concept`
- a repeatable how-to → `Skill`
- a named product, with what and when and why in the body → `Tool`
- a concrete application with an actor and an outcome → `Use case`
- a fill-in artifact → `Template`
- **a counter-intuitive result, a specific number, a named failure mode, or a strong
  disagreement** — the highest-value rows, and in prose they hide in the caveat
  paragraph and the parenthetical rather than in the bolded takeaway

**A templated multi-section report is a corpus, not an argument.** Vendor reports and
"how N teams do X" PDFs repeat one template per section — team blurb, use cases, impact,
tips. The units are almost never the sections. They are the **patterns that recur across
sections**, which the document usually never names, plus the handful of section-specific
findings distinctive enough to stand alone. One row per section reproduces the table of
contents; the cross-cutting pattern is the row, and the per-section instances become the
worked examples inside its body. If a claim appears in six sections, that recurrence is
itself the finding.

**Prose-specific: code blocks are first-class.** A talk shows code on a slide you
cannot read; a post gives you the runnable text. A code block that is a reusable
artifact — a prompt, a config, a schema, a scaffold — is a `Template` row and should
carry the code itself in the body, not a description of it. A code block that only
illustrates a point belongs inside that point's row, or nowhere.

What does not earn a row: the author's bio, the "in this post we will" preamble,
section transitions, the recap section (which by construction adds nothing), the
call-to-action, generic AI commonplaces this post adds nothing to, and anything whose
only claim to interest is that it had its own heading. Those belong in the anchor's
spine, if anywhere.

As calibration only — see the table in `references/extraction.md`. Prose runs denser
per word than speech but thinner than its own outline suggests: a 2,000-word
engineering post typically yields 6–12 units, not the 9 its headings imply and not the
30 its paragraphs imply. **If your candidate list is one-to-one with the article's
headings, you are outlining, not distilling. Start over.**

When a candidate could be two types, `references/kb-schema.md` carries the database's
own precedence rule. Apply it rather than deciding fresh each time; consistency across
430 rows is worth more than a locally better call.

## Step 4 — Reconcile against what is already there

This is the step that keeps the database worth querying. Skipping it produces
near-duplicate rows that split the owner's attention between two half-answers.

Load the title index first — but expect it to arrive in pages, not one shot. At the
current row count the SQL response comes back with `has_more: true`, so pull it in
`LIMIT 100 ORDER BY createdTime` slices and concatenate; using the natural row order
is more stable than paging with `OFFSET`.

```sql
SELECT "Title", "Type", "Theme" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
ORDER BY createdTime LIMIT 100;
-- then LIMIT 100 with WHERE createdTime > '<last row's createdTime>', and repeat
```

The index catches obvious name matches, but LIKE-sweeps and paged reads both miss
paraphrases — "context bus" will not match a search for "shared state". So treat the
index as the sieve and **`notion-search` (semantic, scoped with `data_source_url` to
this collection URL) as the primary check** for every candidate whose topic overlaps
what already exists. Read the actual `Summary` on close matches before deciding.

Give every candidate one of three verdicts:

- **NEW** — nothing in the database answers this question. Create the row.
- **ENHANCE** — an existing row makes the same point but this post adds something real:
  a sharper formulation, a number, a named failure mode, working code, a second
  independent source. Append to that row; do not create a near-duplicate. Keep the
  existing row's structure and add your material with its own attribution, so the row
  now cites two sources rather than looking like it always said this.
- **SKIP** — already fully covered. Record it in the report and in the anchor's segment
  map, so the owner can see the article corroborated existing thinking. That is a
  finding, not a non-event.

Two calls that are specifically harder for written sources:

**"Same topic" is not "same claim."** An existing row on evaluation and a new row on a
specific judge-rubric failure mode are different questions and should both exist,
cross-linked. Reserve SKIP for genuine answer overlap.

**Written ideas travel.** Blog posts cite each other, and a well-linked post frequently
restates a framework the database already has from its original source. If the post is
*relaying* an idea rather than advancing it, the verdict is SKIP or ENHANCE on the
existing row — not a second row attributing someone else's framework to this author.
The `outbound_links` from Step 1 are how you catch this: a claim with a citation
hanging off it usually is not this post's contribution.

## Step 5 — Write, reporting as you go

Create the anchor row first — you need its URL before children can point at it.
Sibling cross-links inside the anchor's spine and the children's bodies also need URLs
that do not exist yet, so the writing itself is two passes:

1. Write the anchor with **placeholder tokens** ({{NEW-1}}, {{NEW-2}}, …) in every
   `<mention-page url="…"/>` that points at a sibling this run will create. Existing
   database rows are linked with their real URLs from the start.
2. Write the children in batches, setting `Part of` to the real anchor URL. Their
   bodies use the same placeholder tokens for links to yet-unwritten siblings.
3. In Step 6, resolve the tokens: replace {{NEW-n}} with the actual page URLs and
   re-apply via `notion-update-page` (`update_content` with a small `content_updates`
   diff, not a full replace).

Keep a token → title table in memory so the swap at the end is mechanical.

The anchor is one row representing the article: `Type` usually `Framework` (or
`Playbook` if the post is fundamentally an ordered procedure), title ending in
`(anchor)`, following the database's existing naming. Its body carries the spine from
Step 2, a segment map of every unit with its block ordinal, and a source block that
records author, publication, retrieval date, and — where it matters — **whose interest
the piece serves**. Full template in `references/kb-schema.md`.

Then write the children in batches of roughly eight to twelve, setting `Part of` to
the anchor. After **each batch**, print a report — the owner asked to see what you got
as you go, not at the end:

```
### Batch 2 of 3 — written
| #  | Row                                              | Type      | @    | Verdict |
|----|--------------------------------------------------|-----------|------|---------|
| 9  | Orchestrator-worker — when the subtasks aren't … | Framework | P41  | NEW     |
| 10 | Evaluator-optimizer loops need a stopping rule   | Concept   | P53  | ENHANCE → [existing row title] |
Running total: 10 new · 2 enhanced · 3 skipped
```

Batching matters for a reason beyond visibility: it gives the owner a place to
interrupt you if the granularity is off, before forty rows exist. If a batch draws a
correction, apply it to the remaining batches rather than only to the row named.

Before the first batch, say plainly how many rows this will create. Writing is direct
and unblocked — that is the agreed mode — but a one-line heads-up costs nothing and
prevents surprise.

## Step 6 — Wire the graph and close

Relations first: `Part of` and `Contains` may or may not be two halves of one two-way
relation. After writing, fetch the anchor and check whether `Contains` actually
populated. If it did not, set it explicitly. A broken hierarchy is invisible until the
day it matters.

Then cross-link. A row's real retrievability comes from the links inside its body, not
only from the parent relation — the database's existing rows reference their siblings
inline with `<mention-page url="…"/>`, and yours should too, in both directions:
between new siblings where one idea depends on another, and outward to existing rows
this article supports, sharpens, or contradicts. Contradiction is worth linking
explicitly; two rows that disagree are more useful than one row that quietly won.

Close with a final report: total created, enhanced (with which rows), skipped (with
which rows covered them), anything you flagged as not fitting the controlled
vocabulary, and the anchor row's URL.

## When things go wrong

- **Paywall or truncated body.** Report it; do not extract from a teaser. Offer the
  browser tools, the publisher's RSS feed (often full-text), or a pasted copy. Never
  reconstruct the argument from the excerpt plus the title.
- **Client-rendered shell.** The script flags it when a large page yields almost no
  text. Re-fetch with the browser tools rather than fighting the HTML.
- **Extraction picked up furniture** — related-posts blocks, comment threads, a
  newsletter footer appearing as blocks. Re-run with a higher `--min-words`, and ignore
  the tail blocks; do not extract rows from them.
- **The post is part of a series.** Say so before writing, and ask whether to ingest
  the siblings too. A part-3 ingested alone produces rows whose reasoning lives in a
  part-1 the database does not have. If the series is being ingested whole, one pillar
  row over per-post anchors is usually right.
- **PDF has no text layer.** The script exits 2 and caches the file. Read the pages with
  the Read tool (`pages: "1-20"`), cite `#page=N`, mark quotes `**Verbatim (page image,
  p.N)**`. This is a normal path, not a failure — do not fall back to guessing.
- **The surviving extractor still shows a high dupe rate.** The text layer is doubled and
  every quote you take will be wrong. Read the affected pages visually instead.
- **Article is off-topic for this database.** Say so before writing. A recipe does not
  become knowledge because it parsed cleanly.
- **Nothing survives reconciliation.** A legitimate outcome — say the post restates what
  the owner already has, name the rows that cover it, and create nothing. That answer
  is worth more than five redundant rows.
- **A candidate fits no existing `Theme`.** Do not add an option. Tag what does fit,
  flag it in the report, and let the owner decide.
- **Non-English article.** Fetch it, note the language in the anchor, and write the rows
  in English; keep short quotes in the original with a translation alongside.
- **The piece is marketing with engineering inside.** Common on vendor blogs, and not a
  reason to skip — but record the incentive in the anchor's source block and never let
  an unaudited vendor benchmark enter a row as a bare number. Attribute it: "X reports
  Y", not "Y".

## Quoting

Quote the sentence that carries the idea, not the paragraph around it — typically one
to three sentences, reproduced **exactly**, since unlike a caption this is the author's
actual published wording. The rest of the body is your own synthesis. Never paste the
article in bulk, never store its full text as a row, and never let a body run mostly
blockquote: it is someone else's work, and a database of article dumps cannot be
retrieved from anyway. The deep link is what makes bulk quoting unnecessary — the
original is one click away.

Code blocks are the one exception to brevity: a short, self-contained artifact may be
reproduced whole in a `Template` row, because a fragment of a config is useless. Keep
it to the artifact, attribute it, and link to the source.

## References

- `references/kb-schema.md` — exact property names and option values, the `Type`
  precedence rule, body templates per type, the anchor template, Notion tool call
  shapes, and how this maps onto Google's Open Knowledge Format.
- `references/extraction.md` — worked examples of the retrieval test, good rows next
  to the bad rows they were nearly written as, and the prose anti-patterns with their
  tells.
