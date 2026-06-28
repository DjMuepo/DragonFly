
import os,json
DATA=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","scan_missions.json"))
def _load():
    if not os.path.exists(DATA):
        m={"missions":[
            {"id":"m1","title":"Scan a chair"},
            {"id":"m2","title":"Scan a tool"},
            {"id":"m3","title":"Scan broken object"},
            {"id":"m4","title":"Scan artifact"}
        ]}
        json.dump(m,open(DATA,"w"),indent=2); return m
    return json.load(open(DATA))
def list_missions(): return _load()["missions"]
