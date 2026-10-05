from flask import Flask, request, jsonify, render_template
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saferoute_web.db")

class SafetyAnalyzer:
    def __init__(self):
        self.lighting_scores = {"Good": 0,"Medium": 1,"Poor": 2}
        self.crowd_scores = {"High": 0,"Medium": 1,"Low": 2}
        self.security_scores = {"Good": 0,"Medium": 1,"Poor": 2}
        self.incident_scores = {"Low": 0,"Medium": 1,"High": 2}
        self.transport_scores = {"Available": 0,"Limited": 1,"None": 2}

    def calculate_score(self, lighting, crowd, security, incidents, transport):
        values = [self.lighting_scores.get(lighting, 1),self.crowd_scores.get(crowd, 1),self.security_scores.get(security, 1),self.incident_scores.get(incidents, 1),self.transport_scores.get(transport, 1)]
        score = sum(values)

        if score <= 2: label = "LOWER"
        elif score <= 5: label = "MODERATE"
        else: label = "HIGHER"
        return score, label
safety_analyzer = SafetyAnalyzer()

def risk_score(lighting, crowd, security, incidents, transport):
    return safety_analyzer.calculate_score(lighting,crowd,security,incidents,transport)

class Database:
    def __init__(self, database_path):
        self.database_path = database_path

    def connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
database = Database(DB)
def db():
    return database.connect()

class Route:
    def __init__(self, name, start, destination, distance, minutes,lighting,crowd,security,incidents,transport):
        self.name = name
        self.start = start
        self.destination = destination
        self.distance = distance
        self.minutes = minutes
        self.lighting = lighting
        self.crowd = crowd
        self.security = security
        self.incidents = incidents
        self.transport = transport

    def calculate_score(self):
        return safety_analyzer.calculate_score(self.lighting,self.crowd,self.security,self.incidents,self.transport)

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
       
@app.route("/")
def home():
    with db() as c:
        route_rows = c.execute("SELECT * FROM routes ORDER BY id").fetchall()
        routes = []
        for row in route_rows:
            route = Route(row["name"],row["start"],row["destination"],row["distance"],row["minutes"],row["lighting"],row["crowd"],row["security"],row["incidents"],row["transport"])
            score, label = route.calculate_score()
            route_data = dict(row)
            route_data["score"] = score
            route_data["label"] = label
            routes.append(route_data)

        contacts=[dict(x) for x in c.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()]
        journeys=c.execute("SELECT COUNT(*) FROM journeys").fetchone()[0]
        saved_journeys=[dict(x) for x in c.execute("SELECT * FROM journeys ORDER BY id DESC LIMIT 20").fetchall()]
        incidents=[dict(x) for x in c.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 10").fetchall()]
        counts={"routes":len(routes),"journeys":journeys,"incidents":c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0],"contacts":len(contacts)}
    return render_template("index.html",routes=routes,contacts=contacts[:2],incidents=incidents,saved_journeys=saved_journeys,counts=counts)

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
    start_text=(d.get("start") or "").strip().lower()
    dest_text=(d.get("destination") or "").strip().lower()
    with db() as c:
        rows=c.execute("SELECT location,category,description,created,status,latitude,longitude FROM incidents ORDER BY id DESC").fetchall()
        matched=[]
        for row in rows:
            x=dict(row); lat=x.get("latitude"); lon=x.get("longitude")
            gps_match=(lat is not None and lon is not None and minlat<=lat<=maxlat and minlon<=lon<=maxlon)
            location_text=(x.get("location") or "").lower()
            description_text=(x.get("description") or "").lower()
            # Text fallback supports reports entered without browser location permission.
            text_match=bool(start_text and dest_text and start_text in (location_text+" "+description_text) and dest_text in (location_text+" "+description_text))
            if gps_match or text_match:
                matched.append(x)
    lighting_terms={"high":("lighting good / bright",),"medium":("lighting moderate",),"low":("poor lighting / dark road","streetlight not working","poor lighting","broken streetlights")}
    light_reports=[]
    for item in matched:
        cat=(item.get("category") or "").strip().lower()
        if cat in sum((list(v) for v in lighting_terms.values()),[]): light_reports.append(item)
    # Recent community reports can inform the status for up to 30 days.
    from datetime import timedelta
    now=datetime.now(); recent=[]
    for item in light_reports:
        try:
            stamp=datetime.strptime(item.get("created", ""), "%Y-%m-%d %H:%M")
            if timedelta(0) <= now-stamp <= timedelta(days=30): recent.append((item,stamp))
        except Exception: pass
    if not recent: lighting_status="Unknown"; lighting_summary="No matching lighting reports in the last 30 days"
    else:
        latest=sorted(recent,key=lambda pair:pair[1],reverse=True)
        cats=[x[0].get("category","").lower() for x in latest]
        low=sum(1 for cat in cats if cat in lighting_terms["low"]); med=sum(1 for cat in cats if cat in lighting_terms["medium"]); high=sum(1 for cat in cats if cat in lighting_terms["high"])
        if low>high and low>=med: lighting_status="Low"
        elif high>low and high>=med: lighting_status="High"
        else: lighting_status="Medium"
        lighting_summary=f"{len(recent)} report(s) in last 30 days; latest {latest[0][1].strftime('%Y-%m-%d %H:%M')}"
    crowd_count=sum(1 for x in matched if "crowd" in (x.get("category") or "").lower() or "crowd" in (x.get("description") or "").lower())
    return jsonify({"streetlights":lights,"incidents":matched[:10],"crowd_reports":crowd_count,"lighting_status":lighting_status,"lighting_summary":lighting_summary,"checked_at":now.strftime("%Y-%m-%d %H:%M"),"note":"Lighting status is based on matching unverified community reports from the last 30 days, not a live brightness measurement. Unknown means insufficient reports."})

@app.route("/api/community-map")
def community_map_api():
    with db() as c:
        rows=c.execute("SELECT latitude,longitude,category FROM incidents WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY id DESC").fetchall()
    points=[]
    for row in rows:
        cat=(row[2] or "Other").lower(); weight=3
        if "harassment" in cat or "hazard" in cat: weight=5
        elif "dark" in cat or "streetlight" in cat or "lighting" in cat: weight=4
        elif "crowd" in cat: weight=2
        points.append({"lat":float(row[0]),"lon":float(row[1]),"weight":weight})
    return jsonify({"points":points,"note":"Community reports are unverified."})

@app.route("/api/analytics")
def analytics_api():
    with db() as c:
        total=int(c.execute("SELECT COUNT(*) FROM journeys").fetchone()[0])
        completed=int(c.execute("SELECT COUNT(*) FROM journeys WHERE status='COMPLETED'").fetchone()[0])
        incidents=int(c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0])
        recent=c.execute("SELECT substr(created,1,10) day, COUNT(*) count FROM journeys GROUP BY substr(created,1,10) ORDER BY day DESC LIMIT 7").fetchall()
    rate=round((completed/total)*100,1) if total else 0
    return jsonify({"total_journeys":total,"completed_journeys":completed,"total_incidents":incidents,"completion_rate":rate,"recent":[dict(x) for x in recent]})

@app.route("/health")
def health(): return jsonify({"status":"ok","app":"SafeRoute"})

init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=False)