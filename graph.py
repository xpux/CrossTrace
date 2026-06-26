"""
graph.py — turn CrossTrace results into an actual social graph.

CrossTrace is a "social graph analyser" but historically only ever emitted
flat CSV/JSON rows. This module reconstructs the graph those rows imply and
exports it in three forms:

    1. JSON      — nodes/edges, easy to load anywhere
    2. GraphML   — opens directly in Gephi, Cytoscape, yEd, etc.
    3. HTML      — a single self-contained file with an offline force-directed
                   viewer. No CDN, no network calls, no external assets, in
                   keeping with the tool's local-only privacy promise.

Nothing here makes a network request or reads anything beyond the results
passed in.
"""

import html
import json
from xml.sax.saxutils import escape as _xml_escape

VISIBLE_TIERS = ("AUTO-CONFIRMED", "QUICK REVIEW", "MANUAL REVIEW", "UNMATCHED_KEPT")


def _attr_escape(value):
    return _xml_escape(str(value), {'"': "&quot;", "'": "&apos;", "\t": "&#9;", "\n": "&#10;", "\r": "&#13;"})


def _node_id(username, display_name, platform):
    base = username or (display_name or "").lower().replace(" ", "_") or "unknown"
    return f"{base}@{platform or '?'}"


def _label(username, display_name):
    if username and display_name:
        return f"{username} / {display_name}"
    return username or display_name or "???"


def build_graph(results, mode="target", include_tiers=VISIBLE_TIERS, unmatched=None):
    nodes = {}
    edges = []
    include = set(include_tiers)

    def ensure_node(username, display_name, platform, kind="account", tier=None, score=None):
        nid = _node_id(username, display_name, platform)
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "label": _label(username, display_name),
                "username": username or "",
                "display_name": display_name or "",
                "platform": platform or "?",
                "kind": kind,
                "tier": tier or "",
                "score": score if score is not None else 0,
            }
        else:
            n = nodes[nid]
            if score is not None and score > n["score"]:
                n["score"] = score
            if tier and not n["tier"]:
                n["tier"] = tier
        return nid

    if mode == "discovery":
        for r in results:
            if r.get("tier") not in include:
                continue
            entry = r.get("entry", {})
            platforms = r.get("platforms", []) or ["?"]
            account_id = ensure_node(
                entry.get("username"),
                entry.get("display_name"),
                platforms[0],
                kind="account",
                tier=r.get("tier"),
                score=r.get("score", 0),
            )
            for seed in r.get("seen_by", []):
                seed_id = ensure_node(seed, "", "seed", kind="seed")
                edges.append({
                    "source": seed_id,
                    "target": account_id,
                    "weight": r.get("score", 0),
                    "kind": "seen_by",
                    "reasons": [],
                })
    else:
        for r in results:
            if r.get("tier") not in include:
                continue
            ea = r.get("entry_a", {})
            eb = r.get("entry_b", {})
            a_id = ensure_node(ea.get("username"), ea.get("display_name"),
                               ea.get("platform"), tier=r.get("tier"), score=r.get("score", 0))
            b_id = ensure_node(eb.get("username"), eb.get("display_name"),
                               eb.get("platform"), tier=r.get("tier"), score=r.get("score", 0))
            if a_id == b_id:
                continue
            edges.append({
                "source": a_id,
                "target": b_id,
                "weight": r.get("score", 0),
                "kind": "match",
                "reasons": r.get("reasons", []),
            })

    if unmatched:
        for r in unmatched:
            if r.get("tier") != "UNMATCHED_KEPT":
                continue
            entry = r.get("entry", {})
            ensure_node(entry.get("username"), entry.get("display_name"),
                        r.get("platform", "?"), kind="unmatched", tier="UNMATCHED_KEPT")

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {"mode": mode, "node_count": len(nodes), "edge_count": len(edges)},
    }


def export_json(graph, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    return path


def export_graphml(graph, path):
    # fix issue 13: use _attr_escape for all XML attribute values to prevent quote injection
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="platform" for="node" attr.name="platform" attr.type="string"/>',
        '  <key id="kind" for="node" attr.name="kind" attr.type="string"/>',
        '  <key id="tier" for="node" attr.name="tier" attr.type="string"/>',
        '  <key id="score" for="node" attr.name="score" attr.type="int"/>',
        '  <key id="weight" for="edge" attr.name="weight" attr.type="int"/>',
        '  <key id="reltype" for="edge" attr.name="reltype" attr.type="string"/>',
        '  <graph edgedefault="undirected">',
    ]
    for n in graph["nodes"]:
        lines.append(f'    <node id="{_attr_escape(n["id"])}">')
        lines.append(f'      <data key="label">{_attr_escape(n["label"])}</data>')
        lines.append(f'      <data key="platform">{_attr_escape(n["platform"])}</data>')
        lines.append(f'      <data key="kind">{_attr_escape(n["kind"])}</data>')
        lines.append(f'      <data key="tier">{_attr_escape(n["tier"])}</data>')
        lines.append(f'      <data key="score">{int(n["score"])}</data>')
        lines.append('    </node>')
    for i, e in enumerate(graph["edges"]):
        lines.append(f'    <edge id="e{i}" source="{_attr_escape(e["source"])}" target="{_attr_escape(e["target"])}">')
        lines.append(f'      <data key="weight">{int(e["weight"])}</data>')
        lines.append(f'      <data key="reltype">{_attr_escape(e["kind"])}</data>')
        lines.append('    </edge>')
    lines.append('  </graph>')
    lines.append('</graphml>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def export_html(graph, path, title="CrossTrace graph"):
    # fix issue 12: escape JSON payload for HTML script context to prevent XSS
    payload = (
        json.dumps(graph)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    doc = _HTML_TEMPLATE.replace("{{TITLE}}", html.escape(title)).replace("{{DATA}}", payload)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  :root { --bg:#0d1017; --panel:#161b25; --ink:#e6edf3; --muted:#8b97a7; --line:#2a3240; }
  * { box-sizing: border-box; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--ink);
    font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  #wrap { display:flex; height:100%; }
  #side { width:280px; flex:0 0 280px; background:var(--panel); border-right:1px solid var(--line);
    padding:16px; overflow:auto; }
  #side h1 { font-size:16px; margin:0 0 4px; letter-spacing:.04em; }
  #side .sub { color:var(--muted); margin:0 0 16px; font-size:12px; }
  #side label { display:block; color:var(--muted); font-size:11px; text-transform:uppercase;
    letter-spacing:.08em; margin:14px 0 4px; }
  #search { width:100%; padding:7px 9px; background:#0d1017; color:var(--ink);
    border:1px solid var(--line); border-radius:6px; }
  .legend div { display:flex; align-items:center; gap:8px; margin:5px 0; color:var(--muted); }
  .dot { width:11px; height:11px; border-radius:50%; flex:0 0 11px; }
  .stat { display:flex; justify-content:space-between; color:var(--muted); margin:3px 0; }
  .stat b { color:var(--ink); font-weight:600; }
  #detail { margin-top:16px; padding-top:14px; border-top:1px solid var(--line); min-height:60px; }
  #detail .none { color:var(--muted); }
  canvas { flex:1; display:block; cursor:grab; }
  canvas:active { cursor:grabbing; }
  .hint { color:var(--muted); font-size:11px; margin-top:18px; }
</style>
</head>
<body>
<div id="wrap">
  <div id="side">
    <h1>CrossTrace</h1>
    <p class="sub" id="modeline"></p>
    <label>Search</label>
    <input id="search" placeholder="filter by username…" autocomplete="off">
    <label>Stats</label>
    <div class="stat"><span>nodes</span><b id="nNodes">0</b></div>
    <div class="stat"><span>links</span><b id="nEdges">0</b></div>
    <label>Confidence</label>
    <div class="legend" id="legend"></div>
    <div id="detail"><span class="none">click a node for detail</span></div>
    <p class="hint">drag nodes · scroll to zoom · drag canvas to pan</p>
  </div>
  <canvas id="c"></canvas>
</div>
<script>
const GRAPH = {{DATA}};
const TIER_COLOR = {
  "AUTO-CONFIRMED":"#3fb950", "QUICK REVIEW":"#d29922", "MANUAL REVIEW":"#db6d28",
  "UNMATCHED_KEPT":"#8b949e", "":"#58a6ff"
};
const KIND_COLOR = { "seed":"#a371f7", "unmatched":"#6e7681" };
function colorFor(n){ if(KIND_COLOR[n.kind]) return KIND_COLOR[n.kind];
  return TIER_COLOR[n.tier] || "#58a6ff"; }

const cv = document.getElementById("c"), ctx = cv.getContext("2d");
const nodes = GRAPH.nodes.map(n => ({...n, x:0, y:0, vx:0, vy:0}));
const byId = {}; nodes.forEach(n => byId[n.id] = n);
const edges = GRAPH.edges.filter(e => byId[e.source] && byId[e.target]);
const adj = {}; nodes.forEach(n => adj[n.id]=0);
edges.forEach(e => { adj[e.source]++; adj[e.target]++; });

document.getElementById("modeline").textContent = "mode: " + (GRAPH.meta?.mode || "—");
document.getElementById("nNodes").textContent = nodes.length;
document.getElementById("nEdges").textContent = edges.length;
(function(){ const seen={}, L=document.getElementById("legend");
  nodes.forEach(n=>{ const k=n.kind==="seed"?"seed user":n.kind==="unmatched"?"single-platform":(n.tier||"matched");
    seen[k]=colorFor(n); });
  Object.entries(seen).forEach(([k,c])=>{ const d=document.createElement("div");
    d.innerHTML='<span class="dot" style="background:'+c+'"></span>'+k; L.appendChild(d); }); })();

let W=0,H=0,DPR=Math.min(window.devicePixelRatio||1,2);
function resize(){ const r=cv.getBoundingClientRect(); W=r.width; H=r.height;
  cv.width=W*DPR; cv.height=H*DPR; ctx.setTransform(DPR,0,0,DPR,0,0); }
window.addEventListener("resize", resize); resize();

let cx=W/2, cy=H/2;
nodes.forEach((n,i)=>{ const a=i/nodes.length*Math.PI*2, rad=Math.min(W,H)*0.32;
  n.x=cx+Math.cos(a)*rad*(0.5+Math.random()*0.5); n.y=cy+Math.sin(a)*rad*(0.5+Math.random()*0.5); });

let view={x:0,y:0,k:1};
function tick(){
  for(let i=0;i<nodes.length;i++){ const a=nodes[i];
    for(let j=i+1;j<nodes.length;j++){ const b=nodes[j];
      let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+0.01, d=Math.sqrt(d2);
      const f=2600/d2; const ux=dx/d, uy=dy/d;
      a.vx+=ux*f; a.vy+=uy*f; b.vx-=ux*f; b.vy-=uy*f; } }
  edges.forEach(e=>{ const a=byId[e.source], b=byId[e.target];
    let dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)+0.01;
    const target=90, f=(d-target)*0.012, ux=dx/d, uy=dy/d;
    a.vx+=ux*f; a.vy+=uy*f; b.vx-=ux*f; b.vy-=uy*f; });
  nodes.forEach(n=>{ n.vx+=(cx-n.x)*0.0009; n.vy+=(cy-n.y)*0.0009;
    if(n===drag) return; n.x+=n.vx*=0.86; n.y+=n.vy*=0.86; });
}
function draw(){
  ctx.clearRect(0,0,W,H); ctx.save();
  ctx.translate(view.x,view.y); ctx.scale(view.k,view.k);
  ctx.lineWidth=1;
  edges.forEach(e=>{ const a=byId[e.source], b=byId[e.target];
    ctx.strokeStyle="rgba(120,140,170,"+(0.12+0.5*(e.weight/100))+")";
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); });
  nodes.forEach(n=>{ const r=5+Math.min(adj[n.id],10)*1.1;
    const dim = filterText && n.username.indexOf(filterText)<0 && n.label.toLowerCase().indexOf(filterText)<0;
    ctx.globalAlpha = dim?0.15:1;
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,Math.PI*2);
    ctx.fillStyle=colorFor(n); ctx.fill();
    if(n===selected){ ctx.lineWidth=2; ctx.strokeStyle="#fff"; ctx.stroke(); }
    if(view.k>0.75 || n===selected){ ctx.globalAlpha=dim?0.15:0.85;
      ctx.fillStyle="#c9d4e0"; ctx.font="11px ui-monospace,monospace";
      ctx.fillText(n.username||n.label, n.x+r+3, n.y+3); }
    ctx.globalAlpha=1; });
  ctx.restore();
}
function loop(){ for(let s=0;s<2;s++) tick(); draw(); requestAnimationFrame(loop); }
loop();

let drag=null, selected=null, panning=false, last=null, filterText="";
function worldPos(ev){ const r=cv.getBoundingClientRect();
  return { x:(ev.clientX-r.left-view.x)/view.k, y:(ev.clientY-r.top-view.y)/view.k }; }
function pick(p){ let best=null, bd=400;
  nodes.forEach(n=>{ const dx=n.x-p.x, dy=n.y-p.y, d=dx*dx+dy*dy;
    if(d<bd){ bd=d; best=n; } }); return best; }
cv.addEventListener("mousedown",ev=>{ const p=worldPos(ev), n=pick(p);
  if(n){ drag=n; selected=n; showDetail(n); } else { panning=true; last={x:ev.clientX,y:ev.clientY}; selected=null; showDetail(null); } });
window.addEventListener("mousemove",ev=>{ if(drag){ const p=worldPos(ev); drag.x=p.x; drag.y=p.y; drag.vx=drag.vy=0; }
  else if(panning){ view.x+=ev.clientX-last.x; view.y+=ev.clientY-last.y; last={x:ev.clientX,y:ev.clientY}; } });
window.addEventListener("mouseup",()=>{ drag=null; panning=false; });
cv.addEventListener("wheel",ev=>{ ev.preventDefault(); const f=ev.deltaY<0?1.1:0.9;
  const r=cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  view.x=mx-(mx-view.x)*f; view.y=my-(my-view.y)*f; view.k*=f; },{passive:false});
document.getElementById("search").addEventListener("input",e=>{ filterText=e.target.value.trim().toLowerCase(); });
function showDetail(n){ const d=document.getElementById("detail");
  if(!n){ d.innerHTML='<span class="none">click a node for detail</span>'; return; }
  const inc=edges.filter(e=>e.source===n.id||e.target===n.id);
  let rows=inc.slice(0,8).map(e=>{ const other=byId[e.source===n.id?e.target:e.source];
    return '<div class="stat"><span>'+escapeHtml(other.username||other.label)+'</span><b>'+e.weight+'%</b></div>'; }).join("");
  d.innerHTML='<div style="color:#e6edf3;font-weight:600;margin-bottom:6px">'+escapeHtml(n.label)+'</div>'+
    '<div class="stat"><span>platform</span><b>'+escapeHtml(n.platform)+'</b></div>'+
    '<div class="stat"><span>tier</span><b>'+escapeHtml(n.tier||n.kind)+'</b></div>'+
    '<div class="stat"><span>connections</span><b>'+inc.length+'</b></div>'+
    (rows?'<label>linked to</label>'+rows:'');
}
function escapeHtml(s){ return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
</script>
</body>
</html>
"""