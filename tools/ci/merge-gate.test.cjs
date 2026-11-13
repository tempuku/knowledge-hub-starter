"use strict";
// Synthetic parser fixtures are policy tests only, NOT real PR/CI acceptance evidence.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const gate = require("./merge-gate.cjs");

const SHA = "a".repeat(40);
const baseline = gate.BASELINE;
const issue = [
  "**Required acceptance scenario IDs:** A-04",
  "## Task-specific validation",
  "- [ ] First requirement with actual report",
  "- [ ] Second requirement with privacy check"
].join("\n");

function body(sha=SHA) {
  return [
    "Closes #26",
    "Design baseline: " + baseline,
    "Design sections: https://github.com/tempuku/knowledge-hub-starter/blob/" + baseline + "/openwiki/design/acceptance.md#a-04-implementation-evidence-and-completion",
    "Head SHA: " + sha,
    "Acceptance IDs: A-04",
    "Privacy/security/integrity: Reviewed synthetic privacy boundaries",
    "Regression impact: Existing validation jobs preserved unchanged",
    "Known limitations: Synthetic tests do not establish real GitHub enforcement",
    "## Validation checklist",
    "- [x] First requirement with actual report",
    "- [x] Second requirement with privacy check",
    "## Evidence (synthetic)",
    "| Check | Head | Command | Fixture revision | Expected | Observed | Artifact | Limits |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
    "| C1 | "+sha+" | node --test tools/ci/merge-gate.test.cjs | fixture-v1-at-sha | Checked issue requirements | Parsed both checks | https://github.com/tempuku/knowledge-hub-starter/actions/runs/1 | Synthetic parser assertion only |",
    "| C2 | "+sha+" | node --test tools/ci/merge-gate.test.cjs | fixture-v1-at-sha | Reject unchecked items | Rejected unchecked checklist accurately | https://github.com/tempuku/knowledge-hub-starter/actions/runs/1 | Synthetic parser assertion only |"
  ].join("\n");
}

test("synthetic complete evidence is structurally accepted", () => {
  assert.deepEqual(gate.validateBody({body:body(),issueNumber:26,issueBody:issue,sha:SHA}),[]);
});
test("missing evidence and unchecked validation fail closed", () => {
  const unchecked = body().replace("- [x] Second", "- [ ] Second");
  assert.notDeepEqual(gate.validateBody({body:unchecked,issueNumber:26,issueBody:issue,sha:SHA}),[]);
  const missing = body().split("\n").filter(line => !line.startsWith("| C2 |")).join("\n");
  assert.match(gate.validateBody({body:missing,issueNumber:26,issueBody:issue,sha:SHA}).join(" "), /C2|one-to-one/);
});
test("head change invalidates old assertions and artifact rows", () => {
  const errors = gate.validateBody({body:body(),issueNumber:26,issueBody:issue,sha:"b".repeat(40)});
  assert.ok(errors.some(s=>s.includes("Head SHA")));
  assert.ok(errors.some(s=>s.includes("evidence is not anchored")));
});
test("acceptance ID ranges expand exactly and reject malformed or reversed input", () => {
  assert.deepEqual([...gate.parseAcceptanceIds("U1–U3, S2 - S4")],
    ["U1", "U2", "U3", "S2", "S3", "S4"]);
  assert.equal(gate.parseAcceptanceIds("U0"), null);
  assert.equal(gate.parseAcceptanceIds("U3-U1"), null);
  assert.equal(gate.parseAcceptanceIds("U1-P3"), null);
  assert.equal(gate.parseAcceptanceIds("U1-bad"), null);
});
test("acceptance IDs compare exact expanded tokens, not substrings", () => {
  const issueWithU1 = issue.replace("A-04", "A-04, U1");
  const bodyWithU10 = body().replace("Acceptance IDs: A-04", "Acceptance IDs: A-04, U10");
  const errors = gate.validateBody({body:bodyWithU10,issueNumber:26,issueBody:issueWithU1,sha:SHA});
  assert.ok(errors.some(e=>e.includes("Missing required scenario ID U1")));
  const validRange = body().replace("Acceptance IDs: A-04", "Acceptance IDs: A-04, U1–U3");
  const issueWithRange = issue.replace("A-04", "A-04, U1-U3");
  assert.deepEqual(gate.validateBody({body:validRange,issueNumber:26,issueBody:issueWithRange,sha:SHA}),[]);
});
test("normative issue ID prose expands ranges and excludes handed-off scenarios", () => {
  const cases = [
    ["P1, P2, P3, P4, P9, P14; P16 performance checks handed to #37.",
      ["P1","P2","P3","P4","P9","P14"]],
    ["P5, P6, P7, P8, P15; S20.",
      ["P5","P6","P7","P8","P15","S20"]],
    ["U1–U8, U14, U17–U24 as applicable; #13/#21 discussions.",
      ["U1","U2","U3","U4","U5","U6","U7","U8","U14",...Array.from({length:8},(_,i)=>"U"+(i+17))]],
    ["S17 and S20; regressions S8–S11. Working real stdio MCP validation required.",
      ["S8","S9","S10","S11","S17","S20"]]
  ];
  for (const [line, expected] of cases)
    assert.deepEqual([...gate.parseIssueAcceptanceIds(line)].sort(), [...expected].sort());
});
test("missing interior scenario in an expanded range fails", () => {
  const issueWithRange = issue.replace("A-04", "A-04, U1–U3");
  const bodyMissingU2 = body().replace("Acceptance IDs: A-04", "Acceptance IDs: A-04, U1, U3");
  const errors = gate.validateBody({body:bodyMissingU2,issueNumber:26,issueBody:issueWithRange,sha:SHA});
  assert.ok(errors.some(e=>e.includes("Missing required scenario ID U2")));
});
test("missing design traceability fails even with evidence present", () => {
  const bad = body().replace("Acceptance IDs: A-04","Acceptance IDs: None");
  const errors = gate.validateBody({body:bad,issueNumber:26,issueBody:issue,sha:SHA});
  assert.ok(errors.some(msg=>msg.includes("scenario")));
});
test("complete SHA-bound evidence needs no human review or reviewer-decision field", () => {
  const text=body();
  assert.equal(text.includes("Reviewer decision:"),false);
  assert.deepEqual(gate.validateBody({body:text,issueNumber:26,issueBody:issue,sha:SHA}),[]);
});
test("core workflow and every required step must be truly successful", () => {
  const run={status:"completed",conclusion:"success"};
  const job={name:"validate-openwiki",conclusion:"success",
    steps:gate.REQUIRED_STEPS.map(name=>({name,conclusion:"success"}))};
  assert.deepEqual(gate.validateCoreRun(run,[job]),[]);
  assert.ok(gate.validateCoreRun({...run,conclusion:"skipped"},[job]).length);
  for (const required of gate.REQUIRED_STEPS) {
    assert.ok(gate.validateCoreRun(run,[{...job,steps:job.steps.filter(s=>s.name!==required)}])
      .some(error=>error.includes(required)), "missing step must fail: " + required);
    assert.ok(gate.validateCoreRun(run,[{...job,steps:job.steps.map(s=>s.name===required?{...s,conclusion:"skipped"}:s)}])
      .some(error=>error.includes(required)), "skipped step must fail: " + required);
    assert.ok(gate.validateCoreRun(run,[{...job,steps:job.steps.map(s=>s.name===required?{...s,conclusion:"failure"}:s)}])
      .some(error=>error.includes(required)), "failed step must fail: " + required);
  }
});
test("core workflow run tied to exact commit and PR", () => {
  const pr={number:99,head:{sha:SHA,ref:"feature",repo:{full_name:"tempuku/knowledge-hub-starter"}}};
  const base={event:"pull_request",head_sha:SHA,head_branch:"feature",
    head_repository:{full_name:"tempuku/knowledge-hub-starter"},
    pull_requests:[{number:99}],created_at:"2026-11-11T12:00:00Z",id:1};
  assert.equal(gate.chooseRun([base],pr)?.id,1);
  assert.equal(gate.chooseRun([{...base,head_sha:"b".repeat(40)}],pr),null);
  assert.equal(gate.chooseRun([{...base,pull_requests:[{number:100}]}],pr),null);
});

test("branch protected flag alone never passes enforced rules inspection", () => {
  const required=[
    {type:"pull_request"},
    {type:"non_fast_forward"},
    {type:"required_status_checks",parameters:{required_status_checks:[
      {context:"validate-openwiki"},{context:"knowledge-merge-gate"}]}}
  ];
  assert.deepEqual(gate.validateProtection({protected:true},required),[]);
  assert.ok(gate.validateProtection({protected:true},[]).length);
  assert.ok(gate.validateProtection({protected:false},required).length);
  assert.ok(gate.validateProtection({protected:true},required.slice(0,2)).length);
  assert.ok(gate.validateProtection({protected:true},required.slice(1)).length);
  assert.ok(gate.validateProtection({protected:true},required.filter(r=>r.type!=="non_fast_forward")).length);
});

test("multi-word pending ledger values cannot pass as evidence", () => {
  const bad = body().replace("node --test tools/ci/merge-gate.test.cjs","Pending verification");
  const errors = gate.validateBody({body:bad,issueNumber:26,issueBody:issue,sha:SHA});
  assert.ok(errors.some(e=>e.includes("C1: missing command")));
});
