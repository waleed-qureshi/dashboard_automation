from app.db import SessionLocal
from app import analytics


def test_compute_member_loads_structure():
    db = SessionLocal()
    res = analytics.compute_member_loads(db)
    assert isinstance(res, list)
    if len(res) > 0:
        first = res[0]
        assert 'user_id' in first
        assert 'utilization_pct' in first
        assert 'status' in first
    db.close()


def test_detect_no_work_until_last_day_runs():
    db = SessionLocal()
    res = analytics.detect_no_work_until_last_day(db)
    assert isinstance(res, list)
    db.close()
