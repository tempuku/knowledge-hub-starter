/* CommonMark/GFM renderer and DOM allowlist sanitizer. Raw HTML is disabled. */
(function (window, document) {
  "use strict";
  var allowed = {P:1,H1:1,H2:1,H3:1,H4:1,H5:1,H6:1,BR:1,HR:1,PRE:1,CODE:1,BLOCKQUOTE:1,OL:1,UL:1,LI:1,STRONG:1,EM:1,DEL:1,A:1,TABLE:1,THEAD:1,TBODY:1,TR:1,TH:1,TD:1,INPUT:1,SPAN:1};
  var safeUrl = function (value, base) {
    var raw=String(value||"").trim(); if(!raw||/[\u0000-\u0020]/.test(raw))return null;
    if(/^https?:\/\//i.test(raw))return raw;
    if(/^javascript:|^data:|^file:|^vbscript:|^mailto:/i.test(raw))return null;
    if(raw.charAt(0)==="#")return raw;
    if(/^(\/|\.\/|\.\.\/)/.test(raw)){try{var url=new URL(raw,base||window.location.href);return url.origin===window.location.origin?url.href:null;}catch(e){return null;}}
    return null;
  };
  var md = window.markdownit({html:false,linkify:false,typographer:false,breaks:false,quotes:"“”‘’"});
  md.enable(["table"]);
  md.core.ruler.after("inline","knowledge_hub_task_boxes",function(state){
    state.tokens.forEach(function(token){
      if(token.type!=="inline"||!/^\[([ xX])\]\s+/.test(token.content||""))return;
      var match=/^\[([ xX])\]\s+/.exec(token.content), children=token.children||[];
      token.content=token.content.slice(match[0].length);
      if(children.length&&children[0].type==="text")children[0].content=children[0].content.replace(/^\[([ xX])\]\s+/,"");
      var box=new state.Token("html_inline","",0);box.content='<input type="checkbox" disabled'+(match[1].toLowerCase()==="x"?' checked="checked"':'')+'> ';
      children.unshift(box);
    });
  });
  md.renderer.rules.image = function (tokens, index, options, env) {
    var token=tokens[index], alt=token.content||token.attrGet("alt")||"image", src=token.attrGet("src"), href=safeUrl(src,env.baseUrl);
    var label="Image: "+alt;
    if(!href)return "<span>"+md.utils.escapeHtml(label)+"</span>";
    return '<a data-kh-image="1" href="'+md.utils.escapeHtml(href)+'">'+md.utils.escapeHtml(label)+"</a>";
  };
  function sanitize(html, options) {
    var parsed=new DOMParser().parseFromString("<body><div>"+html+"</div></body>","text/html"), source=parsed.body.firstChild;
    function copy(node) {
      if(node.nodeType===3)return document.createTextNode(node.nodeValue);
      if(node.nodeType!==1)return document.createDocumentFragment();
      var tag=node.tagName, out;
      if(!allowed[tag]){var fragment=document.createDocumentFragment();Array.prototype.forEach.call(node.childNodes,function(child){fragment.appendChild(copy(child));});return fragment;}
      out=document.createElement(tag.toLowerCase());
      if(tag==="A"){
        var raw=node.getAttribute("href")||"", label=node.textContent||"", resolved=options.resolveLink?options.resolveLink(raw,label):null, canonical=/^record:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:#([^\s]*))?$/.exec(raw), href=resolved||(canonical?"#/records/"+canonical[1]+(canonical[2]?"#"+canonical[2]:""):null)||safeUrl(raw,options.baseUrl);
        if(href){out.setAttribute("href",href);if(/^https?:\/\//i.test(href)){out.setAttribute("target","_blank");out.setAttribute("rel","noopener noreferrer");out.setAttribute("aria-label",label+" (opens in a new tab)");}}
        else out.setAttribute("aria-disabled","true");
      } else if(tag==="TH")out.setAttribute("scope","col");
      else if(tag==="INPUT" && node.getAttribute("type")==="checkbox") {out.setAttribute("type","checkbox");out.disabled=true;out.checked=node.hasAttribute("checked");out.setAttribute("aria-label",out.checked?"Completed task":"Incomplete task");}
      Array.prototype.forEach.call(node.childNodes,function(child){out.appendChild(copy(child));});return out;
    }
    var root=document.createElement("div");root.className="markdown";Array.prototype.forEach.call(source.childNodes,function(child){root.appendChild(copy(child));});
    var slugCounts=Object.create(null);Array.prototype.forEach.call(root.querySelectorAll("h1,h2,h3,h4,h5,h6"),function(heading,index){var slug=(heading.textContent||"").toLowerCase().trim().replace(/\s+/g,"-").replace(/[^a-z0-9\u0080-\uFFFF-]/g,"");if(!slug)return;var count=slugCounts[slug]||0;slugCounts[slug]=count+1;heading.id=count?slug+"-"+(count+1):slug;});
    Array.prototype.forEach.call(root.querySelectorAll("table"),function(table){var wrap=document.createElement("div");wrap.className="table-scroll";table.parentNode.insertBefore(wrap,table);wrap.appendChild(table);});
    /* markdown-it's task-list syntax is emitted only by our controlled token rule. */
    Array.prototype.forEach.call(root.querySelectorAll("ul"),function(list){if(list.querySelector("input[type=checkbox]"))list.className="task-list";});
    return root;
  }
  function render(markdown, options) {
    options=options||{};var env={baseUrl:options.baseUrl||window.location.href};
    return sanitize(md.render(String(markdown||""),env),options);
  }
  window.KnowledgeV1Markdown={render:render,safeUrl:safeUrl};
}(window,document));
