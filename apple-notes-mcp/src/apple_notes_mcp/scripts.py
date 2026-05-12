"""JXA (JavaScript for Automation) snippets driving Notes.app.

All user input is read from environment variables via `getenv()` so we never
splice arbitrary strings into the script source. Each snippet writes JSON to
stdout (via the JXA `run()` return value, which osascript prints as text — so
we explicitly `console.log` the JSON instead and end with `undefined`, to
avoid the default `[object Object]` representation).
"""

# Shared prologue available to every snippet.
_PRELUDE = r"""
ObjC.import('stdlib');
function getenv(k) {
  var v = $.getenv(k);
  return v === undefined || v === null ? "" : ObjC.unwrap(v);
}
function emit(value) {
  // Print JSON to stdout. osascript will append a trailing newline.
  $.NSFileHandle.fileHandleWithStandardOutput
    .writeData($.NSString.alloc.initWithUTF8String(JSON.stringify(value))
      .dataUsingEncoding($.NSUTF8StringEncoding));
}
var Notes = Application('Notes');
Notes.includeStandardAdditions = true;
"""


def jxa(body: str) -> str:
    """Wrap a JXA body with the shared prelude."""
    return _PRELUDE + "\n" + body


# -- list folders -----------------------------------------------------------

LIST_FOLDERS = jxa(r"""
var out = [];
var accounts = Notes.accounts();
for (var i = 0; i < accounts.length; i++) {
  var acct = accounts[i];
  var folders = acct.folders();
  for (var j = 0; j < folders.length; j++) {
    var f = folders[j];
    out.push({
      id: f.id(),
      name: f.name(),
      account: acct.name(),
    });
  }
}
emit(out);
""")


# -- list notes -------------------------------------------------------------

LIST_NOTES = jxa(r"""
var folderFilter = getenv('NOTES_FOLDER');   // optional
var limit = parseInt(getenv('NOTES_LIMIT') || '50', 10);
var out = [];

var accounts = Notes.accounts();
outer:
for (var i = 0; i < accounts.length; i++) {
  var acct = accounts[i];
  var folders = acct.folders();
  for (var j = 0; j < folders.length; j++) {
    var folder = folders[j];
    if (folderFilter && folder.name() !== folderFilter) continue;
    var notes = folder.notes();
    for (var k = 0; k < notes.length; k++) {
      var n = notes[k];
      out.push({
        id: n.id(),
        name: n.name(),
        folder: folder.name(),
        account: acct.name(),
        modification_date: n.modificationDate().toISOString(),
        creation_date: n.creationDate().toISOString(),
      });
      if (out.length >= limit) break outer;
    }
  }
}

// Sort newest first.
out.sort(function(a, b) {
  return b.modification_date.localeCompare(a.modification_date);
});
emit(out);
""")


# -- search notes (substring on name + body) --------------------------------

SEARCH_NOTES = jxa(r"""
var query = (getenv('NOTES_QUERY') || '').toLowerCase();
var limit = parseInt(getenv('NOTES_LIMIT') || '25', 10);
var out = [];

if (!query) { emit([]); } else {
  var accounts = Notes.accounts();
  outer:
  for (var i = 0; i < accounts.length; i++) {
    var folders = accounts[i].folders();
    for (var j = 0; j < folders.length; j++) {
      var folder = folders[j];
      var notes = folder.notes();
      for (var k = 0; k < notes.length; k++) {
        var n = notes[k];
        var name = (n.name() || '').toLowerCase();
        // Read body once with the lock guard, then reuse the unlowercased
        // form for the snippet. Touching `n.plaintext()` a second time outside
        // the try/catch on a locked note would throw and abort the whole search.
        var bodyRaw = '';
        try { bodyRaw = n.plaintext() || ''; }
        catch (e) { continue; /* locked note: skip silently */ }
        var body = bodyRaw.toLowerCase();
        if (name.indexOf(query) !== -1 || body.indexOf(query) !== -1) {
          out.push({
            id: n.id(),
            name: n.name(),
            folder: folder.name(),
            account: accounts[i].name(),
            modification_date: n.modificationDate().toISOString(),
            snippet: bodyRaw.slice(0, 200),
          });
          if (out.length >= limit) break outer;
        }
      }
    }
  }
  emit(out);
}
""")


# -- get note by id ---------------------------------------------------------

GET_NOTE = jxa(r"""
var wantedId = getenv('NOTES_ID');
var found = null;

var accounts = Notes.accounts();
outer:
for (var i = 0; i < accounts.length; i++) {
  var folders = accounts[i].folders();
  for (var j = 0; j < folders.length; j++) {
    var folder = folders[j];
    var notes = folder.notes();
    for (var k = 0; k < notes.length; k++) {
      var n = notes[k];
      if (n.id() === wantedId) {
        found = {
          id: n.id(),
          name: n.name(),
          folder: folder.name(),
          account: accounts[i].name(),
          modification_date: n.modificationDate().toISOString(),
          creation_date: n.creationDate().toISOString(),
          body_html: n.body(),
          body_text: n.plaintext(),
        };
        break outer;
      }
    }
  }
}

if (!found) { throw new Error('Note not found: ' + wantedId); }
emit(found);
""")


# -- create note ------------------------------------------------------------

CREATE_NOTE = jxa(r"""
var title = getenv('NOTES_TITLE');
var body  = getenv('NOTES_BODY');         // HTML or plain text
var folderName = getenv('NOTES_FOLDER');  // optional
var accountName = getenv('NOTES_ACCOUNT');// optional

// Notes uses HTML for the body; if the user passed plain text we wrap it.
function looksLikeHtml(s) { return /<\w+[^>]*>/.test(s); }
function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
var html = looksLikeHtml(body)
  ? body
  : '<div>' + escapeHtml(body).replace(/\n/g,'<br>') + '</div>';

// Apple Notes derives the visible title from the FIRST LINE of body and
// also stores it as the AppleScript `name` property automatically. We
// prepend exactly one `<div>{title}</div>` so the new note has a single
// clean title that matches both the sidebar/list view and the editor
// top. Setting `name` explicitly is not needed and would not survive
// any later body write.
var fullBody = '<div>' + escapeHtml(title) + '</div>' + html;
var props = { body: fullBody };
var newNote;

if (folderName) {
  var accounts = Notes.accounts();
  var target = null;
  for (var i = 0; i < accounts.length && !target; i++) {
    if (accountName && accounts[i].name() !== accountName) continue;
    var folders = accounts[i].folders();
    for (var j = 0; j < folders.length; j++) {
      if (folders[j].name() === folderName) { target = folders[j]; break; }
    }
  }
  if (!target) throw new Error('Folder not found: ' + folderName);
  newNote = Notes.Note(props);
  target.notes.push(newNote);
} else {
  newNote = Notes.make({ new: 'note', withProperties: props });
}

emit({
  id: newNote.id(),
  name: newNote.name(),
  folder: newNote.container().name(),
});
""")


# -- append to note ---------------------------------------------------------

APPEND_TO_NOTE = jxa(r"""
var wantedId = getenv('NOTES_ID');
var addition = getenv('NOTES_BODY');

function looksLikeHtml(s) { return /<\w+[^>]*>/.test(s); }
var htmlAddition = looksLikeHtml(addition)
  ? addition
  : '<div>' + addition.replace(/&/g,'&amp;').replace(/</g,'&lt;')
                       .replace(/>/g,'&gt;').replace(/\n/g,'<br>') + '</div>';

var accounts = Notes.accounts();
var found = null;
outer:
for (var i = 0; i < accounts.length; i++) {
  var folders = accounts[i].folders();
  for (var j = 0; j < folders.length; j++) {
    var notes = folders[j].notes();
    for (var k = 0; k < notes.length; k++) {
      if (notes[k].id() === wantedId) { found = notes[k]; break outer; }
    }
  }
}
if (!found) throw new Error('Note not found: ' + wantedId);

found.body = found.body() + htmlAddition;
emit({ id: found.id(), name: found.name(), appended: true });
""")


# -- update note body -------------------------------------------------------

UPDATE_NOTE = jxa(r"""
var wantedId = getenv('NOTES_ID');
var newBody = getenv('NOTES_BODY');
var newTitle = getenv('NOTES_TITLE');  // optional; empty = keep existing

function looksLikeHtml(s) { return /<\w+[^>]*>/.test(s); }
var html = looksLikeHtml(newBody)
  ? newBody
  : '<div>' + newBody.replace(/&/g,'&amp;').replace(/</g,'&lt;')
                      .replace(/>/g,'&gt;').replace(/\n/g,'<br>') + '</div>';

var accounts = Notes.accounts();
var found = null;
outer:
for (var i = 0; i < accounts.length; i++) {
  var folders = accounts[i].folders();
  for (var j = 0; j < folders.length; j++) {
    var notes = folders[j].notes();
    for (var k = 0; k < notes.length; k++) {
      if (notes[k].id() === wantedId) { found = notes[k]; break outer; }
    }
  }
}
if (!found) throw new Error('Note not found: ' + wantedId);

// Title model: the title is the FIRST LINE of body. If the caller
// passed an explicit `title`, we prepend it as a fresh title line and
// the agent's `body` should NOT include a title line. If `title` is
// empty, we trust the agent's body as-is (the agent is expected to
// preserve the existing title line when appropriate; see the styleguide
// and notes://preservation-rules).
var fullBody = newTitle
  ? ('<div>' + newTitle.replace(/&/g,'&amp;').replace(/</g,'&lt;')
                       .replace(/>/g,'&gt;') + '</div>' + html)
  : html;
found.body = fullBody;

emit({ id: found.id(), name: found.name(), updated: true });
""")


# -- rename note (no body touch) -------------------------------------------

# IMPORTANT: this script ONLY sets the `name` property. It does NOT touch
# `body`. This is the only rename approach that is safe on notes containing
# hidden hyperlinks, because writing `body` back via AppleScript strips
# every <a href="..."> in the live note (Apple's bridge does not expose
# href and overwriting body destroys the live, clickable link).
#
# Side effect to know about: modern Notes derives the title shown at the
# top of the open note body from the first line of body. Since we don't
# touch body, that on-screen title does not update. The Notes sidebar /
# notes-list title (which uses `name`) does update.

RENAME_NOTE = jxa(r"""
var wantedId = getenv('NOTES_ID');
var newName = getenv('NOTES_NEW_NAME');

if (!newName) throw new Error('title (NOTES_NEW_NAME) is required');

var accounts = Notes.accounts();
var found = null;
outer:
for (var i = 0; i < accounts.length; i++) {
  var folders = accounts[i].folders();
  for (var j = 0; j < folders.length; j++) {
    var notes = folders[j].notes();
    for (var k = 0; k < notes.length; k++) {
      if (notes[k].id() === wantedId) { found = notes[k]; break outer; }
    }
  }
}
if (!found) throw new Error('Note not found: ' + wantedId);

found.name = newName;
emit({ id: found.id(), name: found.name(), renamed: true });
""")


# -- delete note ------------------------------------------------------------

DELETE_NOTE = jxa(r"""
var wantedId = getenv('NOTES_ID');

var accounts = Notes.accounts();
var found = null;
outer:
for (var i = 0; i < accounts.length; i++) {
  var folders = accounts[i].folders();
  for (var j = 0; j < folders.length; j++) {
    var notes = folders[j].notes();
    for (var k = 0; k < notes.length; k++) {
      if (notes[k].id() === wantedId) { found = notes[k]; break outer; }
    }
  }
}
if (!found) throw new Error('Note not found: ' + wantedId);

var meta = { id: found.id(), name: found.name() };
Notes.delete(found);
emit(Object.assign(meta, { deleted: true }));
""")
