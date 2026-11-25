from fastapi import APIRouter,Depends
from core import db,require,enqueue
router=APIRouter(prefix="/cutoff")

@router.get("")
def ring_calls(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT c.*,r.title FROM ring_calls c JOIN riding_rings r ON r.code=c.ring ORDER BY c.ring").fetchall()

@router.post("/{ring}")
def run(ring:str,_=Depends(require("operator","reviewer"))):
    with db() as cx:
        return {"job_id":enqueue(cx,"morning-ring",{"ring":ring})}
