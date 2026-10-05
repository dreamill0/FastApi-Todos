"""Playwright/Selenium UI 테스트 공용 설정.

tests/test_integraion.py 가 바라보는 팀 공용 서버(163.239.77.78:5002)에는 현재
로컬 코드보다 오래된 화면(카테고리/중요도 선택, 인라인 수정 폼 없음)이 배포되어
있어 최신 UI 요소를 검증할 수 없다. 그래서 UI 테스트는 conftest.py 의
`live_server` 픽스처가 그때그때 띄우는 로컬 서버를 대상으로 한다.
"""

BASE_URL = "http://127.0.0.1:8765"
