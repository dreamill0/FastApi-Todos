import base64
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from pytest_html import extras
from pytest_metadata.plugin import metadata_key

from tests.ui_config import BASE_URL

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TODO_FILE = PROJECT_ROOT / "todo.json"


def pytest_configure(config):
    config.stash[metadata_key]["Target URL"] = BASE_URL
    config.stash[metadata_key]["UI Frameworks"] = "Selenium (Chrome headless), Playwright (Chromium headless)"
    config.stash[metadata_key]["Scope"] = "To-Do List UI: 추가/완료토글/수정/삭제"


@pytest.fixture(scope="session")
def live_server():
    """UI 테스트 동안 로컬 uvicorn 서버를 띄우고, 끝나면 todo.json을 원상 복구한다."""
    original_todo_json = TODO_FILE.read_text(encoding="utf-8") if TODO_FILE.exists() else None

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        ready = False
        while time.monotonic() < deadline:
            try:
                urlopen(f"{BASE_URL}/todos", timeout=1)
                ready = True
                break
            except URLError:
                time.sleep(0.3)
        if not ready:
            raise RuntimeError("UI 테스트용 로컬 서버가 기동되지 않았습니다.")
        yield BASE_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        if original_todo_json is not None:
            TODO_FILE.write_text(original_todo_json, encoding="utf-8")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return

    extra = getattr(report, "extras", [])
    driver = item.funcargs.get("driver")
    page = item.funcargs.get("page")
    try:
        if driver is not None:
            png = driver.get_screenshot_as_png()
        elif page is not None:
            png = page.screenshot()
        else:
            png = None
        if png is not None:
            extra.append(extras.image(base64.b64encode(png).decode("ascii")))
    except Exception:
        pass
    report.extras = extra
