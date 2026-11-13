"use strict";

// Merge policy for the immutable design baseline from PR #25.
// This file is loaded only from the trusted default branch by merge-gate.yml.
// PR content is DATA; do not check out or execute proposed PR code here.
const BASELINE = "5befec6cc67486327fa36b22f54f22db59cceecb";
const CONTEXT = "knowledge-merge-gate";
const REQUIRED_STEPS = [
  "Test Knowledge Hub frontmatter validation",
  "Test v1 storage schemas and histories in disposable Git repositories",
  "Test deterministic projection primitives (#31)",
  "Validate v1 source records and append-only trusted-base prefix",
  "Test automated PR readiness safety (no approval or merge)",
  "Validate all staged OpenWiki pages and links",
  "Build and smoke-test private diary locally in CI",
  "Check browser JavaScript syntax and iOS 12 compatibility",
  "Test responsive iPhone/iPad/desktop layout and diary interaction",
  "Test the same app in WebKit (modern Safari engine)",
  "Verify public-only export excludes private notes",
  "Test merge gate policy (negative and positive fixtures)"
];

function normalized(s) {
  return String(s || "").replace(/\s+/g, " ").trim();
}

function requiredChecks(issueBody) {
  return [...String(issueBody || "").matchAll(/^\s*-\s*\[[ xX]\]\s*(.+)$/gm)]
    .map(m => normalized(m[1]));
}

function parseEvidence(body) {
  const rows = new Map();
  for (const line of String(body || "").split(/\r?\n/)) {
    if (!/^\s*\|\s*C\d+\s*\|/.test(line)) continue;
    const cells = line.trim().split("|").slice(1, -1).map(normalized);
    if (cells.length !== 8 || rows.has(cells[0])) return null;
    rows.set(cells[0], cells.slice(1));
  }
  return rows;
}

function parseAcceptanceIds(value) {
  const ids = new Set();
  const parts = String(value || "").split(",");
  if (!parts.length) return null;
  for (const raw of parts) {
    const part = raw.trim();
    if (part === "A-04") { ids.add(part); continue; }
    const match = part.match(/^([SPU])\s*(\d+)\s*(?:[-–]\s*([SPU])?\s*(\d+))?$/i);
    if (!match) return null;
    const [, prefixRaw, startRaw, endPrefixRaw, endRaw] = match;
    const prefix = prefixRaw.toUpperCase();
    const start = Number(startRaw);
    const end = endRaw === undefined ? start : Number(endRaw);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < start ||
        (endPrefixRaw && endPrefixRaw.toUpperCase() !== prefix)) return null;
    if (end - start > 500) return null;
    for (let n = start; n <= end; n++) ids.add(prefix + n);
  }
  return ids.size ? ids : null;
}

function parseIssueAcceptanceIds(value) {
  const text = String(value || "");
  if (!text.trim()) return null;
  const ids = new Set();
  if (/\bA-04\b/i.test(text)) ids.add("A-04");
  const segments = text.split(";");
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index];
    if (index > 0 && /handed\s+to|delegat/i.test(segment)) continue;
    const matches = [...segment.matchAll(/\b([SPU])\s*(\d+)\s*(?:[-–]\s*([SPU])?\s*(\d+))?/gi)];
    for (const match of matches) {
      const [, prefixRaw, startRaw, endPrefixRaw, endRaw] = match;
      const prefix = prefixRaw.toUpperCase();
      const start = Number(startRaw);
      const end = endRaw === undefined ? start : Number(endRaw);
      if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < start ||
          (endPrefixRaw && endPrefixRaw.toUpperCase() !== prefix) || end - start > 500) return null;
      for (let n = start; n <= end; n++) ids.add(prefix + n);
    }
  }
  return ids.size ? ids : null;
}

function validDetail(value) {
  const s = normalized(value);
  return s.length >= 5 &&
    !/^(?:tbd|todo|pending\b|placeholder\b|unverified\b|not (?:yet )?(?:measured|verified|validated|tested|run)\b|unchecked\b|none$|n\/a$|example\b|-+$)/i.test(s) &&
    !/<(?:fill|issue|sha|url|command|fixture|result|details|link|id)[^>]*>/i.test(s);
}

function validateBody({body, issueNumber, issueBody, sha}) {
  const failures = [];
  const md = String(body || "");
  const exact = String(sha || "").toLowerCase();
  const req = requiredChecks(issueBody);

  if (!new RegExp("(?:Closes|Fixes|Resolves)\\s+#" + issueNumber + "\\b", "i").test(md))
    failures.push("No issue-closing reference to #" + issueNumber);
  if (!md.includes(BASELINE)) failures.push("Pinned design baseline SHA is absent");
  if (!new RegExp("Head SHA:\\s*\`?" + exact + "\`?", "i").test(md))
    failures.push("Head SHA must match the current 40-character PR head");
  const ids = md.match(/^\s*Acceptance IDs:\s*(.+)$/mi);
  const providedIds = ids && parseAcceptanceIds(ids[1]);
  if (!providedIds)
    failures.push("Concrete acceptance scenario IDs are missing or malformed");
  const issueIdLine = String(issueBody || "").match(/Required acceptance scenario IDs:\*?\*?\s*([^\n]+)/i);
  if (issueIdLine) {
    const requiredIds = parseIssueAcceptanceIds(issueIdLine[1]);
    if (!requiredIds) failures.push("Issue required acceptance scenario IDs are malformed");
    else for (const id of requiredIds) {
      if (!providedIds || !providedIds.has(id)) failures.push("Missing required scenario ID " + id);
    }
  }
  if (!/https:\/\/github\.com\/tempuku\/knowledge-hub-starter\/blob\/5befec6cc67486327fa36b22f54f22db59cceecb\/openwiki\/design\//.test(md))
    failures.push("No design section link pinned to the merged baseline");
  if (req.length === 0) failures.push("Issue has no checkboxes to enforce");

  const claimed = [...md.matchAll(/^\s*-\s*\[([ xX])\]\s*(.+)$/gm)]
    .map(m => ({checked: m[1].toLowerCase() === "x", label: normalized(m[2])}));
  for (const check of req) {
    const matches = claimed.filter(c => c.label === check);
    if (matches.length !== 1 || !matches[0].checked)
      failures.push("Required issue checkbox not checked exactly once: " + check.slice(0, 100));
  }
  if (claimed.some(c => !c.checked))
    failures.push("An unchecked PR validation item remains");

  const evidence = parseEvidence(md);
  if (!evidence) {
    failures.push("Invalid or duplicate evidence table row");
  } else {
    if (evidence.size !== req.length)
      failures.push("Evidence rows must map one-to-one to the issue's " + req.length + " checkboxes");
    for (let i = 1; i <= req.length; i++) {
      const row = evidence.get("C" + i);
      if (!row) { failures.push("Missing evidence row C" + i); continue; }
      const [head, command, fixture, expected, observed, artifact, limits] = row;
      if (head.replace(/\`/g, "").toLowerCase() !== exact)
        failures.push("C" + i + ": evidence is not anchored to current head SHA");
      for (const [name, value] of Object.entries({command,fixture,expected,observed,limits})) {
        if (!validDetail(value)) failures.push("C" + i + ": missing " + name);
      }
      if (!/^https:\/\/[^\s/]+\/[^\s/]+\/[^\s/]+/.test(artifact) ||
          /example\.com|placeholder|\/$/.test(artifact))
        failures.push("C" + i + ": missing concrete evidence/report URL");
    }
  }
  for (const field of ["Privacy/security/integrity", "Regression impact", "Known limitations"]) {
    const m = md.match(new RegExp("^\\s*" + field.replace(/\//g,"\\/") + ":\\s*(.+)$", "mi"));
    if (!m || !validDetail(m[1])) failures.push("Missing explicit " + field + " assessment");
  }

  return failures;
}

function validateCoreRun(run, jobs) {
  if (!run || run.status !== "completed" || run.conclusion !== "success")
    return ["Core validation workflow did not succeed on this head"];
  const matching = (jobs || []).filter(j => j.name === "validate-openwiki");
  if (matching.length !== 1 || matching[0].conclusion !== "success")
    return ["Core validation job missing, skipped or failed"];
  const steps = matching[0].steps || [];
  return REQUIRED_STEPS
    .filter(name => !steps.some(s => s.name === name && s.conclusion === "success"))
    .map(name => "Core CI required step missing/skipped/failed: " + name);
}


function validateProtection(branch, rules) {
  const failures = [];
  // The effective-rules endpoint lists rules applied to this specific branch.
  // Mere branch.protected=true is insufficient: required CI and PR policy must
  // be checked independently instead of assuming any protection is enough.
  if (!branch || branch.protected !== true)
    failures.push("main is not protected by an active GitHub ruleset");
  if (!Array.isArray(rules))
    return [...failures, "Cannot inspect the effective branch rules"];
  if (!rules.some(r => r.type === "pull_request"))
    failures.push("main does not require a PR before merging");
  if (!rules.some(r => r.type === "non_fast_forward"))
    failures.push("main does not prevent force-pushes");
  const contexts = new Set(rules.filter(r => r.type === "required_status_checks")
    .flatMap(r => r.parameters?.required_status_checks || [])
    .map(c => c.context));
  for (const ctx of ["validate-openwiki", CONTEXT]) {
    if (!contexts.has(ctx))
      failures.push("main does not require status " + ctx);
  }
  return failures;
}

function chooseRun(runs, pr) {
  const same = (runs || []).filter(r =>
    r.head_sha === pr.head.sha && r.event === "pull_request" &&
    r.head_branch === pr.head.ref &&
    (!r.head_repository || r.head_repository.full_name === pr.head.repo.full_name) &&
    (!r.pull_requests || !r.pull_requests.length ||
     r.pull_requests.some(p => p.number === pr.number)));
  same.sort((a,b) => (b.created_at || "").localeCompare(a.created_at || "") || b.id-a.id);
  return same[0] || null;
}

async function evaluate({github, owner, repo, pr}) {
  const sha = pr.head.sha;
  const errors = [];
  if (pr.state !== "open" || pr.draft || pr.base.ref !== "main")
    errors.push("PR must be open, non-draft and target main");
  const [issueNumberMatch] = [String(pr.body || "").match(/\b(?:Closes|Fixes|Resolves)\s+#(\d+)\b/i)];
  if (!issueNumberMatch) {
    errors.push("PR must link its implementation issue");
  } else {
    const issue = (await github.rest.issues.get({
      owner, repo, issue_number: Number(issueNumberMatch[1])
    })).data;
    if (issue.pull_request) errors.push("Linked item must be an issue, not a PR");
    errors.push(...validateBody({
      body: pr.body, issueNumber:Number(issueNumberMatch[1]),
      issueBody:issue.body, sha
    }));
  }
  const [branch, applied] = await Promise.all([
    github.rest.repos.getBranch({owner,repo,branch:"main"}),
    github.request("GET /repos/{owner}/{repo}/rules/branches/{branch}",
      {owner,repo,branch:"main"})
  ]);
  errors.push(...validateProtection(branch.data,applied.data));
  const runResponse = await github.rest.actions.listWorkflowRuns({
    owner,repo,workflow_id:"validate-openwiki.yml",event:"pull_request",
    head_sha:sha,per_page:100
  });
  const run = chooseRun(runResponse.data.workflow_runs || [], pr);
  let jobs = [];
  if (run) {
    jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {
      owner,repo,run_id:run.id,filter:"latest",per_page:100
    });
  }
  errors.push(...validateCoreRun(run,jobs));
  return {ok: errors.length === 0, errors, sha, runUrl:run && run.html_url};
}

async function run({github,context,core}) {
  const {owner,repo} = context.repo;
  const payload = context.payload || {};
  let numbers = [];
  const event = context.eventName;
  if (event === "workflow_run") {
    const runData = payload.workflow_run;
    if (!runData || runData.name !== "Validate OKF and diary" ||
        runData.event !== "pull_request" ||
        runData.repository?.full_name !== owner + "/" + repo) return;
    numbers = (runData.pull_requests || []).map(p => p.number);
    if (!numbers.length) {
      const associated = await github.paginate(
        github.rest.repos.listPullRequestsAssociatedWithCommit,
        {owner,repo,commit_sha:runData.head_sha,per_page:100});
      numbers = associated.map(p => p.number);
    }
  } else if (payload.pull_request) {
    numbers = [payload.pull_request.number];
  } else {
    return;
  }
  for (const number of new Set(numbers.filter(Number.isInteger))) {
    const pr = (await github.rest.pulls.get({owner,repo,pull_number:number})).data;
    if (pr.state !== "open" || pr.base.ref !== "main") continue;
    if (event === "workflow_run" && pr.head.sha !== payload.workflow_run.head_sha) continue;
    let outcome;
    try {
      outcome = await evaluate({github,owner,repo,pr});
    } catch(e) {
      outcome = {ok:false,errors:["Gate API evaluation failed closed: " + e.message],sha:pr.head.sha};
    }
    const description = outcome.ok ? "SHA-bound evidence, required CI and main rules verified" :
      (outcome.errors[0] || "Unknown merge-gate failure").slice(0,130);
    await github.rest.repos.createCommitStatus({
      owner,repo,sha:pr.head.sha,context:CONTEXT,
      state:outcome.ok ? "success" : "failure",
      description,
      target_url:context.serverUrl + "/" + owner + "/" + repo + "/actions/runs/" + context.runId
    });
    if (!outcome.ok) core.warning("PR #" + number + " blocked: " + outcome.errors.join("; "));
    else core.info("PR #" + number + " passed at " + outcome.sha);
  }
}

module.exports = {BASELINE,CONTEXT,REQUIRED_STEPS,requiredChecks,parseEvidence,parseAcceptanceIds,parseIssueAcceptanceIds,
  validateBody,validateCoreRun,validateProtection,chooseRun,evaluate,run};
