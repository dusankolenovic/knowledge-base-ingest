# Database mechanics — exact values, templates, and call shapes

Contents:
1. Identifiers
2. Has this article already been ingested?
3. Properties and their exact option values
4. Type — definitions and the precedence rule
5. Tagging: Theme, Domain, Lens
6. Writing the Title and the Summary
7. Citing prose: the three link forms
8. Body templates
9. The anchor row template
10. Notion tool call shapes
11. SQL recipes
12. Why the format is what it is — the OKF mapping

---

## 1. Identifiers

| Thing | Value |
|---|---|
| Database | `https://app.notion.com/p/c1848d3749074bc2b6e1480315352bfa` |
| Data source (SQL table name, `notion-search` scope) | `collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3` |
| `data_source_id` for `notion-create-pages` | `d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3` |

Confirm with `notion-fetch` before writing. If the ID has changed, find it via
`notion-search` for "AI Knowledge Base" and read the `collection://` URL out of the
`<data-source url="…">` tag.

**Before composing any body containing `<mention-page …/>`, fetch the Notion markdown
spec** — mention syntax is easy to get subtly wrong, and a malformed mention becomes
plain text instead of a link, silently breaking the graph:

```
notion-fetch  id="notion://docs/enhanced-markdown-spec"
```

## 2. Has this article already been ingested?

Check first — re-ingesting duplicates a whole subtree, which is far more annoying to
unpick than a single duplicate row.

An article has no equivalent of a video ID, so **one probe is not enough**. The same
piece routinely exists at a personal domain, a Medium mirror, a Substack archive, and
a syndicated copy, and only one of those was recorded as `Source`.

```sql
-- Probe 1: the path slug, which usually survives syndication
SELECT "Title", "Type", "Source" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Source" LIKE '%<distinctive-path-slug>%'

-- Probe 2: the domain, to see what else from this author is already here
SELECT "Title", "Source" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Source" LIKE '%<domain>%'
```

Then **Probe 3**, the one that actually catches mirrors: `notion-search` scoped with
`data_source_url` to the collection, querying the article's exact title and then its
central claim. A mirror under a different domain fails both SQL probes and matches this.

If rows come back, stop and tell the owner, naming the `Source` already on file. Offer
to top up instead: extract as normal, then reconcile every candidate against the
existing subtree, adding only what is genuinely new.

## 3. Properties and their exact option values

Nine properties. Names are case- and space-sensitive.

| Property | Kind | Notes |
|---|---|---|
| `Title` | title | Required |
| `Type` | select | Required, exactly one |
| `Theme` | multi-select | Usually 1–2 |
| `Domain` | multi-select | May be empty — empty means "general" |
| `Lens` | multi-select | Usually 1–2 |
| `Summary` | text | Required in practice: all ~430 rows have one |
| `Source` | url | Required in practice: all ~430 rows have one |
| `Part of` | relation (self) | The parent row |
| `Contains` | relation (self) | The child rows |

**Vocabulary is closed.** The database's own field description says to extend the
option list only when nothing fits, and the value of a controlled vocabulary is that
querying by it is reliable. Passing an unrecognised string to a multi-select can
create a new option silently, which erodes exactly that. Use these strings verbatim:

```
Type    (one of):  Concept | Framework | Use case | Skill | Playbook | Tool | Template
Theme   (0..n):    Evals & Observability | Agents & Workflows | Governance | Data
                   Org & Operating model | GTM | Behavioral science | Prompting
Domain  (0..n):    Sales | Marketing | HR | Dev/Engineering | Product | Strategy
                   Design | Finance
Lens    (0..n):    Business | Technology | Adoption
```

Note the ampersands and the exact casing: `Org & Operating model` is not
`Org & Operating Model`. If a candidate genuinely fits no `Theme`, tag what does fit,
leave `Theme` short, and flag it in the report.

## 4. Type — definitions and the precedence rule

- **Concept** — a single self-contained idea, paragraph-sized.
- **Framework** — a named structure for *thinking*: parts, dimensions, or stages you
  reason with.
- **Playbook** — an ordered sequence for *doing*, executed 1→N. The order is the
  content, so preserve it faithfully.
- **Use case** — a concrete application with an actor and an outcome.
- **Skill** — a repeatable how-to.
- **Tool** — a named product. The name goes in the Title; what/when/why in the body.
- **Template** — a fill-in artifact.

When a candidate could be more than one, the database's precedence rule decides:

```
Playbook  >  Framework  >  Use case  >  Skill  >  Concept
```

`Tool` and `Template` sit outside the chain — they are identified by what the thing
*is* (a named product, a fill-in artifact), so if either genuinely applies, it wins.

The point of the rule is consistency across hundreds of rows, not per-row optimality.
Follow it even when your instinct differs, because a future query filtered to
`Playbook` should return every ordered procedure, not the subset where someone
happened to feel procedural.

**A prose-specific note on `Template`.** Written sources produce far more `Template`
rows than video ones, because a post hands you the actual copyable artifact — a prompt,
a schema, a config, a checklist, an eval rubric — where a talk could only show it on a
slide. When a code block or a fenced artifact is self-contained and reusable, it is a
`Template`, and the artifact itself goes in the body. Resist the temptation to file it
as a `Concept` describing the artifact; the copyable text is the value.

## 5. Tagging: Theme, Domain, Lens

**Lens** is the perspective the row informs: `Business` (outcome, value), `Technology`
(data, tooling, architecture), `Adoption` (behaviour, change, mental models). Most
rows carry one or two. Three means the row is probably too broad to retrieve well.

**Domain** is the business function served. Leaving it empty is a real choice meaning
"general" — about 15% of existing rows do. Tag only what clearly applies; a row tagged
with six domains is tagged with none.

**Theme** is the topical cluster. One or two.

## 6. Writing the Title and the Summary

**Title** names the knowledge unit, never the source — and never the author's heading.

- ✅ `Orchestrator-worker — when subtasks can't be known before the task starts`
- ❌ `Great post on agent patterns`
- ❌ `Building Effective Agents: Workflow Patterns` ← that is the article's outline
- ❌ `Part 2: Common patterns`

Most existing titles take the form `Specific noun phrase — what makes it distinct`,
and run around 100 characters. The em-dash half is doing retrieval work: it is where
the distinguishing keywords live. Anchor rows end in `(anchor)`; use `(pillar)` only
for a genuinely top-level subject with its own sub-anchors beneath it — which is the
right shape when ingesting a multi-part series as a whole.

**Summary** is retrieval bait, not an abbreviation of the body. Write it to be matched
by a question that has not been asked yet: lead with the problem the row solves, then
pack in the distinguishing terms — named things, numbers, the specific failure mode.
Two to four sentences; existing rows run roughly 250–600 characters.

A quick test: if you deleted the Title and read only the Summary, could you tell this
row apart from the other 430? If not, it is too generic to be found.

## 7. Citing prose: the three link forms

The fetch script attaches a link to every block and reports which kind it is in
`anchor_kind`. Use the strongest one available, and **always pair it with the block
ordinal** so the citation degrades gracefully.

| `anchor_kind` | Link | Use it as |
|---|---|---|
| `heading-id` | `https://…/post#what-are-agents` | the durable one; prefer it when the unit sits under an anchored heading |
| `text-fragment` | `https://…/post#:~:text=We%27ve%20worked…,complex%20frameworks.` | the default for a paragraph, quote, or list |
| `section-id` / `page` | `https://…/post#section` or bare | fallback for code blocks and tables |
| `pdf-page` | `https://…/report.pdf#page=20` | the only form for PDFs; cite as `p.20` |

Written as `[¶ P41](url)` in a body, or `[¶ p.20](url)` for a PDF. The ordinal is not decoration: text fragments stop
resolving when the author edits the sentence, and `P41` is what still tells a reader
where to look. Do not silently drop it because the link works today.

Text fragments are honoured by Chrome, Edge, and Safari; Firefox needs a flag and will
land on the page instead. That is an acceptable degradation, not a reason to avoid them.

`#page=N` is honoured by every major browser and by Preview, and unlike a text fragment
it cannot break from an edit — but it is coarser. On a dense report page, add the
subhead to the citation (`p.20, "Speed-up with limitations"`) so a reader lands on the
right paragraph, not just the right page.

### Marking approximate text

Three provenance markers, matching how much the wording can be trusted:

| Marker | When |
|---|---|
| `**Verbatim (P41):**` | HTML, or a PDF with a clean publisher text layer |
| `**Verbatim (OCR, p.20):**` | the script set `text_is_ocr` — recognition artifacts are likely |
| `**Verbatim (page image, p.20):**` | no text layer; you read the rendered page yourself |

This costs three words and tells a future reader how much to trust a quote before they
requote it onward. An OCR'd or vision-read quote that hardens into a citation is exactly
the failure the deep link exists to prevent.

## 8. Body templates

Bodies use structural markdown — headings, lists, tables, short quotes — rather than
freeform prose, because a body an agent can skim is a body it can retrieve from.

### Concept, Framework, Playbook, Skill, Use case

```markdown
**Key idea:** <the claim itself, one or two sentences>

**Verbatim (P41):** [¶ read in context](https://example.com/post#:~:text=…)
> "<one to three sentences, reproduced exactly>"

<Two to five sentences of your own synthesis: the mechanism, why it holds, what it
depends on, what it rules out. This is the part that makes the row useful to someone
facing a situation the author never mentioned. Cross-link related rows inline with
<mention-page url="…"/>.>

**Watch out:** <the real limit, caveat, or failure condition — omit this line entirely
if there isn't one, rather than padding it>
```

For a `Playbook`, replace the synthesis paragraph with the ordered steps, numbered, in
the author's sequence. The order is the content.

### Tool

```markdown
## What it is
<what the product is, one short paragraph>

**Verbatim (P41):** [¶ read in context](https://example.com/post#:~:text=…)
> "<short quote>"

## When to use / why (vs alternatives)
<what someone would otherwise do, and what this changes. Name the alternative.>

## Watch out
<limits, costs, single points of failure, what it does not do>
```

### Template

The one body type where reproducing the source at length is correct — a fragment of a
config or a prompt is useless. Keep it to the artifact itself.

```markdown
**What it is for:** <the job this artifact does, one or two sentences>

**Source:** <author / publication>, [¶ P58](https://example.com/post#section-id)

```<lang>
<the artifact, complete and copyable, exactly as published>
```

**How to adapt it:** <which parts are the skeleton and which are the example's
specifics — the difference between a template and a snippet>

**Watch out:** <version pinning, assumed environment, what it silently depends on>
```

### Attributing a relayed claim

When the post is reporting someone else's number or framework rather than its own —
common on vendor blogs and in link-heavy essays — say whose claim it is in the row
itself, and link the original if the post links it:

```markdown
**Key idea:** <claim>. Reported by <post author> citing <original source>; not
independently verified here.
```

A number that enters the database unattributed becomes a fact by attrition. This one
line prevents that.

## 9. The anchor row template

One anchor per article. `Type` is normally `Framework`; use `Playbook` only if the post
is fundamentally one ordered procedure. `Part of` stays empty unless the article belongs
beneath an existing pillar — check the index for one before defaulting to a root, and
create a `(pillar)` when ingesting a series.

```markdown
## The argument
<The spine from Step 2, in the post's own order: what it argues and through which
moves. Link each unit inline with <mention-page url="…"/> at the point it enters the
argument, so this reads as a narrative rather than a list of links.>

## Segment map
| Block | Unit | Where it went |
|-------|------|---------------|
| P12 | Workflows vs agents is an architectural distinction | <mention-page url="…"/> |
| P29 | Prompt chaining — decomposable tasks only | corroborates <mention-page url="…"/> (existing) |
| P41 | Orchestrator-worker | <mention-page url="…"/> |

## About this source
- **Author:** … · **Publication / site:** …
- **Published:** … · **Last modified:** … · **Retrieved:** YYYY-MM-DD
- **Length:** … words · **Article:** https://example.com/post
- **Standing:** independent / vendor engineering blog / vendor marketing / practitioner
  report — and, if it matters, whose interest the piece serves
- **Cites:** <the two or three outbound links that carry the argument's evidence>
```

Two fields here that the video version does not have, both load-bearing:

For a PDF, add `**Text layer:** publisher / OCR (<producer>) / read visually` to the
source block. It does for quote-trust what **Standing** does for incentive: it records,
once, how much the child rows' quotes can be relied on, so nobody re-derives it later.

**Retrieved** is not bookkeeping. Articles get edited in place, and a year from now the
only way to know whether a broken text fragment means "author rewrote it" or "you
mis-transcribed it" is knowing what day you read it.

**Standing** is how a vendor benchmark is prevented from hardening into a fact. A vendor
engineering blog is often the best available source *and* an artifact with an interest;
both are true, and the row should say so once rather than the reader re-deriving it.

The segment map is the durable version of the batch reports: it records SKIP and
ENHANCE decisions too, so months later it is still visible that this article
corroborated existing thinking rather than being half-ignored.

## 10. Notion tool call shapes

### Create rows

```
notion-create-pages
  parent: { "type": "data_source_id",
            "data_source_id": "d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3" }
  pages: [
    { "properties": {
        "Title":   "Orchestrator-worker — when subtasks can't be known in advance",
        "Type":    "Framework",
        "Theme":   ["Agents & Workflows"],
        "Domain":  ["Dev/Engineering"],
        "Lens":    ["Technology"],
        "Summary": "…",
        "Source":  "https://example.com/post",
        "Part of": ["https://app.notion.com/p/<anchor-page-id>"]
      },
      "content": "…markdown body…" }
  ]
```

`Source` is the **canonical, tracking-stripped** article URL on every row from the
article, never the fragment-bearing one. The fetch script resolves `<link rel=canonical>`
and strips `utm_*`/`fbclid`/`ref` for exactly this reason: it keeps
`GROUP BY "Source"` returning one group per article, which is how the database's
provenance queries work today. Deep links live in bodies.

If the canonical URL differs from the URL the owner handed you (a mirror, a syndicated
copy), use the canonical one and note the URL you were given in the anchor's source
block, so the next dedupe probe finds it either way.

The tool accepts up to 100 pages per call, but write in batches of eight to twelve so
the owner sees a report between them and can stop you early.

**Sibling cross-links need placeholder tokens on the first pass.** Anchor bodies
mention children that do not exist yet; child bodies mention siblings that do not
exist yet either. Write both with `{{NEW-n}}` placeholders in every
`<mention-page url="…"/>` pointing at an as-yet-unwritten row, keep a
`token → title` table as you go, and after the last batch replace every token with
the real URL via a small `notion-update-page` diff (see below). Links to *existing*
rows carry their real URLs from the start.

### Enhance an existing row

Append rather than rewrite — the existing text is hand-curated:

```
notion-update-page
  page_id: "<existing-row-id>"
  command: "insert_content"
  position: { "type": "end" }
  content: "\n**Also — <author>, <publication> (P41):** [¶ read in context](https://example.com/post#:~:text=…)\n> \"…\"\n\n<one or two sentences on what this source adds — the sharper formulation, the number, the failure mode, the working code.>"
```

Do not touch the existing row's properties. If the new material genuinely changes what
the row is about, that is a signal it should have been a NEW row instead.

### Backfill cross-links (second pass)

```
notion-update-page
  page_id: "<page-id>"
  command: "update_content"
  content_updates: [
    { "old_str": "<mention-page url=\"{{NEW-3}}\"/>",
      "new_str": "<mention-page url=\"<real-url-3>\"/>", "replace_all_matches": true },
    { "old_str": "<mention-page url=\"{{NEW-4}}\"/>",
      "new_str": "<mention-page url=\"<real-url-4>\"/>", "replace_all_matches": true }
  ]
```

One call per page, all token swaps batched into a single `content_updates` array. Do
not `replace_content` a whole body just to swap two links.

### Verify the hierarchy

`Part of` and `Contains` may or may not be two halves of one two-way relation. After
writing the children, fetch the anchor and look at its `Contains`:

```
notion-fetch  id="<anchor-page-url>"
```

If `Contains` is empty, set it explicitly:

```
notion-update-page
  page_id: "<anchor-page-id>"
  command: "update_properties"
  properties: { "Contains": ["<child-url-1>", "<child-url-2>", …] }
```

## 11. SQL recipes

Run through `notion-query-data-sources` in `sql` mode. `random()` is not permitted;
a single `SELECT` per call.

Every response is capped at 100 rows and carries `has_more`. Page by natural row
order rather than `OFFSET` — offset paging turned out to skip rows silently at this
row count. The paged sweep is a sieve; **`notion-search` scoped to this data source
is the primary reconciliation tool**, because it catches paraphrases the SQL sweep
cannot (e.g. "context bus" ≠ "shared writable state").

```sql
-- Title index, page 1
SELECT "Title", "Type", "Theme", createdTime
FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
ORDER BY createdTime LIMIT 100;

-- subsequent pages: WHERE createdTime > '<last-createdTime-seen>' LIMIT 100

-- Read summaries for a shortlist before deciding NEW vs ENHANCE vs SKIP
SELECT url, "Title", "Summary"
FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Title" LIKE '%memory%' OR "Summary" LIKE '%memory%';

-- What is already here from this author or publication
SELECT url, "Title", "Source" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Source" LIKE '%<domain>%';

-- Existing rows in a theme, to find the right neighbourhood to link into
SELECT url, "Title" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Theme" LIKE '%Agents & Workflows%';

-- Existing top-level anchors and pillars, to see whether this belongs under one
SELECT url, "Title" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Part of" IS NULL OR "Part of" = '[]';

-- Confirm what you wrote
SELECT "Title", "Type", "Theme", "Lens" FROM "collection://d62ad72b-f5aa-4fa9-b311-2f49ecddcbe3"
WHERE "Source" LIKE '%<path-slug>%';
```

`notion-search` with `data_source_url` set to the collection URL does semantic search
over the rows — better than `LIKE` when the wording differs but the idea matches. Use
`LIKE` to sweep, `notion-search` to judge.

## 12. Why the format is what it is — the OKF mapping

Google Cloud's Open Knowledge Format (v0.2) represents knowledge as concept documents
carrying a small set of structured fields, cross-linked into a graph. This database
already implements that shape; the rules above are that correspondence made explicit,
which is why they are worth following even when a shortcut looks tempting.

| OKF | Here | Consequence for how you write |
|---|---|---|
| `type` — the one required field | `Type` | Never leave it blank or guess; the precedence rule exists so the vocabulary stays reliable |
| `title` | `Title` | Names the concept, not the document it came from — and not the document's headings |
| `description` — "single-sentence summary for search snippets" | `Summary` | Written to be *matched*, not to abbreviate |
| `resource` — canonical URI of the underlying asset | `Source` | Canonical article URL, one per article, tracking stripped, not per claim |
| `tags` | `Theme`, `Domain`, `Lens` | Closed vocabulary; consumers rely on it |
| cross-links form a graph richer than the folder tree | `<mention-page/>` inline, plus `Part of`/`Contains` | The inline links matter as much as the hierarchy |
| `index.md` — progressive disclosure over a directory | the anchor row + its segment map | One row from which the whole article is navigable |
| per-claim source attribution | text-fragment deep links plus block ordinals in bodies | Every claim checkable at its origin |
| "producers SHOULD favour structural markdown over freeform prose" | the body templates | Headings and short quotes, not essays |
| "consumers MUST tolerate unknown types" but producers pick descriptive vocabularies | the seven types | Extend the vocabulary only with the owner's decision |

The one deliberate divergence: OKF v0.2's trust signals (`status`, `verified`,
`stale_after`, `generated`) would need new Notion properties, and the owner chose not
to change the schema. Note that written sources make two of them bite harder than video
does — `stale_after` because posts are edited in place and `verified` because vendor
posts carry unaudited numbers. Until the schema changes, the anchor's **Retrieved** and
**Standing** fields are where that information lives; keep filling them in. If the
schema ever does change, `status: draft` on fresh imports is the highest-value addition
— it lets unreviewed AI-written rows be filtered out of queries with SQL rather than by
reading them.
