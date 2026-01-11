from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional
import os

load_dotenv()

# Database setup
DB_URL = os.getenv("DB_URL", "sqlite:///./tasks.db")
engine = create_engine(DB_URL, echo=True)


def create_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    create_tables()
    yield


app = FastAPI(
    title="Task Management API",
    description="A complete CRUD API for managing tasks",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================
# Database Models
# ============================================

class Task(SQLModel, table=True):
    """Task database model"""
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    priority: str = Field(default="medium")  # low, medium, high
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================
# Request/Response Models
# ============================================

class TaskCreate(BaseModel):
    """Model for creating a new task"""
    title: str
    description: str | None = None
    completed: bool = False
    priority: str = "medium"


class TaskUpdate(BaseModel):
    """Model for full task update (PUT)"""
    title: str
    description: str | None = None
    completed: bool = False
    priority: str = "medium"


class TaskPatch(BaseModel):
    """Model for partial task update (PATCH)"""
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None


# ============================================
# Database Functions
# ============================================

def get_session():
    """Dependency that provides database sessions"""
    with Session(engine) as session:
        yield session


# ============================================
# API Endpoints
# ============================================

@app.get("/", status_code=status.HTTP_200_OK)
def root() -> dict:
    """Root endpoint - API welcome message"""
    return {"message": "Welcome to Task Management API"}


# CREATE - Add new task
@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, session: Session = Depends(get_session)) -> dict:
    """Create a new task"""
    db_task = Task(
        title=task.title,
        description=task.description,
        completed=task.completed,
        priority=task.priority
    )
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return {
        "id": db_task.id,
        "title": db_task.title,
        "description": db_task.description,
        "completed": db_task.completed,
        "priority": db_task.priority,
        "created_at": db_task.created_at.isoformat()
    }


# READ - Get all tasks
@app.get("/tasks", status_code=status.HTTP_200_OK)
def get_all_tasks(session: Session = Depends(get_session)) -> list[dict]:
    """Retrieve all tasks"""
    tasks = session.exec(select(Task)).all()
    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "priority": task.priority,
            "created_at": task.created_at.isoformat()
        }
        for task in tasks
    ]


# READ - Get single task by id
@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def get_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    """Retrieve a task by id"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
        "priority": task.priority,
        "created_at": task.created_at.isoformat()
    }


# UPDATE - Full update (PUT)
@app.put("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def update_task(task_id: int, task: TaskUpdate, session: Session = Depends(get_session)) -> dict:
    """Update a task by id (full update)"""
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_task.title = task.title
    db_task.description = task.description
    db_task.completed = task.completed
    db_task.priority = task.priority

    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    return {
        "id": db_task.id,
        "title": db_task.title,
        "description": db_task.description,
        "completed": db_task.completed,
        "priority": db_task.priority,
        "created_at": db_task.created_at.isoformat()
    }


# UPDATE - Partial update (PATCH)
@app.patch("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def patch_task(task_id: int, task: TaskPatch, session: Session = Depends(get_session)) -> dict:
    """Update a task by id (partial update)"""
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = task.model_dump(exclude_unset=True)
    for key, value in task_data.items():
        setattr(db_task, key, value)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    return {
        "id": db_task.id,
        "title": db_task.title,
        "description": db_task.description,
        "completed": db_task.completed,
        "priority": db_task.priority,
        "created_at": db_task.created_at.isoformat()
    }


# DELETE - Remove task
@app.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    """Delete a task by id"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(task)
    session.commit()

    return {"message": f"Task {task_id} deleted successfully"}
