"""Static content exposed as MCP resources and prompts.

Resources here are intended to be loaded by an LLM agent before it composes
or expands an Apple Note, so it knows exactly which formatting features the
Notes app supports and what HTML to emit through the `create_note`,
`update_note`, and `append_to_note` tools.
"""

# --------------------------------------------------------------------------- #
# Styleguide — what Apple Notes supports, the human-friendly version          #
# --------------------------------------------------------------------------- #

STYLEGUIDE = """\
# Apple Notes — Formatting Capabilities

Apple Notes (Mac, iOS, iCloud) renders rich text from a constrained subset of
HTML. The Notes app stores everything as HTML internally and that's exactly
what you write through this MCP server's `body` parameter. CSS3 is mostly
stripped: rely on semantic tags, not inline styles.

## Paragraph styles

- **Title** — large display heading at the top. Use `<h1>` (one per note).
- **Heading** — section header, *also* renders the section as collapsible in
  modern Notes. Use `<h2>`.
- **Subheading** — sub-section. Use `<h3>`.
- **Body** — the default. Use `<div>` or `<p>` for paragraphs.
- **Monospaced** — fixed-width block. Use `<pre>` or `<code>` (best-effort;
  exact rendering is up to Notes).

> Tip: When a note is long, prefer `<h2>` per major section. The Notes UI
> lets the user collapse/expand each `<h2>`-level section, which is great
> for browsable reference notes.

## Inline formatting

- `<b>` or `<strong>` — bold
- `<i>` or `<em>` — italic
- `<u>` — underline
- `<s>` or `<strike>` — strikethrough
- `<a href="...">` — hyperlink
- `<br>` — soft line break inside a paragraph

Inline color, highlight, and font-size changes are not reliably round-tripped
via the AppleScript HTML interface. Don't rely on them.

## Lists

- **Bulleted list** — `<ul><li>…</li></ul>`
- **Numbered list** — `<ol><li>…</li></ol>`
- **Nested list** — nest `<ul>`/`<ol>` inside an `<li>`
- **Dashed list** — Notes-app feature; not addressable via HTML. Use bullets.
- **Checklist** — when authored through this MCP, Notes renders bullet items.
  True interactive checklists with checked/unchecked state must be added
  inside the Notes UI; they are not round-trippable via AppleScript.
  *If the user explicitly asks for a checklist*, use `<ul>` and prefix each
  item with `☐ ` (open) or `☑ ` (done) so the meaning survives, then mention
  the limitation in chat.

## Tables

`<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` are supported.
Inline CSS is stripped, so don't bother styling cells. Keep tables narrow
(≤ 4 columns) — Notes' rendering on iPhone is unforgiving.

## Block content

- `<blockquote>` — quoted block (limited styling).
- `<hr>` — horizontal rule, useful as a section divider.
- Images embedded as `<img src="data:image/...">` are typically dropped.
  Don't try to embed images via this MCP; the user adds them in the Notes UI.

## Collapsible sections

Any `<h2>` (Heading) creates a collapsible section: everything between this
`<h2>` and the next `<h2>` collapses under it. Use this aggressively for
long-form notes.

## Title handling

The Notes app derives the visible note title from the first line of content.
This MCP's `create_note` tool already inserts the requested title as an
`<h1>` at the top of the body, so don't add another `<h1>` yourself.

## Preservation rules (CRITICAL — read before any update)

When **modifying an existing note** (`append_to_note`, `update_note`), the
golden rule is:

> **Always work from `body_html`. Never write back content derived from
> `body_text`.**

`body_text` is a lossy projection of the note. Several elements are
invisible there but visible in the Notes app, and re-writing from plaintext
silently destroys them:

- `<a href="...">visible label</a>` — the URL is hidden behind the label
  text. In `body_text` you only see `visible label`. If you regenerate the
  body from plaintext, **the link is gone**.
- `<b>`, `<i>`, `<u>`, `<s>` — emphasis is invisible in plaintext.
- `<table>` structure — collapses to a flat run of cell text without
  borders, headers, or rows.
- Bullet/numbered list nesting — nesting depth disappears in plaintext.
- Blockquotes, horizontal rules, monospaced blocks — formatting markers
  are stripped.

### Required workflow for ANY update

1. Call `get_note(note_id)` and read **`body_html`** (not `body_text`).
2. Identify everything that must survive your edit. Pay special attention
   to:
   - Every `<a href="...">` — the URL inside `href=` must be preserved
     verbatim, even if you change the surrounding text.
   - Every `<table>`, `<ul>`, `<ol>`, `<blockquote>`, `<pre>`.
   - Inline emphasis (`<b>`, `<i>`, `<u>`, `<s>`).
3. Make a **minimal, targeted edit** to the HTML — change the smallest
   region needed and leave the rest byte-for-byte identical.
4. Prefer `append_to_note` over `update_note` when you're only adding
   content. Append is non-destructive by definition.
5. When `update_note` is unavoidable, the new `body` must be a superset
   of what was there: every link, table, list and emphasis tag from the
   original must reappear in the rewrite, unless the user explicitly
   asked you to remove it.

If you are unsure whether your rewrite preserves everything, **stop and
ask the user** rather than risk losing data.
"""

# --------------------------------------------------------------------------- #
# HTML reference — terse, copy-pasteable                                      #
# --------------------------------------------------------------------------- #

HTML_REFERENCE = """\
# Apple Notes HTML — Quick Reference

```html
<!-- Headings (note title is auto-prepended; do not add a second <h1>) -->
<h2>Section title (collapsible)</h2>
<h3>Sub-section</h3>

<!-- Paragraphs -->
<div>Paragraph of body text.</div>
<p>Also a paragraph.</p>

<!-- Inline -->
<b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>,
<a href="https://example.com">link</a>, line break:<br>next line

<!-- Bulleted list -->
<ul>
  <li>First item</li>
  <li>Second item
    <ul><li>Nested item</li></ul>
  </li>
</ul>

<!-- Numbered list -->
<ol>
  <li>Step one</li>
  <li>Step two</li>
</ol>

<!-- "Checklist-ish" (true interactive checkboxes can't be authored via API) -->
<ul>
  <li>☐ Buy milk</li>
  <li>☑ Email the report</li>
</ul>

<!-- Table -->
<table>
  <thead><tr><th>Field</th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Owner</td><td>Lucas</td></tr>
    <tr><td>Due</td><td>2026-05-15</td></tr>
  </tbody>
</table>

<!-- Blockquote and divider -->
<blockquote>Pulled quote or callout.</blockquote>
<hr>

<!-- Monospaced block -->
<pre>def hello():
    print("hi")</pre>
```

## Special characters

Always escape `&`, `<`, `>` in user-provided text:
- `&` → `&amp;`
- `<` → `&lt;`
- `>` → `&gt;`

Newlines in plain text become `<br>` (or wrap each line in its own `<div>`).
"""

# --------------------------------------------------------------------------- #
# Preservation rules — focused doc the expand prompt loads up front           #
# --------------------------------------------------------------------------- #

PRESERVATION_RULES = """\
# Apple Notes — Preservation Rules for Updates

When modifying an existing note (`append_to_note`, `update_note`), follow
these rules to avoid silently destroying content. Read this doc **before**
producing any edited HTML.

## The single most important rule

**Always work from `body_html`. Never rewrite a note from `body_text`.**

`body_text` is a lossy projection. The following all look identical to
`body_text` but are very different in the actual note:

| Looks the same in body_text | But the HTML differs |
|---|---|
| `Click here for the docs` | `<a href="https://example.com">Click here for the docs</a>` |
| `Total: 42` | `<b>Total:</b> 42` |
| `A Cell — B Cell` | `<table>…<tr><td>A Cell</td><td>B Cell</td></tr>…</table>` |
| `One Two Three` | `<ul><li>One</li><li><ul><li>Two</li><li>Three</li></ul></li></ul>` |

If you regenerate the body from `body_text`, every link URL, every emphasis
tag, every table cell boundary, every list nesting level **is gone**. The
Notes app will happily save the dumbed-down version and the user's data is
lost.

## Required workflow

1. **Read `body_html`** from `get_note(note_id)`. Ignore `body_text` for
   editing purposes; it's only useful for human-readable summaries.
2. **Inventory everything that must survive your edit**, in particular:
   - Every `<a href="...">` — note both the visible label *and* the URL.
   - Every `<b>`, `<i>`, `<u>`, `<s>`.
   - Every `<table>`, `<ul>`, `<ol>`, `<li>`, `<blockquote>`, `<pre>`,
     `<hr>`.
   - Existing `<h1>`/`<h2>`/`<h3>` — keep them where they are.
3. **Make the smallest possible edit** to the HTML. Treat the existing
   body as authoritative; only the region the user asked you to change
   should differ.
4. **Prefer `append_to_note`** for additions. It is impossible for append
   to lose existing content.
5. **`update_note` is the dangerous one.** Use it only when you must
   rewrite content in place. Before calling it:
   - Compare your new `body` against the original `body_html`.
   - Verify every `<a href="…">` from the original appears (with the same
     URL!) in your output, unless the user explicitly told you to remove
     a specific link.
   - Verify every `<table>`, `<ul>`, `<ol>` is present.
   - If anything is missing and the user didn't ask you to remove it,
     fix the rewrite or stop and ask the user.

## When in doubt

Stop and ask. Apple Notes does not have undo across an MCP write — once
you call `update_note`, the previous body is gone. A clarifying question
to the user is far cheaper than data loss.
"""


# --------------------------------------------------------------------------- #
# Templates — concrete, ready-to-fill examples                                #
# --------------------------------------------------------------------------- #

TEMPLATE_MEETING_NOTE = """\
# Template — Meeting note

A scannable meeting note: metadata table, agenda, decisions, action items.

```html
<h2>Metadata</h2>
<table>
  <tr><td><b>Date</b></td><td>2026-05-08</td></tr>
  <tr><td><b>Attendees</b></td><td>Lucas, Maria, Felipe</td></tr>
  <tr><td><b>Topic</b></td><td>Q3 roadmap review</td></tr>
</table>

<h2>Agenda</h2>
<ol>
  <li>Status of in-flight workstreams</li>
  <li>Customer escalations</li>
  <li>Hiring</li>
</ol>

<h2>Decisions</h2>
<ul>
  <li>Pause workstream X until November.</li>
  <li>Hire one senior engineer for the platform team.</li>
</ul>

<h2>Action items</h2>
<ul>
  <li>☐ Lucas — draft the November plan by Fri.</li>
  <li>☐ Maria — open the platform-eng requisition.</li>
</ul>

<h2>Notes</h2>
<div>Free-form discussion notes here…</div>
```
"""

TEMPLATE_CHECKLIST_NOTE = """\
# Template — Checklist / TODO note

Use bullets prefixed with ☐/☑ (HTML body cannot create true interactive
Notes checkboxes). Group with `<h2>` so each group is collapsible.

```html
<h2>This week</h2>
<ul>
  <li>☐ Finish Q3 OKR draft</li>
  <li>☐ Review Felipe's PR</li>
  <li>☑ Send invoice to ACME</li>
</ul>

<h2>Backlog</h2>
<ul>
  <li>☐ Refactor billing service</li>
  <li>☐ Investigate flaky test in payments suite</li>
</ul>
```
"""

TEMPLATE_LONGFORM_NOTE = """\
# Template — Long-form / reference note

Use `<h2>` per major section so the reader can collapse/expand. Keep
paragraphs short. Use lists and tables to break up dense prose.

```html
<h2>Summary</h2>
<div>One-paragraph TL;DR of what this note covers and why it matters.</div>

<h2>Background</h2>
<div>Context the reader needs before the rest makes sense. Keep to 2-3 short paragraphs.</div>

<h2>Key concepts</h2>
<ul>
  <li><b>Concept A</b> — one-line definition.</li>
  <li><b>Concept B</b> — one-line definition.</li>
</ul>

<h2>Details</h2>
<h3>Sub-topic 1</h3>
<div>…</div>
<h3>Sub-topic 2</h3>
<div>…</div>

<h2>Open questions</h2>
<ol>
  <li>Question one</li>
  <li>Question two</li>
</ol>

<h2>References</h2>
<ul>
  <li><a href="https://example.com">Source 1</a></li>
</ul>
```
"""

TEMPLATE_TABLE_NOTE = """\
# Template — Tabular / data note

Apple Notes tables are unstyled. Keep ≤ 4 columns, use `<th>` for the header
row, and put narrative outside the table (Notes won't word-wrap aggressively).

```html
<h2>Comparison</h2>
<table>
  <thead>
    <tr><th>Option</th><th>Pros</th><th>Cons</th><th>Decision</th></tr>
  </thead>
  <tbody>
    <tr><td>Option A</td><td>Fast</td><td>Expensive</td><td>—</td></tr>
    <tr><td>Option B</td><td>Cheap</td><td>Slow</td><td>✅</td></tr>
  </tbody>
</table>

<h2>Notes on the decision</h2>
<div>Why we picked Option B…</div>
```
"""

TEMPLATES = {
    "meeting": TEMPLATE_MEETING_NOTE,
    "checklist": TEMPLATE_CHECKLIST_NOTE,
    "longform": TEMPLATE_LONGFORM_NOTE,
    "table": TEMPLATE_TABLE_NOTE,
}


# --------------------------------------------------------------------------- #
# Prompt templates                                                            #
# --------------------------------------------------------------------------- #

COMPOSE_NOTE_PROMPT = """\
You are about to create a new Apple Note via the `create_note` tool on this
MCP server.

Before generating the body, **read these resources** so you use formatting
the Notes app actually supports:

- `notes://styleguide` — what Apple Notes supports and how to think about it.
- `notes://html-reference` — exact HTML snippets you can use in the `body`.
- `notes://templates/meeting`, `notes://templates/checklist`,
  `notes://templates/longform`, `notes://templates/table` — pick the closest
  template and adapt it.

When composing the note:

1. **Pick the right template** based on the user's intent (a meeting log, a
   reference doc, a TODO list, a comparison table, etc.). If the request is
   short and unstructured, prefer the long-form template with at most one or
   two `<h2>` sections.
2. **Use semantic structure** — `<h2>` for collapsible sections, `<ul>`/`<ol>`
   for lists, `<table>` for tabular data. Do NOT add a second `<h1>`; the
   `create_note` tool already inserts the title as `<h1>` at the top.
3. **Escape user content**: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`. Replace
   newlines in plain text with `<br>` or wrap each line in `<div>`.
4. **Keep it scannable** — short paragraphs, lists over walls of text, tables
   for anything comparative.
5. **Avoid unsupported formatting** — no inline CSS, no embedded images, no
   custom fonts/colors. If the user wants a true interactive checklist,
   use bullets prefixed with `☐`/`☑` and mention in chat that they'll need
   to convert it inside the Notes app for tap-to-check behavior.

Topic / content the user wants:

{topic}

Now produce the call to `create_note(title=…, body=…)`. The `body` argument
must be valid HTML that follows the styleguide.
"""

EXPAND_NOTE_PROMPT = """\
You are about to expand or update an existing Apple Note (via
`append_to_note` or `update_note`).

## Step 0 — read the rules that prevent data loss

Before doing ANYTHING else, load and read this resource end-to-end:

- `notes://preservation-rules`

It explains why you must work from `body_html` (never `body_text`) and
exactly what to preserve. Do not skip it. A previous run of this prompt
silently deleted hyperlinks because they were "hidden behind" their
visible label text — that must not happen again.

## Step 1 — fetch the current state of the note

Call `get_note(note_id="{note_id}")` and read **`body_html`**. Ignore
`body_text` for editing; it's lossy and will lead you astray.

## Step 2 — inventory what must survive

From `body_html`, list every:

- `<a href="…">` — record each URL and the label so you can verify they
  reappear unchanged in your output.
- `<table>` — note its row/column shape.
- `<ul>` / `<ol>` — note nesting depth and any `☐`/`☑` conventions.
- `<b>`, `<i>`, `<u>`, `<s>` — note where emphasis lives.
- `<h1>`, `<h2>`, `<h3>` — note the section structure.

You will need to confirm that every item in this inventory is present in
your output before you call `update_note`.

## Step 3 — read the styleguide if you'll add new content

If your edit introduces *new* structure (a new section, a new table,
etc.), also load:

- `notes://styleguide`
- `notes://html-reference`

so the additions match what Notes supports.

## Step 4 — produce the edit

- **Strongly prefer `append_to_note`.** It cannot delete existing content.
  Use it whenever the user is adding to the note rather than rewriting it.
- **`update_note` is the dangerous tool.** Only use it when you must
  rewrite content in place. Your new `body` MUST contain every `<a href>`,
  every `<table>`, every `<ul>`/`<ol>`, every emphasis tag from the
  original, unless the user explicitly asked you to remove a specific
  item.
- **Match existing conventions** in the note (heading style, list style,
  metadata-table format, `☐`/`☑` bullets, etc.).
- **Don't duplicate the title.** The note already has its `<h1>` from
  creation — don't add another.
- **Escape user-supplied text**: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`.

## Step 5 — self-check before calling update_note

If you're using `update_note`, compare your output against the inventory
from Step 2:

- Every URL from Step 2 still appears verbatim inside an `<a href="…">`?
- Every table is intact?
- Every list (and its nesting) is intact?
- Every emphasis tag is intact?

If anything in the inventory is missing and the user did NOT ask to
remove it, do not call `update_note`. Either fix the rewrite, or stop
and ask the user for clarification.

## Content the user wants to add / change

{content}
"""
