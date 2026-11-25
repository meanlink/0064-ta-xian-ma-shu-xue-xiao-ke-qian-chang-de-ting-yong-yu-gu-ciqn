from pathlib import Path

from fastapi import APIRouter
from rings_api import router as rings
from walk_api import router as walk
from cutoff_api import router as cutoff
from lessons_api import router as lessons
from paint_decision import run_job

router = APIRouter(prefix="/api")
router.include_router(rings)
router.include_router(walk)
router.include_router(cutoff)
router.include_router(lessons)


def seed(connection):
    connection.execute(Path(__file__).with_name("demo.sql").read_text())
