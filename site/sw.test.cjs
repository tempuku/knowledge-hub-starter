'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function worker() {
  const handlers = {}, writes = [], network = [];
  vm.runInNewContext(fs.readFileSync(__dirname + '/sw.js', 'utf8'), {
    URL,
    self: {location: {origin: 'https://example.test'},
      registration: {scope: 'https://example.test/hub/'},
      addEventListener(name, handler) { handlers[name] = handler; }},
    fetch: async request => { network.push(request.url); return {ok: true, clone() { return this; }}; },
    caches: {open: async () => ({put: async request => writes.push(request.url)})}
  });
  return {handlers, writes, network};
}

for (const [path, cache] of [
  ['data/manifest.json', 'default'],
  ['data/g/' + 'a'.repeat(64) + '/records/one.json', 'default'],
  ['manifest.json', 'default'],
  ['g/' + 'a'.repeat(64) + '/events/one.json', 'default'],
  ['any-private-endpoint.json', 'no-store']
]) {
  test('legacy worker does not intercept native/private request: ' + path, () => {
    const instance = worker();
    let intercepted = false;
    instance.handlers.fetch({request: {method: 'GET', url: 'https://example.test/hub/' + path, cache},
      respondWith() { intercepted = true; }, waitUntil() {}});
    assert.equal(intercepted, false);
    assert.deepEqual(instance.network, []);
    assert.deepEqual(instance.writes, []);
  });
}

test('legacy public shell retains network-first caching', async () => {
  const instance = worker(), pending = [];
  let response;
  const url = 'https://example.test/hub/style.css';
  instance.handlers.fetch({request: {method: 'GET', url, cache: 'default'},
    respondWith(promise) { response = promise; }, waitUntil(promise) { pending.push(promise); }});
  await response;
  await Promise.all(pending);
  assert.deepEqual(instance.network, [url]);
  assert.deepEqual(instance.writes, [url]);
});
