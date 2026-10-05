import pytest
import requests

# 팀 서버에 배포된 실제 주소와 포트
BASE_URL = "http://163.239.77.78:5002"

def test_integration_crud_flow():
    # 1. 추가 (201 Created)
    payload = {"title": "Integration Test", "description": "automated test"}
    res = requests.post(f"{BASE_URL}/todos", json=payload)
    assert res.status_code == 201
    created_todo = res.json()
    todo_id = created_todo["id"]

    # 2. 조회 (200 OK)
    res = requests.get(f"{BASE_URL}/todos")
    assert res.status_code == 200
    todos = res.json()
    assert any(t["id"] == todo_id for t in todos)

    # 3. 수정 (200 OK)
    update_payload = {"title": "Updated Title", "description": "updated desc", "completed": True}
    res = requests.put(f"{BASE_URL}/todos/{todo_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"

    # 4. 삭제 (204 No Content)
    res = requests.delete(f"{BASE_URL}/todos/{todo_id}")
    assert res.status_code == 204

def test_integration_error_cases():
    # 오류 요청 1: title 없이 추가하면 422
    invalid_payload = {"description": "no title"}
    res = requests.post(f"{BASE_URL}/todos", json=invalid_payload)
    assert res.status_code == 422

    # 오류 요청 2: 없는 id를 삭제하면 404
    res = requests.delete(f"{BASE_URL}/todos/999999")
    assert res.status_code == 404