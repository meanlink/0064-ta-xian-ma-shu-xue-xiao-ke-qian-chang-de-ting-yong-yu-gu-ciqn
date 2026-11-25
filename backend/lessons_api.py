from fastapi import APIRouter,Depends
from core import db,require
from lesson_move import Move,assign
router=APIRouter(prefix="/lessons")

@router.get("")
def timetable(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT l.*,m.origin,m.reasoning,m.walk FROM lessons l LEFT JOIN lesson_moves m ON l.code=m.lesson ORDER BY starts_at").fetchall()

@router.post("/{lesson}/move")
def move(lesson:str,data:Move,user=Depends(require("reviewer"))):
    with db() as cx:
        return assign(cx,lesson,data,user["email"])
