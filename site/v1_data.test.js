"use strict";
const assert = require("assert");
const data = require("./v1_data.js");

async function run() {
  assert.strictEqual(data.sha256Hex("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assert.deepStrictEqual(data.tokens("Cafe\u0301 CAFÉ 中文 12 a _x foo_bar"), ["café", "中文", "12", "foo", "bar"]);
  assert.deepStrictEqual(data.tokens("a ".repeat(100)), []);
  assert.strictEqual(data.mondayStart("2026-11-15"), "2026-11-09");
  assert.strictEqual(data.shiftMonth("2024-01-31", 1), "2024-02-29");
  assert.strictEqual(data.shiftMonth("2023-03", -1), "2023-02");
  assert.deepStrictEqual(data.monthBounds("2024-02"), {start: "2024-02-01", end: "2024-02-29"});
  assert.strictEqual(data.parseRoute("#/records?q=caf%C3%A9&sort=updated").sort, "updated");
  assert.strictEqual(data.parseRoute("#/records/nope").state, "invalid");
  assert.strictEqual(data.parseRoute("#/missing").state, "not_found");
  assert.strictEqual(data.serializeRoute({route: "records", q: "café", sort: "title"}), "#/records?q=caf%C3%A9");
  assert.strictEqual(data.serializeRoute({route: "diary", date: "2026-11-15", mode: "week"}), "#/diary?date=2026-11-15");

  const genA = "a".repeat(64), genB = "b".repeat(64);
  const manifestA = {schema_version: 1, generation: genA, source_revision: "rev-a", exporter_version: "v1", policy_digest: "private-v1", published_at: "2026-01-01T00:00:00Z", mode: "public", root: "g/" + genA + "/"};
  const manifestB = Object.assign({}, manifestA, {generation: genB, source_revision: "rev-b", root: "g/" + genB + "/"});
  const recA = [
    {id: "123e4567-e89b-42d3-a456-426614174000", title: "A note", type: "note", status: "stable", project_id: "123e4567-e89b-42d3-a456-426614174099", tags: ["one"], area: "notes", updated_at: "2026-01-02T00:00:00Z", detail_bytes: 20},
    {id: "123e4567-e89b-42d3-a456-426614174001", title: "B note", type: "note", status: "draft", project_id: "123e4567-e89b-42d3-a456-426614174099", tags: ["two"], area: "notes/sub", updated_at: "2026-01-03T00:00:00Z", detail_bytes: 20}
  ];
  const eventOne = {id: "123e4567-e89b-42d3-a456-426614174101", record_id: recA[0].id, sequence: 2, action: "update", recorded_at: "2026-01-02T00:00:00Z", project_id: recA[0].project_id, type: "note", status: "stable", tags: ["one"], area: "notes"};
  const eventTwo = {id: "123e4567-e89b-42d3-a456-426614174102", record_id: recA[0].id, sequence: 1, action: "create", recorded_at: "2026-01-01T00:00:00Z", project_id: recA[0].project_id, type: "note", status: "stable", tags: ["one"], area: "notes"};
  let manifest = manifestA, inflight = 0, maxInflight = 0;
  const docs = {};
  function add(gen, path, value) { docs["/data/g/" + gen + "/" + path] = value; }
  docs["/data/manifest.json"] = () => manifest;
  add(genA, "catalog.json", {schema_version: 1, record_count: 2, event_count: 2, projects: [], areas: [], months: []});
  add(genA, "records/catalog/index.json", {schema_version: 1, record_count: 2, pages: [{number: 1, url: "records/catalog/1.json", count: 1}, {number: 2, url: "records/catalog/2.json", count: 1}]});
  add(genA, "records/catalog/1.json", {schema_version: 1, items: [recA[0]], next: 2});
  add(genA, "records/catalog/2.json", {schema_version: 1, items: [recA[1]], next: null});
  add(genA, "days/2026-01-01/index.json", {schema_version: 1, date: "2026-01-01", change_count: 1, record_count: 1, pages: [{number: 1, url: "days/2026-01-01/1.json", count: 1}]});
  add(genA, "days/2026-01-01/1.json", {schema_version: 1, items: [eventTwo], next: null});
  add(genA, "days/2026-01-02/index.json", {schema_version: 1, date: "2026-01-02", change_count: 1, record_count: 1, pages: [{number: 1, url: "days/2026-01-02/1.json", count: 1}]});
  add(genA, "days/2026-01-02/1.json", {schema_version: 1, items: [eventOne], next: null});
  add(genA, "aliases.json", {schema_version: 1, paths: {}, entries: {}});
  const client = data.create({baseUrl: "/data/", mode: "public", fetchImpl: async (url, init) => {
    assert.strictEqual(init.method, "GET");
    inflight += 1; maxInflight = Math.max(maxInflight, inflight);
    await new Promise(resolve => setTimeout(resolve, 2));
    inflight -= 1;
    const parsed = new URL(url, "https://example.test");
    const path = parsed.pathname;
    if (!docs[path]) return {ok: false, status: 404, json: async () => ({})};
    const value = typeof docs[path] === "function" ? docs[path]() : docs[path];
    return {ok: true, status: 200, json: async () => value};
  }});
  assert.strictEqual((await client.loadManifest()).generation, genA);
  assert.strictEqual((await client.catalog()).record_count, 2);
  const all = await client.catalogRecords();
  assert.strictEqual(all.length, 2);
  assert.strictEqual((await client.resolveRecords({area: "notes"})).items.length, 2);
  assert.deepStrictEqual(await client.projectCounts(recA[0].project_id), {draft: 1, in_progress: 0, stable: 1, completed: 0});
  const initial = await client.diaryInitialRange({start: "2026-01-01", end: "2026-01-02"});
  assert.strictEqual(initial.items.length, 2);
  assert.strictEqual(initial.countsExact, false);
  const exact = await client.diaryRange({start: "2026-01-01", end: "2026-01-02"});
  assert.strictEqual(exact.total_changes, 2);
  assert.strictEqual(exact.total_records, 1);
  assert.ok(maxInflight <= 4, "data requests exceed concurrency limit");
  manifest = manifestB;
  assert.strictEqual((await client.loadManifest()).generation, genA, "active generation changed without activation");
  assert.strictEqual(client.status().updateAvailable.generation, genB);
  client.activateGeneration(manifestB);
  assert.strictEqual(client.status().generation, genB);

  const privateClient = data.create({baseUrl: "/data/", mode: "private", fetchImpl: async (_url, init) => {
    assert.strictEqual(init.cache, "no-store", "private fetch did not bypass browser cache");
    return {ok: true, status: 200, json: async () => Object.assign({}, manifestB, {mode: "private"})};
  }});
  await privateClient.loadManifest();

  let cachePuts = 0;
  global.caches = {open: async () => ({match: async () => undefined, put: async () => { cachePuts += 1; }})};
  const wrongMode = data.create({baseUrl: "/data/", mode: "public", fetchImpl: async () => ({
    ok: true, status: 200, json: async () => Object.assign({}, manifestB, {mode: "private"})
  })});
  await assert.rejects(wrongMode.loadManifest(), error => error.code === "mode_mismatch");
  assert.strictEqual(cachePuts, 0, "private manifest was written to public Cache Storage");

  let networkOnline = true;
  const offlineClient = data.create({baseUrl: "/offline/", mode: "public", fetchImpl: async () => {
    if (!networkOnline) throw new Error("offline");
    return {ok: true, status: 200, json: async () => manifestA};
  }});
  await offlineClient.loadManifest();
  networkOnline = false;
  await offlineClient.loadManifest();
  assert.strictEqual(offlineClient.status().offline, true, "saved public generation was not labelled offline");
}

run().then(() => process.stdout.write("v1_data checks passed\n")).catch(error => { console.error(error); process.exitCode = 1; });
