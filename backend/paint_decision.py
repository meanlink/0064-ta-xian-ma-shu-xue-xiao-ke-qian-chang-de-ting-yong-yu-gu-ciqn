from fastapi import HTTPException
from psycopg.types.json import Jsonb
from stump import fit
from walk_records import latest

COST_CUTOFF=.25

def run_job(cx,kind,payload):
    if kind!="morning-ring":
        raise ValueError(kind)
    code=payload["ring"]
    if not cx.execute("SELECT code FROM riding_rings WHERE code=%s FOR UPDATE",(code,)).fetchone():
        raise HTTPException(404,"未登记围场")
    record=latest(cx,code)
    if not record:
        raise HTTPException(409,"请先录当日巡场")
    history=cx.execute("SELECT * FROM ring_walks WHERE outcome IS NOT NULL ORDER BY observed,code").fetchall()
    training,holdout=history[:-2],history[-2:]
    feature,cutoff,probs,gini=fit(training)
    probability=probs[int(record[feature]>cutoff)]
    holdout_accuracy=sum((probs[int(r[feature]>cutoff)]>=COST_CUTOFF)==r["outcome"] for r in holdout)/len(holdout)
    recommendation=probability>=COST_CUTOFF or record["barrier"]=="closed"
    calibration={"training":len(training),"holdout":len(holdout),"accuracy":holdout_accuracy,"gini":round(gini,4),"cost_threshold":COST_CUTOFF}
    stored={"ring":code,"walk":record["code"],"feature":feature,"cutoff":cutoff,"probability":probability,"close_recommended":recommendation,"calibration":calibration}
    cx.execute('''
      INSERT INTO ring_calls VALUES(%(ring)s,%(walk)s,%(feature)s,%(cutoff)s,%(probability)s,%(close_recommended)s,%(calibration)s)
      ON CONFLICT(ring) DO UPDATE SET walk=excluded.walk,feature=excluded.feature,cutoff=excluded.cutoff,
        probability=excluded.probability,close_recommended=excluded.close_recommended,calibration=excluded.calibration
    ''',stored|{"calibration":Jsonb(calibration)})
    return stored
