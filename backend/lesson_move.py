from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from walk_records import latest_for_lesson

REVIEW_STATES = {"review", "pending_review", "stale"}


class ReviewConflict(HTTPException):
    """409 with machine-readable review state for stale-basis retries."""

    def __init__(self, message, review=None):
        super().__init__(status_code=409, detail=message)
        self.review = review or {}


async def review_conflict_handler(_request, exc: ReviewConflict):
    return JSONResponse(
        status_code=409,
        content={"detail": exc.detail, "message": exc.detail, **exc.review},
    )


class Move(BaseModel):
    target: str
    reasoning: str = Field(min_length=4, max_length=180)
    # Optional optimistic basis token.  The schedule page sends the target
    # walk it reviewed; a late paper record changes the latest basis and a
    # stale token is rejected instead of silently overwriting the review.
    basis: str | None = None
    basis_walk: str | None = None
    expected_basis: str | None = None
    expected_walk: str | None = None
    walk_code: str | None = None
    old_basis: str | None = None
    target_walk: str | None = None

    @property
    def expected_basis_code(self):
        return (
            self.basis
            or self.basis_walk
            or self.expected_basis
            or self.expected_walk
            or self.walk_code
            or self.old_basis
            or self.target_walk
        )


def _add_event(
    cx,
    *,
    event,
    move_status,
    lesson,
    origin,
    target,
    actor,
    origin_walk=None,
    target_walk=None,
    trigger_walk=None,
    reasoning=None,
    detail=None,
):
    cx.execute(
        """
        INSERT INTO lesson_move_events(
            lesson,event,move_status,origin,target,origin_walk,target_walk,
            trigger_walk,reasoning,actor,detail
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            lesson,
            event,
            move_status,
            origin,
            target,
            origin_walk,
            target_walk,
            trigger_walk,
            reasoning,
            actor,
            detail,
        ),
    )


def mark_review(
    cx,
    move,
    *,
    trigger_walk=None,
    reason=None,
    actor="system",
    event="review_opened",
    detail=None,
    commit=False,
):
    """Move an existing transfer order into review without releasing capacity."""
    lesson_code = move["lesson"]
    cx.execute(
        """
        UPDATE lesson_moves
        SET status='review', trigger_walk=COALESCE(%s, trigger_walk),
            review_reason=COALESCE(%s, review_reason)
        WHERE lesson=%s
        """,
        (trigger_walk, reason, lesson_code),
    )
    # Keep the occupied target ring.  Only the lifecycle state changes.
    cx.execute(
        "UPDATE lessons SET state='review' WHERE code=%s AND state <> 'paused'",
        (lesson_code,),
    )
    _add_event(
        cx,
        event=event,
        move_status="review",
        lesson=lesson_code,
        origin=move["origin"],
        target=move["target"],
        actor=actor,
        origin_walk=move.get("walk"),
        target_walk=move.get("target_walk"),
        trigger_walk=trigger_walk or move.get("trigger_walk"),
        reasoning=move.get("reasoning"),
        detail=detail or reason,
    )
    if commit:
        cx.commit()


def invalidate_for_walk(cx, walk_code):
    """Mark transfers for which a newly recorded seal is the new target basis."""
    walk = cx.execute(
        "SELECT * FROM ring_walks WHERE code=%s", (walk_code,)
    ).fetchone()
    if not walk or walk["barrier"] != "closed":
        return []

    rows = cx.execute(
        """
        SELECT m.*, l.starts_at, l.state AS lesson_state
        FROM lessons l
        JOIN lesson_moves m ON m.lesson=l.code
        WHERE m.target=%s AND l.state <> 'paused'
        ORDER BY l.starts_at,l.code
        FOR UPDATE OF l, m
        """,
        (walk["ring"],),
    ).fetchall()

    affected = []
    for move in rows:
        current = latest_for_lesson(cx, move["target"], move["starts_at"])
        if not current or current["code"] != walk_code:
            continue
        reason = f"迟到的封栏记录 {walk_code} 已成为目标场最新依据"
        mark_review(
            cx,
            move,
            trigger_walk=walk_code,
            reason=reason,
            actor="field-record",
            detail=f"来源：{walk['source']}",
        )
        affected.append(move["lesson"])
    return affected


def _close_recommended(cx, walk):
    if walk["barrier"] == "closed":
        return True
    return bool(
        cx.execute(
            "SELECT 1 FROM ring_calls WHERE walk=%s AND close_recommended",
            (walk["code"],),
        ).fetchone()
    )


def _stale_conflict(cx, message, *, lesson=None, move=None, trigger=None, reason=None, reviewer=None):
    review = {
        "course": lesson["code"] if lesson else None,
        "review_required": move is not None,
        "pending_review": move is not None,
        "state": "review" if move is not None else (lesson["state"] if lesson else None),
        "move_status": "review" if move is not None else None,
        "trigger_walk": trigger,
    }
    if lesson is not None and move is not None:
        mark_review(
            cx,
            move,
            trigger_walk=trigger,
            reason=reason,
            actor=reviewer or "reviewer",
            event="signoff_rejected",
            detail=message,
            commit=True,
        )
    raise ReviewConflict(message, review)


def assign(cx, code, payload, reviewer):
    snapshot = cx.execute(
        "SELECT * FROM lessons WHERE code=%s", (code,)
    ).fetchone()
    move_snapshot = None
    if snapshot:
        move_snapshot = cx.execute(
            "SELECT * FROM lesson_moves WHERE lesson=%s", (code,)
        ).fetchone()

    if not snapshot:
        raise HTTPException(409, "课次不存在或当前不能移场")

    # Lock every ring that can participate before locking lesson/move rows.
    # walk_records.record takes the target ring lock first too, giving one
    # consistent lock order and serializing late entry against sign-off.
    ring_codes = {snapshot["ring"], payload.target}
    if move_snapshot:
        ring_codes.add(move_snapshot["origin"])
    ring_codes = sorted(ring_codes)
    # Lock explicitly in sorted order; ORDER BY ... FOR UPDATE does not make
    # the lock acquisition order as obvious across all PostgreSQL plans.
    for ring_code in ring_codes:
        if not cx.execute(
            "SELECT 1 FROM riding_rings WHERE code=%s FOR UPDATE", (ring_code,)
        ).fetchone():
            raise HTTPException(404, "找不到围场")
    rings = {
        row["code"]: row
        for row in cx.execute(
            "SELECT * FROM riding_rings WHERE code=ANY(%s)",
            (ring_codes,),
        ).fetchall()
    }
    if payload.target not in rings:
        raise HTTPException(404, "找不到目标围场")

    lesson = cx.execute(
        "SELECT * FROM lessons WHERE code=%s FOR UPDATE", (code,)
    ).fetchone()
    move = cx.execute(
        "SELECT * FROM lesson_moves WHERE lesson=%s FOR UPDATE", (code,)
    ).fetchone()

    # Another transfer committed between the lock-free snapshot and row locks.
    if lesson["ring"] != snapshot["ring"] or (move is None) != (move_snapshot is None):
        raise HTTPException(409, "课次状态已在并发操作中变更，请刷新后重试")

    if lesson["state"] == "paused":
        raise HTTPException(409, "课次已暂停，不能移场或签核")

    # A repeated successful submit is idempotent and never adds occupancy.
    if lesson["state"] == "moved" and move and move["status"] == "signed":
        if payload.target != lesson["ring"]:
            raise HTTPException(409, "课次已移场；如需改场请先刷新并按最新巡场复核")
        if payload.expected_basis_code:
            current = latest_for_lesson(cx, payload.target, lesson["starts_at"])
            current_code = current["code"] if current else None
            if payload.expected_basis_code != current_code:
                reason = (
                    f"签核依据 {payload.expected_basis_code} 已被最新巡场 "
                    f"{current_code or '（无）'} 替换，移场单退回待复核"
                )
                _stale_conflict(
                    cx,
                    "旧依据已被替换，请按最新可用巡场重新审签；移场单已退回待复核",
                    lesson=lesson,
                    move=move,
                    trigger=current_code,
                    reason=reason,
                    reviewer=reviewer,
                )
        return _result(lesson, move, duplicate=True)

    # Tolerate databases/fixtures using the explicit pending_review/stale
    # aliases, or where move status was marked before lesson state was synced.
    if (
        lesson["state"] == "moved"
        and move
        and move["status"] in REVIEW_STATES
    ) or lesson["state"] in REVIEW_STATES:
        cx.execute("UPDATE lessons SET state='review' WHERE code=%s", (code,))
        lesson = dict(lesson)
        lesson["state"] = "review"

    if lesson["state"] not in ("scheduled", "review"):
        raise HTTPException(409, "课次须待安排或待复核")

    if lesson["state"] == "scheduled":
        if lesson["ring"] == payload.target:
            raise HTTPException(409, "目标围场应与原场不同")
        origin_code = lesson["ring"]
        if move is not None:
            raise HTTPException(409, "移场单状态不一致，请刷新后重试")
    else:
        if move is None:
            raise HTTPException(409, "待复核移场单不存在，请刷新后重试")
        origin_code = move["origin"]
        if payload.target == origin_code:
            raise HTTPException(409, "目标围场应与原场不同")

    origin_walk = latest_for_lesson(cx, origin_code, lesson["starts_at"])
    if not origin_walk:
        raise HTTPException(409, "原场缺少当天开课前实地巡场记录")
    if not _close_recommended(cx, origin_walk):
        raise HTTPException(409, "原场未给出有效的停用建议")

    checks = latest_for_lesson(cx, payload.target, lesson["starts_at"])
    expected_basis = payload.expected_basis_code
    current_basis = checks["code"] if checks else None

    if expected_basis and expected_basis != current_basis:
        reason = (
            f"签核依据 {expected_basis} 已被最新巡场 {current_basis or '（无）'} 替换，"
            "移场单退回待复核"
        )
        _stale_conflict(
            cx,
            "旧依据已被替换，请按最新可用巡场重新审签；移场单已退回待复核",
            lesson=lesson,
            move=move,
            trigger=current_basis,
            reason=reason,
            reviewer=reviewer,
        )

    if not checks or checks["barrier"] != "clear":
        reason = None
        if checks:
            reason = f"最新巡场 {checks['code']} 栏位为 {checks['barrier']}，目标场暂不可用"
        _stale_conflict(
            cx,
            "目标场需有同日开课前可用巡场；旧依据已被替换的，移场单退回重审",
            lesson=lesson,
            move=move,
            trigger=current_basis,
            reason=reason,
            reviewer=reviewer,
        )

    if cx.execute(
        "SELECT 1 FROM ring_calls WHERE walk=%s AND close_recommended",
        (checks["code"],),
    ).fetchone():
        _stale_conflict(
            cx,
            "目标场已有当日停用建议，不能签核移入",
            lesson=lesson,
            move=move,
            trigger=checks["code"],
            reason=f"最新依据 {checks['code']} 已有停用建议",
            reviewer=reviewer,
        )

    destination = rings[payload.target]
    # Exclude this lesson: while pending review its row still occupies the
    # target ring, and re-signing must not count it a second time.
    load = cx.execute(
        """
        SELECT coalesce(sum(riders),0) AS n
        FROM lessons
        WHERE ring=%s AND starts_at=%s AND state<>'paused' AND code<>%s
        """,
        (payload.target, lesson["starts_at"], code),
    ).fetchone()["n"]
    if load + lesson["riders"] > destination["max_riders"]:
        raise HTTPException(409, "目标场同课时人数超出围场核定容量")

    if move is None:
        cx.execute(
            """
            INSERT INTO lesson_moves(
                lesson,origin,target,walk,target_walk,reasoning,reviewed_by,status
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,'signed')
            """,
            (
                code,
                origin_code,
                payload.target,
                origin_walk["code"],
                checks["code"],
                payload.reasoning,
                reviewer,
            ),
        )
        _add_event(
            cx,
            event="signed",
            move_status="signed",
            lesson=code,
            origin=origin_code,
            target=payload.target,
            actor=reviewer,
            origin_walk=origin_walk["code"],
            target_walk=checks["code"],
            reasoning=payload.reasoning,
            detail="移场签核",
        )
        message = "移场已签核"
    else:
        has_original = cx.execute(
            "SELECT 1 FROM lesson_move_events WHERE lesson=%s AND event='signed' LIMIT 1",
            (code,),
        ).fetchone()
        if not has_original:
            # Preserve a pre-audit-table sign-off before the row is updated.
            _add_event(
                cx,
                event="signed",
                move_status="signed",
                lesson=code,
                origin=move["origin"],
                target=move["target"],
                actor=move["reviewed_by"],
                origin_walk=move["walk"],
                target_walk=move.get("target_walk"),
                trigger_walk=move.get("trigger_walk"),
                reasoning=move["reasoning"],
                detail="历史签核补档",
            )
        cx.execute(
            """
            UPDATE lesson_moves
            SET target=%s, walk=%s, target_walk=%s, reasoning=%s,
                reviewed_by=%s, status='signed', trigger_walk=NULL,
                review_reason=NULL, changed_on=now()
            WHERE lesson=%s
            """,
            (
                payload.target,
                origin_walk["code"],
                checks["code"],
                payload.reasoning,
                reviewer,
                code,
            ),
        )
        _add_event(
            cx,
            event="resigned",
            move_status="signed",
            lesson=code,
            origin=origin_code,
            target=payload.target,
            actor=reviewer,
            origin_walk=origin_walk["code"],
            target_walk=checks["code"],
            reasoning=payload.reasoning,
            detail="按更新后的可用巡场重新签核",
        )
        message = "待复核课次已重新签核，原名额不重复占用"

    cx.execute(
        "UPDATE lessons SET ring=%s,state='moved' WHERE code=%s",
        (payload.target, code),
    )
    updated_move = cx.execute(
        "SELECT * FROM lesson_moves WHERE lesson=%s", (code,)
    ).fetchone()
    return _result(lesson | {"ring": payload.target, "state": "moved"}, updated_move, message=message)


def _result(lesson, move, *, message=None, duplicate=False):
    target_walk = move.get("target_walk") if move else None
    result = {
        "course": lesson["code"],
        "lesson": lesson["code"],
        "code": lesson["code"],
        "ring": lesson["ring"],
        "target": lesson["ring"],
        "state": lesson["state"],
        "move_status": move["status"] if move else "signed",
        "status": move["status"] if move else "signed",
        "walk": move["walk"] if move else None,
        "origin_walk": move["walk"] if move else None,
        "target_walk": target_walk,
        "basis": target_walk,
        "basis_walk": target_walk,
        "message": message or "移场已签核",
    }
    if duplicate:
        result["duplicate"] = True
    return result


def timetable(cx):
    rows = cx.execute(
        """
        SELECT l.*,
               rr.max_riders AS ring_capacity,
               (
                   SELECT coalesce(sum(occ.riders),0)
                   FROM lessons occ
                   WHERE occ.ring=l.ring
                     AND occ.starts_at=l.starts_at
                     AND occ.state<>'paused'
               ) AS ring_load,
               m.origin,m.target,m.reasoning,m.walk,m.reviewed_by,m.changed_on,
               m.status AS move_status,m.target_walk,m.trigger_walk,m.review_reason,
               tw.barrier AS trigger_barrier,tw.observed AS trigger_observed,
               tw.source AS trigger_source,
               cb.code AS current_basis,cb.barrier AS current_barrier,
               cb.observed AS current_observed,
               (
                   SELECT e.id
                   FROM lesson_move_events e
                   WHERE e.lesson=l.code AND e.event='signed'
                   ORDER BY e.id LIMIT 1
               ) AS original_event_id
        FROM lessons l
        JOIN riding_rings rr ON rr.code=l.ring
        LEFT JOIN lesson_moves m ON m.lesson=l.code
        LEFT JOIN ring_walks tw ON tw.code=m.trigger_walk
        LEFT JOIN LATERAL (
            SELECT w.code,w.barrier,w.observed
            FROM ring_walks w
            WHERE w.ring=COALESCE(m.target,l.ring)
              AND w.outcome IS NULL
              AND w.observed=((l.starts_at AT TIME ZONE 'UTC') + INTERVAL '8 hours')::date
            ORDER BY NULLIF(regexp_replace(w.code, '[^0-9]', '', 'g'), '')::bigint DESC NULLS LAST,
                     w.code DESC
            LIMIT 1
        ) cb ON true
        ORDER BY l.starts_at,l.code
        """
    ).fetchall()

    for row in rows:
        load = row.get("ring_load") or 0
        capacity = row.get("ring_capacity")
        row["occupied_riders"] = load
        row["occupancy"] = load
        row["capacity"] = capacity
        row["remaining_seats"] = None if capacity is None else max(capacity - load, 0)
        is_review = (
            row["state"] in REVIEW_STATES
            or row.get("move_status") in REVIEW_STATES
            or row["state"] == "review"
            or row.get("move_status") == "review"
        )
        row["review_required"] = is_review
        row["pending_review"] = is_review
        row["needs_review"] = is_review
        row["review"] = is_review
        row["is_stale"] = is_review
        row["status"] = row.get("move_status") or row["state"]
        row["lesson_state"] = row["state"]
        row["review_status"] = "pending_review" if is_review else "signed"
        row["review_state"] = "pending_review" if is_review else "current"
        row["target_walk"] = row.get("target_walk")
        row["signed_basis"] = row.get("target_walk")
        row["basis_walk"] = row.get("target_walk")
        row["basis"] = row.get("target_walk")
        row["trigger_code"] = row.get("trigger_walk")
        row["trigger"] = row.get("trigger_walk")
        row["trigger_walk_code"] = row.get("trigger_walk")
        row["triggered_walk"] = row.get("trigger_walk")
        row["review_trigger"] = row.get("trigger_walk")
        row["review_trigger_walk"] = row.get("trigger_walk")
        row["triggered_by_walk"] = row.get("trigger_walk")
        if row.get("trigger_walk"):
            row["trigger_record"] = {
                "code": row["trigger_walk"],
                "barrier": row.get("trigger_barrier"),
                "observed": row.get("trigger_observed"),
                "source": row.get("trigger_source"),
            }
        else:
            row["trigger_record"] = None
        if row.get("original_event_id"):
            original = cx.execute(
                "SELECT * FROM lesson_move_events WHERE id=%s",
                (row["original_event_id"],),
            ).fetchone()
            row["original_signoff"] = original
        else:
            original = None
            row["original_signoff"] = None

        # Convenient top-level aliases so the first sign-off remains easy to
        # assert after a later re-sign overwrites the current move columns.
        row["original_reviewed_by"] = (original or {}).get("actor") if original else row.get("reviewed_by")
        row["original_reviewer"] = row["original_reviewed_by"]
        row["original_reasoning"] = (original or {}).get("reasoning") if original else row.get("reasoning")
        row["original_walk"] = (original or {}).get("origin_walk") if original else row.get("walk")
        row["original_target_walk"] = (original or {}).get("target_walk") if original else row.get("target_walk")
        row["original_signed_at"] = (original or {}).get("created_at") if original else row.get("changed_on")
    return rows


def history(cx, code):
    lesson = cx.execute("SELECT code FROM lessons WHERE code=%s", (code,)).fetchone()
    if not lesson:
        raise HTTPException(404, "找不到课次")
    return cx.execute(
        "SELECT * FROM lesson_move_events WHERE lesson=%s ORDER BY created_at,id",
        (code,),
    ).fetchall()
