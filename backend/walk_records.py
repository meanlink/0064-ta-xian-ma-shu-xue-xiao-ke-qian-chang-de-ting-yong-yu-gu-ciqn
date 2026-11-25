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

def latest_for_lesson(cx, ring, starts_at):
    """Last active field record for the ring on the lesson's school day.

    Walk rows only carry a day, while lesson starts are timestamptz.  The
    product is used on a China campus, so normalize the lesson instant to
    Asia/Shanghai before comparing dates.  Numeric code order keeps W100 after
    W99; code remains a tie-breaker for safety.
    """
    return cx.execute('''
        SELECT *
        FROM ring_walks
        WHERE ring=%s
          AND outcome IS NULL
          AND observed=((%s::timestamptz AT TIME ZONE 'UTC') + INTERVAL '8 hours')::date
        ORDER BY NULLIF(regexp_replace(code, '[^0-9]', '', 'g'), '')::bigint DESC NULLS LAST,
                 code DESC
        LIMIT 1
    ''',(ring,starts_at)).fetchone()

def record(cx,data):
    # Locking the ring row before inserting serializes late paper-record
    # entry with move sign-off, which takes the same ring row locks.
    if not cx.execute("SELECT 1 FROM riding_rings WHERE code=%s FOR UPDATE",(data.ring,)).fetchone():
        raise HTTPException(404,"找不到围场")
    cx.execute('''
      INSERT INTO ring_walks(code,ring,observed,puddle,rut,moisture,barrier,source)
      VALUES(%(code)s,%(ring)s,%(observed)s,%(puddle)s,%(rut)s,%(moisture)s,%(barrier)s,%(source)s)
    ''',data.model_dump())
    # Imported lazily to avoid a module import cycle with lesson_move.
    from lesson_move import invalidate_for_walk
    reviewed = invalidate_for_walk(cx,data.code)
    return {"code":data.code,"reviewed_lessons":reviewed,"pending_review":reviewed}
