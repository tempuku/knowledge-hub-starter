import readline from 'node:readline';
import {createGateway} from './github.mjs';

const gateway = createGateway();
const captureProperties = {
  title:{type:'string', minLength:3, maxLength:120},
  description:{type:'string', minLength:3, maxLength:350},
  occurred_on:{type:'string', pattern:'^\\d{4}-\\d{2}-\\d{2}$'},
  body:{type:'string', minLength:5, maxLength:12000},
  project:{type:'string', maxLength:60},
  tags:{type:'array', maxItems:8, items:{type:'string'}},
  source_urls:{type:'array', minItems:1, maxItems:6, items:{type:'string', pattern:'^https://', maxLength:500}},
  idempotency_key:{type:'string', minLength:16, maxLength:128}
};
const pathProperty = {type:'string', pattern:'^openwiki/journal/', maxLength:180};
const tools = [
  {name:'knowledge_search',
   description:'Find diary paths in the authenticated private OKF repository; no public data.',
   inputSchema:{type:'object', additionalProperties:false, required:['query'],
     properties:{query:{type:'string', minLength:2, maxLength:50}}},
   annotations:{readOnlyHint:true}},
  {name:'knowledge_read',
   description:'Read one date-partitioned private diary record, including its Git blob SHA.',
   inputSchema:{type:'object', additionalProperties:false, required:['path'],
     properties:{path:pathProperty}},
   annotations:{readOnlyHint:true}},
  {name:'knowledge_validate',
   description:'Validate a private draft diary capture locally; never writes.',
   inputSchema:{type:'object', additionalProperties:false,
     required:['title','description','occurred_on','body','source_urls','idempotency_key'],
     properties:captureProperties},
   annotations:{readOnlyHint:true}},
  {name:'knowledge_capture',
   description:'Create a private draft note atomically on private main only when direct-capture policy is enabled; otherwise create draft PR when review-only is enabled. Never publishes to public Git.',
   inputSchema:{type:'object', additionalProperties:false,
     required:['title','description','occurred_on','body','source_urls','idempotency_key'],
     properties:captureProperties},
   annotations:{readOnlyHint:false, destructiveHint:false, idempotentHint:true}},
  {name:'knowledge_propose_edit',
   description:'Propose body-only revision at an expected Git blob SHA, always in a draft PR; never changes frontmatter.',
   inputSchema:{type:'object', additionalProperties:false,
     required:['path','expected_sha','replacement_body','reason','idempotency_key'],
     properties:{
       path:pathProperty, expected_sha:{type:'string', pattern:'^[a-f0-9]{40}$'},
       replacement_body:{type:'string', minLength:5, maxLength:12000},
       reason:{type:'string', minLength:10, maxLength:500},
       idempotency_key:{type:'string', minLength:16, maxLength:128}
     }},
   annotations:{readOnlyHint:false, destructiveHint:false, idempotentHint:true}}
];
const calls = new Map([
  ['knowledge_search', value => gateway.search(value)],
  ['knowledge_read', value => gateway.read(value)],
  ['knowledge_validate', value => gateway.validate(value)],
  ['knowledge_capture', value => gateway.capture(value)],
  ['knowledge_propose_edit', value => gateway.edit(value)]
]);
let initialized = false;
function send(packet) { process.stdout.write(JSON.stringify(packet) + '\n'); }
function error(id, code, message) { send({jsonrpc:'2.0', id, error:{code, message}}); }

async function handle(line) {
  if (line.length > 100000) return error(null, -32700, 'Message too large');
  let request;
  try { request = JSON.parse(line); }
  catch { return error(null, -32700, 'Parse error'); }
  if (!request || Array.isArray(request) || request.jsonrpc !== '2.0' ||
      typeof request.method !== 'string' || (Object.hasOwn(request, 'id') &&
      typeof request.id !== 'number' && typeof request.id !== 'string'))
    return error(request?.id ?? null, -32600, 'Invalid request');
  if (!Object.hasOwn(request, 'id')) {
    if (request.method === 'notifications/initialized') initialized = true;
    return;
  }
  const id = request.id;
  try {
    let result;
    if (request.method === 'initialize') {
      const offered = request.params?.protocolVersion;
      const supported = ['2025-06-18','2025-03-26'];
      result = {
        protocolVersion:supported.includes(offered) ? offered : '2025-06-18',
        capabilities:{tools:{listChanged:false}},
        serverInfo:{name:'knowledge-hub-strict', version:'0.1.0'},
        instructions:'Private OKF only. Direct writes are opt-in and restricted to new validated drafts.'
      };
      initialized = true;
    } else if (!initialized) {
      throw Error('NOT_INITIALIZED');
    } else if (request.method === 'ping') {
      result = {};
    } else if (request.method === 'tools/list') {
      result = {tools};
    } else if (request.method === 'tools/call') {
      const name = request.params?.name;
      if (typeof name !== 'string' || !calls.has(name)) return error(id, -32602, 'Unknown tool');
      try {
        const output = await calls.get(name)(request.params?.arguments || {});
        result = {content:[{type:'text', text:JSON.stringify(output)}], isError:false};
      } catch (cause) {
        // Tool errors are protocol-success responses, not raw exception dumps.
        const message = typeof cause?.message === 'string' && /^[A-Z0-9_]+(?:: [a-z_]+)?$/.test(cause.message)
          ? cause.message : 'OPERATION_REJECTED';
        result = {content:[{type:'text', text:message}], isError:true};
      }
    } else {
      return error(id, -32601, 'Method not found');
    }
    send({jsonrpc:'2.0', id, result});
  } catch {
    error(id, -32603, 'Internal error');
  }
}

const input = readline.createInterface({input:process.stdin, crlfDelay:Infinity});
for await (const line of input) await handle(line);
