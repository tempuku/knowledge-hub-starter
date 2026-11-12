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
window.addEventListener("hashchange",render);
window.addEventListener("popstate",render);
render();
})();
