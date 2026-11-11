"use strict";

const WORKFLOW = "Validate OKF and diary";

function validSource(run, fullName) {
  return Boolean(run &&
    run.name === WORKFLOW &&
    run.event === "pull_request" &&
    run.status === "completed" &&
    run.conclusion === "success" &&
    run.head_repository?.full_name === fullName &&
    /^[0-9a-f]{40}$/i.test(String(run.head_sha || "")));
}

function canReady(pr, run, fullName) {
  return Boolean(validSource(run, fullName) && pr &&
    pr.state === "open" && pr.draft === true &&
    pr.base?.ref === "main" &&
    pr.head?.sha === run.head_sha &&
    pr.head?.repo?.full_name === fullName);
}

// This changes only Draft -> Ready for review. It never approves or merges.
async function run({github,context,core}) {
  const fullName = context.repo.owner + "/" + context.repo.repo;
  const wf = context.payload?.workflow_run;
  if (!validSource(wf,fullName)) return;

  let ids = (wf.pull_requests || []).map(pr=>pr.number);
  if (!ids.length) {
    const associated=await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit,{
      ...context.repo,commit_sha:wf.head_sha,per_page:100
    });
    ids=associated.map(pr=>pr.number);
  }
  for (const number of new Set(ids.filter(Number.isInteger))) {
    const pr=(await github.rest.pulls.get({...context.repo,pull_number:number})).data;
    if (!canReady(pr,wf,fullName)) continue;
    await github.graphql(
      `mutation($id: ID!) {
        markPullRequestReadyForReview(input: {pullRequestId: $id}) {
          pullRequest { number isDraft }
        }
      }`,
      {id:pr.node_id}
    );
    core.info("Marked PR #"+number+" ready for review at exact CI SHA "+wf.head_sha+
      "; this is NOT approval or authorization to merge.");
  }
}
module.exports={WORKFLOW,validSource,canReady,run};
