from flask import Flask, request, jsonify, render_template_string
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saferoute_web.db")

# Simple, explainable project score; it is not a verified safety rating.
def risk_score(lighting, crowd, security, incidents, transport):
    values = [
        {"Good":0,"Medium":1,"Poor":2}.get(lighting,1),
        {"High":0,"Medium":1,"Low":2}.get(crowd,1),
        {"Good":0,"Medium":1,"Poor":2}.get(security,1),
        {"Low":0,"Medium":1,"High":2}.get(incidents,1),
        {"Available":0,"Limited":1,"None":2}.get(transport,1)
    ]
    score = sum(values)
    return score, "LOWER" if score <= 2 else ("MODERATE" if score <= 5 else "HIGHER")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY,name TEXT,start TEXT,destination TEXT,distance REAL,minutes INTEGER,lighting TEXT,crowd TEXT,security TEXT,incidents TEXT,transport TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY,name TEXT,phone TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS journeys(id INTEGER PRIMARY KEY,start TEXT,destination TEXT,route TEXT,score INTEGER,created TEXT,status TEXT DEFAULT 'PLANNED',completed TEXT)")
        journey_cols={row[1] for row in c.execute("PRAGMA table_info(journeys)").fetchall()}
        if "status" not in journey_cols: c.execute("ALTER TABLE journeys ADD COLUMN status TEXT DEFAULT 'PLANNED'")
        if "completed" not in journey_cols: c.execute("ALTER TABLE journeys ADD COLUMN completed TEXT")
        c.execute("CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY,location TEXT,category TEXT,description TEXT,created TEXT,status TEXT,latitude REAL,longitude REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS lighting_reports(id INTEGER PRIMARY KEY,journey_id INTEGER NOT NULL,start TEXT,destination TEXT,route TEXT,category TEXT,description TEXT,created TEXT,status TEXT,latitude REAL,longitude REAL)")
        if c.execute("SELECT COUNT(*) FROM routes").fetchone()[0]==0:
            c.executemany("INSERT INTO routes(name,start,destination,distance,minutes,lighting,crowd,security,incidents,transport) VALUES(?,?,?,?,?,?,?,?,?,?)",[
            ("Route A - Main Road","ASIET","Perumbavoor",18,40,"Good","High","Good","Low","Available"),
            ("Route B - Town Road","ASIET","Perumbavoor",16.5,36,"Medium","Medium","Medium","Medium","Available"),
            ("Route C - Shortcut","ASIET","Perumbavoor",15,32,"Poor","Low","Poor","High","Limited"),
            ("Route D - Highway","ASIET","Aluva",25,50,"Good","Medium","Good","Low","Available"),
            ("Route E - Local Road","ASIET","Aluva",22,55,"Medium","Low","Medium","Medium","Limited")])

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SafeRoute | Journey safety</title><style>
:root{--navy:#101c32;--blue:#2864e8;--teal:#12b8a6;--ink:#17243b;--muted:#66758b;--line:#e4eaf2;--bg:#f4f7fb}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:15px}body{margin:0;background:var(--bg);color:var(--ink);font:14px system-ui,-apple-system,"Segoe UI",sans-serif}
.ticker{background:#10213b;color:#dce8ff;padding:9px 20px;font-size:11px;white-space:nowrap;overflow:hidden}.ticker b{color:#6de0d2}
header{height:72px;background:white;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 25px;gap:12px;position:sticky;top:0;z-index:4}.logo{width:40px;height:40px;border-radius:13px;background:linear-gradient(135deg,#2864e8,#14b8a6);display:grid;place-items:center;color:white;font-size:24px;font-weight:900}.brand strong{display:block;font-size:20px}.brand small{color:var(--muted);font-size:11px}.status{margin-left:auto;color:#587069;font-size:12px}
.layout{display:flex;min-height:calc(100vh - 100px)}aside{background:var(--navy);width:220px;padding:24px 12px;flex-shrink:0;display:flex;flex-direction:column;gap:5px}aside label{font-size:10px;letter-spacing:1px;color:#8495b4;padding:0 13px 10px;font-weight:bold}aside a{color:#bdc9dd;text-decoration:none;padding:12px;border-radius:9px}aside a:hover{background:#203452;color:white}.note-side{margin-top:auto;border:1px solid #2a3b58;border-radius:10px;padding:13px;color:#aab9d0;font-size:11px;line-height:1.6}
main{flex:1;min-width:0;max-width:1500px;margin:auto;padding:25px 28px 40px}.welcome{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:20px}.eyebrow{color:#5377b7;font-size:10px;letter-spacing:1.4px;font-weight:800;margin:0 0 8px}.welcome h1{font-size:32px;letter-spacing:-1px;margin:0 0 8px}.muted{color:var(--muted);line-height:1.6;margin:0}.small{font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.stat,.panel{background:white;border:1px solid var(--line);border-radius:15px;box-shadow:0 7px 22px #1a2b4b08}.stat{padding:16px}.stat small{display:block;color:var(--muted);font-size:11px}.stat strong{display:block;font-size:25px;margin:5px 0}.panel{padding:22px;margin-bottom:18px}.heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:15px}.heading h2{font-size:20px;margin:0}.tag{background:#edf3ff;color:#3b63b4;border-radius:20px;padding:7px 10px;font-size:10px;font-weight:800;white-space:nowrap}
form.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}label.field{display:flex;flex-direction:column;gap:7px;font-size:12px;font-weight:700;color:#3b4a62}.wide{grid-column:1/-1}input,select,textarea{width:100%;padding:11px 12px;border:1px solid #dce4ef;border-radius:9px;font:inherit;color:var(--ink);background:white}textarea{resize:vertical}.btn{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:9px;padding:11px 14px;font:inherit;font-size:12px;font-weight:800;cursor:pointer;text-decoration:none}.primary{background:var(--blue);color:white}.outline{border:1px solid #dbe3ef;background:white;color:#34445e}.actions{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:15px}.msg{font-size:12px;color:#087f68}
.routes{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}.route{border:1px solid var(--line);border-radius:12px;padding:15px}.route h3{font-size:14px;margin:8px 0 4px}.risk{float:right;border-radius:20px;padding:5px 7px;font-size:9px;font-weight:900}.LOWER{background:#ddf8eb;color:#117c52}.MODERATE{background:#fff2d5;color:#9a6700}.HIGHER{background:#ffe4e8;color:#b4233d}.metrics{display:flex;justify-content:space-between;border-block:1px solid #edf0f5;padding:12px 0;margin:12px 0;font-size:11px}.indicators{display:grid;gap:6px;color:var(--muted);font-size:11px;margin-bottom:13px}.indicators span{display:flex;justify-content:space-between}.locbox{background:#f8fbff;border:1px solid #dce8f4;border-radius:11px;padding:15px}.sos{background:#d92d48;color:white;font-size:14px;padding:14px 20px}.redpanel{border-color:#ffd6dd;background:#fffdfd}.notice{background:#f5f8fc;color:#6c7a90;font-size:11px;line-height:1.6;padding:11px 13px;border-radius:9px;margin-top:13px}.contacts,.reports{display:grid;gap:8px;margin-top:14px}.contact,.report{border:1px solid #e8edf4;border-radius:10px;padding:12px;display:flex;gap:10px;align-items:center}.contact-info{flex:1}.contact-info small{display:block;color:var(--muted);margin-top:4px}.mini{font-size:11px;border:0;border-radius:7px;padding:7px 9px;background:#edf3ff;color:#2859bd;text-decoration:none;cursor:pointer}.remove{background:#fff0f2;color:#b4233d}footer{text-align:center;color:#9aa6b7;font-size:10px;padding:10px}
@media(max-width:1050px){.stats{grid-template-columns:repeat(2,1fr)}.routes{grid-template-columns:repeat(2,1fr)}}@media(max-width:720px){.layout{display:block}aside{width:100%;display:flex;flex-direction:row;overflow:auto;padding:8px;position:sticky;top:72px;z-index:3}aside label,.note-side{display:none}aside a{white-space:nowrap;font-size:11px;padding:10px}main{padding:18px 12px}.welcome{align-items:flex-start;flex-direction:column}.welcome h1{font-size:26px}.stats{gap:8px}.stat{padding:12px}.stat strong{font-size:21px}.panel{padding:16px}.routes{grid-template-columns:1fr}form.grid{grid-template-columns:1fr}.wide{grid-column:auto}.heading h2{font-size:18px}}@media print{aside,.btn,.actions{display:none!important}.layout{display:block}main{padding:0}.panel,.stat{box-shadow:none;break-inside:avoid}}
</style><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"></head><body>
<div class="ticker"><b>SAFER JOURNEYS START WITH A PLAN</b> &nbsp; • &nbsp; Check route indicators &nbsp; • &nbsp; Keep trusted contacts close &nbsp; • &nbsp; In immediate danger contact official emergency services</div>
<header><div class="logo">S</div><div class="brand"><strong>SafeRoute</strong><small>Personal Safety-Aware Journey Planning System</small></div><div class="status">● Safety workspace</div></header>
<div class="layout"><aside><label>WORKSPACE</label><a href="#dashboard">⌂ Dashboard</a><a href="#journey">➤ Plan journey</a><a href="#routes">⇄ Route comparison</a><a href="#location">◎ Live location</a><a href="#emergency">✚ Emergency SOS</a><a href="#contacts">♡ Trusted contacts</a><a href="#incidents">⚑ Report incident</a><a href="#myjourneys">✓ My journeys</a><div class="note-side"><b>Prototype note</b><br>Route indicators are sample data, not a guarantee of safety.</div></aside>
<main><section id="dashboard" class="welcome"><div><p class="eyebrow">PERSONAL SAFETY • JOURNEY PLANNING</p><h1>Plan smarter. Travel prepared.</h1><p class="muted">Plan journeys, compare route indicators, and keep trusted contacts close.</p></div><button class="btn outline" onclick="window.print()">Print overview ↗</button></section>
<div class="stats"><div class="stat"><small>Routes available</small><strong>{{counts.routes}}</strong><small>Sample profiles</small></div><div class="stat"><small>Journeys planned</small><strong>{{counts.journeys}}</strong><small>Saved journeys</small></div><div class="stat"><small>Incident reports</small><strong>{{counts.incidents}}</strong><small>Unverified reports</small></div><div class="stat"><small>Trusted contacts</small><strong>{{counts.contacts}}/2</strong><small>Quick emergency contacts</small></div></div>
<section id="journey" class="panel"><div class="heading"><div><p class="eyebrow">JOURNEY PLANNER</p><h2>Where are you going?</h2></div><span class="tag">01 · PLAN</span></div><form class="grid" onsubmit="event.preventDefault();planJourney()"><label class="field">Starting point<input id="start" placeholder="e.g. ASIET, Kalady" required></label><label class="field">Destination<input id="dest" placeholder="e.g. Perumbavoor" required></label><div class="field wide"><span>Travel preference</span><select id="travelMode"><option value="driving">Driving / car</option><option value="walking">Walking</option><option value="cycling">Cycling</option></select><small class="muted">Routes are requested from OpenStreetMap-based services for the locations you enter.</small></div></form><div class="actions"><button type="button" class="btn primary" onclick="findRoutes()">Find routes</button><button type="button" class="btn outline" onclick="useCurrentLocation()">Use my current location</button><button type="button" class="btn outline" onclick="directions()">Open Google Maps directions ↗</button><span id="journeyMsg" class="msg"></span></div><div id="dynamicRoutes" class="routes" aria-live="polite"></div><div id="routeMap" style="height:380px;border-radius:12px;margin-top:14px;display:none"></div><div class="notice">Interactive map: zoom and drag to inspect the selected route. Press <b>Start journey</b> on a route to open Google Maps directions for that route and travel mode. This demo draws its preview using OpenStreetMap; turn-by-turn navigation is provided by Google Maps. Distance and duration come from the routing service. Alternative routes depend on availability. Safety indicators are not live verified data and are not inferred from route length.</div></section>
<section id="routes" class="panel"><div class="heading"><div><p class="eyebrow">ROUTE COMPARISON</p><h2>Understand route indicators</h2></div><span class="tag">02 · COMPARE</span></div><p class="muted small">Routes shown here are generated from the start and destination entered in Journey Planner. Use the map/navigation service for current road conditions. SafeRoute does not currently have verified, live lighting, crowd, or incident data for each route.</p><div class="actions"><button class="btn outline" onclick="refreshRouteSafety()">Refresh lighting reports</button><span id="lightingRefreshStatus" class="muted small">Updates automatically every 60 seconds after route search.</span></div><div id="routeSummary" class="locbox">Enter a starting point and destination above, then select <b>Find routes</b>.</div></section>
<section id="location" class="panel"><div class="heading"><div><p class="eyebrow">LOCATION SERVICES</p><h2>Live location</h2></div><span class="tag">03 · LOCATE</span></div><div class="locbox"><b id="locStatus">Location not started</b><p id="coords" class="muted small">Press Get my location and allow browser access.</p><p id="accuracy" class="muted small"></p></div><div class="actions"><button class="btn primary" onclick="getLocation()">Get my location</button><button class="btn outline" onclick="openMap()">Open location in Google Maps ↗</button><button class="btn outline" onclick="stopLocation()">Stop updates</button></div><div class="notice">Location accuracy depends on your device and browser permissions. This demo does not continuously share your location with contacts.</div></section>
<section id="emergency" class="panel redpanel"><div class="heading"><div><p class="eyebrow">QUICK RESPONSE</p><h2>Emergency assistance</h2></div><span class="tag" style="background:#ffebef;color:#bf263e">SOS</span></div><p class="muted">Save up to two trusted contacts. SOS prepares a message with your latest location link and offers calling/messaging shortcuts.</p><div class="actions"><button class="btn sos" onclick="prepareSOS()">SOS · Prepare alert</button><a class="btn outline" href="tel:112">Call India emergency number 112 ↗</a></div><div id="sosBox" class="locbox" style="display:none;margin-top:13px"></div><div class="notice" style="background:#fff0f2;color:#a3394c">The site cannot silently call or guarantee SMS delivery. Review and send messages in your phone app. For real emergencies, contact official services.</div></section>
<section id="contacts" class="panel"><div class="heading"><div><p class="eyebrow">PEOPLE YOU TRUST</p><h2>Emergency contacts</h2></div><span class="tag">MAXIMUM 2</span></div><form class="grid" onsubmit="event.preventDefault();saveContact()"><label class="field">Contact name<input id="cname" placeholder="e.g. Amma" required></label><label class="field">Phone number<input id="cphone" type="tel" placeholder="e.g. +91 9876543210" required></label></form><div class="actions"><button class="btn primary" onclick="saveContact()">Save trusted contact</button><span id="contactMsg" class="msg"></span></div><div id="contactList" class="contacts">{% for c in contacts %}<div class="contact"><div class="contact-info"><b>{{c.name}}</b><small>{{c.phone}}</small></div><a class="mini" href="tel:{{c.phone}}">Call</a><button class="mini remove" onclick="deleteContact({{c.id}})">Remove</button></div>{% endfor %}</div></section>
<section id="myjourneys" class="panel"><div class="heading"><div><p class="eyebrow">JOURNEY HISTORY</p><h2>My saved journeys</h2></div><span class="tag">05 · COMPLETE</span></div><p class="muted small">Save a route, then mark it completed when you arrive. After completing it, add a lighting report based on what you actually observed.</p><div id="journeyHistory" class="reports">{% for j in saved_journeys %}<div class="report" style="align-items:flex-start"><div style="flex:1"><b>{{j.start}} → {{j.destination}}</b><p class="muted small">{{j.route}}</p><small>Planned: {{j.created}} · Status: <b>{{j.status}}</b>{% if j.completed %} · Completed: {{j.completed}}{% endif %}</small>{% if j.status != 'COMPLETED' %}<div class="actions"><button class="btn primary" onclick="completeJourney({{j.id}})">Mark journey completed</button></div>{% else %}<p class="muted small">Thank you for completing this journey. Share what you observed on this route.</p><form class="grid" style="margin-top:10px" onsubmit="event.preventDefault();submitLightingReport({{j.id}})"><label class="field">Lighting condition<select id="light-category-{{j.id}}"><option value="High">High — road was well lit</option><option value="Medium">Medium — some areas were dim</option><option value="Low">Low — road was very dark</option><option value="Broken streetlights">Broken streetlights</option></select></label><label class="field">Where on the route? (optional)<input id="light-location-{{j.id}}" placeholder="Street, landmark or area"></label><label class="field wide">Details (optional)<textarea id="light-description-{{j.id}}" rows="2" placeholder="Describe the lighting you observed"></textarea></label><div class="wide"><button type="submit" class="btn primary">Submit lighting report</button><span id="light-msg-{{j.id}}" class="msg" style="margin-left:8px"></span></div></form>{% endif %}</div></div>{% else %}<p class="muted small">No saved journeys yet. Find a route and press “Save journey” to begin.</p>{% endfor %}</div><div class="notice">Prototype note: journeys are stored in this website's local database and are not linked to a verified user account. Anyone with access to this same website instance may see the saved journey list.</div></section>
<section id="incidents" class="panel"><div class="heading"><div><p class="eyebrow">COMMUNITY AWARENESS</p><h2>Report a route incident</h2></div><span class="tag">04 · REPORT</span></div><form class="grid" onsubmit="event.preventDefault();reportIncident()"><label class="field">Location<input id="iloc" placeholder="Street, landmark or area" required></label><label class="field">Category<select id="icat"><option>Road hazard</option><option>Lighting good / bright</option><option>Lighting moderate</option><option>Poor lighting / dark road</option><option>Streetlight not working</option><option>Harassment concern</option><option>Transport issue</option><option>Crowded area</option><option>Low crowd / isolated area</option><option>Other</option></select></label><label class="field wide">Description<textarea id="idesc" rows="3" placeholder="Describe the issue clearly" required></textarea></label></form><div class="actions"><button class="btn primary" onclick="reportIncident()">Submit incident report</button><span id="incidentMsg" class="msg"></span></div><div class="notice">Lighting status is estimated from community reports submitted for the route area, not a live brightness sensor. Reports are UNVERIFIED. No mapped lights does not prove a road is dark. Reports are saved to this website instance; public sharing needs hosting with persistent storage and moderation.</div><div id="reportList" class="reports">{% for i in incidents %}<div class="report"><div><b>{{i.category}}</b><p class="muted small">{{i.location}} — {{i.description}}</p><small>{{i.created}}</small></div><span class="risk MODERATE">{{i.status}}</span></div>{% endfor %}</div></section>
<footer>SafeRoute prototype · Journey awareness and emergency preparedness · Not a replacement for official emergency services.</footer></main></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
let pos=null, watch=null, map=null, routeLayers=[], selectedRoute=null, foundRoutes=[];
const $=id=>document.getElementById(id);
async function api(url,method="GET",data=null){const r=await fetch(url,{method,headers:{"Content-Type":"application/json"},...(data?{body:JSON.stringify(data)}:{})});const j=await r.json();if(!r.ok)throw Error(j.error||"Request failed");return j}
function msg(id,t,bad=false){$(id).textContent=t;$(id).style.color=bad?"#b4233d":"#087f68"}
function pickRoute(index){selectedRoute=foundRoutes[index];if(!selectedRoute)return;document.querySelectorAll("[data-route-index]").forEach(el=>el.style.borderColor="#e4eaf2");let card=document.querySelector('[data-route-index="'+index+'"]');if(card)card.style.borderColor="#2864e8";drawSelectedRoute(index);$("journeyMsg").textContent="Route selected. You can save this journey."; }
async function geocode(place){const u="https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q="+encodeURIComponent(place);const r=await fetch(u,{headers:{"Accept":"application/json"}});if(!r.ok)throw Error("Map search is temporarily unavailable. Try again or use Google Maps.");const a=await r.json();if(!a.length)throw Error('Could not find "'+place+'". Try adding a town or district.');return {lat:Number(a[0].lat),lon:Number(a[0].lon),label:a[0].display_name}}
async function findRoutes(){const start=$("start").value.trim(),destination=$("dest").value.trim(),mode=$("travelMode").value;if(!start||!destination)return msg("journeyMsg","Enter both locations first.",true);msg("journeyMsg","Finding locations and calculating routes…");$("dynamicRoutes").innerHTML="";try{const [a,b]=await Promise.all([geocode(start),geocode(destination)]);const profile=mode==="walking"?"foot":mode==="cycling"?"bike":"driving";const url=`https://router.project-osrm.org/route/v1/${profile}/${a.lon},${a.lat};${b.lon},${b.lat}?alternatives=3&overview=full&geometries=geojson&steps=false`;const res=await fetch(url);if(!res.ok)throw Error("Routing service is unavailable right now.");const data=await res.json();if(data.code!=="Ok"||!data.routes?.length)throw Error("No route found between these locations. Try more specific place names.");foundRoutes=data.routes.map((r,i)=>({...r,index:i,start:a,destination:b,mode}));$("routeSummary").innerHTML="<b>Route search:</b> "+esc(a.label)+" → "+esc(b.label)+"<br><small>Found "+foundRoutes.length+" route option(s). Exact alternatives depend on map data.</small>";renderRoutes();setupMap();drawSelectedRoute(0);foundRoutes.forEach((r,i)=>loadRouteSafety(r,i));msg("journeyMsg","Routes loaded. Checking community lighting reports…");}catch(e){msg("journeyMsg",e.message,true);$("routeSummary").textContent=e.message}}
function renderRoutes(){const root=$("dynamicRoutes");root.innerHTML="";foundRoutes.forEach((r,i)=>{const card=document.createElement("article");card.className="route";card.dataset.routeIndex=i;const km=(r.distance/1000).toFixed(1),mins=Math.max(1,Math.round(r.duration/60));card.innerHTML=`<div style="color:#3769d7;font-size:19px">↗</div><h3>${i===0?"Recommended route": "Alternative route "+i}</h3><p class="muted small">${esc($("start").value.trim())} → ${esc($("dest").value.trim())}</p><div class="metrics"><span><b>${km} km</b><br>Distance</span><span><b>${mins} min</b><br>Estimated time</span></div><div class="indicators" id="safety-${i}"><span>Community lighting status <b>Checking recent reports…</b></span><span>Crowd level <b>No live data</b></span><span>Reported incidents <b>Checking reports…</b></span></div><p class="muted small">Lighting status is based on recent community reports, not a brightness sensor. Unknown means there is not enough information. Reports are unverified.</p><div class="actions"><button type="button" class="btn outline" onclick="pickRoute(${i})">Select route</button><button type="button" class="btn primary" onclick="startJourney(${i})">▶ Start journey</button><button type="button" class="btn outline" onclick="saveSelectedRoute(${i})">Save journey</button><button type="button" class="btn outline" onclick="openGoogleRoute(${i})">Open in Google Maps ↗</button></div>`;root.append(card)})}
async function refreshRouteSafety(){if(!foundRoutes.length){msg("lightingRefreshStatus","Find a route first.",true);return}msg("lightingRefreshStatus","Refreshing reports…");await Promise.all(foundRoutes.map((r,i)=>loadRouteSafety(r,i)));msg("lightingRefreshStatus","Last checked: "+new Date().toLocaleTimeString()+" · auto-refresh every 60 seconds")};setInterval(()=>{if(foundRoutes.length)refreshRouteSafety()},60000);
async function loadRouteSafety(route,index){const box=$("safety-"+index);if(!box)return;try{const coords=route.geometry.coordinates;const stride=Math.max(1,Math.floor(coords.length/18));const sample=coords.filter((_,i)=>i%stride===0);if(sample[sample.length-1]!==coords[coords.length-1])sample.push(coords[coords.length-1]);const res=await api("/api/route-safety","POST",{coordinates:sample});const lighting=res.lighting_status||"Unknown";const lightColor=lighting==="High"?"#18743a":lighting==="Medium"?"#946200":lighting==="Low"?"#b42318":"#596579";const lightDetail=res.lighting_summary||"No recent community lighting reports";const incidents=res.incidents===null?"Unavailable":res.incidents.length?`${res.incidents.length} report(s) · UNVERIFIED`:"No reports in local database";const crowd=res.crowd_reports===null?"No live data":res.crowd_reports>0?`${res.crowd_reports} user report(s) · UNVERIFIED`:"No crowd reports";box.innerHTML=`<span>Community lighting status <b style="color:${lightColor}">${esc(lighting)}</b></span><span>Lighting reports <b>${esc(lightDetail)}</b></span><span>Mapped streetlights <b>${res.streetlights===null?"Unavailable":res.streetlights+" nearby (not proof lights work)"}</b></span><span>Crowd level <b>${esc(crowd)}</b></span><span>Reported incidents <b>${esc(incidents)}</b></span><span>Last checked <b>${esc(res.checked_at||"Unknown")}</b></span>`;if(res.incidents?.length){const extra=document.createElement("div");extra.className="notice";extra.innerHTML="<b>Reports near this route:</b><br>"+res.incidents.map(x=>`${esc(x.category)} — ${esc(x.location)} (${esc(x.created)})`).join("<br>");box.after(extra)}}catch(e){box.innerHTML="<span>Community lighting status <b>Unknown</b></span><span>Crowd level <b>No live data</b></span><span>Reported incidents <b>Could not check</b></span>"}}
function setupMap(){const box=$("routeMap");box.style.display="block";if(!map){map=L.map("routeMap").setView([foundRoutes[0].start.lat,foundRoutes[0].start.lon],12);L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:'&copy; OpenStreetMap contributors',maxZoom:19}).addTo(map)}routeLayers.forEach(l=>map.removeLayer(l));routeLayers=[];setTimeout(()=>map.invalidateSize(),100)}
function drawSelectedRoute(index){const r=foundRoutes[index];if(!r||!map)return;routeLayers.forEach(l=>map.removeLayer(l));routeLayers=[];const coords=r.geometry.coordinates.map(c=>[c[1],c[0]]);const line=L.polyline(coords,{color:"#2864e8",weight:5}).addTo(map);const start=L.marker([r.start.lat,r.start.lon]).bindPopup("Start: "+esc($("start").value)).addTo(map);const end=L.marker([r.destination.lat,r.destination.lon]).bindPopup("Destination: "+esc($("dest").value)).addTo(map);routeLayers=[line,start,end];map.fitBounds(line.getBounds(),{padding:[20,20]});selectedRoute=r}
async function saveSelectedRoute(index){const r=foundRoutes[index];if(!r)return;try{await api("/api/journeys","POST",{start:$("start").value.trim(),destination:$("dest").value.trim(),route:"Dynamic route "+(index+1)+" · "+(r.distance/1000).toFixed(1)+" km · "+Math.round(r.duration/60)+" min",score:0});msg("journeyMsg","Journey saved. See My journeys below to mark it completed.");setTimeout(()=>location.reload(),700)}catch(e){msg("journeyMsg",e.message,true)}}
async function completeJourney(id){if(!confirm("Have you reached your destination and completed this journey?"))return;try{const r=await api("/api/journeys","PATCH",{id,status:"COMPLETED"});alert(r.message+" You can now rate the lighting on this journey.");location.reload()}catch(e){alert(e.message)}}
async function submitLightingReport(id){const category=$("light-category-"+id).value;const locationText=$("light-location-"+id).value.trim();const description=$("light-description-"+id).value.trim();const data={journey_id:id,category,location:locationText,description};if(pos){data.latitude=pos.coords.latitude;data.longitude=pos.coords.longitude}else if(navigator.geolocation){try{const p=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:7000}));data.latitude=p.coords.latitude;data.longitude=p.coords.longitude}catch(e){}}try{const r=await api("/api/lighting-reports","POST",data);msg("light-msg-"+id,r.message);setTimeout(()=>location.reload(),900)}catch(e){msg("light-msg-"+id,e.message,true)}}
function startJourney(index){const r=foundRoutes[index];if(!r)return msg("journeyMsg","Find a route first.",true);pickRoute(index);const mode=r.mode==="walking"?"walking":r.mode==="cycling"?"bicycling":"driving";const url="https://www.google.com/maps/dir/?api=1&origin="+encodeURIComponent($("start").value.trim())+"&destination="+encodeURIComponent($("dest").value.trim())+"&travelmode="+mode;msg("journeyMsg","Opening Google Maps for your selected route. Follow the directions shown there.");window.open(url,"_blank","noopener")}
function openGoogleRoute(index){startJourney(index)}
function directions(){let a=$("start").value.trim(),b=$("dest").value.trim();if(!a||!b)return msg("journeyMsg","Enter start and destination first.",true);window.open("https://www.google.com/maps/dir/?api=1&origin="+encodeURIComponent(a)+"&destination="+encodeURIComponent(b),"_blank","noopener")}
function useCurrentLocation(){if(!navigator.geolocation)return msg("journeyMsg","Location is not supported by this browser.",true);msg("journeyMsg","Getting your current location…");navigator.geolocation.getCurrentPosition(p=>{$("start").value=p.coords.latitude+","+p.coords.longitude;msg("journeyMsg","Current GPS location added as starting point. Enter a destination and find routes.");},()=>msg("journeyMsg","Could not access location. Allow location permission and try again.",true),{enableHighAccuracy:true,timeout:15000})}
function getLocation(){if(!navigator.geolocation)return $("locStatus").textContent="Geolocation is not supported";$("locStatus").textContent="Requesting location permission…";if(watch!==null)navigator.geolocation.clearWatch(watch);watch=navigator.geolocation.watchPosition(p=>{pos=p;$("locStatus").textContent="Location received";$("coords").textContent=p.coords.latitude.toFixed(6)+", "+p.coords.longitude.toFixed(6);$("accuracy").textContent="Device-reported accuracy: about "+Math.round(p.coords.accuracy)+" metres · "+new Date(p.timestamp).toLocaleTimeString()},e=>{$("locStatus").textContent=({1:"Permission denied. Allow location in browser settings.",2:"Location unavailable. Try enabling device location.",3:"Request timed out. Try again."})[e.code]||"Unable to get location"},{enableHighAccuracy:true,maximumAge:0,timeout:20000})}
function stopLocation(){if(watch!==null)navigator.geolocation.clearWatch(watch);watch=null;$("locStatus").textContent="Location updates stopped"}
function mapUrl(){return pos?"https://maps.google.com/?q="+pos.coords.latitude+","+pos.coords.longitude:""}
function openMap(){let u=mapUrl();if(!u)return alert("Get your location first.");window.open(u,"_blank","noopener")}
async function prepareSOS(){let contacts=[];try{contacts=await api("/api/contacts")}catch(e){}let link=mapUrl(),message="SOS! I may need help. Please contact me. My location: "+(link||"Location not available");let box=$("sosBox");box.style.display="block";box.innerHTML="<b>Emergency message prepared</b><p>"+esc(message)+"</p>";if(!link)box.innerHTML+="<p>For a location link, first use Get my location above.</p>";if(contacts.length){contacts.forEach(c=>{let row=document.createElement("p");let sms=document.createElement("a");sms.className="btn primary";sms.href="sms:"+encodeURIComponent(c.phone)+"?body="+encodeURIComponent(message);sms.textContent="Message "+c.name;let call=document.createElement("a");call.className="btn outline";call.style.marginLeft="7px";call.href="tel:"+encodeURIComponent(c.phone);call.textContent="Call "+c.name;row.append(sms,call);box.append(row)})}else box.innerHTML+="<p>Add a trusted contact below to enable quick contact links.</p>";let emergency=document.createElement("a");emergency.href="tel:112";emergency.className="btn outline";emergency.textContent="Call 112";box.append(emergency)}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function saveContact(){try{let r=await api("/api/contacts","POST",{name:$("cname").value.trim(),phone:$("cphone").value.trim()});msg("contactMsg",r.message);setTimeout(()=>location.reload(),500)}catch(e){msg("contactMsg",e.message,true)}}
async function deleteContact(id){if(!confirm("Remove this contact?"))return;try{await api("/api/contacts","DELETE",{id});location.reload()}catch(e){msg("contactMsg",e.message,true)}}
async function reportIncident(){let data={location:$("iloc").value.trim(),category:$("icat").value,description:$("idesc").value.trim()};if(pos){data.latitude=pos.coords.latitude;data.longitude=pos.coords.longitude}try{let r=await api("/api/incidents","POST",data);msg("incidentMsg",r.message);setTimeout(()=>location.reload(),700)}catch(e){msg("incidentMsg",e.message,true)}}
</script></body></html>"""

@app.route("/")
def home():
    with db() as c:
        routes=[dict(x) for x in c.execute("SELECT * FROM routes ORDER BY id").fetchall()]
        contacts=[dict(x) for x in c.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()]
        journeys=c.execute("SELECT COUNT(*) FROM journeys").fetchone()[0]
        saved_journeys=[dict(x) for x in c.execute("SELECT * FROM journeys ORDER BY id DESC LIMIT 20").fetchall()]
        incidents=[dict(x) for x in c.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 10").fetchall()]
        counts={"routes":len(routes),"journeys":journeys,"incidents":c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0],"contacts":len(contacts)}
    for r in routes: r["score"],r["label"]=risk_score(r["lighting"],r["crowd"],r["security"],r["incidents"],r["transport"])
    return render_template_string(PAGE,routes=routes,contacts=contacts[:2],incidents=incidents,saved_journeys=saved_journeys,counts=counts)

@app.route("/api/contacts",methods=["GET","POST","DELETE"])
def contacts_api():
    with db() as c:
        if request.method=="GET": return jsonify([dict(x) for x in c.execute("SELECT * FROM contacts ORDER BY id").fetchall()])
        data=request.get_json(silent=True) or {}
        if request.method=="DELETE":
            c.execute("DELETE FROM contacts WHERE id=?",(data.get("id"),)); return jsonify({"message":"Contact removed."})
        name,phone=data.get("name","").strip(),data.get("phone","").strip()
        if not name or not phone: return jsonify({"error":"Enter both name and phone number."}),400
        if len("".join(ch for ch in phone if ch.isdigit()))<7:return jsonify({"error":"Enter a valid phone number."}),400
        if c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]>=2:return jsonify({"error":"Maximum two trusted contacts. Remove one first."}),400
        c.execute("INSERT INTO contacts(name,phone) VALUES(?,?)",(name,phone));return jsonify({"message":"Trusted contact saved."}),201

@app.route("/api/journeys",methods=["POST","PATCH"])
def journeys_api():
    d=request.get_json(silent=True) or {}
    if request.method=="PATCH":
        try: jid=int(d.get("id"))
        except (TypeError,ValueError): return jsonify({"error":"Invalid journey ID."}),400
        with db() as c:
            cur=c.execute("UPDATE journeys SET status='COMPLETED', completed=? WHERE id=?",(datetime.now().strftime("%Y-%m-%d %H:%M"),jid))
            if not cur.rowcount:return jsonify({"error":"Journey not found."}),404
        return jsonify({"message":"Journey marked completed."})
    start=d.get("start","").strip(); dest=d.get("destination","").strip()
    if not start or not dest:return jsonify({"error":"Enter start and destination."}),400
    with db() as c:
        cur=c.execute("INSERT INTO journeys(start,destination,route,score,created,status) VALUES(?,?,?,?,?,'PLANNED')",(start,dest,d.get("route","Not selected"),int(d.get("score",0)),datetime.now().strftime("%Y-%m-%d %H:%M")))
        jid=cur.lastrowid
    return jsonify({"message":"Journey saved.","id":jid}),201

@app.route("/api/lighting-reports",methods=["POST"])
def lighting_reports_api():
    d=request.get_json(silent=True) or {}
    try: jid=int(d.get("journey_id"))
    except (TypeError,ValueError): return jsonify({"error":"Invalid journey."}),400
    category=d.get("category","").strip()
    if category not in {"High","Medium","Low","Broken streetlights"}:
        return jsonify({"error":"Choose a lighting condition."}),400
    location=d.get("location","").strip()
    description=d.get("description","").strip() or "Community lighting observation after journey completion."
    with db() as c:
        journey=c.execute("SELECT * FROM journeys WHERE id=?",(jid,)).fetchone()
        if not journey: return jsonify({"error":"Journey not found."}),404
        if journey["status"]!="COMPLETED": return jsonify({"error":"Mark this journey completed before submitting lighting feedback."}),400
        stamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        cur=c.execute("INSERT INTO lighting_reports(journey_id,start,destination,route,category,description,created,status,latitude,longitude) VALUES(?,?,?,?,?,?,?,?,?,?)",(jid,journey["start"],journey["destination"],journey["route"],category,description,stamp,"UNVERIFIED",d.get("latitude"),d.get("longitude")))
        # Also add a compatible incident record so existing incident list includes this observation.
        incident_category={"High":"Lighting good / bright","Medium":"Lighting moderate","Low":"Poor lighting / dark road","Broken streetlights":"Streetlight not working"}[category]
        c.execute("INSERT INTO incidents(location,category,description,created,status,latitude,longitude) VALUES(?,?,?,?,?,?,?)",(location or f"{journey['start']} → {journey['destination']}",incident_category,description,stamp,"UNVERIFIED",d.get("latitude"),d.get("longitude")))
    return jsonify({"message":"Lighting report saved for this completed journey. It is marked UNVERIFIED.","id":cur.lastrowid}),201

@app.route("/api/incidents",methods=["POST"])
def incidents_api():
    d=request.get_json(silent=True) or {}; loc=d.get("location","").strip(); desc=d.get("description","").strip()
    if not loc or not desc:return jsonify({"error":"Enter a location and description."}),400
    with db() as c:c.execute("INSERT INTO incidents(location,category,description,created,status,latitude,longitude) VALUES(?,?,?,?,?,?,?)",(loc,d.get("category","Other"),desc,datetime.now().strftime("%Y-%m-%d %H:%M"),"UNVERIFIED",d.get("latitude"),d.get("longitude")))
    return jsonify({"message":"Incident saved as UNVERIFIED."}),201

@app.route("/api/route-safety",methods=["POST"])
def route_safety_api():
    """Community-reported lighting context, not a measured live lux reading."""
    d=request.get_json(silent=True) or {}; coords=d.get("coordinates") or []
    if not coords:return jsonify({"error":"Route geometry is required."}),400
    try: pts=[(float(p[0]),float(p[1])) for p in coords if len(p)>=2]
    except (TypeError,ValueError):return jsonify({"error":"Invalid route coordinates."}),400
    if not pts:return jsonify({"error":"No valid route coordinates."}),400
    lons=[p[0] for p in pts]; lats=[p[1] for p in pts]
    minlon,maxlon=min(lons)-0.003,max(lons)+0.003; minlat,maxlat=min(lats)-0.003,max(lats)+0.003
    lights=None
    try:
        import urllib.request, urllib.parse, json
        query=f'[out:json][timeout:8];node["highway"="street_lamp"]({minlat},{minlon},{maxlat},{maxlon});out count;'
        req=urllib.request.Request("https://overpass-api.de/api/interpreter",data=urllib.parse.urlencode({"data":query}).encode(),headers={"User-Agent":"SafeRouteStudentProject/1.0"})
        with urllib.request.urlopen(req,timeout=10) as response:
            payload=json.loads(response.read().decode()); lights=int(payload.get("elements",[{}])[0].get("tags",{}).get("total",0)) if payload.get("elements") else 0
    except Exception: lights=None
    with db() as c:
        rows=c.execute("SELECT location,category,description,created,status,latitude,longitude FROM incidents WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY id DESC").fetchall()
        matched=[]
        for row in rows:
            x=dict(row); lat=x.get("latitude"); lon=x.get("longitude")
            if lat is not None and lon is not None and minlat<=lat<=maxlat and minlon<=lon<=maxlon:
                x.pop("latitude",None); x.pop("longitude",None); matched.append(x)
    lighting_terms={"high":("lighting good / bright",),"medium":("lighting moderate",),"low":("poor lighting / dark road","streetlight not working","poor lighting","broken streetlights")}
    light_reports=[]
    for item in matched:
        cat=(item.get("category") or "").strip().lower()
        if cat in sum((list(v) for v in lighting_terms.values()),[]): light_reports.append(item)
    # Reports from the last 24 hours count as recent for the display; older reports remain visible but don't determine status.
    from datetime import timedelta
    now=datetime.now(); recent=[]
    for item in light_reports:
        try:
            stamp=datetime.strptime(item.get("created", ""), "%Y-%m-%d %H:%M")
            if now-stamp <= timedelta(hours=24): recent.append((item,stamp))
        except Exception: pass
    if not recent: lighting_status="Unknown"; lighting_summary="No lighting reports in the last 24 hours"
    else:
        latest=sorted(recent,key=lambda pair:pair[1],reverse=True)
        cats=[x[0].get("category","").lower() for x in latest]
        low=sum(1 for cat in cats if cat in lighting_terms["low"]); med=sum(1 for cat in cats if cat in lighting_terms["medium"]); high=sum(1 for cat in cats if cat in lighting_terms["high"])
        if low>high and low>=med: lighting_status="Low"
        elif high>low and high>=med: lighting_status="High"
        else: lighting_status="Medium"
        lighting_summary=f"{len(recent)} report(s) in last 24h; latest {latest[0][1].strftime('%Y-%m-%d %H:%M')}"
    crowd_count=sum(1 for x in matched if "crowd" in (x.get("category") or "").lower() or "crowd" in (x.get("description") or "").lower())
    return jsonify({"streetlights":lights,"incidents":matched[:10],"crowd_reports":crowd_count,"lighting_status":lighting_status,"lighting_summary":lighting_summary,"checked_at":now.strftime("%Y-%m-%d %H:%M"),"note":"Lighting status is based on recent unverified community reports, not a live brightness measurement. Unknown means insufficient reports."})

@app.route("/health")
def health(): return jsonify({"status":"ok","app":"SafeRoute"})

init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=False)
