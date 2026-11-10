import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {configured, route, sourcePath} from './worker.mjs';

const env = {
  ACCESS_AUD: 'test-app-audience',
  ALLOWED_EMAILS: 'Owner@example.test, collaborator@example.test',
  GITHUB_READ_TOKEN: 'local-fixture-token-not-a-secret',
};
const identity = (email='owner@example.test', aud=env.ACCESS_AUD) => ({
  access: {aud, getIdentity: async () => ({email})},
});
const request = (path='/', method='GET') => new Request('https://private-hub.example.test' + path, {method});
const json = {format:'knowledge-hub-calendar-v1', total:1, days:[{date:'2026-11-09',count:1}]};
const privateData = {
  'site-data/data/calendar.json':JSON.stringify(json),
  'site-data/data/days/2026-11-09.json':JSON.stringify({date:'2026-11-09',count:1,pages:1,page_size:50}),
  'site-data/data/days/2026-11-09/1.json':JSON.stringify([{id:'2026-11-09-secret',title:'Private title'}]),
  'site-data/data/entries/2026-11-09-secret.json':JSON.stringify({id:'2026-11-09-secret',body:'Personal private content'}),
};
const publicData = {
  'index.html':'<!doctype html><html><script src="./app.js"></script></html>',
  'app.js':'console.log("public UI");',
  'style.css':'body { color: #000; }',
  'manifest.webmanifest':'{"name":"Knowledge Hub"}',
  'apple-touch-icon.png':'png-data',
};
function mockFetch(overrides={}) {
  const saved = globalThis.fetch;
  const calls = [];
  const privateFiles = {...privateData, ...(overrides.privateFiles || {})};
  const publicFiles = {...publicData, ...(overrides.publicFiles || {})};
  globalThis.fetch = async (input, options) => {
    const url = new URL(input);
    calls.push(url.href);
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'manual');
    if (url.hostname === 'api.github.com') {
      assert.ok(url.pathname.startsWith('/repos/tempuku/knowledge-hub-data/contents/site-data/data/'));
      assert.equal(url.searchParams.get('ref'), 'main');
      assert.equal(options.headers.Authorization, 'Bearer ' + env.GITHUB_READ_TOKEN);
      assert.equal(options.headers.Accept, 'application/vnd.github.raw+json');
      const key = url.pathname.slice('/repos/tempuku/knowledge-hub-data/contents/'.length);
      const body = privateFiles[key];
      return body === undefined ? new Response('missing',{status:404}) : body instanceof Response ? body : new Response(body);
    }
    assert.equal(url.origin, 'https://tempuku.github.io');
    assert.ok(url.pathname.startsWith('/knowledge-hub-starter/'));
    assert.equal(options.headers?.Authorization, undefined);
    const key = url.pathname.slice('/knowledge-hub-starter/'.length);
    const body = publicFiles[key];
    return body === undefined ? new Response('missing',{status:404}) : body instanceof Response ? body : new Response(body);
  };
  return {calls, restore(){globalThis.fetch=saved;}};
}

test('missing identity, incorrect audience and spoofed headers deny every resource before fetching', async () => {
  const mock=mockFetch();
  try {
    for (const path of ['/', '/app.js', '/data/calendar.json',
      '/data/days/2026-11-09.json','/data/entries/2026-11-09-secret.json']) {
      const forged=new Request('https://private-hub.example.test'+path, {
        headers:{'Cf-Access-Authenticated-User-Email':'owner@example.test',
          'Cf-Access-Jwt-Assertion':'unverified-claim'},
      });
      for (const ctx of [{},identity('stranger@example.test'), identity('owner@example.test','wrong-audience'),
        {access:{aud:env.ACCESS_AUD,getIdentity:async()=>{throw Error('no identity');}}}]) {
        assert.equal((await worker.fetch(forged,env,ctx)).status,403,path);
      }
    }
    assert.deepEqual(mock.calls,[]);
  } finally {mock.restore();}
});
test('misconfiguration fails closed, including wildcard or empty allowlists',async()=>{
  const mock=mockFetch();
  try {
    for (const changed of [{}, {...env,GITHUB_READ_TOKEN:''}, {...env,ALLOWED_EMAILS:'*'},
      {...env,ALLOWED_EMAILS:''}, {...env,ACCESS_AUD:''}]) {
      const res=await worker.fetch(request('/'),changed,identity());
      assert.equal(res.status,503);
      assert.match(res.headers.get('cache-control'),/no-store/);
    }
    assert.equal(configured({...env,ALLOWED_EMAILS:'bad-domain'}),null);
    assert.deepEqual(mock.calls,[]);
  } finally {mock.restore();}
});
test('authorized public UI stays behind Access and no private data is requested from Pages',async()=>{
  const mock=mockFetch();
  try {
    for (const path of ['/','/app.js','/style.css','/manifest.webmanifest','/apple-touch-icon.png']) {
      const res=await worker.fetch(request(path),env,identity('OWNER@example.test'));
      assert.equal(res.status,200,path);
      assert.equal(res.headers.get('cache-control'),'private, no-store, max-age=0');
      assert.equal(res.headers.get('access-control-allow-origin'),null);
      assert.match(res.headers.get('content-security-policy'),/connect-src 'self'/);
    }
    assert.equal((await worker.fetch(request('/sw.js'),env,identity())).status,404);
    assert.ok(mock.calls.every(s=>s.startsWith('https://tempuku.github.io/knowledge-hub-starter/')));
    assert.ok(mock.calls.every(s=>!s.includes('/data/')));
  } finally {mock.restore();}
});
test('private API only reads exact generated JSON from a different private repository',async()=>{
  const mock=mockFetch();
  try {
    const requested=['/data/calendar.json','/data/days/2026-11-09.json',
      '/data/days/2026-11-09/1.json','/data/entries/2026-11-09-secret.json'];
    for (const path of requested) {
      const res=await worker.fetch(request(path),env,identity());
      assert.equal(res.status,200,path);
      assert.match(res.headers.get('content-type'),/application\/json/);
      await res.json();
    }
    const privateText=await (await worker.fetch(request(requested[3]),env,identity())).text();
    assert.ok(privateText.includes('Personal private content'));
    assert.ok(mock.calls.every(s=>s.startsWith('https://api.github.com/repos/tempuku/knowledge-hub-data/contents/site-data/data/')));
    const res=await worker.fetch(request('/data/calendar.json','HEAD'),env,identity());
    assert.equal(res.status,200);
    assert.equal(await res.text(),'');
  } finally {mock.restore();}
});
test('unknown paths, query strings, encoded traversal, source Markdown and writes are rejected',async()=>{
  const mock=mockFetch();
  try {
    for (const path of ['/openwiki/journal/2026/11/09/private.md','/data/../../secrets',
      '/data/entries/secret.json','/data/calendar.json?token=x','/data/%2e%2e/secret',
      '/data/days/2026-11-09/0.json','/data/days/2026-11-09/10000.json',
      '/favicon.ico','/.git/config','/data/days/2026-11-09.json?x=1']) {
      assert.equal((await worker.fetch(request(path),env,identity())).status,404,path);
    }
    for (const method of ['POST','PUT','PATCH','DELETE']) {
      assert.equal((await worker.fetch(request('/data/calendar.json',method),env,identity())).status,405);
    }
    assert.deepEqual(mock.calls,[]);
  } finally {mock.restore();}
});
test('private 404, API HTML, upstream redirect and oversized data never fall back to public',async()=>{
  const cases=[
    {privateFiles:{'site-data/data/calendar.json':new Response('missing',{status:404})}},
    {privateFiles:{'site-data/data/calendar.json':'<html>error</html>'}},
    {privateFiles:{'site-data/data/calendar.json':new Response('redirect',{status:302,headers:{Location:'https://example.test'}})}},
    {privateFiles:{'site-data/data/calendar.json':new Response('large',{status:200,headers:{'content-length':String(2*1024*1024)}})}},
  ];
  for (const override of cases) {
    const mock=mockFetch(override);
    try {
      const res=await worker.fetch(request('/data/calendar.json'),env,identity());
      assert.equal(res.status,502);
      const text=await res.text();
      assert.ok(!text.includes(env.GITHUB_READ_TOKEN));
      assert.ok(!text.includes('api.github.com'));
      assert.ok(!text.includes('knowledge-hub-data'));
      assert.equal(mock.calls.length,1);
      assert.ok(mock.calls[0].startsWith('https://api.github.com/'));
    } finally {mock.restore();}
  }
});
test('source and route allowlists reject arbitrary repository paths',()=>{
  assert.deepEqual(route('/data/calendar.json'),{
    kind:'private',path:'site-data/data/calendar.json',mime:'application/json; charset=utf-8'});
  assert.equal(route('/api/secrets'),null);
  assert.equal(route('/sw.js'),null);
  assert.equal(sourcePath('site-data/data/calendar.json'),'site-data/data/calendar.json');
  for (const unsafe of ['../thing','a//b','a/./b','/root','a\\b','https://bad.test','x%2f','']) {
    assert.throws(()=>sourcePath(unsafe));
  }
});
