from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .db import SessionLocal, init_db
from . import analytics

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('/insights')
def insights(db: Session = Depends(get_db)):
    # return small collection of insights
    out = {}
    out['task_status_overview'] = analytics.task_status_overview(db)
    out['tasks_stuck_in_review'] = analytics.find_tasks_stuck_in_review(db)
    out['tasks_no_work_until_last_day'] = analytics.detect_no_work_until_last_day(db)
    out['unusual_behaviors'] = analytics.unusual_behaviors(db)
    out['member_loads'] = analytics.compute_member_loads(db)
    out['lead_source_rank'] = analytics.rank_lead_sources(db)
    out['lead_close_probs'] = analytics.lead_close_predictor(db)
    out['pipeline_forecast'] = analytics.forecast_pipeline(db)
    out['unprofitable_projects'] = analytics.detect_unprofitable_projects(db)
    return out


@router.get('/predictions')
def predictions(db: Session = Depends(get_db)):
    return {"lead_close_probs": analytics.lead_close_predictor(db), "pipeline_forecast": analytics.forecast_pipeline(db)}


@router.get('/alerts')
def alerts(db: Session = Depends(get_db)):
    a = analytics.unusual_behaviors(db)
    # example: project at risk if forecast far below actual
    projects_at_risk = []
    return {"unusual": a, "projects_at_risk": projects_at_risk}


@router.get('/scores')
def scores(db: Session = Depends(get_db)):
    # simplified score outputs
    return {"team_health_score": 75, "pipeline_score": 68}


@router.get('/data/tasks')
def data_tasks(db: Session = Depends(get_db)):
    q = db.execute('select id,title,status,assignee_id,due_date from tasks')
    return [dict(r) for r in q.fetchall()]
