from fastapi import HTTPException
from pydantic import BaseModel,Field
from walk_records import latest
class Move(BaseModel):
    target:str
    reasoning:str=Field(min_length=4,max_length=180)

def assign(cx,code,payload,reviewer):
    lesson=cx.execute("SELECT * FROM lessons WHERE code=%s FOR UPDATE",(code,)).fetchone()
    if not lesson or lesson["state"]!="scheduled" or lesson["ring"]==payload.target:
        raise HTTPException(409,"课次须待安排且目标围场应不同")
    # All concurrent inbound moves serialize on the same pair of ring rows.
    keys=sorted([lesson["ring"],payload.target])
    rings={r["code"]:r for r in cx.execute("SELECT * FROM riding_rings WHERE code=ANY(%s) ORDER BY code FOR UPDATE",(keys,))}
    prior=latest(cx,lesson["ring"])
    if not prior or not cx.execute("SELECT 1 FROM ring_calls WHERE walk=%s AND close_recommended",(prior["code"],)).fetchone():
        raise HTTPException(409,"原场未给出有效的停用建议")
    destination=rings.get(payload.target)
    checks=latest(cx,payload.target)
    if not destination or not checks or checks["observed"]!=prior["observed"] or checks["barrier"]!="clear":
        raise HTTPException(409,"目标场需有同日可用巡场")
    if cx.execute("SELECT 1 FROM ring_calls WHERE walk=%s AND close_recommended",(checks["code"],)).fetchone():
        raise HTTPException(409,"目标场已有当日停用建议")
    load=cx.execute("SELECT coalesce(sum(riders),0) AS n FROM lessons WHERE ring=%s AND starts_at=%s AND state<>'paused'",(payload.target,lesson["starts_at"])).fetchone()["n"]
    if load+lesson["riders"]>destination["max_riders"]:
        raise HTTPException(409,"目标场同课时人数超出围场核定容量")
    cx.execute("INSERT INTO lesson_moves(lesson,origin,target,walk,reasoning,reviewed_by) VALUES (%s,%s,%s,%s,%s,%s)",(code,lesson["ring"],payload.target,prior["code"],payload.reasoning,reviewer))
    cx.execute("UPDATE lessons SET ring=%s,state='moved' WHERE code=%s",(payload.target,code))
    return {"course":code,"ring":payload.target,"state":"moved"}
