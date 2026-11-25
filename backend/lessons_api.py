from fastapi import APIRouter, Depends, HTTPException
from core import db,require
from lesson_move import Move,assign,history,timetable
router=APIRouter(prefix="/lessons")

@router.get("")
def list_timetable(_=Depends(require())):
    with db() as cx:
        return timetable(cx)

@router.get("/{lesson}")
def lesson_detail(lesson:str,_=Depends(require())):
    with db() as cx:
        row=next((item for item in timetable(cx) if item["code"]==lesson),None)
        if not row:
            raise HTTPException(404,"找不到课次")
        return row

@router.get("/{lesson}/history")
def lesson_history(lesson:str,_=Depends(require())):
    with db() as cx:
        return history(cx,lesson)

@router.get("/{lesson}/move")
def get_move(lesson:str,_=Depends(require())):
    with db() as cx:
        row=cx.execute("SELECT * FROM lesson_moves WHERE lesson=%s",(lesson,)).fetchone()
        if not row:
            raise HTTPException(404,"找不到移场签核")
        return row

@router.post("/{lesson}/move")
def move(lesson:str,data:Move,user=Depends(require("reviewer"))):
    with db() as cx:
        return assign(cx,lesson,data,user["email"])

# Explicit aliases for the re-sign vocabulary used by the review workflow.
@router.post("/{lesson}/resign")
@router.post("/{lesson}/review")
def resign(lesson:str,data:Move,user=Depends(require("reviewer"))):
    with db() as cx:
        return assign(cx,lesson,data,user["email"])
