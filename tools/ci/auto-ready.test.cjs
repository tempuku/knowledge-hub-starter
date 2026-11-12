"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {validSource,canReady}=require("./auto-ready.cjs");
const sha="a".repeat(40),repo="tempuku/knowledge-hub-starter";
const run={name:"Validate OKF and diary",event:"pull_request",
  status:"completed",conclusion:"success",head_sha:sha,
  head_repository:{full_name:repo}};
const pr={state:"open",draft:true,base:{ref:"main"},
  head:{sha,repo:{full_name:repo}}};
test("only exact successful same-repository core workflow can trigger ready",()=>{
  assert.equal(validSource(run,repo),true);
  for(const bad of [
    {...run,conclusion:"cancelled"}, {...run,conclusion:"failure"},
    {...run,status:"in_progress"}, {...run,event:"push"},
    {...run,head_repository:{full_name:"untrusted/fork"}},
    {...run,head_sha:"bad"}, {...run,name:"other"}
  ])assert.equal(validSource(bad,repo),false);
});
test("reject stale, unsafe or unrelated PRs",()=>{
  assert.equal(canReady(pr,run,repo),true);
  for(const bad of [
    {...pr,state:"closed"},{...pr,draft:false},
    {...pr,base:{ref:"dev"}},{...pr,head:{...pr.head,sha:"b".repeat(40)}},
    {...pr,head:{...pr.head,repo:{full_name:"untrusted/fork"}}}
  ])assert.equal(canReady(bad,run,repo),false);
});
