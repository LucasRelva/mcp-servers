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
You are about to expand or update an existing Apple Note (via `append_to_note`
or `update_note`).

**Before writing anything, do the following in order:**

1. Call `get_note(note_id="{note_id}")` to read the current `body_html`.
2. Read `notes://styleguide` and `notes://html-reference` so you stay within
   what the Notes app supports.
3. Inspect the existing structure of the note:
   - Which `<h2>` / `<h3>` sections exist?
   - Is it predominantly a checklist, a meeting log, a reference doc, a table?
   - What inline conventions are in use (e.g. `☐` bullets, bold field labels)?

When you write the new content:

- **Match the existing structure.** If the note uses `<h2>` per section, add
  your content under the right `<h2>` (or create a new `<h2>` if it's a
  genuinely new section).
- **Match the existing conventions.** If the note uses `☐`/`☑` bullets for
  TODOs, do the same. If it uses a metadata table, add new rows there rather
  than introducing a new format.
- **Don't duplicate the title.** The note already has its `<h1>` from
  creation; don't add another.
- **Prefer `append_to_note`** when adding content to the end (it's
  non-destructive). Use `update_note` only when you must rewrite the whole
  body — and in that case preserve every existing section unless the user
  asked you to remove it.
- **Escape special characters** in any user-supplied text: `&` → `&amp;`,
  `<` → `&lt;`, `>` → `&gt;`.

Content the user wants to add / change:

{content}
"""
