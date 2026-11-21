/* Pure diary helpers shared by the browser app and Node tests. */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.KnowledgeV1Diary = api;
}(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var eventOrder = function (a, b) {
    return String((b && b.recorded_at) || "").localeCompare(String((a && a.recorded_at) || "")) ||
      ((b && b.sequence) || 0) - ((a && a.sequence) || 0) ||
      String((a && a.id) || "").localeCompare(String((b && b.id) || ""));
  };
  // A status filter selects revisions, but the diary should show the current
  // record once. Keep the most recent event for each record and leave events
  // without a record id untouched.
  var dedupeEventsByRecord = function (items) {
    var seen = Object.create(null), out = [];
    (items || []).slice().sort(eventOrder).forEach(function (event) {
      var id = event && event.record_id;
      if (id) {
        if (seen[id]) return;
        seen[id] = true;
      }
      out.push(event);
    });
    return out;
  };
  return {dedupeEventsByRecord: dedupeEventsByRecord};
}));
