from fastapi import APIRouter,Depends
from core import db,require
from walk_records import Walk,record
router=APIRouter(prefix="/walks")

@router.get("")
def list_walks(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT * FROM ring_walks ORDER BY observed DESC,code").fetchall()

@router.post("")
def add(data:Walk,_=Depends(require("operator","reviewer"))):
    with db() as cx:
        return record(cx,data)
