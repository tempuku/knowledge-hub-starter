import {checkedPath, validateCapture, validateEdit, replaceBody, indexPlan} from './policy.mjs';

const REPO = 'tempuku/knowledge-hub-data';
const API = 'https://api.github.com/repos/' + REPO + '/';
const BASE = 'main';
const MAX_JSON = 300000;
const MAX_FILE = 65536;

function routePath(path) {
  return path.split('/').map(encodeURIComponent).join('/');
}
function assertConfigured(env, write = false) {
  if (typeof env.KNOWLEDGE_GITHUB_TOKEN !== 'string' ||
      env.KNOWLEDGE_GITHUB_TOKEN.length < 20) throw Error('TOKEN_REQUIRED');
  if (write && env.KNOWLEDGE_ENABLE_WRITE !== 'review-only') throw Error('WRITES_DISABLED');
}
export function createGateway(env = process.env, fetchImpl = globalThis.fetch) {
  async function request(path, method = 'GET', body = undefined, absent = false) {
    const response = await fetchImpl(API + path, {
      method, redirect:'manual', signal:AbortSignal.timeout(15000),
      headers:{
        'Authorization':'Bearer ' + env.KNOWLEDGE_GITHUB_TOKEN,
        'Accept':'application/vnd.github+json',
        'Content-Type':'application/json',
        'X-GitHub-Api-Version':'2022-11-28',
        'User-Agent':'knowledge-hub-strict-mcp'
      },
      ...(body === undefined ? {} : {body:JSON.stringify(body)})
    });
    if (response.status === 404 && absent) return null;
    if (response.status < 200 || response.status >= 300 || response.redirected)
      throw Error('GITHUB_REQUEST_FAILED_' + response.status);
    const raw = await response.text();
    if (raw.length > MAX_JSON) throw Error('RESPONSE_TOO_LARGE');
    try { return JSON.parse(raw); } catch { throw Error('BAD_GITHUB_RESPONSE'); }
  }
  async function requirePrivate(write = false) {
    assertConfigured(env, write);
    const repo = await request('');
    // Public Git and private-frontmatter labels do not provide confidentiality.
    if (repo.full_name !== REPO || repo.private !== true || repo.archived === true)
      throw Error('PRIVATE_REPOSITORY_REQUIRED');
  }
  async function file(path, ref = BASE) {
    const json = await request('contents/' + routePath(path) + '?ref=' + encodeURIComponent(ref), 'GET', undefined, true);
    if (json === null) return null;
    if (json.type !== 'file' || json.encoding !== 'base64' ||
        typeof json.content !== 'string' || !/^[0-9a-f]{40}$/.test(json.sha))
      throw Error('INVALID_GITHUB_FILE');
    const bytes = Buffer.from(json.content.replace(/\s/g, ''), 'base64');
    if (bytes.length > MAX_FILE) throw Error('FILE_TOO_LARGE');
    const content = new TextDecoder('utf-8', {fatal:true}).decode(bytes);
    return {content, sha:json.sha};
  }
  async function reference(branch) {
    return request('git/ref/heads/' + branch, 'GET', undefined, true);
  }
  async function ensurePull(branch, title, description) {
    const pulls = await request('pulls?state=open&head=tempuku:' + encodeURIComponent(branch));
    if (!Array.isArray(pulls)) throw Error('INVALID_PULL_LIST');
    if (pulls.length) return {url:pulls[0].html_url, number:pulls[0].number, reused:true};
    const pr = await request('pulls', 'POST', {
      title, body:description, head:branch, base:BASE,
      draft:true, maintainer_can_modify:false
    });
    return {url:pr.html_url, number:pr.number, reused:false};
  }
  async function propose(change) {
    await requirePrivate(true);
    const oldBranch = await reference(change.branch);
    if (oldBranch) {
      const existing = await file(change.path, change.branch);
      if (!existing || existing.content !== change.content)
        throw Error('IDEMPOTENCY_KEY_CONFLICT');
      const pr = await ensurePull(change.branch, change.title, change.description);
      return {status:'existing_proposal', ...pr, path:change.path, branch:change.branch};
    }
    const mainRef = await reference(BASE);
    const mainSha = mainRef?.object?.sha;
    if (!/^[0-9a-f]{40}$/.test(mainSha || '')) throw Error('INVALID_BASE_REF');
    const mainFile = await file(change.path);
    if (change.kind === 'capture' && mainFile) throw Error('RECORD_ALREADY_EXISTS');
    if (change.kind === 'edit' && (!mainFile || mainFile.sha !== change.expected_sha))
      throw Error('STALE_OR_MISSING_RECORD');

    const changes = {[change.path]:change.content};
    if (change.kind === 'capture') {
      const root = await file('openwiki/index.md');
      if (!root || !/\]\(journal\/\)/.test(root.content))
        throw Error('PRIVATE_OKF_BUNDLE_NOT_INITIALIZED');
      const daydir = change.path.slice(0, change.path.lastIndexOf('/'));
      const year = change.day.slice(0,4);
      const month = change.day.slice(5,7);
      const indexPaths = [
        'openwiki/journal/index.md',
        'openwiki/journal/' + year + '/index.md',
        'openwiki/journal/' + year + '/' + month + '/index.md',
        daydir + '/index.md'
      ];
      const indexes = {};
      for (const indexPath of indexPaths) {
        const found = await file(indexPath);
        indexes[indexPath] = found?.content ?? null;
      }
      Object.assign(changes, indexPlan(change.day, change.title, change.slug, indexes));
    }
    // A single immutable tree/commit holds the record and all indexes.
    const headCommit = await request('git/commits/' + mainSha);
    if (!/^[0-9a-f]{40}$/.test(headCommit?.tree?.sha || '')) throw Error('INVALID_BASE_COMMIT');
    const tree = await request('git/trees', 'POST', {
      base_tree:headCommit.tree.sha,
      tree:Object.entries(changes).map(([path, content]) =>
        ({path, mode:'100644', type:'blob', content}))
    });
    const commit = await request('git/commits', 'POST', {
      message:change.title, tree:tree.sha, parents:[mainSha]
    });
    await request('git/refs', 'POST', {
      ref:'refs/heads/' + change.branch, sha:commit.sha
    });
    const pr = await ensurePull(change.branch, change.title, change.description);
    return {status:'draft_pr_created', ...pr, path:change.path, branch:change.branch};
  }
  return {
    async read(args) {
      if (!args || Object.keys(args).sort().join() !== 'path') throw Error('INVALID_ARGUMENTS');
      checkedPath(args.path);
      await requirePrivate();
      const result = await file(args.path);
      if (!result) throw Error('NOT_FOUND');
      return {path:args.path, sha:result.sha, content:result.content};
    },
    async search(args) {
      if (!args || Object.keys(args).sort().join() !== 'query' ||
          typeof args.query !== 'string' || !/^[a-zA-Z0-9 -]{2,50}$/.test(args.query))
        throw Error('INVALID_QUERY');
      await requirePrivate();
      const tree = await request('git/trees/' + BASE + '?recursive=1');
      if (tree.truncated || !Array.isArray(tree.tree) || tree.tree.length > 50000)
        throw Error('SEARCH_INDEX_UNAVAILABLE');
      const query = args.query.toLowerCase();
      return {paths:tree.tree.filter(item => item.type === 'blob' &&
        typeof item.path === 'string' &&
        item.path.toLowerCase().includes(query) &&
        (() => { try { checkedPath(item.path); return true; } catch { return false; } })()
      ).slice(0, 25).map(item => item.path)};
    },
    validate(args) {
      const record = validateCapture(args);
      return {valid:true, path:record.path, status:'draft', visibility:'private',
        review_required:true};
    },
    async capture(args) {
      const record = validateCapture(args);
      const slug = checkedPath(record.path).slug;
      return propose({kind:'capture', ...record, day:record.occurred_on, slug,
        title:'knowledge: capture ' + record.title,
        description:'Strict MCP diary capture.\n\nPrivate data only; draft status; human PR review required.\nNo automatic merge or public publication.'});
    },
    async edit(args) {
      const edit = validateEdit(args);
      await requirePrivate(true);
      const old = await file(edit.path);
      if (!old || old.sha !== edit.expected_sha) throw Error('STALE_OR_MISSING_RECORD');
      const content = replaceBody(old.content, edit);
      return propose({...edit, content, kind:'edit',
        title:'knowledge: propose diary revision',
        description:'Strict MCP body-only edit; review required.\n\nReason: ' + edit.reason +
          '\n\nExpected blob SHA: ' + edit.expected_sha + '\n\nNo automatic merge or public publication.'});
    }
  };
}
