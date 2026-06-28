
import os,json,time,uuid
DATA=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","world_map.json"))
def _load():
    if not os.path.exists(DATA):
        d={"objects":[]}
        json.dump(d,open(DATA,"w"),indent=2)
        return d
    return json.load(open(DATA))
def _save(d): json.dump(d,open(DATA,"w"),indent=2)
def add_object(lat,lon,title,creator="anon"):
    d=_load()
    obj={"id":"obj_"+uuid.uuid4().hex[:8],"lat":lat,"lon":lon,"title":title,"creator":creator,"time":int(time.time())}
    d["objects"].append(obj)
    _save(d)
    return obj
def list_objects(): return _load()["objects"]
