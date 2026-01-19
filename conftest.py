pytest_plugins = [
    "pytest_bdd",
    "steps.home_steps",
    "steps.login_steps",
    "steps.srp_steps",
    "steps.product_steps",
    "steps.cart_steps",
    "steps.checkout_steps",
    "steps.order_steps",
    "steps.tracking_steps",
    "steps.tracking_validation_steps",
]


import shutil
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
# from src.gtas_python_core.gtas_python_core_vault import Vault
import os
import pytest
import requests
from datetime import datetime
from pathlib import Path
import json
import time
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


# # 브라우저 fixture (세션 단위, 한 번만 실행)
# @pytest.fixture(scope="session")
# def browser():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False, args=["--start-maximized"])  # True/False로 headless 제어
#         yield browser
#         browser.close()
#
#
# # 컨텍스트 fixture (브라우저 환경)
# @pytest.fixture(scope="function")
# def context(browser: Browser):
#     context = browser.new_context(no_viewport=True)
#
#     # navigator.webdriver 우회
#     context.add_init_script("""
#         Object.defineProperty(navigator, 'webdriver', {
#             get: () => undefined
#         });
#     """)
#
#     yield context
#     context.close()
#
#
# # 페이지 fixture
# @pytest.fixture(scope="function")
# def page(context: BrowserContext):
#     page = context.new_page()
#     page.set_default_timeout(10000)  # 기본 10초 타임아웃
#     yield page
#     page.close()


STATE_PATH = "state.json"

# ============================================
# BrowserSession: 브라우저 세션 관리 클래스
# ============================================
class BrowserSession:
    """
    브라우저 세션 관리 클래스 - 현재 active page 참조 관리
    상태 관리자 역할: page stack을 통해 탭 전환 추적
    """
    def __init__(self, page):
        """
        BrowserSession 초기화
        
        Args:
            page: fixture에서 생성한 기본 page (seed 역할)
        """
        self._page_stack = [page]  # page stack으로 전환 이력 관리
    
    @property
    def page(self):
        """
        현재 active page 반환 (가장 최근에 전환된 page)
        """
        return self._page_stack[-1]
    
    def switch_to(self, page):
        """
        새 페이지로 전환 (명시적 전환)
        
        Args:
            page: 전환할 Page 객체
        
        Returns:
            bool: 전환 성공 여부
        """
        if not page:
            logger.warning("BrowserSession: None 페이지로 전환 시도 실패")
            return False
        
        try:
            if page.is_closed():
                logger.warning("BrowserSession: 이미 닫힌 페이지로 전환 시도 실패")
                return False
            
            # 페이지 유효성 검증
            current_url = page.url
            if not current_url or current_url == "about:blank":
                logger.warning(f"BrowserSession: 유효하지 않은 URL의 페이지: {current_url}")
                # about:blank는 잠시 후 로드될 수 있으므로 경고만
            
            self._page_stack.append(page)
            logger.info(f"BrowserSession: 새 페이지로 전환 - URL: {current_url} (stack depth: {len(self._page_stack)})")
            return True
        except Exception as e:
            logger.error(f"BrowserSession: 페이지 전환 중 오류 발생: {e}")
            return False
    
    def restore(self):
        """
        이전 페이지로 복귀 (page stack에서 pop)
        
        Returns:
            bool: 복귀 성공 여부 (stack에 이전 페이지가 있는 경우)
        """
        if len(self._page_stack) > 1:
            # 현재 페이지를 pop하여 이전 페이지로 복귀
            self._page_stack.pop()
            logger.info(f"BrowserSession: 이전 페이지로 복귀 - 현재 URL: {self.page.url} (stack depth: {len(self._page_stack)})")
            return True
        else:
            logger.warning("BrowserSession: 복귀할 이전 페이지가 없음")
            return False
    
    def get_page_stack(self):
        """
        디버깅용: 현재 page stack의 URL 리스트 반환
        
        Returns:
            list: page stack의 URL 리스트
        """
        return [p.url for p in self._page_stack]


# ------------------------
# :일: Playwright 세션 단위 fixture
# ------------------------
@pytest.fixture(scope="session")
def pw():
    """Playwright 세션 관리"""
    with sync_playwright() as p:
        yield p
# ------------------------
# :둘: 브라우저 fixture
# ------------------------
@pytest.fixture(scope="session")
def browser(pw):
    """세션 단위 브라우저"""
    browser = pw.chromium.launch(headless=False)
    yield browser
    browser.close()
# ------------------------
# :셋: Context fixture (각 시나리오마다 독립적으로 생성)
# ------------------------
@pytest.fixture(scope="function")
def context(browser, ensure_login_state):
    """
    브라우저 컨텍스트 fixture
    각 시나리오마다 독립적으로 생성되고 종료 시 정리됩니다.
    """
    ctx = browser.new_context(storage_state=ensure_login_state)
    yield ctx
    ctx.close()
# ------------------------
# :셋: 로그인 상태 검증
# ------------------------
def is_state_valid(state_path: str) -> bool:
    """state.json이 유효한지 확인 (쿠키 기반)"""
    if not os.path.exists(state_path):
        return False
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", [])
        now = time.time()
        # 쿠키 하나라도 만료되지 않았으면 로그인 유지 가능
        if any("expires" in c and c["expires"] and c["expires"] > now for c in cookies):
            return True
        return False
    except Exception as e:
        print(f"[WARN] state.json 검증 오류: {e}")
        return False
# ------------------------
# :넷: 로그인 수행 + state.json 저장
# ------------------------
def create_login_state(pw):
    """로그인 수행 후 state.json 저장"""
    from utils.urls import base_url
    print("[INFO] 로그인 절차 시작")
    browser = pw.chromium.launch(headless=False)  # 화면 확인용
    context = browser.new_context()
    page = context.new_page()
    page.goto(base_url())
    # 로그인 페이지 이동 및 입력
    page.click("text=로그인")
    page.fill("#typeMemberInputId", "t4adbuy01")
    page.fill("#typeMemberInputPassword", "Gmkt1004!!")
    page.click("#btn_memberLogin")
    # 로그인 완료 대기
    page.wait_for_selector("text=로그아웃", timeout=15000)
    # 로그인 상태 저장
    context.storage_state(path=STATE_PATH)
    import json
    with open(STATE_PATH, 'r', encoding='utf-8') as f:
        state = json.load(f)
        cookies_count = len(state.get('cookies', []))
        origins_count = len(state.get('origins', []))
        print(f"[DEBUG] 저장된 쿠키 수: {cookies_count}")
        print(f"[DEBUG] 저장된 origins 수: {origins_count}")
        
        if origins_count > 0:
            for origin in state.get('origins', []):
                origin_url = origin.get('origin', 'N/A')
                localStorage_count = len(origin.get('localStorage', []))
                sessionStorage_count = len(origin.get('sessionStorage', []))
                print(f"[DEBUG] Origin: {origin_url}")
                print(f"  - localStorage: {localStorage_count}개 항목")
                print(f"  - sessionStorage: {sessionStorage_count}개 항목")
        else:
            print("[WARNING] origins가 저장되지 않았습니다. localStorage/sessionStorage가 복원되지 않을 수 있습니다.")
    
    browser.close()
    print("[INFO] 로그인 완료 및 state.json 저장됨")
# ------------------------
# :다섯: 로그인 상태 fixture
# ------------------------
@pytest.fixture(scope="session")
def ensure_login_state(pw):
    """
    state.json 존재 여부 및 유효성 확인.
    없거나 만료 시 자동 로그인 수행
    """
    if not os.path.exists(STATE_PATH):
        print("[INFO] state.json 없음 → 로그인 시도")
        create_login_state(pw)
    elif not is_state_valid(STATE_PATH):
        print("[INFO] state.json 만료됨 → 재로그인 시도")
        create_login_state(pw)
    else:
        print("[INFO] 로그인 세션 유효 → 기존 state.json 사용")
    return STATE_PATH
# ------------------------
# :넷: page fixture (각 시나리오마다 독립적으로 생성)
# ------------------------
@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """
    각 시나리오에서 사용할 page 객체
    각 시나리오마다 독립적으로 생성되고 종료 시 정리됩니다.
    """
    page = context.new_page()
    page.set_default_timeout(10000)
    yield page
    page.close()


# ------------------------
# :다섯: BrowserSession fixture (각 시나리오마다 독립적으로 생성)
# ------------------------
@pytest.fixture(scope="function")
def browser_session(page):
    """
    BrowserSession fixture - 현재 active page 참조 관리
    각 시나리오마다 독립적으로 생성됩니다.
    """
    return BrowserSession(page)


# ------------------------
# :여섯: BDD context fixture (각 시나리오마다 독립적으로 생성)
# ------------------------
@pytest.fixture(scope="function")
def bdd_context():
    """
    시나리오 내 스텝 간 데이터 공유를 위한 전용 객체
    각 시나리오마다 독립적으로 생성됩니다.
    이름 충돌이 없고, 시나리오 메타데이터와 비즈니스 데이터를 분리해서 관리
    
    하위 호환성: 딕셔너리처럼 사용 가능 (bdd_context['key']) + store 속성 사용 가능 (bdd_context.store['key'])
    """
    class Context:
        def __init__(self):
            self.store = {}
            self._dict = {}  # 하위 호환성을 위한 딕셔너리
        
        def __getitem__(self, key):
            """딕셔너리처럼 접근 가능 (하위 호환성)"""
            # store에 있으면 store에서, 없으면 _dict에서
            if key in self.store:
                return self.store[key]
            return self._dict[key]
        
        def __setitem__(self, key, value):
            """딕셔너리처럼 설정 가능 (하위 호환성)"""
            # store와 _dict 모두에 저장 (양쪽에서 접근 가능)
            self.store[key] = value
            self._dict[key] = value
        
        def get(self, key, default=None):
            """딕셔너리처럼 get 메서드 사용 가능 (하위 호환성)"""
            if key in self.store:
                return self.store[key]
            return self._dict.get(key, default)
        
        def __contains__(self, key):
            """in 연산자 지원"""
            return key in self.store or key in self._dict
    
    return Context()


# ============================================
# pytest-bdd hooks (필요 시 추가)
# ============================================
# 각 시나리오가 독립적으로 실행되므로 feature 단위 상태 관리 hook은 제거됨


def pytest_report_teststatus(report, config):
    # 이름에 'wait_'가 들어간 테스트는 리포트 출력에서 숨김
    if any(keyword in report.nodeid for keyword in ["wait_", "fetch"]):
        return report.outcome, None, ""
    return None


# TestRail 연동을 위한 전역 변수 (주석 처리된 TestRail 코드 활성화 시 사용)
testrail_run_id = None


@pytest.hookimpl(hookwrapper=True)
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    """
    각 스텝 실행 후 TestRail에 기록
    스텝 파라미터에서 TC 번호를 추출하여 TestRail에 기록
    """
    outcome = yield
    
    try:
        # 스텝 실행 결과 확인
        if outcome.excinfo is not None:
            step_status = "failed"
            error_msg = str(outcome.excinfo[1]) if outcome.excinfo[1] else "Unknown error"
        else:
            # Soft Assertion 지원: bdd_context에서 실패 여부 확인
            step_status = "passed"
            error_msg = None
            
            if step_func_args:
                bdd_context = step_func_args.get('bdd_context')
                if bdd_context and hasattr(bdd_context, 'get'):
                    # validation_failed 플래그 확인
                    if bdd_context.get('validation_failed'):
                        step_status = "failed"
                        error_msg = bdd_context.get('validation_error_message', '검증 실패')
        
        # TC 번호 추출 시도
        step_case_id = None
        
        # 1. step_func_args에서 TC 번호 파라미터 찾기 (tc_id, tc_module_exposure 등)
        if step_func_args:
            for arg_name, arg_value in step_func_args.items():
                # TC 번호 형식 확인 (C로 시작하는 문자열)
                if isinstance(arg_value, str) and arg_value.startswith("C") and len(arg_value) > 1 and arg_value[1:].isdigit():
                    step_case_id = arg_value
                    break
        
        # 2. step_func_args에서 bdd_context를 통해 TC 번호 찾기
        if step_case_id is None and step_func_args:
            bdd_context = step_func_args.get('bdd_context')
            if bdd_context and hasattr(bdd_context, 'get'):
                step_case_id = bdd_context.get('testrail_tc_id')
        
        # TestRail 기록 (testrail_run_id가 설정되어 있고 TC 번호가 있을 때만)
        if step_case_id and testrail_run_id:
            # Cxxxx → 숫자만 추출
            case_id_num = int(step_case_id[1:]) if step_case_id.startswith("C") else int(step_case_id)
            
            status_id = 5 if step_status == "failed" else 1
            comment = f"스텝: {step.name}\n"
            if error_msg:
                comment += f"오류: {error_msg}"
            
            payload = {
                "status_id": status_id,
                "comment": comment,
            }
            
            try:
                # testrail_post 함수는 TestRail 연동 코드가 활성화되면 사용 가능
                # testrail_post(
                #     f"add_result_for_case/{testrail_run_id}/{case_id_num}", 
                #     payload
                # )
                print(f"[TestRail] 스텝 '{step.name}' 결과 기록 (case_id: {step_case_id}, status: {step_status})")
            except Exception as e:
                print(f"[WARNING] 스텝 TestRail 기록 실패: {e}")
        elif step_case_id:
            # TC 번호는 있지만 testrail_run_id가 없는 경우 (TestRail 연동 미활성화)
            print(f"[TestRail] 스텝 '{step.name}' TC 번호 발견: {step_case_id} (TestRail 연동 미활성화)")
    
    except Exception as e:
        print(f"[ERROR] pytest_bdd_after_step 처리 중 예외 발생: {e}")


# JSON 파일이 들어 있는 폴더 지정
JSON_DIR = Path(__file__).parent / "json"  # json 폴더 내의 JSON 파일 전부 대상


# config.json 파일 로드 (파일이 없거나 비어있을 수 있음)
config = {}
try:
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as config_file:
            content = config_file.read().strip()
            if content:
                config = json.loads(content)
except (json.JSONDecodeError, FileNotFoundError) as e:
    # config.json이 없거나 비어있거나 잘못된 형식이어도 계속 진행
    print(f"[WARNING] config.json 로드 실패 (무시됨): {e}")

# # 환경변수 기반 설정
# TESTRAIL_BASE_URL = config['tr_url']
# TESTRAIL_PROJECT_ID = config['project_id']
# TESTRAIL_SUITE_ID = config['suite_id']
# TESTRAIL_SECTION_ID = config['section_id']  # ✅ 섹션 이름으로 지정
# TESTRAIL_USER = (Vault("gmarket").get_Kv_credential("authentication/testrail/automation")).get("username")
# TESTRAIL_TOKEN = (Vault("gmarket").get_Kv_credential("authentication/testrail/automation")).get("password")
# TESTRAIL_MILESTONE_ID = config['milestone_id']
# testrail_run_id = None
# case_id_map = {}  # {섹션 이름: [케이스ID 리스트]}


# def testrail_get(endpoint):
#     url = f"{TESTRAIL_BASE_URL}/index.php?/api/v2/{endpoint}"
#     r = requests.get(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN))
#     r.raise_for_status()
#     return r.json()


# def testrail_post(endpoint, payload=None, files=None):
#     url = f"{TESTRAIL_BASE_URL}/index.php?/api/v2/{endpoint}"
#     if files:
#         r = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN), files=files)
#     else:
#         r = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN), json=payload)
#     r.raise_for_status()
#     return r.json()


# @pytest.hookimpl(tryfirst=True)
# def pytest_sessionstart(session):
#     """
#     테스트 실행 시작 시:
#     1. section_id 기반으로 해당 섹션의 케이스 ID 가져오기
#     2. 그 케이스들로 Run 생성
#     """
#     global testrail_run_id, case_id_map
#     # 1. section_id 직접 사용
#     if testrail_run_id is not None:
#         print(f"[TestRail] 이미 Run(ID={testrail_run_id})이 존재합니다. 새 Run 생성 생략")
#         return
#     if not TESTRAIL_SECTION_ID:
#         raise RuntimeError("[TestRail] TESTRAIL_SECTION_ID가 정의되지 않았습니다.")
#     # 2. 섹션 내 케이스 가져오기
#     cases = testrail_get(
#         f"get_cases/{TESTRAIL_PROJECT_ID}&suite_id={TESTRAIL_SUITE_ID}&section_id={TESTRAIL_SECTION_ID}"
#     )
#     case_ids = [c["id"] for c in cases]
#     case_id_map[TESTRAIL_SECTION_ID] = case_ids
#     if not case_ids:
#         raise RuntimeError(f"[TestRail] section_id '{TESTRAIL_SECTION_ID}'에 케이스가 없습니다.")
#     # 3. Run 생성
#     run_name = f"AD Regression test dweb {datetime.now():%Y-%m-%d %H:%M:%S}"
#     payload = {
#         "suite_id": TESTRAIL_SUITE_ID,
#         "name": run_name,
#         "include_all": False,
#         "case_ids": case_ids,
#         "milestone_id": TESTRAIL_MILESTONE_ID
#     }
#     run = testrail_post(f"add_run/{TESTRAIL_PROJECT_ID}", payload)
#     testrail_run_id = run["id"]
#     print(f"[TestRail] section_id '{TESTRAIL_SECTION_ID}' Run 생성 완료 (ID={testrail_run_id})")


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     """
#     각 테스트 결과를 TestRail에 기록 + 실패 시 스크린샷 첨부
#     INTERNALERROR 방지를 위해 모든 외부 호출은 try/except로 보호
#     """
#     outcome = yield
#     result = outcome.get_result()

#     try:
#         case_id = item.funcargs.get("case_id")
#         if case_id is None or testrail_run_id is None:
#             return

#         # Cxxxx → 숫자만 추출
#         if isinstance(case_id, str) and case_id.startswith("C"):
#             case_id = case_id[1:]
#         case_id = int(case_id)  # API는 int만 허용

#         screenshot_path = None
#         if result.when == "call":  # 실행 단계만 기록
#             if result.failed:
#                 status_id = 5  # Failed
#                 comment = f"테스트 실패: {result.longrepr}"

#                 # 스크린샷 시도
#                 try:
#                     page = item.funcargs.get("page")
#                     if page and not page.is_closed():
#                         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                         screenshot_path = f"screenshots/{case_id}_{timestamp}.png"
#                         os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
#                         page.screenshot(path=screenshot_path, timeout=2000)
#                 except Exception as e:
#                     print(f"[WARNING] 스크린샷 실패: {e}")

#             elif result.skipped:
#                 status_id = 2  # Blocked
#                 comment = "테스트 스킵"
#             else:
#                 status_id = 1  # Passed
#                 comment = "테스트 성공"

#             # 실행 시간 기록
#             duration_sec = getattr(result, "duration", 0)
#             if duration_sec and duration_sec > 0.1:
#                 elapsed = f"{duration_sec:.1f}s"
#             else:
#                 elapsed = None

#             # stdout 로그 추가
#             stdout = getattr(item, "_stdout_capture", None)
#             if stdout:
#                 comment += f"\n\n--- stdout 로그 ---\n{stdout.strip()}"

#             # TestRail 기록
#             payload = {
#                 "status_id": status_id,
#                 "comment": comment,
#             }
#             if elapsed:
#                 payload["elapsed"] = elapsed

#             result_id = None
#             try:
#                 result_obj = testrail_post(
#                     f"add_result_for_case/{testrail_run_id}/{case_id}", payload
#                 )
#                 result_id = result_obj.get("id")
#             except Exception as e:
#                 print(f"[WARNING] TestRail 기록 실패: {e}")

#             # 스크린샷 첨부
#             if screenshot_path and result_id:
#                 try:
#                     with open(screenshot_path, "rb") as f:
#                         testrail_post(
#                             f"add_attachment_to_result/{result_id}",
#                             files={"attachment": f},
#                         )
#                 except Exception as e:
#                     print(f"[WARNING] TestRail 스크린샷 업로드 실패: {e}")

#             print(f"[TestRail] case {case_id} 결과 기록 ({status_id})")

#     except Exception as e:
#         # 어떤 이유로든 pytest 자체 중단 방지
#         print(f"[ERROR] pytest_runtest_makereport 처리 중 예외 발생 (무시됨): {e}")

# @pytest.hookimpl(trylast=True)
# def pytest_sessionfinish(session, exitstatus):
#     """
#     전체 테스트 종료 후 Run 닫기
#     """
#     global testrail_run_id
#     if testrail_run_id:
#         testrail_post(f"close_run/{testrail_run_id}", {})
#         print(f"[TestRail] Run {testrail_run_id} 종료 완료")

#     screenshots_dir = "screenshots"
#     if os.path.exists(screenshots_dir):
#         shutil.rmtree(screenshots_dir)  # 폴더 통째로 삭제
#         print(f"[CLEANUP] '{screenshots_dir}' 폴더 삭제 완료")
