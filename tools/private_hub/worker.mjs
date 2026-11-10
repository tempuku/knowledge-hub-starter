/**
 * Knowledge Hub private read-only gateway (Phase 1). This is a DIRECT Worker:
 * no Static Assets binding, no public/private data fallback, no browser token.
 *
 * The existing GitHub Pages app is public and supplies ONLY UI assets.
 * Private JSON is fetched from a SEPARATE private GitHub repository.
 * Every route requires verified Cloudflare Access identity + exact audience
 * + an explicit email allowlist, including HTML, icons and errors.
 *
 * Does not create a private repo, deploy, or implement Git-backed editing.
 */
const PRIVATE_REPO = 'tempuku/knowledge-hub-data';
const PRIVATE_REF = 'main';
const PUBLIC_APP = 'https://tempuku.github.io/knowledge-hub-starter';
const MAX_BYTES = 1024 * 1024;
const TEXT_ASSETS = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/style.css', ['style.css', 'text/css; charset=utf-8']],
  ['/manifest.webmanifest', ['manifest.webmanifest', 'application/manifest+json']],
  ['/apple-touch-icon.png', ['apple-touch-icon.png', 'image/png']],
  ['/icon-192.png', ['icon-192.png', 'image/png']],
  ['/icon-512.png', ['icon-512.png', 'image/png']],
]);
// Deliberately DO NOT serve /sw.js. A network-first service worker could
// retain the user's private diary in Cache Storage on an old iPad.
const SECURITY = Object.freeze({
  'Cache-Control': 'private, no-store, max-age=0',
  'Pragma': 'no-cache',
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'none'",
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
});

function response(body, status=200, mime='text/plain; charset=utf-8', head=false) {
  return new Response(head ? null : body, {
    status, headers: {...SECURITY, 'Content-Type': mime},
  });
}
function configured(env) {
  if (!env || typeof env.ACCESS_AUD !== 'string' || !env.ACCESS_AUD.trim() ||
      typeof env.GITHUB_READ_TOKEN !== 'string' || !env.GITHUB_READ_TOKEN.trim() ||
      typeof env.ALLOWED_EMAILS !== 'string') return null;
  const addresses = env.ALLOWED_EMAILS.split(',').map(v => v.trim().toLowerCase());
  if (!addresses.length || addresses.some(e => !/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(e))) return null;
  return new Set(addresses);
}
async function authorized(env, ctx, allowlist) {
  // ctx.access is provided by an Access-protected DIRECT Worker invocation.
  // Never trust Cf-Access-* request headers from the browser.
  if (!ctx?.access || ctx.access.aud !== env.ACCESS_AUD ||
      typeof ctx.access.getIdentity !== 'function') return false;
  try {
    const user = await ctx.access.getIdentity();
    const email = typeof user?.email === 'string' ? user.email.trim().toLowerCase() : '';
    return allowlist.has(email);
  } catch (_) { return false; }
}
function sourcePath(path) {
  if (typeof path !== 'string' || path.length > 200 || path.length === 0 ||
      /[\\:%?#\x00-\x1f\x7f]/.test(path) ||
      path.startsWith('/') ||
      path.split('/').some(x => !x || x === '.' || x === '..')) {
    throw new Error('Invalid source path');
  }
  return path.split('/').map(encodeURIComponent).join('/');
}
function route(path) {
  if (TEXT_ASSETS.has(path)) {
    const [name, mime] = TEXT_ASSETS.get(path);
    return {kind:'public', path:name, mime};
  }
  if (path === '/data/calendar.json') return {kind:'private', path:'site-data/data/calendar.json', mime:'application/json; charset=utf-8'};
  const date = /^\/data\/days\/(\d{4}-\d{2}-\d{2})\.json$/.exec(path);
  if (date) return {kind:'private', path:'site-data/data/days/' + date[1] + '.json', mime:'application/json; charset=utf-8'};
  const page = /^\/data\/days\/(\d{4}-\d{2}-\d{2})\/([1-9]\d{0,3})\.json$/.exec(path);
  if (page) return {kind:'private', path:'site-data/data/days/' + page[1] + '/' + page[2] + '.json', mime:'application/json; charset=utf-8'};
  const entry = /^\/data\/entries\/(\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]{0,100})\.json$/.exec(path);
  if (entry) return {kind:'private', path:'site-data/data/entries/' + entry[1] + '.json', mime:'application/json; charset=utf-8'};
  return null;
}
async function bounded(res, maxBytes=MAX_BYTES) {
  const n = res.headers.get('content-length');
  if (n !== null && (!/^\d+$/.test(n) || Number(n) > maxBytes)) throw Error('Unexpected response size');
  if (!res.body) return new Uint8Array();
  const reader = res.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) throw Error('Unexpected response size');
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const result = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
  return result;
}
async function fromPublicPages(path) {
  // Public UI only. Never fetch or fall back to public /data/ endpoints.
  const url = PUBLIC_APP + '/' + sourcePath(path);
  const upstream = await fetch(url, {method:'GET', redirect:'manual'});
  if (upstream.status !== 200 || upstream.redirected) throw Error('Public app source unavailable');
  return bounded(upstream);
}
async function fromPrivateRepo(env, path) {
  const api = 'https://api.github.com/repos/' + PRIVATE_REPO + '/contents/' + sourcePath(path) + '?ref=' + PRIVATE_REF;
  const upstream = await fetch(api, {
    method:'GET', redirect:'manual',
    headers:{
      'Authorization':'Bearer ' + env.GITHUB_READ_TOKEN,
      'Accept':'application/vnd.github.raw+json',
      'X-GitHub-Api-Version':'2022-11-28',
      'User-Agent':'knowledge-hub-private-gateway',
    },
  });
  if (upstream.status !== 200 || upstream.redirected) throw Error('Private source unavailable');
  const raw = await bounded(upstream);
  // Refuse HTML/GitHub API errors masquerading as diary JSON.
  JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(raw));
  return raw;
}
export default {
  async fetch(request, env, ctx) {
    const head = request.method === 'HEAD';
    const allowed = configured(env);
    if (!allowed) return response('Private Knowledge Hub is not configured', 503, undefined, head);
    if (!(await authorized(env, ctx, allowed))) return response('Access required', 403, undefined, head);
    if (request.method !== 'GET' && !head) return response('Read-only gateway', 405);
    try {
      const url = new URL(request.url);
      if (url.search || url.pathname.includes('%') || url.pathname.includes('\\'))
        return response('Not found', 404, undefined, head);
      const selected = route(url.pathname);
      if (!selected) return response('Not found', 404, undefined, head);
      const body = selected.kind === 'public'
        ? await fromPublicPages(selected.path)
        : await fromPrivateRepo(env, selected.path);
      return response(body, 200, selected.mime, head);
    } catch (_) {
      // No GitHub URL, private record body, token or raw upstream message.
      return response('Private resource unavailable', 502, undefined, head);
    }
  },
};
export {configured, sourcePath, route};
