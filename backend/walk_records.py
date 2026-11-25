from datetime import date
from pydantic import BaseModel, Field
from typing import Literal
from fastapi import HTTPException

class Walk(BaseModel):
    code:str=Field(pattern=r"^W[0-9]{2,6}$")
    ring:str
    observed:date
    puddle:int=Field(ge=0,le=100)
    rut:int=Field(ge=0,le=100)
    moisture:int=Field(ge=0,le=100)
    barrier:Literal["clear","review","closed"]
    source:str=Field(min_length=2,max_length=120)

def latest(cx,ring):
    return cx.execute("SELECT * FROM ring_walks WHERE ring=%s AND outcome IS NULL ORDER BY observed DESC,code DESC LIMIT 1",(ring,)).fetchone()

def record(cx,data):
    if not cx.execute("SELECT 1 FROM riding_rings WHERE code=%s FOR UPDATE",(data.ring,)).fetchone():
        raise HTTPException(404,"找不到围场")
    cx.execute('''
      INSERT INTO ring_walks(code,ring,observed,puddle,rut,moisture,barrier,source)
      VALUES(%(code)s,%(ring)s,%(observed)s,%(puddle)s,%(rut)s,%(moisture)s,%(barrier)s,%(source)s)
    ''',data.model_dump())
    return {"code":data.code}
