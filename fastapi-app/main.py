import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator  # ← 추가

BASE_DIR = Path(__file__).resolve().parent       # main.py 가 있는 폴더
TODO_FILE = BASE_DIR / "todo.json"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

if not TODO_FILE.exists():                       # 없으면 빈 목록으로 만들어 둔다
    TODO_FILE.write_text("[]", encoding="utf-8")

app = FastAPI(title="To-Do List API")

# ← 추가: Prometheus 메트릭 엔드포인트(/metrics). 요청 수·응답 시간 등을 자동으로 수집
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

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


@app.get("/todos")                               # 목록 조회
def get_todos() -> list[TodoItem]:
    return load_todos()


@app.post("/todos", status_code=201)             # 추가 — id 는 서버가 매긴다
def create_todo(payload: TodoIn) -> TodoItem:
    todos = load_todos()
    new_id = max((t.id for t in todos), default=0) + 1
    todo = TodoItem(id=new_id, **payload.model_dump())
    save_todos(todos + [todo])
    return todo


@app.put("/todos/{todo_id}", responses={404: {"description": "Not Found"}})  # 수정
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
    
    # 기존 아이템의 completed 값만 변경
    todos[idx].completed = payload.completed
    save_todos(todos)
    return todos[idx]


@app.get("/", include_in_schema=False)           # 화면 서빙
def read_root() -> FileResponse:
    return FileResponse(INDEX_FILE, media_type="text/html")