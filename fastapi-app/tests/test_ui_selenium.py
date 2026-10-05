"""Selenium(Chrome, headless)을 이용한 To-Do List UI 테스트."""
import uuid

import pytest
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


@pytest.fixture
def driver(live_server):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    drv = webdriver.Chrome(options=options)
    drv.get(live_server)
    WebDriverWait(drv, 10).until(EC.presence_of_element_located((By.ID, "todo-form")))
    yield drv
    drv.quit()


def unique_title() -> str:
    return f"Selenium-{uuid.uuid4().hex[:8]}"


def find_item(driver, title):
    def _find(d):
        try:
            return next((li for li in d.find_elements(By.TAG_NAME, "li") if title in li.text), None)
        except StaleElementReferenceException:
            return None

    return WebDriverWait(driver, 10, ignored_exceptions=(StaleElementReferenceException,)).until(_find)


def find_editing_item(driver):
    def _find(d):
        try:
            forms = d.find_elements(By.CSS_SELECTOR, ".edit-form")
            return forms[0].find_element(By.XPATH, "./..") if forms else None
        except StaleElementReferenceException:
            return None

    return WebDriverWait(driver, 10, ignored_exceptions=(StaleElementReferenceException,)).until(_find)


def item_is_gone(driver, title):
    try:
        return not any(title in li.text for li in driver.find_elements(By.TAG_NAME, "li"))
    except StaleElementReferenceException:
        return False


def add_todo(driver, title, description="Selenium 테스트", category="공부", priority="⭐⭐"):
    driver.find_element(By.ID, "title").send_keys(title)
    driver.find_element(By.ID, "description").send_keys(description)
    Select(driver.find_element(By.ID, "category")).select_by_value(category)
    Select(driver.find_element(By.ID, "priority")).select_by_value(priority)
    driver.find_element(By.CSS_SELECTOR, "#todo-form button[type='submit']").click()
    return find_item(driver, title)


def delete_todo(driver, title):
    item = find_item(driver, title)
    item.find_element(By.XPATH, ".//button[text()='Delete']").click()
    WebDriverWait(driver, 10).until(EC.alert_is_present())
    driver.switch_to.alert.accept()
    WebDriverWait(driver, 10, ignored_exceptions=(StaleElementReferenceException,)).until(
        lambda d: item_is_gone(d, title)
    )


def test_page_loads_with_todo_form(driver):
    assert driver.title == "To-Do List"
    assert "Mint To-Do List" in driver.find_element(By.TAG_NAME, "h1").text
    assert driver.find_element(By.ID, "todo-form").is_displayed()


def test_add_todo_appears_in_list(driver):
    title = unique_title()
    try:
        item = add_todo(driver, title, description="추가 테스트", category="과제", priority="⭐⭐⭐")
        assert title in item.text
        assert "추가 테스트" in item.text
        assert "과제" in item.text
    finally:
        delete_todo(driver, title)


def test_toggle_complete_marks_item_done(driver):
    title = unique_title()
    try:
        item = add_todo(driver, title)
        checkbox = item.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        checkbox.click()

        def is_done(d):
            try:
                li = find_item(d, title)
                return "done" in li.find_element(By.TAG_NAME, "span").get_attribute("class")
            except StaleElementReferenceException:
                return False

        WebDriverWait(driver, 10, ignored_exceptions=(StaleElementReferenceException,)).until(is_done)
    finally:
        delete_todo(driver, title)


def test_edit_todo_updates_title(driver):
    title = unique_title()
    updated_title = f"{title}-Updated"
    try:
        add_todo(driver, title)
        item = find_item(driver, title)
        item.find_element(By.XPATH, ".//button[text()='Edit']").click()

        # 수정 모드에서는 제목이 <input value="...">에만 담겨 li.text로는 더 이상
        # 찾을 수 없으므로, 화면에 하나뿐인 .edit-form을 통해 접근한다.
        editing_item = find_editing_item(driver)
        title_input = editing_item.find_element(By.CSS_SELECTOR, "input[type='text']")
        title_input.clear()
        title_input.send_keys(updated_title)
        editing_item.find_element(By.XPATH, ".//button[text()='Save']").click()

        updated_item = find_item(driver, updated_title)
        assert updated_title in updated_item.text
    finally:
        delete_todo(driver, updated_title)


def test_delete_todo_removes_item(driver):
    title = unique_title()
    add_todo(driver, title)
    delete_todo(driver, title)
    assert item_is_gone(driver, title)
