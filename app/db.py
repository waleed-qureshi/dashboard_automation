from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

DATABASE_URL = "sqlite:///./reports.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    capacity_hours_per_week = Column(Float, default=40.0)
    role = Column(String, default="member")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="todo")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, default=4.0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    review_started_at = Column(DateTime, nullable=True)
    blocked = Column(Boolean, default=False)
    status_change_count = Column(Integer, default=0)

    assignee = relationship("User")


class TimeLog(Base):
    __tablename__ = "timelogs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    hours = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(Text, nullable=True)
    files_attached = Column(Boolean, default=False)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    client = Column(String)
    forecasted_revenue = Column(Float, default=0.0)
    actual_revenue = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    status = Column(String, default="on track")


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    converted = Column(Boolean, default=False)
    lost = Column(Boolean, default=False)
    lost_reason = Column(String, nullable=True)
    priority = Column(Integer, default=1)
    estimated_value = Column(Float, default=0.0)


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
