"""JXA snippets driving Reminders.app.

Reminders priority values used by AppleScript:
  0 = none, 1 = high, 5 = medium, 9 = low
"""

_PRELUDE = r"""
ObjC.import('stdlib');
function getenv(k) {
  var v = $.getenv(k);
  return v === undefined || v === null ? "" : ObjC.unwrap(v);
}
function emit(value) {
  $.NSFileHandle.fileHandleWithStandardOutput
    .writeData($.NSString.alloc.initWithUTF8String(JSON.stringify(value))
      .dataUsingEncoding($.NSUTF8StringEncoding));
}
function isoOrNull(d) { return d ? d.toISOString() : null; }
function parseDateOrNull(s) {
  if (!s) return null;
  var d = new Date(s);
  if (isNaN(d.getTime())) throw new Error('Invalid date: ' + s);
  return d;
}
function priorityFromString(p) {
  if (!p) return 0;
  var m = { none: 0, high: 1, medium: 5, low: 9 };
  if (p in m) return m[p];
  var n = parseInt(p, 10);
  if (!isNaN(n)) return n;
  throw new Error('Invalid priority: ' + p);
}
function priorityToString(n) {
  return ({0:'none',1:'high',5:'medium',9:'low'})[n] || String(n);
}
function reminderToObj(r, listName) {
  return {
    id: r.id(),
    name: r.name(),
    body: r.body() || '',
    list: listName,
    completed: r.completed(),
    completion_date: isoOrNull(r.completionDate()),
    due_date: isoOrNull(r.dueDate()),
    remind_me_date: isoOrNull(r.remindMeDate()),
    priority: priorityToString(r.priority()),
    flagged: r.flagged(),
    creation_date: isoOrNull(r.creationDate()),
    modification_date: isoOrNull(r.modificationDate()),
  };
}
var Reminders = Application('Reminders');
Reminders.includeStandardAdditions = true;

// Fast lookup using `whose` (server-side filter, single Apple Event)
// instead of iterating + calling .id() on every reminder.
function findReminderById(wantedId) {
  var lists = Reminders.lists();
  for (var i = 0; i < lists.length; i++) {
    var matches = lists[i].reminders.whose({ id: wantedId })();
    if (matches.length > 0) return { reminder: matches[0], list: lists[i] };
  }
  return null;
}
"""


def jxa(body: str) -> str:
    return _PRELUDE + "\n" + body


# -- list lists -------------------------------------------------------------

LIST_LISTS = jxa(r"""
var out = [];
var lists = Reminders.lists();
for (var i = 0; i < lists.length; i++) {
  var l = lists[i];
  out.push({ id: l.id(), name: l.name() });
}
emit(out);
""")


# -- list reminders ---------------------------------------------------------

LIST_REMINDERS = jxa(r"""
var listFilter   = getenv('REM_LIST');                 // optional list name
var includeDone  = getenv('REM_INCLUDE_COMPLETED') === '1';
var onlyDone     = getenv('REM_ONLY_COMPLETED') === '1';
var limit        = parseInt(getenv('REM_LIMIT') || '100', 10);

// Pull each property as a bulk array (one Apple Event per call) instead of
// touching each reminder individually. This is dramatically faster.
function bulkFetch(rs) {
  return {
    ids:   rs.id(),
    names: rs.name(),
    bodies: rs.body(),
    completed: rs.completed(),
    completionDates: rs.completionDate(),
    dueDates: rs.dueDate(),
    remindMeDates: rs.remindMeDate(),
    priorities: rs.priority(),
    flagged: rs.flagged(),
    creationDates: rs.creationDate(),
    modificationDates: rs.modificationDate(),
  };
}

var out = [];
var lists = Reminders.lists();

outer:
for (var i = 0; i < lists.length; i++) {
  var l = lists[i];
  if (listFilter && l.name() !== listFilter) continue;
  var listName = l.name();
  var b = bulkFetch(l.reminders);
  for (var j = 0; j < b.ids.length; j++) {
    var done = b.completed[j];
    if (onlyDone && !done) continue;
    if (!includeDone && !onlyDone && done) continue;
    out.push({
      id: b.ids[j],
      name: b.names[j],
      body: b.bodies[j] || '',
      list: listName,
      completed: done,
      completion_date: isoOrNull(b.completionDates[j]),
      due_date: isoOrNull(b.dueDates[j]),
      remind_me_date: isoOrNull(b.remindMeDates[j]),
      priority: priorityToString(b.priorities[j]),
      flagged: b.flagged[j],
      creation_date: isoOrNull(b.creationDates[j]),
      modification_date: isoOrNull(b.modificationDates[j]),
    });
    if (out.length >= limit) break outer;
  }
}

// Sort: incomplete first, then by due date (nulls last), then by modification.
out.sort(function(a, b) {
  if (a.completed !== b.completed) return a.completed ? 1 : -1;
  var ad = a.due_date || '9999';
  var bd = b.due_date || '9999';
  if (ad !== bd) return ad < bd ? -1 : 1;
  return (b.modification_date || '').localeCompare(a.modification_date || '');
});
emit(out);
""")


# -- search reminders -------------------------------------------------------

SEARCH_REMINDERS = jxa(r"""
var query = (getenv('REM_QUERY') || '').toLowerCase();
var includeDone = getenv('REM_INCLUDE_COMPLETED') === '1';
var limit = parseInt(getenv('REM_LIMIT') || '50', 10);

var out = [];
if (!query) { emit([]); } else {
  var lists = Reminders.lists();
  outer:
  for (var i = 0; i < lists.length; i++) {
    var l = lists[i];
    var listName = l.name();
    var ids = l.reminders.id();
    var names = l.reminders.name();
    var bodies = l.reminders.body();
    var completed = l.reminders.completed();
    var dueDates = l.reminders.dueDate();
    var priorities = l.reminders.priority();
    var flagged = l.reminders.flagged();
    var modDates = l.reminders.modificationDate();
    var remindAt = l.reminders.remindMeDate();
    var compDates = l.reminders.completionDate();
    var creDates = l.reminders.creationDate();
    for (var j = 0; j < ids.length; j++) {
      if (!includeDone && completed[j]) continue;
      var nm = (names[j] || '').toLowerCase();
      var bd = (bodies[j] || '').toLowerCase();
      if (nm.indexOf(query) !== -1 || bd.indexOf(query) !== -1) {
        out.push({
          id: ids[j], name: names[j], body: bodies[j] || '', list: listName,
          completed: completed[j],
          completion_date: isoOrNull(compDates[j]),
          due_date: isoOrNull(dueDates[j]),
          remind_me_date: isoOrNull(remindAt[j]),
          priority: priorityToString(priorities[j]),
          flagged: flagged[j],
          creation_date: isoOrNull(creDates[j]),
          modification_date: isoOrNull(modDates[j]),
        });
        if (out.length >= limit) break outer;
      }
    }
  }
  emit(out);
}
""")


# -- get reminder by id -----------------------------------------------------

GET_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var hit = findReminderById(wantedId);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
emit(reminderToObj(hit.reminder, hit.list.name()));
""")


# -- create reminder --------------------------------------------------------

CREATE_REMINDER = jxa(r"""
var name      = getenv('REM_NAME');
var body      = getenv('REM_BODY');
var listName  = getenv('REM_LIST');         // optional
var dueDate   = parseDateOrNull(getenv('REM_DUE_DATE'));      // ISO 8601
var remindAt  = parseDateOrNull(getenv('REM_REMIND_AT'));      // ISO 8601
var priority  = priorityFromString(getenv('REM_PRIORITY'));    // none/high/medium/low
var flagged   = getenv('REM_FLAGGED') === '1';

var props = { name: name };
if (body)     props.body = body;
if (dueDate)  props.dueDate = dueDate;
if (remindAt) props.remindMeDate = remindAt;
if (priority) props.priority = priority;
if (flagged)  props.flagged = true;

var newRem;
if (listName) {
  var lists = Reminders.lists();
  var target = null;
  for (var i = 0; i < lists.length; i++) {
    if (lists[i].name() === listName) { target = lists[i]; break; }
  }
  if (!target) throw new Error('List not found: ' + listName);
  newRem = Reminders.Reminder(props);
  target.reminders.push(newRem);
} else {
  newRem = Reminders.make({ new: 'reminder', withProperties: props });
}

emit(reminderToObj(newRem, newRem.container().name()));
""")


# -- update reminder --------------------------------------------------------

UPDATE_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var hit = findReminderById(wantedId);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
var found = hit.reminder;
var foundList = hit.list;

// Each field only updates if a corresponding env var is non-empty.
// Use REM_CLEAR_<field>=1 to explicitly null a field.
function envSet(k) { return getenv(k) !== ''; }
function envClear(k) { return getenv(k) === '1'; }

if (envSet('REM_NAME'))      found.name = getenv('REM_NAME');
if (envSet('REM_BODY'))      found.body = getenv('REM_BODY');
if (envClear('REM_CLEAR_BODY')) found.body = '';

if (envSet('REM_DUE_DATE'))  found.dueDate = parseDateOrNull(getenv('REM_DUE_DATE'));
if (envClear('REM_CLEAR_DUE_DATE')) found.dueDate = null;

if (envSet('REM_REMIND_AT')) found.remindMeDate = parseDateOrNull(getenv('REM_REMIND_AT'));
if (envClear('REM_CLEAR_REMIND_AT')) found.remindMeDate = null;

if (envSet('REM_PRIORITY'))  found.priority = priorityFromString(getenv('REM_PRIORITY'));
if (envSet('REM_FLAGGED'))   found.flagged = getenv('REM_FLAGGED') === '1';

emit(reminderToObj(found, foundList.name()));
""")


# -- complete / uncomplete reminder -----------------------------------------

SET_COMPLETED = jxa(r"""
var wantedId = getenv('REM_ID');
var done     = getenv('REM_COMPLETED') === '1';
var hit = findReminderById(wantedId);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
hit.reminder.completed = done;
emit(reminderToObj(hit.reminder, hit.list.name()));
""")


# -- delete reminder --------------------------------------------------------

DELETE_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var hit = findReminderById(wantedId);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
var meta = { id: hit.reminder.id(), name: hit.reminder.name() };
Reminders.delete(hit.reminder);
emit(Object.assign(meta, { deleted: true }));
""")


# -- create / delete list ---------------------------------------------------

CREATE_LIST = jxa(r"""
var name = getenv('REM_LIST_NAME');
var newList = Reminders.make({ new: 'list', withProperties: { name: name } });
emit({ id: newList.id(), name: newList.name() });
""")
