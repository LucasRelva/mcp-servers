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

// Find a reminder using server-side `whose` filtering.
// If `listHint` (a list name) is provided, we only scan that one list, which
// avoids iterating every list (each enumeration is an Apple Event round-trip
// and Reminders.app can be very slow when iCloud sync is in flight).
function findReminderById(wantedId, listHint) {
  var lists;
  if (listHint) {
    var candidates = Reminders.lists.whose({ name: listHint })();
    if (candidates.length === 0) {
      throw new Error('List not found (hint): ' + listHint);
    }
    lists = candidates;
  } else {
    lists = Reminders.lists();
  }
  for (var i = 0; i < lists.length; i++) {
    var matches = lists[i].reminders.whose({ id: wantedId })();
    if (matches.length > 0) return { reminder: matches[0], list: lists[i] };
  }
  return null;
}

// Slim representation: 4 round-trips instead of 11. Use this for write
// confirmations where the agent doesn't need every field of the reminder.
function reminderSlimObj(r, listName) {
  return {
    id: r.id(),
    name: r.name(),
    list: listName,
    completed: r.completed(),
  };
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

// Push the completion filter to Reminders.app via `whose`. Without this
// we'd pull every completed reminder (potentially thousands, going back
// years) over Apple Events and filter in JS. With it, the app does the
// filter and only sends matches.
function reminderRefs(list) {
  if (onlyDone)         return list.reminders.whose({ completed: true });
  if (!includeDone)     return list.reminders.whose({ completed: false });
  return list.reminders;
}

// Pull each property as a bulk array (one Apple Event per call) instead of
// touching each reminder individually.
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
var lists = listFilter
  ? Reminders.lists.whose({ name: listFilter })()
  : Reminders.lists();

outer:
for (var i = 0; i < lists.length; i++) {
  var l = lists[i];
  var listName = l.name();
  var b = bulkFetch(reminderRefs(l));
  for (var j = 0; j < b.ids.length; j++) {
    out.push({
      id: b.ids[j],
      name: b.names[j],
      body: b.bodies[j] || '',
      list: listName,
      completed: b.completed[j],
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
    // Server-side filter: only iterate non-completed reminders unless
    // includeDone, and skip absurd O(N) scans of years of completed work.
    var rs = includeDone
      ? l.reminders
      : l.reminders.whose({ completed: false });
    var ids = rs.id();
    var names = rs.name();
    var bodies = rs.body();
    var completed = rs.completed();
    var dueDates = rs.dueDate();
    var priorities = rs.priority();
    var flagged = rs.flagged();
    var modDates = rs.modificationDate();
    var remindAt = rs.remindMeDate();
    var compDates = rs.completionDate();
    var creDates = rs.creationDate();
    for (var j = 0; j < ids.length; j++) {
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
var listHint = getenv('REM_LIST_HINT');
var hit = findReminderById(wantedId, listHint);
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

emit(reminderSlimObj(newRem, newRem.container().name()));
""")


# -- update reminder --------------------------------------------------------

UPDATE_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var listHint = getenv('REM_LIST_HINT');
var hit = findReminderById(wantedId, listHint);
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

emit(reminderSlimObj(found, foundList.name()));
""")


# -- complete / uncomplete reminder -----------------------------------------

SET_COMPLETED = jxa(r"""
var wantedId = getenv('REM_ID');
var done     = getenv('REM_COMPLETED') === '1';
var listHint = getenv('REM_LIST_HINT');
var hit = findReminderById(wantedId, listHint);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
hit.reminder.completed = done;
emit(reminderSlimObj(hit.reminder, hit.list.name()));
""")


# -- delete reminder --------------------------------------------------------

DELETE_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var listHint = getenv('REM_LIST_HINT');
var hit = findReminderById(wantedId, listHint);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
// Capture the slim shape BEFORE deleting (we can't read off a deleted
// reference). This matches the {id, name, list, completed} contract the
// other write tools return, plus `deleted: true` so callers can branch on
// it.
var meta = {
  id: hit.reminder.id(),
  name: hit.reminder.name(),
  list: hit.list.name(),
  completed: hit.reminder.completed(),
};
Reminders.delete(hit.reminder);
emit(Object.assign(meta, { deleted: true }));
""")


# -- move reminder between lists --------------------------------------------

# Reminders.app's AppleScript dictionary exposes a `move` verb but it is
# unreliable (Apple has never properly wired it up across iCloud lists --
# silent no-ops are common). The robust approach is to clone the reminder
# into the target list and delete the original. The id necessarily changes;
# the response includes both the old id and the new id so the caller can
# remap any local references.

MOVE_REMINDER = jxa(r"""
var wantedId = getenv('REM_ID');
var listHint = getenv('REM_LIST_HINT');
var targetListName = getenv('REM_TARGET_LIST');

if (!targetListName) throw new Error('target_list is required');

var hit = findReminderById(wantedId, listHint);
if (!hit) throw new Error('Reminder not found: ' + wantedId);
var src = hit.reminder;
var srcListName = hit.list.name();

if (srcListName === targetListName) {
  // Nothing to do, but still return a slim object so the contract holds.
  emit({
    id: src.id(),
    previous_id: src.id(),
    name: src.name(),
    list: srcListName,
    completed: src.completed(),
    moved: false,
    note: 'already in target list',
  });
} else {
  var targets = Reminders.lists.whose({ name: targetListName })();
  if (targets.length === 0) {
    throw new Error('Target list not found: ' + targetListName);
  }
  var targetList = targets[0];

  // Snapshot the source's properties in one batch.
  var props = {
    name:     src.name(),
    body:     src.body() || '',
    completed: src.completed(),
  };
  var due       = src.dueDate();
  var remindAt  = src.remindMeDate();
  var priority  = src.priority();
  var flagged   = src.flagged();
  var completionDate = src.completionDate();

  if (due)       props.dueDate = due;
  if (remindAt)  props.remindMeDate = remindAt;
  if (priority)  props.priority = priority;
  if (flagged)   props.flagged = true;
  if (props.completed && completionDate) props.completionDate = completionDate;

  var clone = Reminders.Reminder(props);
  targetList.reminders.push(clone);

  var oldId = src.id();
  Reminders.delete(src);

  emit({
    id: clone.id(),
    previous_id: oldId,
    name: clone.name(),
    list: targetListName,
    completed: clone.completed(),
    moved: true,
  });
}
""")


# -- create / delete list ---------------------------------------------------

CREATE_LIST = jxa(r"""
var name = getenv('REM_LIST_NAME');
var newList = Reminders.make({ new: 'list', withProperties: { name: name } });
emit({ id: newList.id(), name: newList.name() });
""")
