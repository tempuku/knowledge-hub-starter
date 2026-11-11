import assert from "node:assert/strict";
import test from "node:test";
import { validateKnowledgeFrontmatter } from "./knowledge-frontmatter.mjs";

const concept = fields => `---\n${fields}\n---\n\n# Example\n`;

test("accepts standard statuses and the documented completed extension", () => {
  for (const status of ["draft", "stable", "deprecated", "completed"]) {
    assert.equal(validateKnowledgeFrontmatter(concept(`type: concept\nstatus: ${status}`)).valid, true);
  }
});

test("rejects unknown, mistyped and body-only statuses", () => {
  for (const status of ["complete", "unknown", "true", "[completed]"]) {
    assert.equal(validateKnowledgeFrontmatter(concept(`type: concept\nstatus: ${status}`)).valid, false);
  }
  assert.equal(validateKnowledgeFrontmatter(
    concept("type: concept\nstatus: invalid") + "status: completed\n").valid, false);
});

test("completed does not bypass other metadata or YAML failures", () => {
  for (const fields of [
    "status: completed",
    "type: ''\nstatus: completed",
    "type: concept\nstatus: completed\ntags: invalid",
    "type: concept\nstatus: completed\nsources: [{title: missing-resource}]",
    "type: concept\nstatus: completed\nverified: {by: ''}",
    "type: concept\nstatus: completed\nstatus: draft",
  ]) {
    assert.equal(validateKnowledgeFrontmatter(concept(fields)).valid, false, fields);
  }
});
