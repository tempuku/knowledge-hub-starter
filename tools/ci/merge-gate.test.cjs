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
    "Known limitations: Synthetic tests do not establish live review",
    "Reviewer decision: Approved after manual evidence inspection",
    "## Validation checklist",
    "- [x] First requirement with actual report",
    "- [x] Second requirement with privacy check",
    "## Evidence (synthetic)",
    "| Check | Head | Command | Fixture revision | Expected | Observed | Artifact | Limits |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
    "| C1 | "+sha+" | node --test tools/ci/merge-gate.test.cjs | fixture-v1-at-sha | Checked issue requirements | Parsed both checks | https://github.com/tempuku/knowledge-hub-starter/actions/runs/1 | Synthetic parser assertion only |",
    "| C2 | "+sha+" | node --test tools/ci/merge-gate.test.cjs | fixture-v1-at-sha | Reject unchecked items | Unchecked items blocked | https://github.com/tempuku/knowledge-hub-starter/actions/runs/1 | Synthetic parser assertion only |"
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
test("missing design traceability or reviewer decision fails", () => {
  const bad = body().replace("Reviewer decision: Approved","Reviewer decision: Pending")
    .replace("Acceptance IDs: A-04","Acceptance IDs: None");
  const errors = gate.validateBody({body:bad,issueNumber:26,issueBody:issue,sha:SHA});
  assert.ok(errors.some(s=>s.includes("not approved")));
  assert.ok(errors.some(s=>s.includes("scenario")));
});
test("independent approved review must attest to this exact head", () => {
  const make = (login,commit_id,state="APPROVED",message="Evidence verified for head SHA: " + SHA) =>
    ({user:{login,type:"User"},author_association:"COLLABORATOR",state,commit_id,submitted_at:"2026-11-11T12:00:00Z",body:message});
  assert.equal(gate.validateReview([make("reviewer",SHA)],"author",SHA),true);
  assert.equal(gate.validateReview([make("author",SHA)],"author",SHA),false);
  assert.equal(gate.validateReview([make("reviewer","b".repeat(40))],"author",SHA),false);
  assert.equal(gate.validateReview([make("reviewer",SHA,"CHANGES_REQUESTED")],"author",SHA),false);
  assert.equal(gate.validateReview([make("reviewer",SHA,"APPROVED","LGTM")],"author",SHA),false);
  assert.equal(gate.validateReview([{...make("reviewer",SHA),author_association:"NONE"}],"author",SHA),false);
});
test("latest decision from reviewer overrides earlier approval", () => {
  const r={user:{login:"reviewer",type:"User"},author_association:"COLLABORATOR",commit_id:SHA,body:"Evidence verified for head SHA: "+SHA};
  const reviews=[
    {...r,state:"APPROVED",submitted_at:"2026-11-11T12:00:00Z"},
    {...r,state:"CHANGES_REQUESTED",submitted_at:"2026-11-11T12:00:01Z"}
  ];
  assert.equal(gate.validateReview(reviews,"author",SHA),false);
});
test("core workflow and every required step must be truly successful", () => {
  const run={status:"completed",conclusion:"success"};
  const job={name:"validate-openwiki",conclusion:"success",
    steps:gate.REQUIRED_STEPS.map(name=>({name,conclusion:"success"}))};
  assert.deepEqual(gate.validateCoreRun(run,[job]),[]);
  assert.ok(gate.validateCoreRun({...run,conclusion:"skipped"},[job]).length);
  assert.ok(gate.validateCoreRun(run,[{...job,steps:job.steps.slice(1)}]).length);
  assert.ok(gate.validateCoreRun(run,[{...job,conclusion:"skipped"}]).length);
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
