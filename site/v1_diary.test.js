'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {dedupeEventsByRecord} = require('./v1_diary.js');

function event(recordId, recordedAt, sequence, extra) {
  return Object.assign({id: recordId + '-' + sequence, record_id: recordId, recorded_at: recordedAt, sequence}, extra || {});
}

test('status filter keeps the latest revision per record', () => {
  const routingNew = event('routing', '2026-11-21T18:00:00Z', 4, {title: 'Archon routing stack — public status'});
  const clothing = event('clothing', '2026-11-21T12:00:00Z', 2, {title: 'Идеи в одежде'});
  const routingOld = event('routing', '2026-11-21T09:00:00Z', 3, {title: 'Archon routing stack — public status'});
  const result = dedupeEventsByRecord([routingOld, clothing, routingNew]);
  assert.deepEqual(result.map(item => item.id), [routingNew.id, clothing.id]);
  assert.equal(result.length, 2, 'two records must render as two rows');
});

test('dedupe compares event times instead of input order', () => {
  const older = event('one', '2026-11-20T23:00:00Z', 1);
  const newer = event('one', '2026-11-21T01:00:00Z', 2);
  assert.deepEqual(dedupeEventsByRecord([older, newer]).map(item => item.id), [newer.id]);
  assert.deepEqual(dedupeEventsByRecord([newer, older]).map(item => item.id), [newer.id]);
});

test('dedupe leaves events without a record id untouched', () => {
  const first = {id: 'legacy-1', recorded_at: '2026-11-21T10:00:00Z'};
  const second = {id: 'legacy-2', recorded_at: '2026-11-21T09:00:00Z'};
  assert.deepEqual(dedupeEventsByRecord([first, second]).map(item => item.id), ['legacy-1', 'legacy-2']);
});

test('dedupe does not mutate its input', () => {
  const input = [event('one', '2026-11-20T00:00:00Z', 1), event('one', '2026-11-21T00:00:00Z', 2)];
  const copy = input.slice();
  dedupeEventsByRecord(input);
  assert.deepEqual(input, copy);
});
