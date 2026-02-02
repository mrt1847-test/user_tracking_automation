"""
G마켓 홈 페이지 객체
"""
from pages.base_page import BasePage
from playwright.sync_api import Page
from utils.urls import base_url
import logging

logger = logging.getLogger(__name__)


class HomePage(BasePage):
    """G마켓 홈 페이지"""
    
    # 선택자 정의
    SEARCH_INPUT = "input[placeholder*='검색']"
    SEARCH_BUTTON = "button[type='submit']"
    LOGIN_BUTTON = "로그인"
    LOGOUT_BUTTON = "text=로그아웃"
    
    def __init__(self, page: Page):
        """
        HomePage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)
        self.base_url = base_url()
    
    def navigate(self) -> None:
        """홈 페이지로 이동"""
        logger.info("홈 페이지로 이동")
        self.goto(self.base_url)
    
    def fill_search_input(self, keyword: str) -> None:
        """
        검색어 입력
        
        Args:
            keyword: 검색할 상품명
        """
        logger.debug(f"검색어 입력: {keyword}")
        self.fill("#form__search-keyword", keyword)
    
    def click_search_button(self) -> None:
        """검색 버튼 클릭"""
        logger.debug("검색 버튼 클릭")
        
        # 부모 버튼 요소를 직접 클릭 (이미지가 아닌)
        search_button = self.page.locator("button.button__search.general-clk-spm-d")
        
        # 요소가 나타날 때까지 대기
        search_button.wait_for(state="attached", timeout=10000)
        logger.debug("검색 버튼 발견")
        
        # 요소가 화면에 보이도록 명시적으로 스크롤
        search_button.scroll_into_view_if_needed(timeout=10000)
        logger.debug("검색 버튼 스크롤 완료")
        
        # 요소가 보일 때까지 대기
        search_button.wait_for(state="visible", timeout=10000)
        logger.debug("검색 버튼 표시 확인")
        
        # 클릭 시도
        try:
            search_button.click(timeout=5000)
            logger.debug("일반 클릭 성공")
        except Exception as e:
            logger.warning(f"일반 클릭 실패, force 클릭 시도: {e}")
            search_button.click(force=True)
            logger.debug("force 클릭 완료")
        
        logger.info("검색 버튼 클릭 완료")
    
    def wait_for_search_results(self) -> None:
        """검색 결과 페이지 로드 대기"""
        logger.debug("검색 결과 로드 대기")
        self.page.wait_for_load_state("networkidle")
    
    def click_login(self) -> None:
        """로그인 버튼 클릭"""
        logger.info("로그인 버튼 클릭")
        login_button = self.page.get_by_text("로그인", exact=True)
        
        # 요소가 실제로 존재하는지 확인
        count = login_button.count()
        if count == 0:
            raise Exception("로그인 버튼을 찾을 수 없습니다")
        logger.debug(f"로그인 버튼 {count}개 발견")
        
        # 요소가 클릭 가능한 상태가 될 때까지 대기
        login_button.wait_for(state="visible", timeout=10000)
        login_button.scroll_into_view_if_needed()
        
        # 요소가 실제로 클릭 가능한지 확인
        is_visible = login_button.is_visible()
        is_enabled = login_button.is_enabled() if hasattr(login_button, 'is_enabled') else True
        logger.debug(f"로그인 버튼 상태 - visible: {is_visible}, enabled: {is_enabled}")
        
        if not is_visible:
            raise Exception("로그인 버튼이 보이지 않습니다")
        
        # 현재 URL 저장 (클릭 전)
        current_url = self.page.url
        logger.debug(f"클릭 전 URL: {current_url}")
        
        # 클릭 시도
        try:
            login_button.click(timeout=5000)
            logger.debug("일반 클릭 성공")
        except Exception as e:
            logger.warning(f"일반 클릭 실패, force 클릭 시도: {e}")
            login_button.click(force=True)
            logger.debug("force 클릭 완료")
        
        # 클릭 후 로그인 페이지로 이동했는지 확인
        try:
            # 로그인 페이지의 입력 필드가 나타날 때까지 대기
            self.page.wait_for_selector("#typeMemberInputId", timeout=5000)
            logger.info("로그인 페이지로 이동 확인됨")
        except Exception as e:
            # URL이 변경되었는지 확인
            new_url = self.page.url
            logger.warning(f"로그인 페이지 요소를 찾을 수 없음. 현재 URL: {new_url}")
            if current_url == new_url:
                raise Exception(f"로그인 버튼 클릭 후 페이지가 변경되지 않았습니다. URL: {new_url}")
        
        logger.info("로그인 버튼 클릭 완료")
    
    def is_logged_in(self) -> bool:
        """
        로그인 상태 확인
        
        Returns:
            로그인되어 있으면 True, 아니면 False
        """
        return self.is_visible("text='로그아웃'", timeout=5000)
    
    def click_logout(self) -> None:
        """로그아웃 버튼 클릭"""
        logger.info("로그아웃 버튼 클릭")
        self.click("text='로그아웃'")

    def click_cart(self) -> None:
        """장바구니 버튼 클릭"""
        logger.info("장바구니 버튼 클릭")
        self.click("[title='장바구니']")

    def click_my_page(self) -> None:
        """마이페이지 버튼 클릭"""
        logger.info("마이페이지 버튼 클릭")
        self.click("[title='나의 쇼핑정보']")

