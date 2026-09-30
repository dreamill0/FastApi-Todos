import pytest
from fastapi.testclient import TestClient

import main
from main import app, save_todos, load_todos, TodoItem

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown(tmp_path, monkeypatch):
    # 실제 todo.json 대신 테스트마다 새 임시 파일 사용
    monkeypatch.setattr(main, "TODO_FILE", tmp_path / "todo.json")
    save_todos([])  # 테스트 전 초기화
    yield
    # 테스트 후 정리

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    todo = TodoItem(id=1, title="Test", description="Test description", category="일반", priority="중", completed=False)
    save_todos([todo])
    response = client.get("/todos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test"

def test_create_todo():
    # main.py의 TodoIn 스펙(title, description, category, priority, completed)에 맞춤
    todo = {
        "title": "Test", 
        "description": "Test description", 
        "category": "업무", 
        "priority": "상", 
        "completed": False
    }
    response = client.post("/todos", json=todo)
    assert response.status_code == 201           # 생성 성공 = 201 Created
    assert response.json()["title"] == "Test"
    assert response.json()["id"] == 1            # id 는 서버가 부여
    assert len(load_todos()) == 1                # 파일에도 저장됐는지 확인

def test_create_todo_invalid():
    todo = {"description": "Test description"}   # 필수 필드 title 누락
    response = client.post("/todos", json=todo)
    assert response.status_code == 422

def test_update_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", category="일반", priority="중", completed=False)
    save_todos([todo])
    updated_todo = {
        "title": "Updated", 
        "description": "Updated description", 
        "category": "공부", 
        "priority": "하", 
        "completed": True
    }
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_update_todo_not_found():
    updated_todo = {
        "title": "Updated", 
        "description": "Updated description", 
        "category": "공부", 
        "priority": "하", 
        "completed": True
    }
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 404

def test_delete_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", category="일반", priority="중", completed=False)
    save_todos([todo])
    response = client.delete("/todos/1")
    assert response.status_code == 204           # 삭제 성공 = 204 No Content
    assert load_todos() == []

def test_delete_todo_not_found():
    response = client.delete("/todos/1")
    assert response.status_code == 404