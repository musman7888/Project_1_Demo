import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from main import app, get_session, Task


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture(name="session")
def session_fixture():
    """Create a new database session for each test"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with overridden database session"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="sample_task")
def sample_task_fixture(client: TestClient):
    """Create a sample task for testing"""
    task_data = {
        "title": "Sample Task",
        "description": "This is a sample task",
        "completed": False,
        "priority": "medium"
    }
    response = client.post("/tasks", json=task_data)
    return response.json()


# ============================================
# Success Tests - Root Endpoint
# ============================================

def test_root(client: TestClient):
    """Test root endpoint returns welcome message"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Task Management API"}


# ============================================
# Success Tests - CREATE
# ============================================

def test_create_task(client: TestClient):
    """Test POST creates new task with all fields"""
    task_data = {
        "title": "Complete project",
        "description": "Finish the API project",
        "completed": False,
        "priority": "high"
    }
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Complete project"
    assert data["description"] == "Finish the API project"
    assert data["completed"] == False
    assert data["priority"] == "high"
    assert "id" in data
    assert "created_at" in data


def test_create_task_minimal(client: TestClient):
    """Test POST creates task with only required fields"""
    task_data = {"title": "Minimal task"}
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal task"
    assert data["description"] is None
    assert data["completed"] == False
    assert data["priority"] == "medium"


def test_create_task_with_completed_status(client: TestClient):
    """Test POST creates task with completed status"""
    task_data = {
        "title": "Already done",
        "completed": True
    }
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 201
    assert response.json()["completed"] == True


# ============================================
# Success Tests - READ
# ============================================

def test_get_all_tasks_empty(client: TestClient):
    """Test GET all tasks returns empty list when no tasks"""
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_tasks(client: TestClient, sample_task):
    """Test GET all tasks returns list with tasks"""
    response = client.get("/tasks")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Sample Task"


def test_get_task_by_id(client: TestClient, sample_task):
    """Test GET task by id returns correct task"""
    task_id = sample_task["id"]
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Sample Task"
    assert data["description"] == "This is a sample task"


# ============================================
# Success Tests - UPDATE (PUT)
# ============================================

def test_update_task_put(client: TestClient, sample_task):
    """Test PUT performs full update"""
    task_id = sample_task["id"]
    updated_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "completed": True,
        "priority": "high"
    }
    response = client.put(f"/tasks/{task_id}", json=updated_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["description"] == "Updated description"
    assert data["completed"] == True
    assert data["priority"] == "high"


def test_update_task_put_clears_optional_fields(client: TestClient, sample_task):
    """Test PUT clears optional fields when not provided"""
    task_id = sample_task["id"]
    updated_data = {
        "title": "Minimal Update",
        "description": None,
        "completed": False,
        "priority": "low"
    }
    response = client.put(f"/tasks/{task_id}", json=updated_data)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] is None


# ============================================
# Success Tests - UPDATE (PATCH)
# ============================================

def test_update_task_patch_title(client: TestClient, sample_task):
    """Test PATCH updates only title"""
    task_id = sample_task["id"]
    patch_data = {"title": "Patched Title"}
    response = client.patch(f"/tasks/{task_id}", json=patch_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Patched Title"
    assert data["description"] == "This is a sample task"  # Unchanged


def test_update_task_patch_completed(client: TestClient, sample_task):
    """Test PATCH updates only completed status"""
    task_id = sample_task["id"]
    patch_data = {"completed": True}
    response = client.patch(f"/tasks/{task_id}", json=patch_data)

    assert response.status_code == 200
    data = response.json()
    assert data["completed"] == True
    assert data["title"] == "Sample Task"  # Unchanged


def test_update_task_patch_priority(client: TestClient, sample_task):
    """Test PATCH updates only priority"""
    task_id = sample_task["id"]
    patch_data = {"priority": "high"}
    response = client.patch(f"/tasks/{task_id}", json=patch_data)

    assert response.status_code == 200
    assert response.json()["priority"] == "high"


def test_update_task_patch_multiple_fields(client: TestClient, sample_task):
    """Test PATCH updates multiple fields"""
    task_id = sample_task["id"]
    patch_data = {
        "title": "Multi-patch",
        "completed": True
    }
    response = client.patch(f"/tasks/{task_id}", json=patch_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Multi-patch"
    assert data["completed"] == True


# ============================================
# Success Tests - DELETE
# ============================================

def test_delete_task(client: TestClient, sample_task):
    """Test DELETE removes task and returns success message"""
    task_id = sample_task["id"]
    response = client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"]

    # Verify task is actually deleted
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


# ============================================
# Fail Tests - 404 Not Found
# ============================================

def test_get_task_not_found(client: TestClient):
    """Test GET with invalid id returns 404"""
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_put_not_found(client: TestClient):
    """Test PUT with invalid id returns 404"""
    updated_data = {
        "title": "Test",
        "description": None,
        "completed": False,
        "priority": "medium"
    }
    response = client.put("/tasks/999", json=updated_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_patch_not_found(client: TestClient):
    """Test PATCH with invalid id returns 404"""
    patch_data = {"title": "Test"}
    response = client.patch("/tasks/999", json=patch_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_delete_task_not_found(client: TestClient):
    """Test DELETE with invalid id returns 404"""
    response = client.delete("/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ============================================
# Fail Tests - Validation Errors
# ============================================

def test_create_task_missing_title(client: TestClient):
    """Test POST without title returns 422"""
    task_data = {"description": "No title provided"}
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 422


def test_create_task_empty_body(client: TestClient):
    """Test POST with empty body returns 422"""
    response = client.post("/tasks", json={})

    assert response.status_code == 422


# ============================================
# Parameterized Tests
# ============================================

@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_create_task_with_priorities(client: TestClient, priority: str):
    """Test creating tasks with different priority levels"""
    task_data = {"title": f"Task with {priority} priority", "priority": priority}
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 201
    assert response.json()["priority"] == priority


@pytest.mark.parametrize("completed", [True, False])
def test_create_task_with_completed_status_parametrized(client: TestClient, completed: bool):
    """Test creating tasks with different completed statuses"""
    task_data = {"title": "Status test", "completed": completed}
    response = client.post("/tasks", json=task_data)

    assert response.status_code == 201
    assert response.json()["completed"] == completed
