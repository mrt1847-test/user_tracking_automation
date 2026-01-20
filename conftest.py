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
import re
from src.gtas_python_core_v2.gtas_python_core_vault_v2 import Vault
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
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


# TestRail 연동을 위한 전역 변수
testrail_run_id = None


# ============================================
# TestRail 헬퍼 함수들
# ============================================

def _get_page_from_request(request, step_func_args=None):
    """
    request나 step_func_args에서 page 객체 찾기
    
    Args:
        request: pytest request 객체
        step_func_args: 스텝 함수 인자 딕셔너리
    
    Returns:
        Page 객체 또는 None
    """
    page = None
    
    # request에서 찾기
    if hasattr(request, 'fixturenames'):
        try:
            if "browser_session" in request.fixturenames:
                browser_session = request.getfixturevalue("browser_session")
                if browser_session and hasattr(browser_session, 'page'):
                    page = browser_session.page
        except Exception:
            pass
        
        if not page:
            try:
                if "page" in request.fixturenames:
                    page = request.getfixturevalue("page")
            except Exception:
                pass
    
    # step_func_args에서 찾기
    if not page and step_func_args:
        if "browser_session" in step_func_args:
            browser_session = step_func_args.get("browser_session")
            if browser_session and hasattr(browser_session, 'page'):
                page = browser_session.page
        elif "page" in step_func_args:
            page = step_func_args.get("page")
    
    return page


def _capture_screenshot(case_id_num, request=None, step_func_args=None):
    """
    스크린샷 캡처 및 저장
    
    Args:
        case_id_num: TestRail 케이스 ID 번호 또는 파일명 식별자
        request: pytest request 객체
        step_func_args: 스텝 함수 인자 딕셔너리
    
    Returns:
        스크린샷 파일 경로 또는 None
    """
    try:
        page = _get_page_from_request(request, step_func_args)
        
        if page and not page.is_closed():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # case_id_num이 숫자면 TestRail 케이스 ID, 아니면 일반 파일명
            if isinstance(case_id_num, (int, str)) and str(case_id_num).isdigit():
                screenshot_path = f"screenshots/{case_id_num}_{timestamp}.png"
            else:
                screenshot_path = f"screenshots/{case_id_num}_{timestamp}.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            page.screenshot(path=screenshot_path, timeout=2000)
            print(f"[TestRail] 스크린샷 저장 완료: {screenshot_path}")
            return screenshot_path
    except Exception as e:
        print(f"[WARNING] 스크린샷 저장 실패: {e}")
    
    return None


# 프론트 실패 처리 헬퍼 함수는 utils.frontend_helpers에서 import
from utils.frontend_helpers import capture_frontend_failure_screenshot


def _collect_step_logs():
    """
    현재 스텝의 로그 수집
    
    Returns:
        로그 문자열 또는 None
    """
    try:
        logs = test_log_handler.get_logs()
        if logs and logs.strip():
            return logs
    except Exception as e:
        print(f"[WARNING] 로그 수집 실패: {e}")
    
    return None


def _attach_screenshot_to_testrail(result_id, screenshot_path):
    """
    TestRail 결과에 스크린샷 첨부
    
    Args:
        result_id: TestRail 결과 ID
        screenshot_path: 스크린샷 파일 경로
    """
    if not screenshot_path or not result_id:
        return
    
    try:
        with open(screenshot_path, "rb") as f:
            testrail_post(
                f"add_attachment_to_result/{result_id}",
                files={"attachment": f},
            )
        print(f"[TestRail] 스크린샷 첨부 완료: {screenshot_path}")
    except Exception as e:
        print(f"[WARNING] TestRail 스크린샷 업로드 실패: {e}")


@pytest.hookimpl(hookwrapper=True)
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    """
    각 스텝 실행 후 TestRail에 기록
    스텝 파라미터에서 TC 번호를 추출하여 TestRail에 기록
    로그와 스크린샷 첨부 기능 포함
    """
    outcome = yield
    
    try:
        # 디버깅: testrail_run_id 확인
        print(f"[DEBUG] pytest_bdd_after_step 실행: 스텝='{step.name}', testrail_run_id={testrail_run_id}")
        
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
                    # 검증 스텝인지 확인 (스텝 이름에 "정합성 검증" 포함)
                    is_validation_step = "정합성 검증" in step.name
                    
                    if is_validation_step:
                        # 검증 스텝: validation_failed만 확인 (프론트 실패 정보는 이미 error_message에 포함됨)
                        if bdd_context.get('validation_failed'):
                            step_status = "failed"
                            error_msg = bdd_context.get('validation_error_message', '검증 실패')
                    else:
                        # 프론트 동작 스텝: frontend_action_failed 확인
                        if bdd_context.get('frontend_action_failed'):
                            step_status = "failed"
                            if error_msg is None:
                                error_msg = bdd_context.get('frontend_error_message', '프론트 동작 실패')
        
        # TC 번호 추출 시도
        step_case_id = None
        
        # 디버깅: step_func_args 내용 확인
        if step_func_args:
            print(f"[DEBUG] step_func_args 키: {list(step_func_args.keys())}")
            # TC 번호 후보 값들 확인 (모든 값 출력)
            for arg_name, arg_value in step_func_args.items():
                if arg_name != 'bdd_context':  # bdd_context는 너무 클 수 있으므로 제외
                    print(f"[DEBUG] step_func_args[{arg_name}] = {arg_value} (타입: {type(arg_value).__name__})")
        
        # 1. step_func_args에서 TC 번호 파라미터 찾기 (tc_id, tc_module_exposure, tc_product_exposure 등)
        if step_func_args:
            for arg_name, arg_value in step_func_args.items():
                # TC 번호 형식 확인 (C로 시작하는 문자열)
                if isinstance(arg_value, str):
                    arg_value_stripped = arg_value.strip()
                    # C로 시작하고 뒤에 숫자가 오는 경우
                    if arg_value_stripped.startswith("C") and len(arg_value_stripped) > 1:
                        try:
                            # C 뒤의 부분이 숫자인지 확인
                            if arg_value_stripped[1:].isdigit():
                                step_case_id = arg_value_stripped
                                print(f"[DEBUG] step_func_args에서 TC 번호 발견: {arg_name}={step_case_id}")
                                break
                        except (ValueError, IndexError):
                            pass
        
        # 2. step_func_args에서 bdd_context를 통해 TC 번호 찾기
        if step_case_id is None and step_func_args:
            bdd_context = step_func_args.get('bdd_context')
            if bdd_context:
                print(f"[DEBUG] bdd_context 타입: {type(bdd_context).__name__}, hasattr('get'): {hasattr(bdd_context, 'get')}")
                if hasattr(bdd_context, 'get'):
                    step_case_id = bdd_context.get('testrail_tc_id')
                    if step_case_id:
                        print(f"[DEBUG] bdd_context.get('testrail_tc_id')에서 TC 번호 발견: {step_case_id}")
                elif hasattr(bdd_context, 'store'):
                    step_case_id = bdd_context.store.get('testrail_tc_id')
                    if step_case_id:
                        print(f"[DEBUG] bdd_context.store.get('testrail_tc_id')에서 TC 번호 발견: {step_case_id}")
                
                # 디버깅: bdd_context에 저장된 모든 testrail 관련 키 확인
                if hasattr(bdd_context, 'get'):
                    testrail_keys = [k for k in dir(bdd_context) if 'testrail' in k.lower() or 'tc' in k.lower()]
                    if testrail_keys:
                        print(f"[DEBUG] bdd_context의 testrail 관련 키: {testrail_keys}")
                        for key in ['testrail_tc_id', 'tc_id']:
                            if hasattr(bdd_context, 'get'):
                                value = bdd_context.get(key)
                                if value:
                                    print(f"[DEBUG] bdd_context.get('{key}') = {value}")
        
        print(f"[DEBUG] 추출된 TC 번호: {step_case_id}, testrail_run_id: {testrail_run_id}, step_status: {step_status}")
        
        # TestRail 기록 (testrail_run_id가 설정되어 있고 TC 번호가 있을 때만)
        if step_case_id and testrail_run_id:
            print(f"[DEBUG] TestRail 기록 시작: case_id={step_case_id}, status={step_status}")
            # Cxxxx → 숫자만 추출
            case_id_num = int(step_case_id[1:]) if step_case_id.startswith("C") else int(step_case_id)
            
            # skip_reason 확인
            skip_reason = None
            if step_func_args:
                bdd_context = step_func_args.get('bdd_context')
                if bdd_context:
                    if hasattr(bdd_context, 'get'):
                        skip_reason = bdd_context.get('skip_reason')
                    elif hasattr(bdd_context, 'store'):
                        skip_reason = bdd_context.store.get('skip_reason')
            
            # 상태 결정: skip_reason이 있으면 skip (4), 실패면 failed (5), 아니면 passed (1)
            if skip_reason:
                status_id = 4  # TestRail skip/retest 상태
                step_status = "skipped"
            elif step_status == "failed":
                status_id = 5
            else:
                status_id = 1
            
            comment = f"스텝: {step.name}\n"
            if skip_reason:
                comment += f"Skip: {skip_reason}\n"
            if error_msg:
                comment += f"오류: {error_msg}"
            
            # 로그 수집
            log_content = _collect_step_logs()
            if log_content:
                comment += f"\n\n--- 실행 로그 ---\n{log_content}"
            
            # 스크린샷 경로 확인 (프론트 실패 시점에 찍은 스크린샷 우선 사용)
            screenshot_path = None
            if step_status == "failed":
                # 검증 스텝인지 확인
                is_validation_step = "정합성 검증" in step.name
                
                if is_validation_step:
                    # 검증 스텝: 프론트 실패로 인한 로그 수집 실패인 경우 프론트 실패 스크린샷 사용
                    if step_func_args:
                        bdd_context = step_func_args.get('bdd_context')
                        if bdd_context:
                            # 프론트 실패가 있고 error_message에 "프론트 실패 사유"가 포함되어 있으면 스크린샷 사용
                            if hasattr(bdd_context, 'get'):
                                if bdd_context.get('frontend_action_failed') and error_msg and "[프론트 실패 사유]" in error_msg:
                                    screenshot_path = bdd_context.get('frontend_failure_screenshot')
                            elif hasattr(bdd_context, 'store'):
                                if bdd_context.store.get('frontend_action_failed') and error_msg and "[프론트 실패 사유]" in error_msg:
                                    screenshot_path = bdd_context.store.get('frontend_failure_screenshot')
                    
                    # 스크린샷이 없으면 검증 실패 스크린샷 찍기
                    if not screenshot_path:
                        screenshot_path = _capture_screenshot(case_id_num, request, step_func_args)
                else:
                    # 프론트 동작 스텝: 프론트 실패 스크린샷 확인
                    if step_func_args:
                        bdd_context = step_func_args.get('bdd_context')
                        if bdd_context:
                            if hasattr(bdd_context, 'get'):
                                screenshot_path = bdd_context.get('frontend_failure_screenshot')
                            elif hasattr(bdd_context, 'store'):
                                screenshot_path = bdd_context.store.get('frontend_failure_screenshot')
                    
                    # 저장된 스크린샷이 없으면 새로 찍기
                    if not screenshot_path:
                        screenshot_path = _capture_screenshot(case_id_num, request, step_func_args)
            
            payload = {
                "status_id": status_id,
                "comment": comment,
            }
            
            result_id = None
            try:
                print(f"[DEBUG] TestRail API 호출: add_result_for_case/{testrail_run_id}/{case_id_num}")
                result_obj = testrail_post(
                    f"add_result_for_case/{testrail_run_id}/{case_id_num}", 
                    payload
                )
                result_id = result_obj.get("id")
                print(f"[TestRail] 스텝 '{step.name}' 결과 기록 완료 (case_id: {step_case_id}, status: {step_status}, result_id: {result_id})")
            except Exception as e:
                print(f"[WARNING] 스텝 TestRail 기록 실패: {e}")
                import traceback
                print(f"[DEBUG] TestRail 기록 실패 상세:\n{traceback.format_exc()}")
            
            # 스크린샷 첨부
            _attach_screenshot_to_testrail(result_id, screenshot_path)
            
        elif step_case_id:
            # TC 번호는 있지만 testrail_run_id가 없는 경우 (TestRail 연동 미활성화)
            print(f"[DEBUG] TC 번호는 있지만 testrail_run_id가 None입니다. step_case_id={step_case_id}, testrail_run_id={testrail_run_id}")
            print(f"[TestRail] 스텝 '{step.name}' TC 번호 발견: {step_case_id} (TestRail 연동 미활성화)")
        elif not step_case_id:
            # TC 번호가 없는 경우
            print(f"[DEBUG] TC 번호를 찾을 수 없습니다. step_func_args={step_func_args is not None}, step_status={step_status}")
        
        # TC 번호가 없지만 실패한 프론트 동작 스텝인 경우 - 스크린샷만 저장 (참고용)
        if step_status == "failed" and not step_case_id:
            # 프론트 동작 실패인 경우 로그만 남기고 스크린샷 저장
            print(f"[TestRail] 스텝 '{step.name}' 실패 (TC 번호 없음): {error_msg}")
            # 프론트 실패 시점에 찍은 스크린샷 확인
            screenshot_path = None
            if step_func_args:
                bdd_context = step_func_args.get('bdd_context')
                if bdd_context:
                    if hasattr(bdd_context, 'get'):
                        screenshot_path = bdd_context.get('frontend_failure_screenshot')
                    elif hasattr(bdd_context, 'store'):
                        screenshot_path = bdd_context.store.get('frontend_failure_screenshot')
            
            # 저장된 스크린샷이 없으면 새로 찍기
            if not screenshot_path:
                screenshot_path = _capture_screenshot(f"frontend_fail_{step.name.replace(' ', '_')}", request, step_func_args)
            
            if screenshot_path:
                logger.info(f"프론트 동작 실패 스크린샷 저장: {screenshot_path}")
    
    except Exception as e:
        print(f"[ERROR] pytest_bdd_after_step 처리 중 예외 발생: {e}")


# JSON 파일이 들어 있는 폴더 지정
JSON_DIR = Path(__file__).parent / "json"  # json 폴더 내의 JSON 파일 전부 대상


# Config 파일 로딩
config = {}
try:
    with open('config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    raise RuntimeError("config.json 파일을 찾을 수 없습니다.")
except json.JSONDecodeError as e:
    raise RuntimeError(f"config.json 파일의 JSON 형식이 잘못되었습니다: {e}")

# 환경변수 기반 설정
try:
    TESTRAIL_BASE_URL = config['tr_url']
    TESTRAIL_PROJECT_ID = config['project_id']
    TESTRAIL_SUITE_ID = config['suite_id']
    TESTRAIL_SECTION_ID = config['section_id']
    TESTRAIL_MILESTONE_ID = config['milestone_id']
except KeyError as e:
    raise RuntimeError(f"config.json에 필수 키 '{e}'가 없습니다.")

try:
    if Vault is None:
        raise RuntimeError("Vault 모듈을 import할 수 없습니다.")
    vault_credentials = Vault("gmarket").get_Kv_credential("authentication/testrail/automation")
    TESTRAIL_USER = vault_credentials.get("username")
    TESTRAIL_TOKEN = vault_credentials.get("password")
    if not TESTRAIL_USER or not TESTRAIL_TOKEN:
        raise RuntimeError("TestRail 인증 정보(username 또는 password)가 없습니다.")
except Exception as e:
    raise RuntimeError(f"TestRail 인증 정보를 가져오는 중 오류 발생: {e}")
testrail_run_id = None
case_id_map = {}  # {섹션 이름: [케이스ID 리스트]}
test_logs = {}  # {nodeid: 로그 문자열} - 테스트별 로그 저장
current_test_nodeid = None  # 현재 실행 중인 테스트의 nodeid


def testrail_get(endpoint):
    url = f"{TESTRAIL_BASE_URL}/index.php?/api/v2/{endpoint}"
    r = requests.get(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN))
    r.raise_for_status()
    return r.json()


def testrail_post(endpoint, payload=None, files=None):
    url = f"{TESTRAIL_BASE_URL}/index.php?/api/v2/{endpoint}"
    if files:
        r = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN), files=files)
    else:
        r = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_TOKEN), json=payload)
    r.raise_for_status()
    return r.json()




def get_all_subsection_ids(parent_section_id, all_sections, visited=None):
    """
    지정된 섹션 ID와 모든 하위 섹션 ID를 재귀적으로 찾기
    
    Args:
        parent_section_id: 부모 섹션 ID (int 또는 str)
        all_sections: 모든 섹션 리스트 (TestRail API에서 가져온 전체 섹션)
        visited: 이미 방문한 섹션 ID 집합 (순환 참조 방지)
    
    Returns:
        list: 부모 섹션 ID와 모든 하위 섹션 ID 리스트 (중복 제거됨)
    """
    if visited is None:
        visited = set()
    
    # 타입 통일 (정수로 변환)
    if isinstance(parent_section_id, str):
        try:
            parent_section_id = int(parent_section_id)
        except ValueError:
            print(f"[WARNING] parent_section_id를 정수로 변환 실패: {parent_section_id}")
            return [parent_section_id] if parent_section_id not in visited else []
    
    # 이미 방문한 섹션이면 빈 리스트 반환 (순환 참조 및 중복 방지)
    if parent_section_id in visited:
        return []
    
    visited.add(parent_section_id)
    section_ids = [parent_section_id]
    
    # parent_id가 parent_section_id인 모든 하위 섹션 찾기
    for section in all_sections:
        section_parent_id = section.get("parent_id")
        
        # parent_id가 None이면 최상위 섹션이므로 스킵
        if section_parent_id is None:
            continue
        
        # 타입 통일 (정수로 변환)
        if isinstance(section_parent_id, str):
            try:
                section_parent_id = int(section_parent_id)
            except ValueError:
                continue
        
        # parent_id가 일치하는 경우
        if section_parent_id == parent_section_id:
            child_section_id = section["id"]
            # 타입 통일
            if isinstance(child_section_id, str):
                try:
                    child_section_id = int(child_section_id)
                except ValueError:
                    continue
            
            # 아직 방문하지 않은 자식 섹션만 추가
            if child_section_id not in visited:
                section_ids.append(child_section_id)
                # 재귀적으로 하위 섹션의 하위 섹션도 찾기
                child_subsection_ids = get_all_subsection_ids(child_section_id, all_sections, visited)
                section_ids.extend(child_subsection_ids)
    
    return section_ids


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """
    테스트 실행 시작 시:
    1. section_id 기반으로 해당 섹션과 모든 하위 섹션의 케이스 ID 가져오기
    2. 그 케이스들로 Run 생성
    """
    global testrail_run_id, case_id_map
    
    print(f"[DEBUG] pytest_sessionstart 실행 시작")
    print(f"[DEBUG] 현재 testrail_run_id 값: {testrail_run_id}")
    
    if testrail_run_id is not None:
        print(f"[TestRail] 이미 Run(ID={testrail_run_id})이 존재합니다. 새 Run 생성 생략")
        return
    
    if not TESTRAIL_SECTION_ID:
        print(f"[ERROR] TESTRAIL_SECTION_ID가 정의되지 않았습니다.")
        raise RuntimeError("[TestRail] TESTRAIL_SECTION_ID가 정의되지 않았습니다.")
    
    # TESTRAIL_SECTION_ID를 정수로 변환
    try:
        section_id_int = int(TESTRAIL_SECTION_ID)
    except (ValueError, TypeError):
        raise RuntimeError(f"[TestRail] TESTRAIL_SECTION_ID '{TESTRAIL_SECTION_ID}'를 정수로 변환할 수 없습니다.")
    
    # 1. 모든 섹션 가져오기
    print(f"[TestRail] 모든 섹션 가져오기 중...")
    all_sections = testrail_get(
        f"get_sections/{TESTRAIL_PROJECT_ID}&suite_id={TESTRAIL_SUITE_ID}"
    )
    
    # 디버깅: 섹션 구조 확인
    print(f"[TestRail] 총 {len(all_sections)}개 섹션 발견")
    print(f"[TestRail] 찾고자 하는 섹션 ID: {section_id_int} (타입: {type(section_id_int).__name__})")
    
    # 지정된 섹션이 존재하는지 확인
    section_exists = any(s.get("id") == section_id_int for s in all_sections)
    if not section_exists:
        print(f"[WARNING] 섹션 ID {section_id_int}가 존재하지 않습니다.")
        print(f"[DEBUG] 사용 가능한 섹션 ID 샘플 (최대 10개):")
        for s in all_sections[:10]:
            print(f"  - ID: {s.get('id')}, Name: {s.get('name')}, Parent ID: {s.get('parent_id')}")
    
    # 2. 지정된 섹션과 모든 하위 섹션 ID 찾기 (중복 제거)
    all_section_ids = get_all_subsection_ids(section_id_int, all_sections)
    # 중복 제거 (혹시 모를 중복 방지)
    all_section_ids = list(dict.fromkeys(all_section_ids))  # 순서 유지하면서 중복 제거
    print(f"[TestRail] 섹션 ID {section_id_int}와 하위 섹션 {len(all_section_ids) - 1}개 발견 (중복 제거됨): {all_section_ids}")
    
    # 3. 각 섹션의 케이스 가져오기 (중복 섹션 ID는 건너뛰기)
    all_case_ids = []
    processed_sections = set()  # 이미 처리한 섹션 ID 추적
    for section_id in all_section_ids:
        # 이미 처리한 섹션이면 건너뛰기
        if section_id in processed_sections:
            continue
        processed_sections.add(section_id)
        
        try:
            cases = testrail_get(
                f"get_cases/{TESTRAIL_PROJECT_ID}&suite_id={TESTRAIL_SUITE_ID}&section_id={section_id}"
            )
            section_case_ids = [c["id"] for c in cases]
            all_case_ids.extend(section_case_ids)
            case_id_map[section_id] = section_case_ids
            if section_case_ids:
                print(f"[TestRail] 섹션 {section_id}: {len(section_case_ids)}개 케이스 발견")
        except Exception as e:
            print(f"[WARNING] 섹션 {section_id}의 케이스 가져오기 실패: {e}")
    
    # 중복 제거 (같은 케이스가 여러 섹션에 있을 수 있음)
    all_case_ids = list(set(all_case_ids))
    
    if not all_case_ids:
        raise RuntimeError(f"[TestRail] section_id '{section_id_int}'와 하위 섹션에 케이스가 없습니다.")
    
    print(f"[TestRail] 총 {len(all_case_ids)}개 케이스 수집 완료")
    
    # 4. Run 생성
    run_name = f"Gmarket Regression test dweb {datetime.now():%Y-%m-%d %H:%M:%S}"
    payload = {
        "suite_id": TESTRAIL_SUITE_ID,
        "name": run_name,
        "include_all": False,
        "case_ids": all_case_ids,
        "milestone_id": TESTRAIL_MILESTONE_ID
    }
    try:
        print(f"[DEBUG] TestRail Run 생성 시도: project_id={TESTRAIL_PROJECT_ID}, case_ids 개수={len(all_case_ids)}")
        run = testrail_post(f"add_run/{TESTRAIL_PROJECT_ID}", payload)
        testrail_run_id = run["id"]
        print(f"[TestRail] section_id '{section_id_int}' (하위 섹션 포함) Run 생성 완료 (ID={testrail_run_id})")
        print(f"[DEBUG] pytest_sessionstart 완료: testrail_run_id={testrail_run_id}")
    except Exception as e:
        print(f"[ERROR] TestRail Run 생성 실패: {e}")
        import traceback
        print(f"[DEBUG] Run 생성 실패 상세:\n{traceback.format_exc()}")
        raise


# 커스텀 로그 핸들러 - 테스트 실행 중 로그를 수집
class TestLogHandler(logging.Handler):
    """테스트 실행 중 로그를 수집하는 커스텀 핸들러"""
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        """로그 레코드를 수집"""
        if record.levelno >= logging.INFO:  # INFO 이상만 수집
            log_message = self.format(record)
            self.logs.append(log_message)
    
    def clear(self):
        """로그 초기화"""
        self.logs = []
    
    def get_logs(self):
        """수집된 로그 반환"""
        return "\n".join(self.logs)

# 전역 로그 핸들러
test_log_handler = TestLogHandler()
test_log_handler.setLevel(logging.INFO)
test_log_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

# 루트 로거에 핸들러 추가
root_logger = logging.getLogger()
root_logger.addHandler(test_log_handler)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    """테스트 시작 시 로그 핸들러 초기화"""
    global current_test_nodeid
    current_test_nodeid = item.nodeid
    test_log_handler.clear()
    
    outcome = yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """테스트 종료 시 로그 핸들러 초기화 (다음 테스트와 로그 섞임 방지)"""
    outcome = yield
    # teardown 후에 초기화 (pytest_runtest_logreport와 pytest_runtest_makereport가 모두 실행된 후)
    # 다음 테스트가 있는 경우에만 초기화 (마지막 테스트는 세션 종료 시 정리)
    if nextitem:
        test_log_handler.clear()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_logreport(report):
    """
    각 테스트의 로그를 수집하여 test_logs에 저장
    pytest_runtest_makereport보다 먼저 실행되도록 tryfirst=True 설정
    """
    outcome = yield
    # setup, call, teardown 모든 단계에서 로그 수집
    if report.when == "call":  # 실행 단계만
        nodeid = report.nodeid
        if report.outcome in ("passed", "failed", "skipped"):
            # 수집된 로그 가져오기 (이 시점에 현재 테스트의 로그만 있어야 함)
            # pytest_runtest_setup과 pytest_bdd_before_scenario에서 이미 초기화했으므로
            # 현재 테스트의 로그만 있어야 함
            logs = test_log_handler.get_logs()
            if logs and logs.strip():
                # nodeid를 키로 사용하여 저장 (성공/실패 모두 저장)
                test_logs[nodeid] = logs
                # 로그 라인 수 확인
                log_lines = logs.split(chr(10))
                print(f"[DEBUG] 테스트 {nodeid} 로그 수집 완료: {len(log_lines)}줄 (outcome: {report.outcome})")
                # 로그를 test_logs에 저장했으므로 즉시 초기화 (다음 테스트와 로그 섞임 방지)
                # pytest_runtest_makereport에서 사용할 때까지는 test_logs에 보관됨
                test_log_handler.clear()
            else:
                print(f"[DEBUG] 테스트 {nodeid} 로그 없음 (빈 로그 또는 수집 실패, outcome: {report.outcome})")
                # 로그가 없어도 초기화 (이전 로그 제거)
                test_log_handler.clear()



@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """
    전체 테스트 종료 후 Run 닫기
    """
    global testrail_run_id
    if testrail_run_id:
        testrail_post(f"close_run/{testrail_run_id}", {})
        print(f"[TestRail] Run {testrail_run_id} 종료 완료")

    screenshots_dir = "screenshots"
    if os.path.exists(screenshots_dir):
        shutil.rmtree(screenshots_dir)  # 폴더 통째로 삭제
        print(f"[CLEANUP] '{screenshots_dir}' 폴더 삭제 완료")
