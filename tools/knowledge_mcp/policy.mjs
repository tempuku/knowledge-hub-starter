import { createHash } from 'node:crypto';

const ENTRY_PATH = /^openwiki\/journal\/(\d{4})\/(\d{2})\/(\d{2})\/([a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?)\.md$/;
const ALLOWED_CAPTURE = new Set(['title', 'description', 'occurred_on', 'body', 'project', 'tags', 'source_urls', 'idempotency_key']);
const ALLOWED_EDIT = new Set(['path', 'expected_sha', 'replacement_body', 'reason', 'idempotency_key']);
const MAX_BODY = 12000;

export function requireObject(value, allowed) {
  if (!value || Array.isArray(value) || typeof value !== 'object') throw Error('INVALID_ARGUMENTS');
  for (const key of Object.keys(value)) if (!allowed.has(key)) throw Error('UNKNOWN_FIELD: ' + key);
}
function string(value, key, max, min = 1) {
  if (typeof value !== 'string' || value.trim().length < min ||
      value.length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value))
    throw Error('INVALID_' + key.toUpperCase());
  return value.trim();
}
function textBody(value, key = 'body') {
  const body = string(value, key, MAX_BODY, 5);
  // Generated diary JSON is consumed by multiple UI clients. Do not admit raw
  // HTML or scriptable URLs into a stored draft even on a private origin.
  if (body.includes('<') || /(?:javascript|vbscript|data)\s*:/i.test(body))
    throw Error('UNSAFE_MARKDOWN');
  return body;
}
export function checkedDate(value) {
  const day = string(value, 'occurred_on', 10, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) ||
      !Number.isFinite(Date.parse(day + 'T00:00:00Z')) ||
      new Date(day + 'T00:00:00Z').toISOString().slice(0, 10) !== day)
    throw Error('INVALID_OCCURED_ON');
  return day;
}
export function checkedPath(path) {
  if (typeof path !== 'string' || path.length > 180 || path.includes('%') ||
      path.includes('\\') || !ENTRY_PATH.test(path)) throw Error('INVALID_PATH');
  const match = ENTRY_PATH.exec(path);
  const day = match[1] + '-' + match[2] + '-' + match[3];
  checkedDate(day);
  if (match[4] === 'index' || match[4] === 'log') throw Error('RESERVED_PATH');
  return { path, day, slug: match[4] };
}
function keyHash(key, action) {
  const id = string(key, 'idempotency_key', 128, 16);
  if (!/^[a-zA-Z0-9_.:-]+$/.test(id)) throw Error('INVALID_IDEMPOTENCY_KEY');
  return createHash('sha256').update(action + ':' + id).digest('hex').slice(0, 14);
}
function slugFor(title) {
  return title.normalize('NFKD').toLowerCase().replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48)
    .replace(/-+$/g, '') || 'entry';
}
function yaml(value) { return JSON.stringify(value); }
function validatedSources(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 6) throw Error('SOURCES_REQUIRED');
  const sources = [];
  for (const item of value) {
    const s = string(item, 'source_url', 500);
    let u;
    try { u = new URL(s); } catch { throw Error('INVALID_SOURCE_URL'); }
    if (u.protocol !== 'https:' || u.username || u.password || !u.hostname || u.hash.length > 120)
      throw Error('INVALID_SOURCE_URL');
    sources.push(s);
  }
  if (new Set(sources).size !== sources.length) throw Error('DUPLICATE_SOURCE_URL');
  return sources;
}
export function validateCapture(value) {
  requireObject(value, ALLOWED_CAPTURE);
  const title = string(value.title, 'title', 120, 3);
  const description = string(value.description, 'description', 350, 3);
  const occurred_on = checkedDate(value.occurred_on);
  const body = textBody(value.body);
  const sources = validatedSources(value.source_urls);
  const hash = keyHash(value.idempotency_key, 'capture');
  const slug = slugFor(title) + '-' + hash.slice(0, 10);
  const path = 'openwiki/journal/' + occurred_on.replaceAll('-', '/') + '/' + slug + '.md';
  checkedPath(path);
  let project = '';
  if (value.project !== undefined && value.project !== '') {
    project = string(value.project, 'project', 60);
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(project)) throw Error('INVALID_PROJECT');
  }
  const tags = value.tags === undefined ? [] : value.tags;
  if (!Array.isArray(tags) || tags.length > 8 || new Set(tags).size !== tags.length ||
      tags.some(tag => typeof tag !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(tag) || tag.length > 40))
    throw Error('INVALID_TAGS');
  const header = [
    '---', 'type: diary-entry', 'title: ' + yaml(title),
    'description: ' + yaml(description),
    'occurred_on: ' + yaml(occurred_on),
    ...(project ? ['project: ' + yaml(project)] : []),
    'tags: ' + JSON.stringify(tags), 'status: draft',
    'visibility: private', 'sources:',
    ...sources.map(resource => '  - resource: ' + yaml(resource)),
    '---', '', '# ' + title, '', body, ''
  ].join('\n');
  return {title, occurred_on, path, content:header, branch:'mcp/capture-' + hash};
}
export function validateEdit(value) {
  requireObject(value, ALLOWED_EDIT);
  const {path, day} = checkedPath(value.path);
  const expected_sha = string(value.expected_sha, 'expected_sha', 40, 40);
  if (!/^[0-9a-f]{40}$/.test(expected_sha)) throw Error('INVALID_EXPECTED_SHA');
  const replacement_body = textBody(value.replacement_body, 'replacement_body');
  const reason = string(value.reason, 'reason', 500, 10);
  return {path, day, expected_sha, replacement_body, reason,
    branch:'mcp/edit-' + keyHash(value.idempotency_key, 'edit')};
}
export function replaceBody(existing, edit) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n[\s\S]*$/.exec(existing);
  if (!match) throw Error('INVALID_EXISTING_FRONTMATTER');
  const fm = match[1];
  if (!/^type:\s*['"]?diary-entry['"]?\s*$/m.test(fm) ||
      !/^visibility:\s*['"]?private['"]?\s*$/m.test(fm))
    throw Error('NOT_PRIVATE_DIARY');
  const dateMatch = /^occurred_on:\s*['"]?(\d{4}-\d{2}-\d{2})['"]?\s*$/m.exec(fm);
  if (!dateMatch || dateMatch[1] !== edit.day) throw Error('DATE_MISMATCH');
  // Preserve the complete frontmatter, including original occurrence date,
  // sources and status. A content-only proposal cannot silently change it.
  return '---\n' + fm + '\n---\n\n' + edit.replacement_body + '\n';
}
function addIndexEntry(existing, heading, label, target) {
  const line = '* [' + label.replace(/[\[\]\r\n]/g, '') + '](' + target + ')';
  if (existing === null) return '# ' + heading + '\n\n' + line + '\n';
  if (!/^# .+\n/.test(existing)) throw Error('INVALID_INDEX');
  const lines = existing.split(/\r?\n/);
  if (lines.some(v => /^\s*[*-] \[[^\]]+\]\(([^)]+)\)/.test(v) &&
      /^\s*[*-] \[[^\]]+\]\(([^)]+)\)/.exec(v)[1] === target)) throw Error('INDEX_TARGET_EXISTS');
  return existing.replace(/\s*$/, '') + '\n' + line + '\n';
}
export function indexPlan(day, title, slug, indexes) {
  const [year, month, date] = day.split('-');
  const monthName = new Intl.DateTimeFormat('en', {month:'long', timeZone:'UTC'}).format(
    new Date(day + 'T00:00:00Z'));
  const specs = [
    ['openwiki/journal/index.md', 'Diary by year', year, year + '/'],
    ['openwiki/journal/' + year + '/index.md', year + ' diary', monthName, month + '/'],
    ['openwiki/journal/' + year + '/' + month + '/index.md', monthName + ' ' + year + ' diary', monthName + ' ' + Number(date), date + '/'],
    ['openwiki/journal/' + year + '/' + month + '/' + date + '/index.md', day + ' — diary records', title, slug + '.md']
  ];
  const changes = {};
  for (const [path, heading, label, target] of specs) {
    const current = indexes[path] ?? null;
    if (current !== null && current.split(/\r?\n/).some(line =>
      /^\s*[*-] \[[^\]]+\]\(([^)]+)\)/.test(line) &&
      /^\s*[*-] \[[^\]]+\]\(([^)]+)\)/.exec(line)[1] === target)) continue;
    changes[path] = addIndexEntry(current, heading, label, target);
  }
  return changes;
}
