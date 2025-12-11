import random
from datetime import datetime, timedelta
import os, sys
# ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.db import init_db, SessionLocal, User, Task, TimeLog, Lead, Project


def seed():
    init_db()
    db = SessionLocal()
    # create users
    users = []
    for i in range(5):
        u = User(name=f"User {i+1}", capacity_hours_per_week=40)
        db.add(u)
        users.append(u)
    db.commit()

    # create projects
    for i in range(3):
        p = Project(name=f"Project {i+1}", client=f"Client {i+1}", forecasted_revenue=10000*(i+1), actual_revenue=8000*(i+1), cost=9000*(i+1))
        db.add(p)
    db.commit()

    # create tasks
    users_db = db.query(User).all()
    projects_db = db.query(Project).all()
    for i in range(30):
        assignee = random.choice(users_db)
        due = datetime.utcnow() + timedelta(days=random.randint(-5, 10))
        t = Task(title=f"Task {i+1}", assignee_id=assignee.id, status=random.choice(["todo", "in review", "done"]), due_date=due)
        if random.random() < 0.2:
            t.review_started_at = datetime.utcnow() - timedelta(days=random.randint(0,6))
        if random.random() < 0.05:
            t.blocked = True
        t.status_change_count = random.randint(0,8)
        t.project_id = random.choice(projects_db).id
        db.add(t)
    db.commit()

    tasks = db.query(Task).all()
    # timelogs
    for t in tasks:
        if random.random() < 0.7:
            for _ in range(random.randint(1,3)):
                tl = TimeLog(task_id=t.id, user_id=t.assignee_id, hours=random.uniform(0.5,4.0), created_at=datetime.utcnow() - timedelta(days=random.randint(0,10)), comment=(None if random.random()<0.3 else "worked"), files_attached=(random.random()<0.5))
                db.add(tl)
    db.commit()

    # leads
    sources = ["google","referral","ads","events","partner"]
    for i in range(50):
        src = random.choice(sources)
        converted = random.random() < 0.25
        lost = (not converted) and (random.random() < 0.4)
        l = Lead(source=src, created_at=datetime.utcnow() - timedelta(days=random.randint(0,120)), converted=converted, lost=lost, lost_reason=(None if not lost else random.choice(["price","no_budget","no-fit"])), priority=random.randint(1,5), estimated_value=random.uniform(1000,20000))
        db.add(l)
    db.commit()

    print("Sample data created in reports.db")
    db.close()


if __name__ == '__main__':
    seed()
