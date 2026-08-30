# Extraction judgment — worked examples

The mechanics in `kb-schema.md` are learnable in one read. The judgment here is what
separates a database worth querying from a pile of highlights. These examples are about
the decision, not the topic.

## 1. The retrieval test, applied

Before writing a row, finish this sentence: *"Six months from now, in the middle of
real work, I type __________ and this row is the answer."*

If you cannot fill the blank with something a person would actually type, you do not
have a row.

| Candidate | The question it answers | Verdict |
|---|---|---|
| "Orchestrator-worker — for tasks whose subtasks can't be known before the task starts" | *"how do I structure an agent when I can't predict the steps up front"* | **Row.** Answers a live architectural fork. |
| "The post distinguishes workflows from agents" | *"what is an agent"* — the article's premise, not its contribution | **Not a row.** Belongs in the anchor's spine. |
| "The author works on Anthropic's applied AI team" | — | **Not a row.** Anchor's source block. |
| "Agentic systems trade latency and cost for better task performance, and that tradeoff should be explicit" | *"is an agent worth it here or should I just chain two prompts"* | **Row.** Answers a decision someone is defending in a design review. |

Notice the pattern: rows that survive answer a **decision** or a **symptom**. Rows that
fail state a **topic** — and in prose, the topics arrive pre-labelled as headings, which
is what makes them so easy to file by mistake.

## 2. Where the value hides in written sources

In a talk, the highest-value content is the unrehearsed aside. Prose has no asides —
every sentence was chosen. The equivalent hiding places:

| Look here | Why | What it usually yields |
|---|---|---|
| Parentheticals and em-dash clauses | too specific for the main line, too true to cut | the real constraint |
| Footnotes and endnotes | where the author put the thing that complicates the argument | the caveat that makes the framework usable |
| The paragraph after "in practice" / "the exception is" / "we tried X first" | earned experience, not theory | named failure modes |
| Comments *inside* code blocks | written for a reader who will run it | the assumption the prose never states |
| The second-to-last section | where honest posts put the limitations, just before the recap | `Watch out` material for several rows at once |
| Outbound links | the argument's citations | whether this post is advancing an idea or relaying one |

Conversely, **the bolded takeaway sentence is usually the weakest candidate in the
paragraph.** Authors bold what is memorable and general; you need what is specific and
distinguishing. Bold text is a good place to find *where* an idea is, and a bad place
to find the *wording* of the row.

## 3. The row, next to the row it was nearly written as

**Pair A — the heading trap (the dominant prose failure)**

❌ `Common patterns for agentic systems`
Summary: *"The post covers five common patterns for building agentic systems."*

This is a row that exists because the article had an H2 called "Common patterns". It
answers no question. Anyone who types "agentic patterns" gets a row that tells them
there are five and does not tell them which one to use.

✅ Five sibling rows, one per pattern, each titled by **the condition under which you
would pick it** rather than by its name alone —
`Prompt chaining — for tasks that decompose cleanly into fixed subtasks`,
`Routing — when input classes need genuinely different handling, not one prompt straddling both`,
and so on — plus a parent `Framework` row that names the set and links them.

The parent earns its place because the *choice between* the patterns is itself a
knowledge unit. The article's H2 does not; the choice does.

**Pair B — the topic trap**

❌ `Agents vs workflows`
Summary: *"The article explains the difference between agents and workflows."*

✅ `Workflows vs agents — the split is who controls the path, not how smart the model is`
Summary: *"Teams argue about whether a system 'is an agent' when the load-bearing
question is whether the control flow is fixed in code or decided by the model at
runtime. Explains why that boundary predicts cost, latency, and debuggability, and why
most production systems that call themselves agents are orchestrated workflows.
Relevant when scoping a build or defending a simpler design."*

The second gets retrieved because it contains the words someone in trouble would use:
*control flow, runtime, cost, latency, debuggability, production*. The first contains
only the words everyone uses.

**Pair C — the listicle**

A "12 lessons from shipping AI features" post does not contain 12 rows. It typically
contains three or four real ones, five restatements of common knowledge, and three
items that exist because 12 is a better headline number than 4.

❌ twelve rows mirroring the twelve headings.
✅ the three or four that survive the retrieval test, plus SKIP notes in the segment map
for the rest, so it is visible you considered and rejected them.

**Pair D — the artifact that was filed as a description**

❌ `Evaluation rubric design` (`Concept`) — a body describing that the author uses a
five-criterion rubric with written rationale.

✅ `Judge rubric — five-criterion scoring template with rationale field` (`Template`) —
the actual rubric reproduced, plus two lines on which parts are skeleton and which are
this author's specifics.

When a post hands you the copyable thing, the copyable thing is the row. This is the
single most common way a written source gets under-extracted relative to its value.

## 4. Anti-patterns and their tells

**Heading mirroring.** *Tell:* your row titles, read in order, reconstruct the
article's table of contents. Or: your row count equals the H2 count. *Fix:* throw the
list away and re-derive from the spine. Some headings hold three ideas; some hold none.
Check every remaining coincidence between a row and a heading and keep it only if you
can defend it independently.

**Summary collapse.** *Tell:* four rows for a 3,000-word post, each Summary trying to
cover a whole section. *Fix:* for each row, list the distinct questions it currently
answers. If more than one, split it.

**Restating the commonplace.** *Tell:* the row would be equally true if you had never
read the post. *Fix:* keep only what this source adds — a number, a mechanism, a named
failure, a formulation sharper than the generic version. If nothing, drop it.

**Relaying as authoring.** *Tell:* the row credits this post with a framework the post
itself attributes to someone else — often with a link sitting right there in the
sentence. *Fix:* check `outbound_links`. If the post is passing an idea along, the
verdict is SKIP or ENHANCE against the row the database already has from the original,
not a fresh row under this author's name.

**Quote-as-body.** *Tell:* the body is 80% blockquote. Prose makes this far easier to
fall into than a transcript did, because the text is already clean and copying is
frictionless. *Fix:* the quote is evidence; the synthesis is the product. If you cannot
write two sentences explaining why the claim holds and what it depends on, you have not
understood it well enough to file it — and you may be republishing rather than
extracting.

**Furniture rows.** *Tell:* a row sourced from the last few blocks of the fetch — a
newsletter CTA, a related-posts list, an author bio, a comment. *Fix:* re-run with a
higher `--min-words`, and treat the tail of the block list with suspicion generally.

**Orphan rows.** *Tell:* a row with no `Part of` and no inline mentions. *Fix:* every
row should sit under the anchor and point at at least one neighbour. A row nothing
links to is a row nothing will lead you to.

## 5. NEW vs ENHANCE vs SKIP — the calls that are actually hard

**SKIP** — the database has `LLM-as-judge — a graded rubric with written rationale…`
and the post explains LLM-as-judge at the same level of detail. Nothing added. Record
it in the segment map as corroboration and move on. Resisting the urge to write it
anyway is the whole discipline.

**ENHANCE** — same existing row, but the post names a failure mode it does not cover:
judges drifting when the rubric has more than five criteria. Same question, better
answer. Append the quote, the deep link, and two sentences. Do not create
`LLM-as-judge failure modes` as a sibling — it would split the answer across two rows,
and the owner would find whichever one ranked higher that day.

**ENHANCE, prose-specific** — the database has the idea from a conference talk, and this
post gives the same idea *with working code*. That is a genuine addition and usually an
`ENHANCE` on the existing row rather than a new one — unless the code is a
self-contained reusable artifact, in which case it is a `Template` row cross-linked to
the concept. The test: would someone ever want the artifact without the argument? If
yes, two rows.

**NEW despite overlap** — the database has a row on evaluation signal generally; the
post gives a specific procedure for building a judge from disagreement cases. Same
*topic*, different *question* (`"how do I evaluate"` vs `"how do I build the judge"`).
Two rows, cross-linked. Topic overlap is not answer overlap.

**NEW despite the same author** — the owner may already have this author's talk on the
same subject. Written and spoken versions of one argument are usually not duplicates:
the post typically carries the precision and the code, the talk carries the framing and
the war stories. Reconcile claim by claim, not source by source.

The rule underneath all of it: ask what question each row answers. Merge on matching
questions, not matching subject matter and not matching source.

## 6. Calibration

Density, not length, sets the count — and prose density varies more by *genre* than by
word count. Rough shapes:

| Source | Typical yield |
|---|---|
| 1,500–3,000 word engineering post, one argument | 1 anchor + 6–12 units |
| 5,000+ word essay or deep-dive | 1 anchor + 10–20 units |
| Documentation page or reference guide | 1 anchor + 4–10 units, several of them `Template` or `Tool` |
| "N lessons / N tips" listicle | 1 anchor + 3–6 units — far fewer than N |
| Product launch or release post | 1 anchor + 2–6 units, mostly `Tool` |
| Newsletter issue (multiple unrelated items) | often no anchor at all — see below |
| Opinion / position piece | 1 anchor + 2–5 units; the argument is one idea, not many |
| Templated multi-section report ("how N teams use X") | 1 anchor + 8–15 units — cross-cutting patterns, **not** one per section |
| Scanned PDF read page-by-page | same as its genre; the reading method does not change the count |

A newsletter issue covering six unrelated links is not one source with one spine. Either
ingest the one item worth keeping as a standalone row citing the newsletter, or treat
each substantive item as its own mini-ingest. Forcing an anchor over unrelated items
produces a spine that is really a table of contents, which is the heading trap wearing a
different hat.

If your count lands far outside these, that is not automatically wrong — but check which
failure you are in. Too many almost always means you followed the headings. Too few
usually means you summarised the post instead of distilling it.

## 7. Corpus-shaped sources

A vendor report profiling ten teams against one template is the hardest version of the
heading trap, because the sections look like legitimate structure and each one is
genuinely about something different.

The test that resolves it: **would a reader ever want this section without the others?**
For "Claude Code for the legal team" the answer is almost always no — what they want is
"how do non-engineers actually use this", which no single section answers and all ten
support. The recurrence *is* the unit.

| Instead of | Write |
|---|---|
| 10 rows, one per team profiled | 1 anchor + the patterns that recur across teams |
| `Claude Code for security engineering` | `Custom slash commands as team-level workflow encoding` (with security eng as one instance) |
| a row per named use case | the use cases as worked examples inside the pattern rows they evidence |

Two things earn a standalone row from a single section: a **specific number** stated only
there (a first-attempt success rate, a measured cycle time), and a **formulation** sharp
enough to be quoted (a named methodology, a phrase that captures a distinction).
Everything else is evidence for a cross-cutting row.

A tell that you got it right: the anchor's segment map has many more entries in the
"corroborates" column than in the "new row" column, because the document's job was to
show the same handful of things happening repeatedly.

## 8. A note on quoting written sources

Auto-captions were approximate, which licensed silent correction and paraphrase. For
HTML and clean-text PDFs the opposite holds: the text is the author's exact published
wording, and it is their work. Three consequences.

**The exception is OCR.** When the script flags `text_is_ocr`, you are back in
auto-caption territory — recognition mangles exactly the words that matter most here,
product names and jargon (`T op tips`, `MCP` → `MCB`). Fix what you recognise with
confidence, leave what you do not, paraphrase anything too garbled to trust, and mark the
body `**Verbatim (OCR, p.N)**`. If a quote is load-bearing, open the cached PDF and read
that page visually before writing the row. A confident misquote outlives the source.

**Reproduce quotes exactly.** No cleaning, no tightening, no fixing their comma. If you
need to omit, use an ellipsis. If you need to paraphrase, drop the blockquote and write
it as your own synthesis with the deep link attached — a paraphrase inside quotation
marks is a misquote.

**Keep them short.** One to three sentences. The deep link makes length unnecessary: the
original is one click away, and a body that reproduces half a section is republishing.

**Never store the article.** No row is a full-text dump, and the transcript-equivalent
temptation is stronger here because the text is already clean markdown. A database of
article dumps cannot be retrieved from anyway — that is the same reason the ground rules
exist, not a separate rule bolted on.
