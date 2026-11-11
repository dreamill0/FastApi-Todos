import json
import logging                                   
import sys                                       
import time                                      
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional
from prometheus_fastapi_instrumentator import Instrumentator  # Prometheus 메트릭 수집

BASE_DIR = Path(__file__).resolve().parent       # main.py 가 있는 폴더
TODO_FILE = BASE_DIR / "todo.json"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

if not TODO_FILE.exists():                       # 파일이 없으면 빈 목록으로 생성
    TODO_FILE.write_text("[]", encoding="utf-8")

app = FastAPI(title="To-Do List API")

# Prometheus 메트릭 엔드포인트(/metrics) 자동 수집 설정
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# 액세스 로그를 표준 출력(stdout)으로 기록
# Docker가 stdout을 컨테이너 로그로 저장하고, Alloy가 그 로그를 읽어 Loki로 전송
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)
custom_logger.addHandler(logging.StreamHandler(sys.stdout))
custom_logger.propagate = False                  # 상위 로거로 넘겨 두 번 찍히는 것을 방지

# uvicorn 기본 액세스 로그 끄기 (아래 미들웨어가 대신 기록)
# 켜 두면 요청 1번에 로그가 2줄씩 남아 대시보드 카운트가 2배가 됨
logging.getLogger("uvicorn.access").disabled = True


@app.middleware("http")                          # 모든 요청을 한 줄씩 기록
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    client = request.client.host if request.client else "-"
    # 형식: IP - "METHOD PATH HTTP/1.1" 상태코드 응답시간 → 7번 LogQL 쿼리가 이 형식으로 파싱
    custom_logger.info(
        f'{client} - "{request.method} {request.url.path} HTTP/1.1" '
        f'{response.status_code} {duration:.3f}s'
    )
    return response

class TodoIn(BaseModel):                         # 클라이언트가 보내는 데이터 (id 없음)
    title: str = Field(min_length=1, max_length=100)
    description: str = ""
    category: str = "일반"
    priority: str = "중"
    completed: bool = False

class TodoStatusUpdate(BaseModel):
    completed: bool

class TodoItem(TodoIn):                          # 서버가 돌려주는 데이터 (id 있음)
    id: int


def load_todos() -> list[TodoItem]:
    raw = TODO_FILE.read_text(encoding="utf-8") if TODO_FILE.exists() else "[]"
    return [TodoItem(**t) for t in json.loads(raw)]


def save_todos(todos: list[TodoItem]) -> None:
    data = json.dumps([t.model_dump() for t in todos], indent=2, ensure_ascii=False)
    TODO_FILE.write_text(data, encoding="utf-8")


def find_index(todos: list[TodoItem], todo_id: int) -> int:
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            return i
    raise HTTPException(404, "To-Do item not found")


@app.get("/todos")                                            # 목록 조회 (카테고리, 정렬, 페이지네이션 지원)
def get_todos(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "id",
    order: str = "asc"
) -> list[TodoItem]:
    todos = load_todos()
    
    # 1. 카테고리 필터링 (전체가 아니거나 값이 있을 때)
    if category and category != "전체":
        todos = [t for t in todos if t.category == category]
        
    # 2. 정렬 (Sorting)
    reverse_flag = (order.lower() == "desc")
    try:
        todos = sorted(todos, key=lambda x: getattr(x, sort_by, 0), reverse=reverse_flag)
    except AttributeError:
        pass  # 잘못된 필드명인 경우 정렬을 건너뜁니다.
        
    # 3. 페이지네이션 (Skip & Limit)
    return todos[skip : skip + limit]


@app.post("/todos", status_code=201)                           # 할 일 추가
def create_todo(payload: TodoIn) -> TodoItem:
    todos = load_todos()
    new_id = max((t.id for t in todos), default=0) + 1
    todo = TodoItem(id=new_id, **payload.model_dump())
    save_todos(todos + [todo])
    return todo


@app.put("/todos/{todo_id}", responses={404: {"description": "Not Found"}})  # 전체 수정
def update_todo(todo_id: int, payload: TodoIn) -> TodoItem:
    todos = load_todos()
    todo = TodoItem(id=todo_id, **payload.model_dump())
    todos[find_index(todos, todo_id)] = todo
    save_todos(todos)
    return todo


@app.delete("/todos/{todo_id}", status_code=204, responses={404: {"description": "Not Found"}})  # 삭제
def delete_todo(todo_id: int) -> None:
    todos = load_todos()
    del todos[find_index(todos, todo_id)]
    save_todos(todos)


@app.patch("/todos/{todo_id}/status", responses={404: {"description": "Not Found"}})  # 완료 상태만 수정
def update_todo_status(todo_id: int, payload: TodoStatusUpdate) -> TodoItem:
    todos = load_todos()
    idx = find_index(todos, todo_id)
    
    todos[idx].completed = payload.completed
    save_todos(todos)
    return todos[idx]


@app.get("/", include_in_schema=False)                         # 프론트엔드 HTML 화면 서빙
def read_root() -> FileResponse:
    return FileResponse(INDEX_FILE, media_type="text/html")