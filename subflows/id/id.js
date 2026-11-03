// Book-keeping for the ID check. Maestro JS cannot read the screen: the YAML
// copies text into maestro.copiedText and calls this with ACTION; results go
// to output.id, and the lines scripts/report.py reads go to the log:
//   LEDGER|<id or UUID>|<person>|<household>|<device>
//   CHECK|PASS or FAIL|<text>
//   NOTE|<text>      BLOCKED|<text>
// Never throws - a thrown error reports only as "Unknown error"; a problem
// is left in output.id.failure for the YAML to fail on. Failed checks
// collect in output.id.failed, for the case to fail on at its end.
//
// CASE (optional) tags CHECK / NOTE / BLOCKED lines for a second case run
// inside this one - X2 inside X1 - as "X2:CHECK|...". run-case.ps1 records
// each tag as its own case; untagged lines belong to the case being run.
if (typeof output.id === 'undefined') {
  output.id = { available: -1, total: -1, last: '', ack: '', failure: '', failed: '', people: {} };
}

var action = typeof ACTION === 'undefined' ? '' : ACTION;
var tag = typeof CASE === 'undefined' || !CASE ? '' : CASE + ':';
var copied = String(maestro.copiedText || '').trim();

if (action === 'count') {
  // WHAT: available | total. The figure is the copied text, digits only.
  var n = /^\d+$/.test(copied) ? parseInt(copied, 10) : -1;
  output.id[WHAT] = n;
  output.id.failure = n < 0 ? 'Could not read the ' + WHAT + ' ID count (read "' + copied + '").' : '';
}

if (action === 'card') {
  // PERSON's ID, read off their card: a 12-digit pool ID, or the
  // "No Beneficiary ID" tag when a UUID was saved instead. HOUSEHOLD names
  // the household for the ledger.
  var m = copied.match(/\d{12}/);
  var id = m ? m[0] : (/No Beneficiary ID/i.test(copied) ? 'UUID' : '');
  output.id.last = id;
  output.id.failure = id ? '' : 'Could not read ' + PERSON + "'s ID off the card (read \"" + copied + '").';
  if (id) {
    output.id.people[PERSON] = id;
    // The device that gave the ID (run-case.ps1 passes DEVICE_ID per part):
    // two-device cases (X9, D5) record IDs from both.
    var device = typeof DEVICE_ID === 'undefined' ? '' : DEVICE_ID;
    console.log('LEDGER|' + id + '|' + PERSON + '|' + HOUSEHOLD + '|' + device);
  }
}

if (action === 'ack') {
  // The ID in the Acknowledgement's "Token ID: <id>" for PERSON. Not a
  // ledger row: the card is the record (read-card.yaml); X2 compares the two.
  var a = copied.match(/\d{12}/);
  output.id.ack = a ? a[0] : '';
  output.id.failure = a ? '' : 'Could not read the ID on ' + PERSON + "'s Acknowledgement (read \"" + copied + '").';
}

if (action === 'check') {
  // One expected result: OK is "true" when met. TEXT says what was expected
  // and what was found.
  var ok = String(OK) === 'true';
  console.log(tag + 'CHECK|' + (ok ? 'PASS' : 'FAIL') + '|' + TEXT);
  if (!ok && !tag) {
    output.id.failed = output.id.failed ? output.id.failed + '; ' + TEXT : TEXT;
  }
}

if (action === 'distinct') {
  // One check over a case's people: PEOPLE is "label=id,label=id,...";
  // every ID must be 12 digits and no two the same.
  var pairs = String(PEOPLE).split(',');
  var seen = {};
  var bad = [];
  var shown = [];
  for (var i = 0; i < pairs.length; i++) {
    var kv = pairs[i].split('=');
    var label = kv[0];
    var pid = kv.length > 1 ? kv[1] : '';
    shown.push(label + ' ' + pid);
    if (!/^\d{12}$/.test(pid)) bad.push(label + ' has no 12-digit ID');
    else if (seen[pid]) bad.push(label + ' has the same ID as ' + seen[pid]);
    else seen[pid] = label;
  }
  var text = pairs.length + ' different 12-digit IDs - ' + shown.join(', ') + (bad.length ? ' (' + bad.join('; ') + ')' : '');
  console.log(tag + 'CHECK|' + (bad.length ? 'FAIL' : 'PASS') + '|' + text);
  if (bad.length && !tag) {
    output.id.failed = output.id.failed ? output.id.failed + '; ' + text : text;
  }
}

if (action === 'var') {
  // A value a later part of the same case needs (scripts/run-case.ps1
  // passes it on as -e NAME=VALUE): Maestro loses this phone after 5-7
  // minutes, so long cases run as several short Maestro runs.
  console.log('VAR|' + NAME + '|' + VALUE);
}

if (action === 'note') {
  console.log(tag + 'NOTE|' + TEXT);
}

if (action === 'blocked') {
  console.log(tag + 'BLOCKED|' + TEXT);
  output.id.failure = 'BLOCKED - ' + TEXT;
}
