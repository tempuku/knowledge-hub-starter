/* Read-only v1 projection client. Text-only rendering intentionally prevents
   untrusted Markdown, SVG, HTML and script execution. */
(() => {
"use strict";
const app = document.getElementById("app");
let manifest, root, token = 0;
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
};
const link = (label, route) => { const a=el("a",label);a.href="#"+route;return a; };
const heading = (title) => {app.replaceChildren(el("h1",title));};
const get = async (path) => {
  const response = await fetch(path, {cache:"no-cache"});
  if (!response.ok) throw new Error("HTTP "+response.status);
  const value = await response.json();
  if (value.schema_version !== 1) throw new Error("Update required: unsupported schema");
  return value;
};
const data = path => get(root+path);
const panel = (...nodes) => {const p=el("section",undefined,"panel");p.append(...nodes);app.append(p);return p;};
const error = (err) => {
  const p=panel(el("p","Could not load this resource: "+err.message,"error"));
  const b=el("button","Retry");b.onclick=render;p.append(b);
};
const parse = () => {
  const [path, query] = location.hash.slice(1).split("?");
  return {parts:(path||"/diary").split("/").filter(Boolean),params:new URLSearchParams(query||"")};
};
const metadata = async () => {
  manifest=await get("./manifest.json");
  if (manifest.mode !== "public" || !/^g\/[a-f0-9]{64}\/$/.test(manifest.root))
    throw new Error("Public v1 generation unavailable");
  root="./"+manifest.root;
};
const render = async () => {
  const current=++token;
  heading("Loading…");
  try {
    await metadata();
    if(current!==token)return;
    const {parts,params}=parse();
    const route=parts[0]||"diary";
    if(route==="record" && parts[1]){
      const id=parts[1];
      if(!/^[0-9a-f-]{36}$/.test(id))throw new Error("Invalid record ID");
      const meta=await data("records/"+id+".meta.json");
      if(current!==token)return;
      heading(meta.title);
      panel(el("p",meta.description||""),el("small",meta.status+" · "+meta.area));
      if(meta.detail_bytes>262144){
        const b=el("button","Load full content");
        b.onclick=()=>showRecord(id,current);
        panel(b);
      } else await showRecord(id,current);
      panel(link("History","/history/"+id));
    } else if(route==="history" && parts[1]){
      const id=parts[1],history=await data("history/"+id+"/index.json");
      if(current!==token)return;
      heading("History");
      if(!history.event_count)panel(el("p","No published history"));
      for(const page of history.pages){
        const section=panel(el("small","Page "+page.number));
        const b=el("button","Load revisions");
        b.onclick=async()=>{b.disabled=true;try{
          const result=await data(page.url);
          const list=el("ul",undefined,"list");
          for(const e of result.items){const li=el("li");li.append(link((e.title||e.summary||e.id)+" · "+e.recorded_at,"/event/"+e.id));list.append(li);}
          section.append(list);b.remove();
        }catch(e){b.disabled=false;section.append(el("p",e.message,"error"));}};
        section.append(b);
      }
    } else if(route==="event" && parts[1]){
      const id=parts[1],meta=await data("events/"+id+".meta.json");
      if(current!==token)return;
      heading((meta.title||meta.summary||"Event")+" · revision "+meta.sequence);
      panel(el("p",meta.summary),el("small",meta.recorded_at));
      const b=el("button","Load revision and diff");
      const section=panel(b);
      b.onclick=async()=>{b.disabled=true;try{
        const value=await data("events/"+id+".json");
        section.append(el("h2","This revision"),el("pre",value.event.after),
          el("h2","Previous revision"),el("pre",value.event.before||"(creation)"),
          el("h2","Exact diff"),el("pre",value.diff.text||"No changed lines"));
        b.remove();
      }catch(e){b.disabled=false;section.append(el("p",e.message,"error"));}};
    } else if(route==="diary"){
      heading("Diary · UTC");
      const catalog=await data("catalog.json");
      if(current!==token)return;
      for(const month of catalog.months){
        const section=panel(el("h2",month.month),el("p",month.change_count+" changes · "+month.record_count+" records"));
        const year=month.month.slice(0,4),calendar=await data("calendar/"+year+".json");
        if(current!==token)return;
        for(const day of calendar.days.filter(x=>x.date.startsWith(month.month))){
          const b=el("button",day.date+" · "+day.change_count+" changes");
          b.onclick=()=>loadDay(day.date,section);
          section.append(b);
        }
      }
    } else if(["records","projects","today","calendar"].includes(route)){
      await renderCollection(route,params,current);
    } else {
      heading("Not found");
      panel(link("Back to Diary","/diary"));
    }
  } catch(e){if(current===token){heading("Knowledge Hub");error(e);}}
};
async function showRecord(id,current){
  const value=await data("records/"+id+".json");
  if(current!==token)return;
  const section=panel(el("h2","Current file"),el("pre",value.content));
  // Never turn user-authored Markdown into executable HTML.
  section.append(el("small","Source path: "+value.path));
}
async function loadDay(day,section){
  try{
    const index=await data("days/"+day+"/index.json");
    const box=el("div");
    for(const page of index.pages){
      const b=el("button","Load page "+page.number);
      b.onclick=async()=>{b.disabled=true;try{
        const result=await data(page.url);
        const list=el("ul");
        for(const event of result.items){const li=el("li");li.append(link((event.title||event.summary||event.id)+" · "+event.recorded_at,"/event/"+event.id));list.append(li);}
        box.append(list);b.remove();
      }catch(e){b.disabled=false;box.append(el("p",e.message,"error"));}};
      box.append(b);
    }
    section.append(box);
  }catch(e){section.append(el("p",e.message,"error"));}
}

const tokenize = text => [...new Set((text.normalize("NFC").toLowerCase().match(/[^\W_]+/gu)||[])
  .filter(t=>t.length>=2&&t.length<=64))];
const archived = record => record.status==="deprecated";
async function allRecords(current){
  const index=await data("records/catalog/index.json");
  const items=[];
  for(const page of index.pages){
    const result=await data(page.url);
    if(current!==token)return [];
    items.push(...result.items);
  }
  return items;
}
async function renderCollection(route,params,current){
  const records=await allRecords(current);
  if(current!==token)return;
  const includeArchived=params.get("archived")==="1";
  const visible=records.filter(r=>includeArchived||!archived(r));
  heading({records:"Records / Search",projects:"Projects",today:"Today",calendar:"Calendar"}[route]);
  const nav=panel();
  const archive=el("label");
  const toggle=el("input");toggle.type="checkbox";toggle.checked=includeArchived;
  toggle.onchange=()=>{params.set("archived",toggle.checked?"1":"0");
    location.hash="/"+route+"?"+params.toString();};
  archive.append(toggle,document.createTextNode(" Include archived"));nav.append(archive);
  if(route==="records"){
    const search=el("input");search.type="search";search.placeholder="Search records";
    search.setAttribute("aria-label","Search records");
    search.value=params.get("q")||"";
    nav.append(search);
    let searchSerial=0;
    const output=panel();
    const show=async()=>{
      const serial=++searchSerial;
      const terms=tokenize(search.value);
      if(terms.length>8){output.replaceChildren(el("p","Maximum eight search tokens"));return;}
      let matched=visible.map(r=>({record:r,score:0}));
      if(terms.length){
        const shards=new Map();
        const manifest=await data("search/manifest.json");
        const published=new Set(manifest.shards.map(s=>s.prefix));
        // WebCrypto is required for the deterministic SHA-256 shard interface.
        for(const term of terms){
          const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(term));
          if(serial!==searchSerial||current!==token)return;
          const prefix=Array.from(new Uint8Array(digest)).slice(0,1).map(b=>b.toString(16).padStart(2,"0")).join("");
          if(!shards.has(prefix))shards.set(prefix,published.has(prefix)?await data("search/"+prefix+".json"):{terms:{}});
        }
        const hits=new Map();
        for(const term of terms){
          const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(term));
          const prefix=new Uint8Array(digest)[0].toString(16).padStart(2,"0");
          const entries=shards.get(prefix).terms[term]||[];
          const currentHits=new Map(entries.map(e=>[e.record_id,Math.max(...e.fields.map(f=>({title:8,tag:4,description:2,body:1}[f]||0)))]));
          for(const id of [...hits.keys()])if(!currentHits.has(id))hits.delete(id);
          if(hits.size===0&&term===terms[0])for(const [id,score] of currentHits)hits.set(id,score);
          else for(const [id,score] of currentHits)if(hits.has(id))hits.set(id,hits.get(id)+score);
        }
        matched=matched.filter(x=>hits.has(x.record.id)).map(x=>({...x,score:hits.get(x.record.id)}));
      }
      if(serial!==searchSerial||current!==token)return;
      matched.sort((a,b)=>b.score-a.score||b.record.updated_at.localeCompare(a.record.updated_at)||a.record.id.localeCompare(b.record.id));
      output.replaceChildren(el("p",matched.length+" matching records"));
      let offset=0;
      const more=el("button","Load more");
      more.onclick=()=>{
        for(const {record} of matched.slice(offset,offset+50)){
          const p=el("p");p.append(link(record.title,"/record/"+record.id),el("small"," · "+record.status+" · "+record.area));output.append(p);
        }
        offset+=50;
        more.hidden=offset>=matched.length;
      };
      output.append(more);more.click();
    };
    let timer;
    search.oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{
      params.set("q",search.value);history.replaceState(null,"","#/records?"+params.toString());show();
    },250);};
    await show();
  } else if(route==="projects"){
    const projects=visible.filter(r=>r.type==="project");
    if(!projects.length)panel(el("p","No published projects"));
    for(const project of projects){
      const section=panel(el("h2",project.title),link("Open project","/record/"+project.id));
      const children=visible.filter(r=>r.project_id===project.id);
      section.append(el("p",children.length+" linked records"));
      for(const child of children){const p=el("p");p.append(link(child.title,"/record/"+child.id));section.append(p);}
    }
  } else if(route==="today"){
    const day=new Date().toISOString().slice(0,10);
    panel(el("p","Today · "+day+" (UTC)"));
    const month=await data("reminders/"+day.slice(0,7)+".json").catch(e=>{if(e.message==="HTTP 404")return {items:[]};throw e;});
    const hits=month.items.filter(r=>r.start_date<=day&&r.end_date>=day&&visible.some(x=>x.id===r.record_id));
    if(!hits.length)panel(el("p","No reminders today"));
    for(const item of hits){const p=panel(el("p",item.text));p.append(link(item.title,"/record/"+item.record_id));}
  } else if(route==="calendar"){
    const month=params.get("month")||new Date().toISOString().slice(0,7);
    const input=el("input");input.type="month";input.value=month;
    input.onchange=()=>{params.set("month",input.value);location.hash="/calendar?"+params.toString();};
    nav.append(input);
    const reminders=await data("reminders/"+month+".json").catch(e=>{if(e.message==="HTTP 404")return {items:[]};throw e;});
    const items=reminders.items.filter(r=>visible.some(x=>x.id===r.record_id));
    if(!items.length)panel(el("p","No published reminders this month"));
    for(const item of items){const p=panel(el("p",item.start_date+" – "+item.end_date+" · "+item.text));p.append(link(item.title,"/record/"+item.record_id));}
  }
}

window.addEventListener("hashchange",render);
window.addEventListener("popstate",render);
render();
})();
