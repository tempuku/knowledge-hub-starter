/* Read-only Knowledge Hub v1 app. One route state drives selection and rendering. */
(function (window, document) {
  "use strict";
  var app = document.getElementById("route-content"), live = document.getElementById("live-status");
  var api = window.KnowledgeV1Data && window.KnowledgeV1Data.create ? window.KnowledgeV1Data.create({baseUrl:"./data/",mode:"public"}) : null;
  var token = 0, manifest = null, latestDate = null, pendingRoute = false, restoringHistory = false, expandSections = false, filtersOpen = false;
  var previousFocus = Object.create(null), routeMemory = Object.create(null), pageState = Object.create(null), defaultFilters = {project:"",area:"",type:"",status:"",tag:"",action:""};
  if(api&&api.setUpdateHandler)api.setUpdateHandler(function(){var note=document.getElementById("update-available");if(!note){note=text("div","Update available. Refresh to load the new published generation.","update-banner");note.id="update-available";document.getElementById("app-footer").before(note);}});
  var nowDate = function () { return new Date().toISOString().slice(0, 10); };
  var text = function (tag, value, cls) { var el = document.createElement(tag); if (value !== undefined && value !== null) el.textContent = String(value); if (cls) el.className = cls; return el; };
  var button = function (label, fn, cls) { var b = text("button", label, cls || "btn"); b.type = "button"; b.addEventListener("click", fn); return b; };
  var link = function (label, route, cls) { var a = text("a", label, cls || ""); a.href = "#" + route; return a; };
  var routeBox = function (title, intro) { while(app.firstChild)app.removeChild(app.firstChild);app.setAttribute("aria-busy", "false"); var box = text("div", undefined, "route-wrap"); var h = text("h1", title); h.tabIndex = -1; box.appendChild(h); if (intro) box.appendChild(text("p", intro, "route-intro")); app.appendChild(box); return box; };
  var panel = function (parent, title) { var section = text("section", undefined, "panel"); if (title) { var h = text("h2", title); section.appendChild(h); } parent.appendChild(section); return section; };
  var announce = function (msg) { live.textContent = ""; window.setTimeout(function () { live.textContent = msg; }, 10); };
  var fail = function (parent, err, retry) { var box = text("div", undefined, "error"); box.setAttribute("role", "alert"); box.appendChild(text("p", err && err.message ? err.message : "This section could not be loaded.")); box.appendChild(button("Retry", retry, "btn secondary")); parent.appendChild(box); };
  var queryString = function (params) { var keys = Object.keys(params).sort(), out=[]; keys.forEach(function (key) { var value=params[key]; if (value !== "" && value !== null && value !== undefined && value !== false) out.push(encodeURIComponent(key)+"="+encodeURIComponent(String(value))); }); return out.length ? "?"+out.join("&") : ""; };
  var saveRouteMemory = function(){var active=document.activeElement;routeMemory[window.location.hash||"#/diary"]={scroll:document.getElementById("app").scrollTop,windowY:window.scrollY||0,focusId:active&&active.id||""};};
  var go = function (path, params, replace) { var value = "#" + path + queryString(params || {});if(!replace)saveRouteMemory(); if (replace) window.history.replaceState(window.history.state, "", value); else window.location.hash = value; };
  var parseRoute = function () {
    var hash = window.location.hash || "", raw = hash.replace(/^#/, ""), q = raw.indexOf("?"), path = q < 0 ? raw : raw.slice(0,q), query = q < 0 ? "" : raw.slice(q+1);
    var parts = path.split("/").filter(Boolean), params = new URLSearchParams(query), name = parts[0] || "diary";
    var fragment="",fragmentAt=path.indexOf("#");if(fragmentAt>=0){fragment=path.slice(fragmentAt+1);path=path.slice(0,fragmentAt);parts=path.split("/").filter(Boolean);name=parts[0]||"diary";}
    var route = {name:name, id:parts[1] || "", params:params,fragment:fragment};
    try { route.id=decodeURIComponent(route.id); } catch (e) { route.invalid=true; }
    if (name === "record") route.name="records"; if (name === "event") route.name="events"; if (name === "history") { route.name="records"; route.params.set("tab","history"); }
    return route;
  };
  var safeId = function (id) { return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(id); };
  var fmtDate = function (s) { if (!s) return ""; return s + " UTC"; };
  var readFrontmatter = function (s) { return String(s || "").replace(/^---\s*\n[\s\S]*?\n---\s*(?:\n|$)/, ""); };
  var apiGet = async function (path) {
    if (api && api.get) return api.get(path);
    var root = "./data/" + (manifest && manifest.root ? manifest.root : "");
    var response = await fetch(root + path, {cache:"no-cache"}); if (!response.ok) { var error = new Error(response.status === 404 ? "Record unavailable in this view." : "Request failed ("+response.status+")"); error.status=response.status; throw error; }
    var value=await response.json(); if(value.schema_version!==1)throw new Error("Update required: unsupported data schema."); return value;
  };
  var dataCall = async function (method, args, fallbackPath) { if (api && typeof api[method] === "function") return api[method](args); return apiGet(fallbackPath); };
  var initialize = async function (refresh) {
    var loaded=null;if(refresh)aliasCache=null;
    if (api && api.loadManifest) { loaded=await api.loadManifest({refresh:!!refresh,activate:!!refresh});manifest=loaded.manifest||loaded; }
    else { var res=await fetch("./manifest.json",{cache:"no-cache"}); if(!res.ok)throw new Error("Published data is unavailable."); manifest=await res.json(); if(manifest.schema_version!==1)throw new Error("Update required: unsupported manifest."); }
    if (!manifest || manifest.mode !== "public" || !manifest.root) throw new Error("Public demo data is unavailable.");
    document.getElementById("build-state").textContent = "Public demo";
    document.getElementById("sidebar-status").textContent = "Read-only public records";
    document.getElementById("source-revision").textContent = String(manifest.source_revision || "").slice(0,12) || "source unavailable";
    document.getElementById("source-revision").setAttribute("aria-label", "Source revision " + (manifest.source_revision || "unavailable"));
    var published = document.getElementById("app-footer");
    if (published && manifest.published_at) published.firstChild.textContent = "Published " + manifest.published_at + " · ";
    if (loaded && loaded.offline || manifest.offline || api&&api.status&&api.status().offline) { var offline=text("div","Offline — showing saved data from "+(manifest.published_at || "an earlier publication"),"offline-banner"); app.insertBefore(offline,app.firstChild); }
    if (loaded && loaded.updateAvailable) { var update=text("div","Update available. Refresh to load the new published generation.","update-banner");update.id="update-available";document.getElementById("app-footer").before(update); }
    return manifest;
  };
  var allRecords = async function () {
    if (api && api.catalogPages) return api.catalogPages();
    if (api && api.resolveRecords) { var result=await api.resolveRecords({}); return Array.isArray(result)?result:(result.items||[]); }
    var idx=await apiGet("records/catalog/index.json"), out=[];
    for(var i=0;i<idx.pages.length;i++) { var page=await apiGet(idx.pages[i].url); out=out.concat(page.items || []); }
    return out;
  };
  var catalog = async function () { return dataCall("catalog", {}, "catalog.json"); };
  var statusNode = function (value) { var labels={draft:"✎ Draft",stable:"✓ Stable",in_progress:"◷ In progress",completed:"✓ Completed",deprecated:"▣ Archived"}; var key=value || "unknown"; return text("span",labels[key] || "? Unknown", "status"); };
  var statusText = function (parent, value) { var node=statusNode(value); node.setAttribute("data-status",value || "unknown"); parent.appendChild(node); };
  var aliasCache = null;
  var getAliases = async function () {
    if (aliasCache) return aliasCache;
    if (!api || !api.aliases) { aliasCache = {}; return aliasCache; }
    try { aliasCache = await api.aliases() || {}; } catch (e) { aliasCache = {}; }
    return aliasCache;
  };
  var foldText = function (value) { return String(value === undefined || value === null ? "" : value).toLowerCase(); };
  var cmpCase = function (a, b) { var x = foldText(a), y = foldText(b); if (x < y) return -1; if (x > y) return 1; return 0; };
  var cmpId = function (a, b) { return String(a.id).localeCompare(String(b.id)); };
  var cmpTitle = function (a, b) { return cmpCase(a.title, b.title) || cmpId(a, b); };
  var cmpUpdated = function (a, b) { return String(b.updated_at || "").localeCompare(String(a.updated_at || "")) || cmpId(a, b); };
  var countLabel = function (n, one, many) { return n + " " + (n === 1 ? one : many); };
  var statusLabel = function (value) { var labels = {draft: "Draft", stable: "Stable", in_progress: "In progress", completed: "Completed", deprecated: "Archived"}; return labels[value] || "Unknown"; };
  var areaLabel = function (value) {
    if (!value) return "No section";
    var known = {adr: "ADR", notes: "Notes", projects: "Projects", design: "Design", concepts: "Concepts", private: "Private", journal: "Journal"};
    return String(value).split("/").map(function (part) {
      if (known[part]) return known[part];
      var words = part.replace(/-/g, " ").trim();
      return words ? words.charAt(0).toUpperCase() + words.slice(1) : part;
    }).join(" / ");
  };
  var areaNode = function (value) { return text("span", areaLabel(value), "badge area-label"); };
  var projectAlias = function (id, aliases) { var current = aliases && aliases.current_entries; return id && current && current[id] ? current[id] : id; };
  var belongsToProject = function (record, project, aliases) { return record.project_id === project.id || projectAlias(record.project_id, aliases) === project.id; };
  var projectTitles = function (records, aliases) {
    var map = {};
    records.forEach(function (record) { if (record.type === "project") map[record.id] = record.title || record.id; });
    var current = aliases && aliases.current_entries || {};
    Object.keys(current).forEach(function (alias) { if (map[current[alias]]) map[alias] = map[current[alias]]; });
    return map;
  };
  var projectTitle = function (id, map) { return id ? (map[id] || id) : "No project"; };
  var addOption = function (select, value, label) { var option = document.createElement("option"); option.value = value; option.textContent = label; select.appendChild(option); return option; };
  var selectField = function (form, labelText, choices, current, onChange) {
    var label = document.createElement("label"); label.appendChild(text("span", labelText));
    var select = document.createElement("select"); select.setAttribute("aria-label", labelText); addOption(select, "", "All");
    choices.forEach(function (choice) { addOption(select, choice.value, choice.label); });
    select.value = current || "";
    if (current && select.value !== current) { addOption(select, current, current); select.value = current; }
    select.addEventListener("change", function () { onChange(select.value); });
    label.appendChild(select); form.appendChild(label); return select;
  };
  var choiceValues = function (records, key, includeDeprecated) {
    var seen = {}, values = [];
    records.forEach(function (record) {
      if (!includeDeprecated && record.status === "deprecated") return;
      var raw = key === "tag" ? (record.tags || []) : [record[key]];
      raw.forEach(function (value) { if (value === undefined || value === null || value === "") return; value = String(value); if (!seen[value]) { seen[value] = true; values.push(value); } });
    });
    values.sort(cmpCase);
    return values;
  };
  var valueChoices = function (records, key, includeDeprecated, labelFor) {
    return choiceValues(records, key, includeDeprecated).map(function (value) { return {value: value, label: labelFor ? labelFor(value) : value}; });
  };
  var projectChoices = function (records, map, includeDeprecated) {
    var seen = {}, choices = [];
    records.forEach(function (record) {
      if (!includeDeprecated && record.status === "deprecated") return;
      var id = record.project_id; if (!id || seen[id]) return; seen[id] = true;
      choices.push({value: id, label: map[id] || id});
    });
    choices.sort(function (a, b) { return cmpCase(a.label, b.label) || cmpCase(a.value, b.value); });
    return choices;
  };
  var setupSearch = function (route) {
    var field=document.getElementById("global-search"), form=document.getElementById("global-search-form");
    if (route.name === "records") field.value=route.params.get("q") || "";
    form.onsubmit=function (event) { event.preventDefault(); go("/records",{q:field.value}); };
    var keydown=function(event){ if(event.key==="/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) && !event.target.isContentEditable){event.preventDefault();field.focus();} if(event.key==="Escape" && document.activeElement===field){field.value="";field.blur();} };
    document.removeEventListener("keydown",window.__khSearchKey||function(){}); window.__khSearchKey=keydown; document.addEventListener("keydown",keydown);
  };
  var setupMobileNav = function () {
    var main=document.getElementById("app"), host=main.querySelector(".route-wrap"); if(!host || host.querySelector(".mobile-nav"))return;
    var nav=document.createElement("div"); nav.className="mobile-nav";
    var trigger=button(expandSections?"Close Sections":"Sections",function(){expandSections=!expandSections; render();},"btn secondary"); trigger.id="sections-toggle"; trigger.setAttribute("aria-expanded",String(expandSections)); trigger.setAttribute("aria-controls","sections-panel"); nav.appendChild(trigger);
    var list=document.createElement("nav"); list.className="section-panel"; list.id="sections-panel"; list.hidden=!expandSections; list.setAttribute("aria-label","Sections");
    ["Today","Projects","Records","Diary","Calendar"].forEach(function(label){var key=label.toLowerCase();list.appendChild(link(label,"/"+key));}); nav.appendChild(list); var intro=host.querySelector(".route-intro"); host.insertBefore(nav,intro?intro.nextSibling:host.children[1] || null);
    trigger.addEventListener("keydown",function(e){if(e.key==="Escape"&&expandSections){expandSections=false;render();var t=document.getElementById("sections-toggle");if(t)t.focus();}});
  };
  var setNav = function (name) { Array.prototype.forEach.call(document.querySelectorAll("#primary-nav a"),function(a){if(a.getAttribute("data-route")===name)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");}); };
  var eventLink = function (event, view) { return "/events/"+event.id+queryString({view:view || "revision"}); };
  var recordLink = function (id, tab) { return "/records/"+id+queryString({tab:tab && tab!=="content"?tab:""}); };
  var resolveAliases = async function (route, serial) {
    if(!api || !api.aliases || !route.id)return route;
    var aliases=await api.aliases(), paths=aliases.paths||{}, entries=aliases.entries||{}, currentEntries=aliases.current_entries||{};
    if(route.name==="events" && entries[route.id]){ if(serial===token)go("/events/"+entries[route.id],{view:route.params.get("view")||"revision"},true); return {name:"events",id:entries[route.id],params:route.params}; }
    if(route.name==="records"){
      var canonical=currentEntries[route.id];
      if(canonical&&canonical!==route.id){if(serial===token)go("/records/"+canonical,{tab:route.params.get("tab")||""},true);return {name:"records",id:canonical,params:route.params};}
      if(!safeId(route.id)){var ids=paths[route.id]||[];if(!ids.length&&canonical&&canonical!==route.id)ids=[canonical]; if(ids.length===1){if(serial===token)go("/records/"+ids[0],{tab:route.params.get("tab")||""},true);return {name:"records",id:ids[0],params:route.params};} if(ids.length>1){route.ambiguous=ids;return route;} }
    }
    return route;
  };
  var dateParts = function (date) { var d=new Date(date+"T00:00:00Z"),day=(d.getUTCDay()+6)%7; d.setUTCDate(d.getUTCDate()-day); var end=new Date(d);end.setUTCDate(end.getUTCDate()+6);return {start:d.toISOString().slice(0,10),end:end.toISOString().slice(0,10)}; };
  var dateIsValid = function (value) { if(!/^\d{4}-\d\d-\d\d$/.test(value||""))return false;var d=new Date(value+"T00:00:00Z");return !isNaN(d.getTime())&&d.toISOString().slice(0,10)===value; };
  var diaryParams = function(date,mode,route){var p={date:date,mode:mode};["project","area","type","status","tag","action"].forEach(function(f){if(route&&route.params.get(f))p[f]=route.params.get(f);});return p;};
  var latestChange = async function () {
    if(latestDate)return latestDate;
    var cat=await catalog(), months=cat.months||[];
    if(months.length){var y=months.map(function(x){return x.month;}).sort().reverse()[0].slice(0,4),cal=await dataCall("calendar",y,"calendar/"+y+".json");var days=(cal.days||[]).map(function(x){return x.date;}).sort().reverse();if(days.length)latestDate=days[0];}
    latestDate=latestDate || nowDate();return latestDate;
  };
  var loadDiaryEvents = async function (start,end) {
    if(api&&api.diaryInitialRange){var params=parseRoute().params,filters={};["project","area","type","status","tag","action"].forEach(function(key){if(params.get(key))filters[key]=params.get(key);});return api.diaryInitialRange({start:start,end:end,filters:filters});}
    if(api&&api.diaryRange&&api.dayIndex&&api.dayPage){var dates=[],cursor=start;while(cursor<=end){dates.push(cursor);var nextDate=new Date(cursor+"T00:00:00Z");nextDate.setUTCDate(nextDate.getUTCDate()+1);cursor=nextDate.toISOString().slice(0,10);}var results=await Promise.all(dates.map(async function(day){try{var index=await api.dayIndex(day),dayItems=[];for(var pageNo=1;pageNo<=(index.pages||[]).length;pageNo++){var page=await api.dayPage(day,pageNo);dayItems=dayItems.concat(page.items||[]);}return {day:day,items:dayItems};}catch(e){if(e.code==="unavailable")return {day:day,items:[]};return {day:day,items:[],error:e};}}));var gathered=[],errors=[];results.forEach(function(result){gathered=gathered.concat(result.items);if(result.error)errors.push({day:result.day,error:result.error});});return {items:gathered,total_changes:gathered.length,total_records:Array.from(new Set(gathered.map(function(item){return item.record_id;}))).length,dayErrors:errors};}
    if(api && api.diaryRange){var result=await api.diaryRange({start:start,end:end,filters:{}}); return result;}
    var d=new Date(start+"T00:00:00Z"), last=new Date(end+"T00:00:00Z"), days=[];
    while(d<=last){days.push(d.toISOString().slice(0,10));d.setUTCDate(d.getUTCDate()+1);}
    var indexes=await Promise.all(days.map(function(day){return apiGet("days/"+day+"/index.json").catch(function(e){if(e.status===404)return null;return {day:day,error:e};});}));
    var all=[],errors=[]; for(var n=0;n<indexes.length;n++){var index=indexes[n];if(!index)continue;if(index.error){errors.push(index);continue;}for(var j=0;j<index.pages.length;j++){try{var page=await apiGet(index.pages[j].url);all=all.concat(page.items||[]);}catch(e){errors.push({day:index.date,error:e});}}}
    return {items:all,total_changes:all.length,total_records:Array.from(new Set(all.map(function(x){return x.record_id;}))).length,dayErrors:errors};
  };
  var diaryScreen = async function (route, serial) {
    var mode=route.params.get("mode")||"week", validModes=["day","week","month"];if(validModes.indexOf(mode)<0)throw new Error("Invalid view. Reset view to continue.");
    var date=route.params.get("date"); if(route.params.has("date")&&!dateIsValid(date))throw new Error("Invalid view. Reset view to continue.");if(!route.params.has("date"))date=await latestChange();
    if(!route.params.has("date")){go("/diary",{date:date,mode:mode},true);}
    var dayDate=new Date(date+"T00:00:00Z"), start, end;
    if(mode==="day")start=end=date;
    else if(mode==="week"){var range=dateParts(date);start=range.start;end=range.end;}
    else {start=date.slice(0,7)+"-01";var last=new Date(Date.UTC(+date.slice(0,4),+date.slice(5,7),0));end=last.toISOString().slice(0,10);}
    var title="Diary", box=routeBox(title); setNav("diary");
    var toolbar=text("div",undefined,"toolbar");
    var modes=text("div",undefined,"segmented"); ["day","week","month"].forEach(function(m){var b=button(m.charAt(0).toUpperCase()+m.slice(1),function(){go("/diary",diaryParams(date,m,route));},"");b.setAttribute("aria-pressed",String(mode===m));modes.appendChild(b);});toolbar.appendChild(modes);
    var delta=mode==="day"?1:mode==="week"?7:0;var prev=button("Previous period",function(){var d=new Date(date+"T00:00:00Z");if(mode==="month")d=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()-1,Math.min(d.getUTCDate(),new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),0)).getUTCDate())));else d.setUTCDate(d.getUTCDate()-delta);go("/diary",diaryParams(d.toISOString().slice(0,10),mode,route));},"btn secondary");var next=button("Next period",function(){var d=new Date(date+"T00:00:00Z");if(mode==="month")d=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,Math.min(d.getUTCDate(),new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+2,0)).getUTCDate())));else d.setUTCDate(d.getUTCDate()+delta);go("/diary",diaryParams(d.toISOString().slice(0,10),mode,route));},"btn secondary");toolbar.append(prev,next,button("Today",function(){go("/diary",diaryParams(nowDate(),mode,route));},"btn secondary"),button("Latest change",async function(){go("/diary",diaryParams(await latestChange(),mode,route));},"btn secondary"));
    var dateLabel=document.createElement("label");dateLabel.appendChild(text("span","Jump to date (UTC)"));var input=document.createElement("input");input.type="date";input.value=date;input.setAttribute("aria-label","Jump to date (UTC)");input.addEventListener("change",function(){if(input.value)go("/diary",{date:input.value,mode:mode});});dateLabel.appendChild(input);toolbar.appendChild(dateLabel);box.appendChild(text("p",start+" – "+end+" · UTC","route-intro"));box.appendChild(toolbar);
    var quickWrap=text("div",undefined,"quick-filters");box.appendChild(quickWrap);
    var filters=text("details",undefined,"panel filter-panel");filters.id="filter-panel";filters.open=filtersOpen;filters.addEventListener("toggle",function(){filtersOpen=filters.open;});var summary=text("summary","Filters");summary.id="filter-toggle";summary.setAttribute("aria-controls","diary-filters");filters.appendChild(summary);
    var catalogRecords=[],catalogData=null;
    try{var loaded=await Promise.all([allRecords(),catalog().catch(function(){return null;})]);catalogRecords=loaded[0]||[];catalogData=loaded[1];}catch(e){catalogRecords=[];}
    if(serial!==token)return;
    var aliases=await getAliases();if(serial!==token)return;
    var projectMap=projectTitles(catalogRecords,aliases),areaValues=choiceValues(catalogRecords,"area",true),projectValues=projectChoices(catalogRecords,projectMap,true);
    ((catalogData&&catalogData.areas)||[]).forEach(function(area){var path=typeof area==="string"?area:area&&area.path;if(path&&areaValues.indexOf(path)<0)areaValues.push(path);});
    ((catalogData&&catalogData.projects)||[]).forEach(function(project){var id=typeof project==="string"?project:project&&project.id;if(!id)return;for(var known=false,i=0;i<projectValues.length;i+=1){if(projectValues[i].value===id){known=true;break;}}if(!known)projectValues.push({value:id,label:(project&&project.title)||projectMap[id]||id});});
    areaValues.sort(cmpCase);
    projectValues.sort(function(a,b){return cmpCase(a.label,b.label)||cmpCase(a.value,b.value);});
    var filterChoices={
      project:projectValues,
      area:areaValues.map(function(value){return {value:value,label:value};}),
      type:valueChoices(catalogRecords,"type",true),
      status:valueChoices(catalogRecords,"status",true,statusLabel).sort(function(a,b){return cmpCase(a.label,b.label);}),
      tag:valueChoices(catalogRecords,"tag",true),
      action:[{value:"CREATED",label:"Created"},{value:"UPDATED",label:"Updated"},{value:"MOVED",label:"Moved"},{value:"ARCHIVED",label:"Archived"},{value:"REOPENED",label:"Reopened"},{value:"IMPORTED",label:"Imported"}]
    };
    var form=text("div",undefined,"filter-form");form.id="diary-filters";var fields=["project","area","type","status","tag","action"];
    fields.forEach(function(field){selectField(form,field.charAt(0).toUpperCase()+field.slice(1),filterChoices[field]||[],route.params.get(field)||"",function(value){var p={date:date,mode:mode};fields.forEach(function(f){p[f]=f===field?value:(route.params.get(f)||"");});go("/diary",p);});});
    var quick=button("◷ In progress",function(){var currentStatus=route.params.get("status")||"",p={date:date,mode:mode};fields.forEach(function(f){p[f]=f==="status"?(currentStatus==="in_progress"?"":"in_progress"):(route.params.get(f)||"");});go("/diary",p);},"btn secondary quick-filter");quick.setAttribute("aria-pressed",String((route.params.get("status")||"")==="in_progress"));quickWrap.appendChild(quick);
    filters.appendChild(form);var clear=button("Clear filters",function(){go("/diary",{date:date,mode:mode});},"btn secondary");filters.appendChild(clear);box.appendChild(filters);
    var active=fields.filter(function(f){return !!route.params.get(f);}).length;summary.textContent=active?"Filters ("+active+")":"Filters";
    if(active){box.appendChild(text("p",route.params.get("status")?"Status filter shows one row per current record.":"Filters apply to the revision shown.","meta"));}
    app.setAttribute("aria-busy","true");
    var data=await loadDiaryEvents(start,end);if(serial!==token)return;
    var items=(data.items||[]).slice();items=items.filter(function(e){return fields.every(function(f){var v=route.params.get(f);if(!v)return true;if(f==="project")return e.project_id===v;if(f==="area")return e.area===v||e.area.indexOf(v+"/")===0;if(f==="type")return e.type===v;if(f==="status")return e.status===v;if(f==="tag")return (e.tags||[]).indexOf(v)>=0;if(f==="action")return e.action===v;return true;});});
    var statusFilter=route.params.get("status")||"",recordMap=Object.create(null);catalogRecords.forEach(function(record){if(record&&record.id)recordMap[record.id]=record;});
    var dedupeByRecord=window.KnowledgeV1Diary&&window.KnowledgeV1Diary.dedupeEventsByRecord||function(events){return (events||[]).slice();};
    if(statusFilter)items=dedupeByRecord(items);
    var countRecords=data.total_records !== undefined && !active ? data.total_records : Array.from(new Set(items.map(function(e){return e.record_id;}))).length;
    var countNode=text("p",data.countsExact===false?(statusFilter?"Calculating records":"Calculating changes · records"):statusFilter?countRecords+" records":items.length+" changes · "+countRecords+" records","meta");box.appendChild(countNode);
    var diaryEmpty=null;if(!items.length&&data.countsExact!==false){diaryEmpty=panel(box);diaryEmpty.appendChild(text("p","No changes in this period.","empty"));diaryEmpty.appendChild(button("Latest change",async function(){go("/diary",diaryParams(await latestChange(),mode,route));},"btn secondary"));if(active)diaryEmpty.appendChild(button("Clear filters",function(){go("/diary",{date:date,mode:mode});},"btn secondary"));}else if(!items.length&&data.countsExact===false){diaryEmpty=panel(box);diaryEmpty.appendChild(text("p","Loading filtered results…","meta"));}
    var groups={};items.forEach(function(event){var day=(event.recorded_at||"").slice(0,10);(groups[day]||(groups[day]=[])).push(event);});
    var keys=Object.keys(groups).sort().reverse(); if(mode==="day" && !keys.length)keys=[date]; if(mode==="week" && !active){var d=new Date(start+"T00:00:00Z"),e=new Date(end+"T00:00:00Z");while(d<=e){var k=d.toISOString().slice(0,10);if(!groups[k])groups[k]=[];d.setUTCDate(d.getUTCDate()+1);}keys=Object.keys(groups).sort().reverse();}
    // Keep every day folded except the latest one that actually has changes.
    // This keeps Week/Month compact instead of expanding the whole range.
    var openDay=null;if(mode==="day")openDay=date;else{for(var oi=0;oi<keys.length;oi++){if((groups[keys[oi]]||[]).length){openDay=keys[oi];break;}}}
    var loaded=pageState[window.location.hash]||50;
    var dayHost=text("div",undefined,"diary-days");box.appendChild(dayHost);
    keys.forEach(function(day){var block=text("section",undefined,"day-block diary-day");var events=groups[day]||[];var pageDesc=(data.dayIndexes||[]).filter(function(x){return x.date===day;})[0];var dayTotal=statusFilter?events.length:(pageDesc&&pageDesc.index?pageDesc.index.change_count:events.length);var opened=day===openDay;var header=button(day+" · "+dayTotal+(statusFilter?" records":" changes"),function(){var body=block.querySelector(".day-items");var expanded=header.getAttribute("aria-expanded")==="true";header.setAttribute("aria-expanded",String(!expanded));body.hidden=expanded;},"");header.setAttribute("aria-expanded",String(opened));block.appendChild(header);var body=text("div",undefined,"day-items");body.hidden=!opened;
      var dayError=(data.dayErrors||[]).filter(function(e){return e.date===day||e.day===day;})[0]||(pageDesc&&pageDesc.error?{error:pageDesc.error}:null);if(dayError)fail(body,dayError.error,function(){render();});var pageNumber=events.length?1:0;events.forEach(function(ev){body.appendChild(statusFilter?renderRecordEventRow(ev,recordMap[ev.record_id]):renderEventRow(ev,items));});var descriptors=pageDesc&&pageDesc.index?pageDesc.index.pages:[];var more=null;var addMore=function(){if(!descriptors||pageNumber>=descriptors.length)return;if(!more||!more.parentNode){more=button("Load more",async function(){more.disabled=true;try{pageNumber++;var result=await api.dayPage(day,pageNumber);if(serial!==token)return;(result.items||[]).forEach(function(ev){body.insertBefore(renderEventRow(ev,items),more);});if(pageNumber>=descriptors.length){more.remove();}else more.disabled=false;}catch(e){more.disabled=false;fail(body,e,function(){more.click();});}},"btn secondary load-more");body.appendChild(more);}};if(pageNumber>0&&!statusFilter)addMore();if(!events.length&&descriptors&&descriptors.length&&!statusFilter)header.addEventListener("click",async function(){if(body.getAttribute("data-loaded")==="true")return;body.setAttribute("data-loaded","true");var loading=text("p","Loading…","meta");body.appendChild(loading);try{var firstPage=await api.dayPage(day,1);if(serial!==token)return;loading.remove();(firstPage.items||[]).forEach(function(ev){body.appendChild(renderEventRow(ev,firstPage.items));});pageNumber=1;addMore();}catch(e){loading.remove();body.removeAttribute("data-loaded");fail(body,e,function(){header.click();});}});block.appendChild(body);dayHost.appendChild(block);});
    app.setAttribute("aria-busy","false");if(data.countsExact===false&&api&&api.diaryRange){var exactFilters={};fields.forEach(function(f){if(route.params.get(f))exactFilters[f]=route.params.get(f);});api.diaryRange({start:start,end:end,filters:exactFilters}).then(function(exact){if(serial!==token)return;if(exact.countsExact===false){countNode.textContent="Counts could not be calculated.";return;}var exactItems=statusFilter?dedupeByRecord(exact.items):(exact.items||[]);countNode.textContent=statusFilter?exactItems.length+" records":exact.total_changes+" changes · "+exact.total_records+" records";if(!active&&!exact.items.length){if(diaryEmpty)diaryEmpty.remove();diaryEmpty=panel(box);diaryEmpty.appendChild(text("p","No changes in this period.","empty"));diaryEmpty.appendChild(button("Latest change",async function(){go("/diary",diaryParams(await latestChange(),mode,route));},"btn secondary"));}if(active){if(diaryEmpty)diaryEmpty.remove();while(dayHost.firstChild)dayHost.removeChild(dayHost.firstChild);var exactGroups={};exactItems.forEach(function(ev){var eventDay=(ev.recorded_at||"").slice(0,10);(exactGroups[eventDay]||(exactGroups[eventDay]=[])).push(ev);});var exactDays=Object.keys(exactGroups).sort().reverse();exactDays.forEach(function(eventDay){var evs=exactGroups[eventDay],block=text("section",undefined,"day-block diary-day"),header=button(eventDay+" · "+evs.length+(statusFilter?" records":" changes"),function(){var body=block.querySelector(".day-items"),expanded=header.getAttribute("aria-expanded")==="true";header.setAttribute("aria-expanded",String(!expanded));body.hidden=expanded;},"");header.setAttribute("aria-expanded",String(exactDays[0]===eventDay));block.appendChild(header);var body=text("div",undefined,"day-items");body.hidden=header.getAttribute("aria-expanded")!=="true";var offset=0,more=null;var appendChunk=function(){evs.slice(offset,offset+50).forEach(function(ev){body.insertBefore(statusFilter?renderRecordEventRow(ev,recordMap[ev.record_id]):renderEventRow(ev,exact.items),more||null);});offset+=50;if(more&&offset>=evs.length)more.remove();};if(evs.length>50)more=button("Load more",function(){appendChunk();},"btn secondary load-more");appendChunk();if(more)body.appendChild(more);block.appendChild(body);dayHost.appendChild(block);});if(!exactItems.length){diaryEmpty=panel(box);diaryEmpty.appendChild(text("p","No changes in this period.","empty"));diaryEmpty.appendChild(button("Latest change",async function(){go("/diary",diaryParams(await latestChange(),mode,route));},"btn secondary"));diaryEmpty.appendChild(button("Clear filters",function(){go("/diary",{date:date,mode:mode});},"btn secondary"));}}}).catch(function(){if(serial===token){countNode.textContent="Counts could not be calculated.";}});}
  };
  var renderEventRow = function (ev, visible) {
    var row=text("article",undefined,"event-row");var title=ev.title||ev.summary||"Untitled record";var h=text("h2",title);row.appendChild(h);if(ev.summary)row.appendChild(text("p",ev.summary));row.appendChild(text("p",(ev.action||"Change")+" · "+(ev.recorded_at||"")+" UTC","meta"));if(ev.occurred_on||ev.occurred_at)row.appendChild(text("p","Occurred "+(ev.occurred_on||"")+(ev.occurred_at?" "+ev.occurred_at:""),"meta"));var meta=text("p",undefined,"meta");statusText(meta,ev.status);if(ev.area){meta.appendChild(text("span"," "));meta.appendChild(areaNode(ev.area));}if(ev.project_id)meta.appendChild(text("span"," · "+(ev.project_title||ev.project_id)));if(ev.actor_label)meta.appendChild(text("span"," · "+ev.actor_label));if(ev.provenance_kind && ev.provenance_kind!=="native")meta.appendChild(text("span"," · Imported history","badge"));row.appendChild(meta);
    var actions=text("div",undefined,"actions");actions.appendChild(link("Open current record",recordLink(ev.record_id)));actions.appendChild(link("View this revision",eventLink(ev,"revision")));actions.appendChild(link("Show changes",eventLink(ev,"diff")));var fileUrl=publicSourceUrl(ev.record_id);if(fileUrl){var file=text("a","File: "+String((window.KnowledgeHubConfig.publicSourcePaths||{})[ev.record_id]).split(/[\\/]/).pop());file.href=fileUrl;file.target="_blank";file.rel="noopener noreferrer";file.setAttribute("aria-label",file.textContent+" (opens in a new tab)");actions.appendChild(file);}row.appendChild(actions);if(ev.operation_id&&visible.filter(function(x){return x.operation_id===ev.operation_id;}).length>1)row.appendChild(text("p","Same operation","badge"));return row;
  };
  var renderRecordEventRow = function (ev, record) {
    var row=text("article",undefined,"record-row"),heading=text("h3");
    heading.appendChild(link((record&&record.title)||ev.title||ev.summary||"Untitled record",recordLink(ev.record_id)));row.appendChild(heading);
    var meta=text("p",undefined,"meta");statusText(meta,(record&&record.status)||ev.status);
    var area=(record&&record.area)||ev.area;
    if(area){meta.appendChild(text("span"," "));meta.appendChild(areaNode(area));}
    meta.appendChild(text("span"," · "+((record&&record.type)||ev.type||"record")));
    if(ev.recorded_at)meta.appendChild(text("span"," · Latest change: "+ev.recorded_at));
    row.appendChild(meta);
    if(record&&record.description)row.appendChild(text("p",record.description));
    return row;
  };
  var recordScreen = async function (route, serial) {
    if(!safeId(route.id)) { await resolveAliases(route,serial); if(route.ambiguous){renderAmbiguous(route);return;} if(!safeId(route.id))throw new Error("Record unavailable in this view."); }
    var meta=await dataCall("recordMeta",route.id,"records/"+route.id+".meta.json"); if(serial!==token)return;
    var box=routeBox(meta.title||"Record");setNav("records");var status=panel(box);statusText(status,meta.status);if(meta.area){status.appendChild(text("span"," "));status.appendChild(areaNode(meta.area));}status.appendChild(text("p",meta.description||""));status.appendChild(text("p",meta.project_title||"","meta"));if(meta.updated_at)status.appendChild(text("p","Last recorded update · "+meta.updated_at,"meta"));
    var tab=route.params.get("tab")||"content", tabs=text("nav",undefined,"record-tabs");tabs.setAttribute("aria-label","Record views");["content","history","source"].forEach(function(key){var a=link(key.charAt(0).toUpperCase()+key.slice(1),recordLink(route.id,key));if(tab===key)a.setAttribute("aria-current","page");tabs.appendChild(a);});box.appendChild(tabs);
    if(tab==="content")await renderRecordContent(box,route.id,meta,serial);
    else if(tab==="history")await renderHistory(box,route.id,meta,serial);
    else if(tab==="source")await renderSource(box,route.id,meta,serial);
    else throw new Error("Invalid view. Reset view to continue.");
    if(route.fragment)applyFragment(box,route.fragment);
  };
  var applyFragment=function(box,fragment){var id;try{id=decodeURIComponent(fragment);}catch(e){id=fragment;}var target=document.getElementById(id);if(target){target.tabIndex=-1;target.scrollIntoView();target.focus();}else box.appendChild(text("p","Section no longer available.","meta"));};
  var renderRecordContent = async function (box,id,meta,serial) {
    var section=panel(box,"Content");if(meta.detail_bytes>262144){section.appendChild(text("p","This record is "+meta.detail_bytes+" bytes. Load the full content to continue."));section.appendChild(button("Load full content",async function(){try{await loadRecordBody(section,id,serial,true);}catch(e){fail(section,e,function(){renderRecordContent(box,id,meta,serial);});}}));return;}
    await loadRecordBody(section,id,serial);
  };
  var loadRecordBody = async function (section,id,serial,force) { var value=force?await apiGet("records/"+id+".json"):await dataCall("record",id,"records/"+id+".json");if(serial!==token)return;var content=readFrontmatter(value.content||"");var links=value.links||[];var byHref=Object.create(null);links.forEach(function(l){if(l.href&&l.target_id&&l.available!==false)byHref[l.href]="#/records/"+l.target_id+(l.fragment?"#"+encodeURIComponent(l.fragment):"");});var rendered=window.KnowledgeV1Markdown.render(content,{baseUrl:window.location.href,resolveLink:function(href,label){return byHref[href]||null;},approvedAssets:[]});section.appendChild(rendered);
    // Incoming links are derived from the eligible source graph at publish time.
    // Never display an unresolved, unpublished or private record identifier.
    var incoming=value.backlinks||[];
    if(incoming.length){var group=text("div",undefined,"related-records");group.appendChild(text("h3","Referenced by"));var list=text("ul");incoming.forEach(function(item){if(!safeId(item.source_id)||!item.title)return;var li=text("li");li.appendChild(link(item.title,recordLink(item.source_id)));list.appendChild(li);});group.appendChild(list);section.appendChild(group);}
  };
  var publicSourceUrl = function (id) { var cfg=window.KnowledgeHubConfig||{};if(!sourceApproved(id))return null;try{var base=new URL(cfg.sourceURLBase,window.location.href);if(base.protocol!=="https:"&&base.protocol!=="http:")return null;var path=String(cfg.publicSourcePaths[id]||"").replace(/\\/g,"/");if(!path||path.charAt(0)==="/"||path.split("/").some(function(part){return !part||part==="."||part==="..";}))return null;var encoded=path.split("/").map(function(part){return encodeURIComponent(part);}).join("/");return new URL(encoded,base.href.replace(/\/?$/,"/")).href;}catch(e){return null;} };
  var sourceApproved = function(id){var cfg=window.KnowledgeHubConfig||{};return !!(cfg.sourceURLBase&&cfg.publicSourcePaths&&cfg.publicSourcePaths[id]&&Array.isArray(cfg.publicSourceRecordIds)&&cfg.publicSourceRecordIds.indexOf(id)>=0);};
  var renderSource = async function (box,id,meta,serial) {
    var section=panel(box,"Source");if(!sourceApproved(id)){section.appendChild(text("p","Exact source is unavailable in this view."));return;}if(meta.detail_bytes>262144){section.appendChild(text("p","This record is "+meta.detail_bytes+" bytes. Load the full source to continue."));section.appendChild(button("Load full source",function(){loadSource(true);},"btn"));return;}await loadSource(false);
    async function loadSource(force){try{var url=publicSourceUrl(id);if(!url)throw new Error("Exact source is unavailable in this view.");var response=await fetch(url,{cache:"no-store"});if(!response.ok)throw new Error("Exact source could not be loaded.");var source=await response.text();if(serial!==token)return;var pre=text("pre",source,"source-text");pre.tabIndex=0;section.appendChild(pre);var copy=button("Copy source",async function(){try{await navigator.clipboard.writeText(source);announce("Source copied.");}catch(e){var selection=window.getSelection();var range=document.createRange();range.selectNodeContents(pre);selection.removeAllRanges();selection.addRange(range);announce("Clipboard unavailable. Source selected for manual copying.");}});section.appendChild(copy);var file=text("a","File: "+String((window.KnowledgeHubConfig.publicSourcePaths||{})[id]).split(/[\\/]/).pop());file.href=url;file.target="_blank";file.rel="noopener noreferrer";file.setAttribute("aria-label",file.textContent+" (opens in a new tab)");section.appendChild(file);section.appendChild(text("p","Exact current source bytes.","meta"));}catch(e){fail(section,e,function(){loadSource(force);});}}
  };
  var renderHistory = async function (box,id,meta,serial) {
    var section=panel(box,"History");try{var index=await dataCall("historyIndex",id,"history/"+id+"/index.json");if(!index.event_count){section.appendChild(text("p","No published history."));return;}var pages=index.pages||[],pageNumber=pageState[window.location.hash]||1,all=[];for(var i=0;i<Math.min(pageNumber,pages.length);i++){var page=api&&api.historyPage?await api.historyPage(id,pages[i].number):await apiGet(pages[i].url);all=all.concat(page.items||[]);}if(serial!==token)return;all.sort(function(a,b){return b.sequence-a.sequence;});section.appendChild(text("p","Current version is labelled current. Showing published history.","meta"));all.forEach(function(ev){var row=renderEventRow(ev,all);if(ev.sequence===meta.version)row.insertBefore(text("span","Current version","badge"),row.firstChild);section.appendChild(row);});if(pageNumber<pages.length)section.appendChild(button("Load more",function(){pageState[window.location.hash]=pageNumber+1;render();},"btn secondary"));}catch(e){fail(section,e,function(){renderHistory(box,id,meta,serial);});}
  };
  var renderEvent = async function (route,serial) {
    if(!safeId(route.id))throw new Error("Event unavailable in this view.");var meta=await dataCall("eventMeta",route.id,"events/"+route.id+".meta.json");if(serial!==token)return;var view=route.params.get("view")||"revision";if(["revision","before","diff"].indexOf(view)<0)throw new Error("Invalid view. Reset view to continue.");var current=null;try{current=await dataCall("recordMeta",meta.record_id,"records/"+meta.record_id+".meta.json");}catch(e){}if(serial!==token)return;var isCurrent=current&&current.version===meta.sequence;var box=routeBox("Revision "+meta.sequence+" · "+meta.recorded_at+" UTC");setNav("diary");box.appendChild(text("p",isCurrent?"Current revision":"You are viewing a past revision.","badge"));box.appendChild(text("h2",meta.title||meta.summary||"Historical record"));var tabs=text("nav",undefined,"record-tabs");tabs.setAttribute("aria-label","Revision views");["revision","before","diff"].forEach(function(v){var label={revision:"This revision",before:"Previous revision",diff:"Changes"}[v],a=link(label,eventLink(meta,v));if(view===v)a.setAttribute("aria-current","page");tabs.appendChild(a);});box.appendChild(tabs);var actions=text("div",undefined,"actions");actions.appendChild(link("Open current record",recordLink(meta.record_id)));actions.appendChild(link("Back to diary","/diary"));var fileUrl=publicSourceUrl(meta.record_id);if(fileUrl){var file=text("a","File: "+String((window.KnowledgeHubConfig.publicSourcePaths||{})[meta.record_id]).split(/[\\/]/).pop());file.href=fileUrl;file.target="_blank";file.rel="noopener noreferrer";actions.appendChild(file);}box.appendChild(actions);
    if(meta.detail_bytes>262144){var gate=panel(box);gate.appendChild(text("p","This revision is "+meta.detail_bytes+" bytes. Load the full revision to continue."));gate.appendChild(button("Load full revision",function(){loadEventDetail(box,route,meta,view,serial);},"btn"));return;}await loadEventDetail(box,route,meta,view,serial);
  };
  var loadEventDetail = async function (box,route,meta,view,serial) {try{var value=meta.detail_bytes>262144?await apiGet("events/"+route.id+".json"):await dataCall("event",route.id,"events/"+route.id+".json");if(serial!==token)return;var ev=value.event||{}, section=panel(box,{revision:"This revision",before:"Previous revision",diff:"Changes"}[view]);var content=view==="before"?ev.before:view==="revision"?ev.after:null;if(view==="before"&&ev.before===null){section.appendChild(text("p","This record did not exist before this change."));return;}if(view==="diff"){if(ev.action==="MOVED"&&!(value.diff&&value.diff.text))section.appendChild(text("p","Content unchanged; moved from "+(ev.path_before||"unknown")+" to "+(ev.path_after||"unknown")+"."));else{var pre=text("pre",undefined,"revision-diff");(value.diff&&value.diff.text||"").split("\n").forEach(function(line){var span=text("span",line+"\n");if(line.charAt(0)==="+")span.className="diff-added";if(line.charAt(0)==="-")span.className="diff-removed";pre.appendChild(span);});section.appendChild(pre);}return;}
      var rendered=window.KnowledgeV1Markdown.render(readFrontmatter(content||""),{baseUrl:window.location.href,approvedAssets:[]});section.appendChild(rendered);section.appendChild(text("p","Status in this revision: "+(meta.status||"Unknown"),"meta"));}catch(e){fail(box,e,function(){loadEventDetail(box,route,meta,view,serial);});}};
  var renderAmbiguous = function (route) {var box=routeBox("Choose a record");box.appendChild(text("p","This old path matches more than one published record. Choose the intended title."));var list=panel(box);route.ambiguous.forEach(async function(id){try{var meta=await dataCall("recordMeta",id,"records/"+id+".meta.json");list.appendChild(link(meta.title+" · "+meta.area,recordLink(id)));}catch(e){}});};
  var recordsScreen = async function (route, serial) {
    var box = routeBox("Records"); setNav("records");
    var q = route.params.get("q") || "", sort = route.params.get("sort") === "updated" ? "updated" : "";
    var archivedParam = route.params.get("archived") === "1", statusParam = route.params.get("status") || "";
    var includeArchived = archivedParam || statusParam === "deprecated";
    var readParams = function (overrides) {
      var values = {q:q, area:route.params.get("area")||"", project:route.params.get("project")||"", type:route.params.get("type")||"", status:statusParam, tag:route.params.get("tag")||"", archived:archivedParam?"1":"", sort:sort};
      if (overrides) Object.keys(overrides).forEach(function (key) { values[key] = overrides[key] === false ? "" : overrides[key]; });
      return values;
    };
    var state = text("p", q ? "Searching…" : "Loading records…", "meta"), output;
    var records = await allRecords(); if (serial !== token) return;
    var aliases = await getAliases(); if (serial !== token) return;
    var titleMap = projectTitles(records, aliases), items;
    if (api && api.search && q) {
      var searchResult = await api.search(q); items = searchResult.items || [];
      items.forEach(function (record) { record.score = (searchResult.scores || {})[record.id] || 0; });
    } else items = records.slice();
    if (serial !== token) return;
    if (!Array.isArray(items)) items = items.items || [];
    var filterCount = ["area", "project", "type", "status", "tag"].filter(function (key) { return !!route.params.get(key); }).length;
    var panelDetails = text("details", undefined, "panel filter-panel"); panelDetails.id = "filter-panel"; panelDetails.open = filtersOpen;
    panelDetails.addEventListener("toggle", function () { filtersOpen = panelDetails.open; });
    var panelSummary = text("summary", filterCount ? "Filters (" + filterCount + ")" : "Filters");
    panelSummary.id = "filter-toggle"; panelSummary.setAttribute("aria-controls", "records-filters"); panelDetails.appendChild(panelSummary);
    var form = text("div", undefined, "filter-form"); form.id = "records-filters";
    var filters = form;
    selectField(filters, "Area", valueChoices(records, "area", includeArchived), readParams().area, function (value) { go("/records", readParams({area:value})); });
    selectField(filters, "Project", projectChoices(records, titleMap, includeArchived), readParams().project, function (value) { go("/records", readParams({project:value})); });
    selectField(filters, "Type", valueChoices(records, "type", includeArchived), readParams().type, function (value) { go("/records", readParams({type:value})); });
    selectField(filters, "Status", valueChoices(records, "status", includeArchived, statusLabel).sort(function (a, b) { return cmpCase(a.label, b.label); }), readParams().status, function (value) { go("/records", readParams({status:value})); });
    selectField(filters, "Tag", valueChoices(records, "tag", includeArchived), readParams().tag, function (value) { go("/records", readParams({tag:value})); });
    var sortLabel = document.createElement("label"); sortLabel.appendChild(text("span", "Sort"));
    var sortSelect = document.createElement("select"); sortSelect.setAttribute("aria-label", "Sort");
    addOption(sortSelect, "", "Title A–Z"); addOption(sortSelect, "updated", "Updated recently"); sortSelect.value = sort;
    sortSelect.addEventListener("change", function () { go("/records", readParams({sort:sortSelect.value})); });
    sortLabel.appendChild(sortSelect); filters.appendChild(sortLabel);
    var quickWrap = text("div", undefined, "quick-filters");
    var quick = button("◷ In progress", function () { go("/records", readParams({status:statusParam === "in_progress" ? "" : "in_progress"})); }, "btn secondary quick-filter");
    quick.setAttribute("aria-pressed", String(statusParam === "in_progress")); quickWrap.appendChild(quick);
    var archivedLabel = document.createElement("label"), check = document.createElement("input");
    check.type = "checkbox"; check.checked = includeArchived;
    check.addEventListener("change", function () {
      if (check.checked) go("/records", readParams({archived:"1"}));
      else go("/records", readParams({archived:"", status:statusParam === "deprecated" ? "" : statusParam}));
    });
    archivedLabel.append(check, document.createTextNode(" Include archived")); form.appendChild(archivedLabel);
    panelDetails.appendChild(form);
    box.appendChild(state); box.appendChild(quickWrap); box.appendChild(panelDetails);
    var active = readParams(), activeArchived = active.archived === "1" || active.status === "deprecated";
    items = items.filter(function (record) {
      if (!activeArchived && record.status === "deprecated") return false;
      return (!active.area || record.area === active.area || record.area.indexOf(active.area + "/") === 0) &&
        (!active.project || record.project_id === active.project) &&
        (!active.type || record.type === active.type) &&
        (!active.status || record.status === active.status) &&
        (!active.tag || (record.tags || []).indexOf(active.tag) >= 0);
    });
    if (q && sort !== "updated") items.sort(function (a, b) { return (b.score || 0) - (a.score || 0) || String(b.updated_at || "").localeCompare(String(a.updated_at || "")) || cmpId(a, b); });
    else if (sort === "updated") items.sort(cmpUpdated);
    else items.sort(cmpTitle);
    var activeLabels = [];
    [["area", "Area"], ["project", "Project"], ["type", "Type"], ["status", "Status"], ["tag", "Tag"]].forEach(function (pair) {
      var value = active[pair[0]]; if (!value) return;
      var label = pair[0] === "project" ? projectTitle(value, titleMap) : pair[0] === "status" ? statusLabel(value) : value;
      activeLabels.push(pair[1] + ": " + label);
    });
    if (archivedParam) activeLabels.push("Include archived");
    state.textContent = items.length + " matching records";
    if (activeLabels.length) {
      var summary = text("p", "Active filters: " + activeLabels.join(" · "), "meta");
      summary.appendChild(document.createTextNode(" "));
      summary.appendChild(button("Clear all", function () { go("/records", {q:q, sort:sort}); }, "btn secondary clear-all"));
      box.appendChild(summary);
    }
    if (!items.length) {
      var empty = panel(box); empty.appendChild(text("p", "No matching records.", "empty"));
      var emptyActions = text("div", undefined, "actions");
      emptyActions.appendChild(button("Clear filters", function () { go("/records", {q:q, sort:sort}); }, "btn secondary"));
      if (q) emptyActions.appendChild(button("Clear search", function () { go("/records", readParams({q:""})); }, "btn secondary"));
      empty.appendChild(emptyActions); return;
    }
    output = panel(box);
    var offset = pageState[window.location.hash] || 0;
    items.slice(0, offset + 50).forEach(function (record) {
      var row = text("article", undefined, "record-row"), heading = text("h2");
      heading.appendChild(link(record.title || "Untitled", recordLink(record.id))); row.appendChild(heading);
      if (record.description) row.appendChild(text("p", record.description));
      var metaBox = text("p", undefined, "meta"); statusText(metaBox, record.status);
      if (record.area) { metaBox.appendChild(text("span", " ")); metaBox.appendChild(areaNode(record.area)); }
      metaBox.appendChild(text("span", " · " + projectTitle(record.project_id, titleMap)));
      if (record.updated_at) metaBox.appendChild(text("span", " · Updated " + record.updated_at));
      row.appendChild(metaBox); output.appendChild(row);
    });
    if (items.length > offset + 50) output.appendChild(button("Load more", function () { pageState[window.location.hash] = offset + 50; render(); }, "btn secondary load-more"));
  };
  var projectRank = {in_progress:0, stable:1, draft:2, completed:3};
  var cmpProject = function (a, b) { var left = projectRank[a.status], right = projectRank[b.status]; if (left === undefined) left = 4; if (right === undefined) right = 4; return left - right || cmpTitle(a, b); };
  var projectsScreen = async function (route, serial) {
    var records = await allRecords(); if (serial !== token) return;
    var box = routeBox("Projects"); setNav("projects");
    var aliases = await getAliases(); if (serial !== token) return;
    var projects = records.filter(function (record) { return record.type === "project" && record.status !== "deprecated"; });
    projects.sort(cmpProject);
    if (route.id) {
      var project = null;
      projects.forEach(function (candidate) { if (candidate.id === route.id) project = candidate; });
      if (!project) throw new Error("Record unavailable in this view.");
      box.querySelector("h1").textContent = project.title || "Project";
      var detail = await dataCall("record", route.id, "records/" + route.id + ".json"); if (serial !== token) return;
      var children = records.filter(function (record) { return belongsToProject(record, project, aliases) && record.type !== "project" && record.status !== "deprecated"; });
      var incoming = detail && Array.isArray(detail.backlinks) ? detail.backlinks : [];
      var summary = text("div", undefined, "project-summary"); statusText(summary, project.status);
      summary.appendChild(text("span", "Last updated " + (project.updated_at || "unknown") + " · " + countLabel(project.version || 0, "revision", "revisions"), "meta"));
      summary.appendChild(text("span", countLabel(children.length, "related current record", "related current records") + " · " + countLabel(incoming.length, "backlink", "backlinks"), "meta"));
      box.appendChild(summary);
      var content = panel(box, "About this project");
      content.appendChild(window.KnowledgeV1Markdown.render(readFrontmatter(detail && detail.content || ""), {approvedAssets:[]}));
      var related = panel(box, "Related records");
      if (!children.length) { related.appendChild(text("p", "No records in this project.", "empty")); related.appendChild(link("Browse records", "/records")); }
      else {
        var list = text("ul", undefined, "group-list project-records");
        children.forEach(function (record) {
          var item = text("li", undefined, "record-row"), heading = text("h3");
          heading.appendChild(link(record.title || "Untitled", recordLink(record.id))); item.appendChild(heading);
          var meta = text("p", undefined, "meta"); statusText(meta, record.status);
          if (record.area) { meta.appendChild(text("span", " ")); meta.appendChild(areaNode(record.area)); }
          item.appendChild(meta); list.appendChild(item);
        });
        related.appendChild(list);
      }
      var changes = panel(box, "Recent changes");
      try {
        var index = await dataCall("historyIndex", project.id, "history/" + project.id + "/index.json"); if (serial !== token) return;
        if (!index.event_count) changes.appendChild(text("p", "No published history."));
        else {
          var pages = index.pages || [], show = pageState[window.location.hash] || 5, all = [];
          for (var pageNumber = 0; pageNumber < pages.length && all.length < show; pageNumber += 1) {
            var page = api && api.historyPage ? await api.historyPage(project.id, pages[pageNumber].number) : await apiGet(pages[pageNumber].url);
            all = all.concat(page.items || []);
          }
          if (serial !== token) return;
          all.sort(function (a, b) { return b.sequence - a.sequence; });
          all.slice(0, show).forEach(function (event) { changes.appendChild(renderEventRow(event, all)); });
          if (show < index.event_count) changes.appendChild(button("Load more", function () { pageState[window.location.hash] = show + 5; render(); }, "btn secondary load-more"));
        }
      } catch (error) { fail(changes, error, function () { render(); }); }
      var referenceItems = incoming.filter(function (item) { return item && safeId(item.source_id) && item.title; });
      if (referenceItems.length) {
        var references = panel(box, "Referenced by"), referenceList = text("ul");
        referenceItems.forEach(function (item) { var entry = text("li"); entry.appendChild(link(item.title, recordLink(item.source_id))); referenceList.appendChild(entry); });
        references.appendChild(referenceList);
      }
      return;
    }
    if (!projects.length) box.appendChild(text("p", "No published projects.", "empty"));
    var backlinkCounts = {};
    await Promise.all(projects.map(async function (project) {
      try { var detail = await dataCall("record", project.id, "records/" + project.id + ".json"); backlinkCounts[project.id] = detail && Array.isArray(detail.backlinks) ? detail.backlinks.length : 0; }
      catch (error) { backlinkCounts[project.id] = 0; }
    }));
    if (serial !== token) return;
    projects.forEach(function (project) {
      var section = panel(box); section.classList.add("project-card");
      var heading = text("h2"); heading.appendChild(link(project.title || "Untitled project", "/projects/" + project.id)); section.appendChild(heading);
      if (project.description) section.appendChild(text("p", project.description));
      var children = records.filter(function (record) { return belongsToProject(record, project, aliases) && record.type !== "project" && record.status !== "deprecated"; });
      var counts = {draft:0, stable:0, in_progress:0, completed:0};
      children.forEach(function (record) { if (counts[record.status] !== undefined) counts[record.status] += 1; });
      var meta = text("div", undefined, "project-meta"); statusText(meta, project.status);
      meta.appendChild(text("span", countLabel(children.length, "related current record", "related current records") + " · " + countLabel(backlinkCounts[project.id] || 0, "backlink", "backlinks"), "meta"));
      meta.appendChild(text("span", "Last updated " + (project.updated_at || "unknown") + " · " + countLabel(project.version || 0, "revision", "revisions"), "meta"));
      section.appendChild(meta);
      var countLine = text("p", undefined, "project-counts");
      [["draft", "Draft"], ["stable", "Stable"], ["in_progress", "In progress"], ["completed", "Completed"]].forEach(function (pair) {
        if (counts[pair[0]]) countLine.appendChild(text("span", pair[1] + " " + counts[pair[0]], "count-chip"));
      });
      if (countLine.firstChild) section.appendChild(countLine);
      section.appendChild(link("Open project", "/projects/" + project.id));
    });
  };
  var todayScreen = async function (route, serial) {
    var day = nowDate(), box = routeBox("Today", day + " · UTC"); setNav("today");
    var value = await dataCall("today", {date:day}, "reminders/" + day.slice(0,7) + ".json"); if (serial !== token) return;
    var currentRecords = await allRecords(); if (serial !== token) return;
    var recent = (value.recently_updated || []).filter(function (record) { return record.status !== "deprecated"; }).sort(cmpUpdated).slice(0, 10);
    var sections = {"Important dates today":value.today || [], "Upcoming seven dates":value.upcoming || [], "Recently updated":recent};
    var names = ["Important dates today", "Upcoming seven dates", "Recently updated"];
    names.forEach(function (name, index) {
      var section = panel(box, name), items = sections[name] || [];
      if (!items.length) { section.appendChild(text("p", index === 2 ? "None recently updated." : "None.", "empty")); return; }
      items.forEach(function (item) {
        var recordId = item.record_id || item.id, row = text("article", undefined, "record-row"), heading = text("h3");
        heading.appendChild(link(item.title || item.text || "Record", recordLink(recordId))); row.appendChild(heading);
        if (index === 2) {
          var meta = text("p", undefined, "meta"); statusText(meta, item.status);
          meta.appendChild(text("span", " · " + (item.type || "record")));
          if (item.updated_at) meta.appendChild(text("span", " · Updated " + item.updated_at));
          row.appendChild(meta);
        } else if (item.text) row.appendChild(text("p", item.text));
        section.appendChild(row);
      });
    });
    var ongoing = currentRecords.filter(function (record) { return record.status === "in_progress" && record.type !== "project"; }).sort(cmpUpdated);
    var activePanel = panel(box, "In progress work");
    if (!ongoing.length) activePanel.appendChild(text("p", "No in-progress work items.", "empty"));
    ongoing.forEach(function (record) {
      var item = text("article", undefined, "record-row"), heading = text("h3");
      heading.appendChild(link(record.title || "Untitled", recordLink(record.id))); item.appendChild(heading);
      var meta = text("p", undefined, "meta"); statusText(meta, record.status);
      meta.appendChild(text("span", " · " + (record.type || "record")));
      meta.appendChild(text("span", " · Last recorded update: " + (record.updated_at || "unknown")));
      item.appendChild(meta);
      if (record.description) item.appendChild(text("p", record.description));
      activePanel.appendChild(item);
    });
    activePanel.appendChild(link("View projects", "/projects"));
    box.appendChild(link("View calendar", "/calendar")); box.appendChild(link("See all records", "/records"));
  };
  var calendarScreen = async function (route,serial) {var month=route.params.get("month")||nowDate().slice(0,7);if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))throw new Error("Invalid view. Reset view to continue.");if(!route.params.has("month"))go("/calendar",{month:month},true);var day=route.params.get("day")||"";if(day&&(!dateIsValid(day)||day.slice(0,7)!==month))throw new Error("Invalid view. Reset view to continue.");var box=routeBox("Calendar",month+" · UTC");setNav("calendar");var controls=text("div",undefined,"toolbar");var input=document.createElement("input");input.type="month";input.value=month;input.setAttribute("aria-label","Month (UTC)");input.addEventListener("change",function(){go("/calendar",{month:input.value,day:day});});controls.append(button("Previous month",function(){go("/calendar",{month:shiftMonth(month,-1),day:""});},"btn secondary"),button("Next month",function(){go("/calendar",{month:shiftMonth(month,1),day:""});},"btn secondary"),button("Today",function(){go("/calendar",{month:nowDate().slice(0,7)});},"btn secondary"),input);box.appendChild(controls);
    var reminders=await dataCall("reminders",month,"reminders/"+month+".json");if(serial!==token)return;var items=(reminders.items||[]).filter(function(x){return x.status!=="deprecated";});var grid=panel(box,"Important dates · Monday–Sunday");var table=text("table",undefined,"calendar-table");table.setAttribute("aria-label","Important dates calendar");var thead=document.createElement("thead"),headerRow=document.createElement("tr");["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].forEach(function(d){var th=text("th",d);th.scope="col";headerRow.appendChild(th);});thead.appendChild(headerRow);table.appendChild(thead);var tbody=document.createElement("tbody");var parts=month.split("-"),first=new Date(Date.UTC(+parts[0],+parts[1]-1,1)),offset=(first.getUTCDay()+6)%7,count=new Date(Date.UTC(+parts[0],+parts[1],0)).getUTCDate(),cells=[];for(var blank=0;blank<offset;blank++)cells.push(null);for(var n=1;n<=count;n++)cells.push(n);while(cells.length%7)cells.push(null);for(var rowIndex=0;rowIndex<cells.length;rowIndex+=7){var tr=document.createElement("tr");for(var col=0;col<7;col++){var td=document.createElement("td"),value=cells[rowIndex+col];if(value){var current=month+"-"+(value<10?"0":"")+value,hits=items.filter(function(x){return x.start_date<=current&&x.end_date>=current;});var cell=button(String(value)+(hits.length?" · "+hits.length:""),function(d){return function(){go("/calendar",{month:month,day:d});};}(current),"");cell.setAttribute("aria-label",current+(hits.length?": "+hits.length+" reminders":""));cell.setAttribute("aria-selected",String(current===day));if(current===nowDate())cell.setAttribute("aria-current","date");if(hits.length)cell.className+=" has-reminder";td.appendChild(cell);}tr.appendChild(td);}tbody.appendChild(tr);}table.appendChild(tbody);grid.appendChild(table);
    var agenda=panel(box,day?"Agenda · "+day:"Month agenda");var shown=items.filter(function(x){return day?x.start_date<=day&&x.end_date>=day:x.start_date.slice(0,7)<=month&&x.end_date.slice(0,7)>=month;});if(!shown.length)agenda.appendChild(text("p","No important dates in this period.","empty"));shown.forEach(function(item){var row=text("article",undefined,"record-row");row.appendChild(link(item.title,recordLink(item.record_id)));row.appendChild(text("p",item.text));row.appendChild(text("p",item.start_date===item.end_date?item.start_date:item.start_date+" – "+item.end_date,"meta"));statusText(row,item.status);agenda.appendChild(row);});agenda.appendChild(text("p","Important dates are not notifications.","meta"));if(day)agenda.appendChild(link("View changes on this day","/diary"+queryString({date:day,mode:"day"})));};
  var shiftMonth=function(month,delta){var p=month.split("-");var d=new Date(Date.UTC(+p[0],+p[1]-1+delta,1));return d.toISOString().slice(0,7);};
  var render = async function () {
    var serial=++token;app.setAttribute("aria-busy","true");var oldHash=window.location.hash;
    try { if(!manifest)await initialize(false); else if(api&&api.loadManifest){var check=await api.loadManifest({refresh:false});if(check.generation&&manifest.generation&&check.generation!==manifest.generation){var note=document.getElementById("update-available");if(!note){note=text("div","Update available. Refresh to load the new published generation.","update-banner");note.id="update-available";document.getElementById("app-footer").before(note);} }}
      if(serial!==token)return;var route=parseRoute();route=await resolveAliases(route,serial);if(serial!==token)return;setupSearch(route);setNav(route.name);
      if(route.name==="diary")await diaryScreen(route,serial);
      else if(route.name==="records"&&route.id)await recordScreen(route,serial);
      else if(route.name==="records")await recordsScreen(route,serial);
      else if(route.name==="events")await renderEvent(route,serial);
      else if(route.name==="projects")await projectsScreen(route,serial);
      else if(route.name==="today")await todayScreen(route,serial);
      else if(route.name==="calendar")await calendarScreen(route,serial);
      else {var box=routeBox("Page not found");box.appendChild(text("p","The requested page is not available."));box.appendChild(link("Go to diary","/diary"));}
      if(serial!==token)return;setupMobileNav();app.setAttribute("aria-busy","false");
      var headingNode=app.querySelector("h1");if(restoringHistory){var memory=routeMemory[window.location.hash||"#/diary"];if(memory){app.scrollTop=memory.scroll||0;if(memory.focusId&&document.getElementById(memory.focusId))document.getElementById(memory.focusId).focus();else if(headingNode)headingNode.focus();if(memory.windowY)window.scrollTo(0,memory.windowY);}else if(headingNode)headingNode.focus();}else if(headingNode)headingNode.focus();restoringHistory=false;pendingRoute=false;announce("Page loaded.");
    } catch(error){if(serial!==token)return;var box;if(error&&(/invalid view/i.test(error.message)||error.code&&error.code.indexOf("invalid_")===0)){box=routeBox("Invalid view");box.appendChild(text("p","The route contains an unsupported value."));box.appendChild(button("Reset view",function(){go("/diary",{},true);render();},"btn"));}else if(error&&(error.code==="unavailable"||error.status===404)){box=routeBox("Record unavailable in this view");box.appendChild(text("p","This record is unavailable in this view."));box.appendChild(button("Back",function(){window.history.back();},"btn secondary"));}else{box=routeBox("Knowledge Hub");fail(box,error,function(){manifest=null;render();});}app.setAttribute("aria-busy","false");var errorHeading=app.querySelector("h1");if(errorHeading)errorHeading.focus();}
  };
  document.addEventListener("click",function(event){var anchor=event.target.closest&&event.target.closest('a[href^="#/"]');if(anchor)saveRouteMemory();});
  window.addEventListener("hashchange",function(){pendingRoute=true;render();});
  window.addEventListener("popstate",function(){pendingRoute=true;restoringHistory=true;render();});
  document.getElementById("refresh").addEventListener("click",async function(){try{manifest=null;await initialize(true);var note=document.getElementById("update-available");if(note)note.remove();pendingRoute=true;render();}catch(e){announce("Refresh failed. Retry.");}});
  document.addEventListener("keydown",function(e){if(e.key==="Escape"){var details=document.querySelector("#filter-panel[open]");if(details){details.open=false;var trigger=document.getElementById("filter-toggle");if(trigger)trigger.focus();}}});
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(function(){});
  render();
}(window, document));
