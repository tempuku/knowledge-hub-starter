import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedPath, checkedDate, validateCapture, validateEdit, replaceBody, indexPlan} from './policy.mjs';

const capture = {
  title:'Cloudflare access status',
  description:'Record an evidenced infrastructure decision',
  occurred_on:'2026-11-10',
  body:'Decision: keep private content in a separate repository.',
  project:'knowledge-hub',
  tags:['security','infrastructure'],
  source_urls:['https://github.com/tempuku/knowledge-hub-starter/issues/2'],
  idempotency_key:'fixture-cloudflare-2026-11-10'
};
const editArgs = {
  path:'openwiki/journal/2026/11/10/cloudflare-access-status-deadbeef000.md',
  expected_sha:'a'.repeat(40),
  replacement_body:'Updated content with supporting details.',
  reason:'New test evidence requires a revision',
  idempotency_key:'fixture-edit-0000000001'
};
function fails(fn, code) { assert.throws(fn, e => e.message.includes(code)); }

test('capture emits valid private draft with deterministic path and source', () => {
  const a=validateCapture(capture), b=validateCapture({...capture});
  assert.deepEqual(a,b);
  assert.match(a.path,/^openwiki\/journal\/2026\/11\/10\/cloudflare-access-status-[0-9a-f]{10}\.md$/);
  assert.match(a.content,/^visibility: private$/m);
  assert.match(a.content,/^status: draft$/m);
  assert.match(a.content,/^occurred_on: "2026-11-10"$/m);
  assert.match(a.content,/github.com\/tempuku/);
});
test('unknown fields cannot request visibility or override server-selected repository', () => {
  fails(()=>validateCapture({...capture,visibility:'public'}),'UNKNOWN_FIELD');
  fails(()=>validateCapture({...capture,path:'../../secrets'}),'UNKNOWN_FIELD');
  fails(()=>validateCapture({...capture,type:'decision'}),'UNKNOWN_FIELD');
  fails(()=>validateEdit({...editArgs,visibility:'public'}),'UNKNOWN_FIELD');
});
test('reject invalid and future-impossible dates, path traversal, indexes', () => {
  for (const value of ['2026-02-30','2026-13-01','not-a-date'])
    fails(()=>checkedDate(value),'INVALID_OCCURED_ON');
  for (const value of ['../secrets.md','openwiki/adr/0001.md',
    'openwiki/journal/2026/11/10/../secrets.md',
    'openwiki/journal/2026/11/10/index.md',
    'openwiki/journal/2026/11/10/a%2f.md'])
    fails(()=>checkedPath(value),'_PATH');
});
test('reject malicious markdown, non-HTTPS sources, invalid tags and oversized body', () => {
  fails(()=>validateCapture({...capture,body:'<img src=x onerror=alert(1)>'}),'UNSAFE_MARKDOWN');
  fails(()=>validateCapture({...capture,body:'[click](javascript:alert(1))'}),'UNSAFE_MARKDOWN');
  fails(()=>validateCapture({...capture,body:'a'.repeat(12001)}),'INVALID_BODY');
  fails(()=>validateCapture({...capture,source_urls:['http://example.com']}),'INVALID_SOURCE_URL');
  fails(()=>validateCapture({...capture,source_urls:[] }),'SOURCES_REQUIRED');
  fails(()=>validateCapture({...capture,tags:['a','a']}),'INVALID_TAGS');
});
test('revision preserves immutable frontmatter and rejects public edits', () => {
  const original=validateCapture(capture).content;
  const edited=replaceBody(original, {day:'2026-11-10',replacement_body:'Updated content with supporting details.'});
  assert.equal(edited.split('---')[1], original.split('---')[1]);
  assert.match(edited,/Updated content with supporting details/);
  fails(()=>replaceBody(original.replace('visibility: private','visibility: public'),
    {day:'2026-11-10',replacement_body:'updated content'}),'NOT_PRIVATE_DIARY');
  fails(()=>replaceBody(original,{day:'2026-11-09',replacement_body:'updated content'}),'DATE_MISMATCH');
  fails(()=>validateEdit({...editArgs,expected_sha:'abc'}),'INVALID_EXPECTED_SHA');
});
test('indexes cover year/month/day and only add missing links', () => {
  const a=validateCapture(capture);
  const slug=checkedPath(a.path).slug;
  const plan=indexPlan('2026-11-10',capture.title,slug,{
    'openwiki/journal/index.md':'# Diary by year\n\n* [2026](2026/)\n',
    'openwiki/journal/2026/index.md':'# 2026 diary\n\n* [November](11/)\n',
    'openwiki/journal/2026/11/index.md':'# November 2026 diary\n\n* [November 9](09/)\n'
  });
  assert.equal(Object.keys(plan).length,2);
  assert.match(plan['openwiki/journal/2026/11/index.md'],/\(10\/\)/);
  assert.match(plan['openwiki/journal/2026/11/10/index.md'], new RegExp(slug+'.md'));
});
