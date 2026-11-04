from main import app, save_todos, load_todos, TodoItem

def test_get_todos_with_category_filter():
    # 서로 다른 카테고리를 가진 두 개의 투두 생성
    todo1 = TodoItem(id=1, title="공부하기", description="파이썬 공부", category="공부", priority="상", completed=False)
    todo2 = TodoItem(id=2, title="운동하기", description="헬스장 가기", category="개인", priority="중", completed=False)
    save_todos([todo1, todo2])

    # 1. "공부" 카테고리로 필터링 조회 요청
    response = client.get("/todos?category=공부")
    assert response.status_code == 200
    data = response.json()
    
    # "공부" 카테고리 항목만 1개 반환되는지 확인
    assert len(data) == 1
    assert data[0]["title"] == "공부하기"
    assert data[0]["category"] == "공부"

    # 2. 존재하지 않는 카테고리로 조회 시 빈 리스트 반환 확인
    response_empty = client.get("/todos?category=존재안함")
    assert response_empty.status_code == 200
    assert response_empty.json() == []