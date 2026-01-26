"""
Base Page Object 클래스
모든 Page Object의 기본이 되는 클래스
"""
from playwright.sync_api import Page, Locator
from typing import Optional
from urllib.parse import unquote, parse_qs, urlparse
import logging
import time

logger = logging.getLogger(__name__)


class BasePage:
    """모든 Page Object의 기본 클래스"""
    
    def __init__(self, page: Page):
        """
        BasePage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        self.page = page
        self.timeout = 30000  # 기본 타임아웃 30초
    
    def goto(self, url: str) -> None:
        """
        페이지로 이동
        
        Args:
            url: 이동할 URL
        """
        logger.info(f"페이지 이동: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
    
    def click(self, selector: str, timeout: Optional[int] = None) -> None:
        """
        요소 클릭 (Locator 방식)
        
        Args:
            selector: CSS 선택자 또는 XPath
            timeout: 타임아웃 (기본값: self.timeout)
        """
        timeout = timeout or self.timeout
        logger.debug(f"클릭: {selector}")
        self.page.locator(selector).click(timeout=timeout)
    
    def fill(self, selector: str, value: str, timeout: Optional[int] = None) -> None:
        """
        입력 필드에 값 입력 (Locator 방식)
        
        Args:
            selector: CSS 선택자 또는 XPath
            value: 입력할 값
            timeout: 타임아웃 (기본값: self.timeout)
        """
        timeout = timeout or self.timeout
        logger.debug(f"입력: {selector} = {value}")
        self.page.locator(selector).fill(value, timeout=timeout)
    
    def get_text(self, selector: str, timeout: Optional[int] = None) -> str:
        """
        요소의 텍스트 가져오기
        
        Args:
            selector: CSS 선택자 또는 XPath
            timeout: 타임아웃 (기본값: self.timeout)
            
        Returns:
            요소의 텍스트
        """
        timeout = timeout or self.timeout
        logger.debug(f"텍스트 가져오기: {selector}")
        return self.page.locator(selector).inner_text(timeout=timeout)
    
    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Locator:
        """
        요소가 나타날 때까지 대기
        
        Args:
            selector: CSS 선택자 또는 XPath
            timeout: 타임아웃 (기본값: self.timeout)
            
        Returns:
            Locator 객체
        """
        timeout = timeout or self.timeout
        logger.debug(f"요소 대기: {selector}")
        return self.page.wait_for_selector(selector, timeout=timeout)
    
    def wait_for_url(self, url_pattern: str, timeout: Optional[int] = None) -> None:
        """
        URL이 변경될 때까지 대기
        
        Args:
            url_pattern: URL 패턴 (정규식 또는 문자열)
            timeout: 타임아웃 (기본값: self.timeout)
        """
        timeout = timeout or self.timeout
        logger.debug(f"URL 대기: {url_pattern}")
        self.page.wait_for_url(url_pattern, timeout=timeout)
    
    def is_visible(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        요소가 보이는지 확인
        
        Args:
            selector: CSS 선택자 또는 XPath
            timeout: 타임아웃 (기본값: self.timeout)
            
        Returns:
            요소가 보이면 True, 아니면 False
        """
        timeout = timeout or self.timeout
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False
    
    def screenshot(self, path: str) -> None:
        """
        스크린샷 저장
        
        Args:
            path: 저장할 경로
        """
        logger.info(f"스크린샷 저장: {path}")
        self.page.screenshot(path=path)
    
    def get_title(self) -> str:
        """
        페이지 제목 가져오기
        
        Returns:
            페이지 제목
        """
        return self.page.title()
    
    def get_url(self) -> str:
        """
        현재 URL 가져오기
        
        Returns:
            현재 URL
        """
        return self.page.url
    
    # ============================================
    # Playwright 역할 기반 및 고급 로케이터 메서드
    # ============================================
    
    def get_by_role(self, role: str, name: str = None, **kwargs) -> Locator:
        """
        역할 기반 로케이터 (가장 권장되는 방법)
        
        Args:
            role: ARIA 역할 (예: "button", "textbox", "link", "heading" 등)
            name: 접근 가능한 이름 (선택사항)
            **kwargs: 추가 옵션 (checked, disabled, exact 등)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_role("button", name="검색").click()
            self.get_by_role("textbox", name="이름").fill("홍길동")
        """
        logger.debug(f"역할 기반 로케이터: role={role}, name={name}")
        return self.page.get_by_role(role, name=name, **kwargs)
    
    def get_by_text(self, text: str, exact: bool = False) -> Locator:
        """
        텍스트 기반 로케이터
        
        Args:
            text: 찾을 텍스트
            exact: 정확히 일치해야 하는지 (기본값: False)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_text("로그인").click()
            self.get_by_text("저장하기", exact=True).click()
        """
        logger.debug(f"텍스트 기반 로케이터: text={text}, exact={exact}")
        return self.page.get_by_text(text, exact=exact)
    
    def get_by_label(self, text: str, exact: bool = False) -> Locator:
        """
        라벨 기반 로케이터
        
        Args:
            text: 라벨 텍스트
            exact: 정확히 일치해야 하는지 (기본값: False)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_label("이메일").fill("test@example.com")
        """
        logger.debug(f"라벨 기반 로케이터: text={text}, exact={exact}")
        return self.page.get_by_label(text, exact=exact)
    
    def get_by_placeholder(self, text: str, exact: bool = False) -> Locator:
        """
        Placeholder 기반 로케이터
        
        Args:
            text: Placeholder 텍스트
            exact: 정확히 일치해야 하는지 (기본값: False)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_placeholder("검색어를 입력하세요").fill("노트북")
        """
        logger.debug(f"Placeholder 기반 로케이터: text={text}, exact={exact}")
        return self.page.get_by_placeholder(text, exact=exact)
    
    def get_by_alt_text(self, text: str, exact: bool = False) -> Locator:
        """
        Alt 텍스트 기반 로케이터 (이미지용)
        
        Args:
            text: Alt 텍스트
            exact: 정확히 일치해야 하는지 (기본값: False)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_alt_text("로고").click()
        """
        logger.debug(f"Alt 텍스트 기반 로케이터: text={text}, exact={exact}")
        return self.page.get_by_alt_text(text, exact=exact)
    
    def get_by_title(self, text: str, exact: bool = False) -> Locator:
        """
        Title 속성 기반 로케이터
        
        Args:
            text: Title 텍스트
            exact: 정확히 일치해야 하는지 (기본값: False)
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_title("도움말").click()
        """
        logger.debug(f"Title 기반 로케이터: text={text}, exact={exact}")
        return self.page.get_by_title(text, exact=exact)
    
    def get_by_test_id(self, test_id: str) -> Locator:
        """
        Test ID 기반 로케이터 (data-testid 속성)
        
        Args:
            test_id: Test ID 값
        
        Returns:
            Locator 객체
        
        Example:
            self.get_by_test_id("search-button").click()
        """
        logger.debug(f"Test ID 기반 로케이터: test_id={test_id}")
        return self.page.get_by_test_id(test_id)
    
    def locator(self, selector: str) -> Locator:
        """
        범용 로케이터 (CSS 선택자, XPath 등)
        
        Args:
            selector: 선택자 (CSS, XPath 등)
        
        Returns:
            Locator 객체
        
        Example:
            self.locator("button.submit").click()
            self.locator("//div[@class='item']").first.click()
        """
        logger.debug(f"범용 로케이터: selector={selector}")
        return self.page.locator(selector)
    
    def get_by_role_and_click(self, role: str, name: str = None, timeout: Optional[int] = None, **kwargs) -> None:
        """
        역할 기반 로케이터로 요소 찾아서 클릭
        
        Args:
            role: ARIA 역할
            name: 접근 가능한 이름
            timeout: 타임아웃 (기본값: self.timeout)
            **kwargs: 추가 옵션
        """
        timeout = timeout or self.timeout
        logger.debug(f"역할 기반 클릭: role={role}, name={name}")
        self.get_by_role(role, name=name, **kwargs).click(timeout=timeout)
    
    def get_by_role_and_fill(self, role: str, value: str, name: str = None, timeout: Optional[int] = None, **kwargs) -> None:
        """
        역할 기반 로케이터로 입력 필드 찾아서 값 입력
        
        Args:
            role: ARIA 역할 (보통 "textbox")
            value: 입력할 값
            name: 접근 가능한 이름
            timeout: 타임아웃 (기본값: self.timeout)
            **kwargs: 추가 옵션
        """
        timeout = timeout or self.timeout
        logger.debug(f"역할 기반 입력: role={role}, name={name}, value={value}")
        self.get_by_role(role, name=name, **kwargs).fill(value, timeout=timeout)
    
    def get_by_text_and_click(self, text: str, exact: bool = False, timeout: Optional[int] = None) -> None:
        """
        텍스트 기반 로케이터로 요소 찾아서 클릭
        
        Args:
            text: 텍스트
            exact: 정확히 일치해야 하는지
            timeout: 타임아웃 (기본값: self.timeout)
        """
        timeout = timeout or self.timeout
        logger.debug(f"텍스트 기반 클릭: text={text}")
        self.get_by_text(text, exact=exact).click(timeout=timeout)
    
    def click_and_expect_dialog(self, selector: str = None, locator: Locator = None, timeout: Optional[int] = None) -> None:
        """
        요소를 클릭하고 얼럿이 나타나는 것을 기대하며 수락 (expect_event 방식)
        
        Args:
            selector: 클릭할 요소의 선택자 (selector 또는 locator 중 하나 필수)
            locator: 클릭할 Locator 객체 (selector 또는 locator 중 하나 필수)
            timeout: 타임아웃 (기본값: self.timeout)
            
        Raises:
            ValueError: selector와 locator 둘 다 제공되지 않은 경우
            TimeoutError: 얼럿이 나타나지 않은 경우
        """
        if selector is None and locator is None:
            raise ValueError("selector 또는 locator 중 하나를 제공해야 합니다.")
        
        timeout = timeout or self.timeout
        logger.debug(f"얼럿을 기대하며 클릭")
        
        with self.page.expect_event("dialog", timeout=timeout) as dialog_info:
            if locator:
                locator.click(timeout=timeout)
            else:
                self.click(selector, timeout=timeout)
        
        dialog = dialog_info.value
        dialog.accept()
        logger.debug(f"얼럿 수락 완료: {dialog.message}")
    
    # ============================================
    # URL 파싱 헬퍼 메서드
    # ============================================
    
    def parse_url(self, url: str):
        """
        URL을 파싱하여 ParseResult 객체 반환
        
        Args:
            url: 파싱할 URL
            
        Returns:
            ParseResult 객체
        """
        return urlparse(url)
    
    def parse_query_params(self, url: str):
        """
        URL의 쿼리 파라미터를 파싱하여 딕셔너리로 반환
        
        Args:
            url: 파싱할 URL
            
        Returns:
            쿼리 파라미터 딕셔너리
        """
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)
    
    def decode_url(self, encoded_url: str) -> str:
        """
        URL 인코딩된 문자열을 디코딩
        
        Args:
            encoded_url: 인코딩된 URL 문자열
            
        Returns:
            디코딩된 문자열
        """
        return unquote(encoded_url)
    
    # ============================================
    # 네트워크 트래킹 관련 헬퍼 메서드
    # ============================================
    
    @staticmethod
    def wait_until_pdp_pv_collected(tracker, goodscode: str, page: Page, timeout_ms: int = 15000, poll_interval: float = 0.3) -> None:
        """
        PDP PV 로그 수집이 확인될 때까지 폴링
        해당 goodscode에 대한 PDP PV 로그 수신 시 logger.info 출력 후 종료
        
        Args:
            tracker: NetworkTracker 인스턴스
            goodscode: 상품 코드
            page: Playwright Page 객체
            timeout_ms: 타임아웃 (밀리초, 기본값: 15000)
            poll_interval: 폴링 간격 (초, 기본값: 0.3)
        """
        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        deadline = time.time() + (timeout_ms / 1000.0)
        while time.time() < deadline:
            logs = tracker.get_pdp_pv_logs_by_goodscode(goodscode)
            if logs:
                logger.info(f"PDP PV 수집 확인됨: goodscode={goodscode}")
                return
            time.sleep(poll_interval)
        logger.warning(f"PDP PV 수집 대기 타임아웃 ({timeout_ms}ms): goodscode={goodscode}")
        time.sleep(2)

