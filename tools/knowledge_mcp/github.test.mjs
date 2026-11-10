import test from 'node:test';
import assert from 'node:assert/strict';
import {createGateway} from './github.mjs';
import {validateCapture} from './policy.mjs';

const A='a'.repeat(40), B='b'.repeat(40), C='c'.repeat(40), D='d'.repeat(40);
const sample={
  title:'Cloudflare write gateway', description:'Notes about a verified gateway',
  occurred_on:'2026-11-10', body:'A checked diary entry with a source.',
  tags:['security'], source_urls:['https://github.com/tempuku/knowledge-hub-starter/issues/2'],
  idempotency_key:'fixture-cloudflare-gateway-2026'
};
function server(mode='direct-write', options={}) {
  const files=new Map([
    ['openwiki/index.md','# OpenWiki\n\n* [Journal](journal/)\n'],
    ['openwiki/journal/index.md','# Diary by year\n\n* [2026](2026/)\n'],
    ['openwiki/journal/2026/index.md','# 2026 diary\n\n* [November](11/)\n'],
    ['openwiki/journal/2026/11/index.md','# November 2026 diary\n\n* [November 9](09/)\n']
  ]);
  const paths = [];
  const changes = [];
  const calls = [];
  const json=(value,status=200)=>new Response(JSON.stringify(value),{status});
  const fakeFetch=async(url,init)=>{
    assert.match(url,/^https:\/\/api\.github\.com\/repos\/tempuku\/knowledge-hub-data\//);
    assert.equal(init.headers.Authorization,'Bearer test-token-very-long-000000001');
    const u=new URL(url), path=u.pathname.split('/repos/tempuku/knowledge-hub-data/')[1] || '';
    paths.push(path); calls.push({path, method:init.method, body:init.body && JSON.parse(init.body)});
    if (path === '') return json({full_name:'tempuku/knowledge-hub-data',private:options.public !== true,archived:false});
    if (path.startsWith('contents/') && init.method === 'GET') {
      const name=decodeURIComponent(path.slice('contents/'.length));
      return files.has(name)
        ? json({type:'file',encoding:'base64',sha:options.shaOverride?.[name] || A,
            content:Buffer.from(files.get(name)).toString('base64')})
        : json({message:'Not found'},404);
    }
    if (path.startsWith('git/ref/heads/') && init.method === 'GET') {
      return path === 'git/ref/heads/main'
        ? json({object:{sha:B}}) : json({message:'Not found'},404);
    }
    if (path === 'git/commits/'+B) return json({tree:{sha:C}});
    if (path.startsWith('git/trees/'+B)) {
      return json({truncated:false,tree:[...files].map(([path])=>({type:'blob',path}))});
    }
    if (path === 'git/trees' && init.method === 'POST') {
      assert.equal(init.body,'unused'); // overridden below by parsed body test
    }
    if (path === 'git/commits' && init.method === 'POST') return json({sha:D});
    if (path === 'git/refs/heads/main' && init.method === 'PATCH') return json({ref:'refs/heads/main'});
    if (path === 'git/refs' && init.method === 'POST') return json({ref:'refs/heads/mcp'});
    if (path.startsWith('pulls?') && init.method === 'GET') return json([]);
    if (path === 'pulls' && init.method === 'POST') return json({html_url:'https://github.com/tempuku/knowledge-hub-data/pull/1',number:1});
    return json({message:'Unknown mocked route'},404);
  };
  // Wrap API fake to validate planned tree changes.
  const fixtureFetch=async(url,init)=>{
    const path=new URL(url).pathname.split('/repos/tempuku/knowledge-hub-data/')[1] || '';
    if (path === 'git/trees' && init.method === 'POST') {
      assert.equal(init.headers.Authorization,'Bearer test-token-very-long-000000001');
      const tree=JSON.parse(init.body);
      changes.push(...tree.tree);
      assert.equal(tree.base_tree,C);
      calls.push({path,method:init.method,body:tree});
      return json({sha:'e'.repeat(40)});
    }
    return fakeFetch(url,init);
  };
  const env={KNOWLEDGE_GITHUB_TOKEN:'test-token-very-long-000000001',KNOWLEDGE_ENABLE_WRITE:mode};
  return {api:createGateway(env,fixtureFetch),files,paths,changes,calls};
}
async function rejects(promise, reason) {
  await assert.rejects(promise, e=>e.message.includes(reason));
}
test('new private diary capture commits record, indexes, receipt in one private atomic tree', async()=>{
  const s=server(); const result=await s.api.capture(sample);
  assert.equal(result.status,'committed_private');
  assert.ok(result.commit_sha);
  assert.ok(s.changes.some(v=>v.path === validateCapture(sample).path));
  assert.ok(s.changes.some(v=>v.path.endsWith('/2026/11/index.md')));
  assert.ok(s.changes.some(v=>v.path.endsWith('/2026/11/10/index.md')));
  assert.ok(s.changes.some(v=>v.path.startsWith('.knowledge-mcp/operations/')));
  assert.equal(s.calls.filter(v=>v.path==='git/refs/heads/main' && v.method==='PATCH').length,1);
  assert.equal(s.calls.some(v=>v.path==='pulls'),false);
});
test('review-only mode does not update main and opens draft PR', async()=>{
  const s=server('review-only'); const result=await s.api.capture(sample);
  assert.equal(result.status,'draft_pr_created');
  assert.equal(result.number,1);
  assert.equal(s.calls.some(v=>v.path==='git/refs/heads/main' && v.method==='PATCH'),false);
  assert.equal(s.calls.find(v=>v.path==='pulls').body.draft,true);
});
test('public or missing token fails before record access', async()=>{
  const s=server('direct-write',{public:true});
  await rejects(s.api.capture(sample),'PRIVATE_REPOSITORY_REQUIRED');
  assert.equal(s.paths.some(p=>p.startsWith('contents/')),false);
  const noToken=createGateway({KNOWLEDGE_ENABLE_WRITE:'direct-write'},async()=>{throw Error('network unexpected')});
  await rejects(noToken.capture(sample),'TOKEN_REQUIRED');
});
test('update with SHA edits private body in one atomic commit and writes receipt',async()=>{
  const s=server(); const path='openwiki/journal/2026/11/10/example.md';
  s.files.set(path,validateCapture(sample).content);
  const input={path,expected_sha:A,replacement_body:'A validated replacement body with source context.',
    reason:'More recent evidence supports updated content',
    idempotency_key:'fixture-update-cloudflare-2026'};
  const result=await s.api.edit(input);
  assert.equal(result.status,'updated_private');
  const body=s.changes.find(v=>v.path===path).content;
  assert.match(body,/validated replacement body/);
  assert.match(body,/^occurred_on: "2026-11-10"$/m);
  assert.match(body,/^visibility: private$/m);
  assert.ok(s.changes.some(v=>v.path.startsWith('.knowledge-mcp/operations/')));
});
test('stale SHA fails without commits, public diary cannot be changed',async()=>{
  const s=server(); const path='openwiki/journal/2026/11/10/example.md';
  s.files.set(path,validateCapture(sample).content);
  const input={path,expected_sha:'f'.repeat(40),replacement_body:'A validated replacement body.',
    reason:'More recent evidence supports updated content',idempotency_key:'fixture-update-sha-2026'};
  await rejects(s.api.edit(input),'STALE_OR_MISSING_RECORD');
  s.files.set(path,validateCapture(sample).content.replace('visibility: private','visibility: public'));
  await rejects(s.api.edit({...input,expected_sha:A}),'NOT_PRIVATE_DIARY');
  assert.equal(s.calls.some(v=>v.path==='git/commits' && v.method==='POST'),false);
});
test('agent cannot directly update outside direct-write mode', async()=>{
  const s=server('direct-capture'); const path='openwiki/journal/2026/11/10/example.md';
  s.files.set(path,validateCapture(sample).content);
  const input={path,expected_sha:A,replacement_body:'A validated replacement body.',
    reason:'More recent evidence supports updated content',idempotency_key:'fixture-update-review-2026'};
  const result=await s.api.edit(input);
  assert.equal(result.status,'draft_pr_created');
  assert.equal(s.calls.some(v=>v.path==='git/refs/heads/main' && v.method==='PATCH'),false);
});
test('duplicate same-day title is rejected before any commit',async()=>{
  const s=server();
  s.files.set('openwiki/journal/2026/11/10/cloudflare-write-gateway-aaaaaaaaaa.md','x');
  await rejects(s.api.capture(sample),'POSSIBLE_DUPLICATE_RECORD');
  assert.equal(s.calls.some(v=>v.path==='git/commits' && v.method==='POST'),false);
});
