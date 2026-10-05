"""Playwright(Chromium, headless)을 이용한 To-Do List UI 테스트."""
import uuid

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture
def page(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.on("dialog", lambda dialog: dialog.accept())
        pg = context.new_page()
        pg.goto(live_server)
        pg.wait_for_selector("#todo-form")
        yield pg
        context.close()
        browser.close()


def unique_title() -> str:
    return f"Playwright-{uuid.uuid4().hex[:8]}"


def find_item(page, title):
    item = page.locator("li", has_text=title)
    item.first.wait_for(state="visible", timeout=10_000)
    return item.first


def find_editing_item(page):
    form = page.locator("li .edit-form")
    form.first.wait_for(state="visible", timeout=10_000)
    return page.locator("li", has=page.locator(".edit-form")).first


def item_is_gone(page, title):
    return page.locator("li", has_text=title).count() == 0


def add_todo(page, title, description="Playwright 테스트", category="공부", priority="⭐⭐"):
    page.fill("#title", title)
    page.fill("#description", description)
    page.select_option("#category", category)
    page.select_option("#priority", priority)
    page.click("#todo-form button[type='submit']")
    return find_item(page, title)


def delete_todo(page, title):
    item = find_item(page, title)
    item.locator("button", has_text="Delete").click()
    page.wait_for_function(
        "title => ![...document.querySelectorAll('li')].some(li => li.textContent.includes(title))",
        arg=title,
    )


def test_page_loads_with_todo_form(page):
    assert page.title() == "To-Do List"
    assert "Mint To-Do List" in page.locator("h1").inner_text()
    assert page.locator("#todo-form").is_visible()


def test_add_todo_appears_in_list(page):
    title = unique_title()
    try:
        item = add_todo(page, title, description="추가 테스트", category="과제", priority="⭐⭐⭐")
        text = item.inner_text()
        assert title in text
        assert "추가 테스트" in text
        assert "과제" in text
    finally:
        delete_todo(page, title)


def test_toggle_complete_marks_item_done(page):
    title = unique_title()
    try:
        item = add_todo(page, title)
        item.locator("input[type='checkbox']").check()
        page.wait_for_function(
            "title => {"
            "  const li = [...document.querySelectorAll('li')].find(el => el.textContent.includes(title));"
            "  return li && li.querySelector('span.done');"
            "}",
            arg=title,
        )
    finally:
        delete_todo(page, title)


def test_edit_todo_updates_title(page):
    title = unique_title()
    updated_title = f"{title}-Updated"
    try:
        add_todo(page, title)
        item = find_item(page, title)
        item.locator("button", has_text="Edit").click()

        # 수정 모드에서는 제목이 <input value="...">에만 담겨 텍스트 검색(has_text)으로는
        # 더 이상 찾을 수 없으므로, 화면에 하나뿐인 .edit-form을 통해 접근한다.
        editing_item = find_editing_item(page)
        editing_item.locator("input[type='text']").first.fill(updated_title)
        editing_item.locator("button", has_text="Save").click()

        updated_item = find_item(page, updated_title)
        assert updated_title in updated_item.inner_text()
    finally:
        delete_todo(page, updated_title)


def test_delete_todo_removes_item(page):
    title = unique_title()
    add_todo(page, title)
    delete_todo(page, title)
    assert item_is_gone(page, title)
