from fastapi import APIRouter,Depends
from core import db,require
from ring_register import register
router=APIRouter(prefix="/rings")

@router.get("")
def list_rings(_=Depends(require())):
    with db() as cx:
        return register(cx)
