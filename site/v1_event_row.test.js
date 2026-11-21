"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "v1.js"), "utf8");

// Extract a named function assignment's body by matching braces while
// ignoring braces inside quoted strings.
function functionBody(name) {
  const marker = "var " + name + " = function";
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, name + " should be defined");
  const open = source.indexOf("{", start);
  assert.notEqual(open, -1, name + " should have a body");
  let depth = 0, quote = null, escaped = false;
  for (let i = open; i < source.length; i += 1) {
    const ch = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") { quote = ch; continue; }
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  assert.fail(name + " body should be balanced");
}

test("renderEventRow does not render record status on change cards", () => {
  const body = functionBody("renderEventRow");
  assert.equal(body.includes("statusText("), false, "update cards must not show a status badge");
  // Other metadata must remain on the row.
  assert.ok(body.includes("ev.project_id"), "project metadata should remain");
  assert.ok(body.includes("ev.actor_label"), "actor metadata should remain");
  assert.ok(body.includes("Imported history"), "imported history metadata should remain");
});

test("status rendering is retained on record surfaces", () => {
  assert.ok(source.includes("statusText(status,meta.status)"), "record detail page should show status");
  assert.ok(source.includes("Status in this revision"), "revision detail keeps historical status metadata");
});
