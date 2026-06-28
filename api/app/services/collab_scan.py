
import os,json,uuid,time
DATA=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","collab_scans.json"))
def _load():
    if not os.path.exists(DATA):
        d={"scans":[]}
        json.dump(d,open(DATA,"w"),indent=2)
        return d
    return json.load(open(DATA))
def _save(d): json.dump(d,open(DATA,"w"),indent=2)
def submit_scan(object_id,angle,user):
    d=_load()
    s={"id":"scan_"+uuid.uuid4().hex[:8],"object_id":object_id,"angle":angle,"user":user,"time":int(time.time())}
    d["scans"].append(s); _save(d); return s
def get_scans(object_id): return [s for s in _load()["scans"] if s["object_id"]==object_id]
