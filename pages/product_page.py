"""
상품 상세 페이지 객체
"""
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator
from utils.urls import product_url
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ProductPage(BasePage):
    """상품 상세 페이지"""

    
    def __init__(self, page: Page):
        """
        ProductPage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)
    
    def go_to_product_page(self, goodscode: str) -> None:
        """
        상품 페이지로 이동
        
        Args:
            goodscode: 상품번호
        """
        logger.info(product_url(goodscode))
        self.goto(product_url(goodscode))

    def is_product_detail_displayed(self) -> bool:
        """
        상품 상세 페이지가 표시되었는지 확인
        구매하기 버튼이나 상품 상세 페이지의 핵심 요소가 나타나는지 확인
        """
        try:
            # domcontentloaded까지는 빠르게 기다림 (필수)
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            
            # 상품 상세 페이지의 핵심 요소 확인 (구매하기 버튼)
            # 이 요소가 나타나면 상품 상세 페이지가 로드된 것으로 간주
            buy_button = self.page.locator("#coreInsOrderBtn")
            buy_button.wait_for(state="attached", timeout=15000)
            
            logger.debug("상품 상세 페이지 확인됨 (구매하기 버튼 발견)")
            return True
        except Exception as e:
            logger.warning(f"상품 상세 페이지 확인 실패: {e}")
            return False
    
    def get_product_name(self) -> str:
        """상품명 가져오기"""
        # TODO: 구현
        return self.get_text(self.PRODUCT_NAME)
    
    def contains_product_name(self, product_name: str) -> bool:
        """상품명에 특정 텍스트가 포함되어 있는지 확인"""
        # TODO: 구현
        actual_name = self.get_product_name()
        return product_name in actual_name
    
    def get_product_price(self) -> str:
        """상품 가격 가져오기"""
        # TODO: 구현
        return self.get_text(self.PRODUCT_PRICE)
    
    def is_price_displayed(self, expected_price: str) -> bool:
        """상품 가격이 올바르게 표시되는지 확인"""
        # TODO: 구현
        actual_price = self.get_product_price()
        return expected_price in actual_price
    
    def select_option(self) -> None:
        """상품 옵션 선택"""
        # TODO: 구현
        logger.info("상품 옵션 선택")
    
    def select_specific_option(self, option_name: str) -> None:
        """특정 옵션 선택"""
        # TODO: 구현
        logger.info(f"옵션 선택: {option_name}")
    
    def change_quantity(self) -> None:
        """수량 변경"""
        # TODO: 구현
        logger.info("수량 변경")
    
    def change_quantity_to(self, quantity: str) -> None:
        """수량을 특정 개수로 변경"""
        # TODO: 구현
        self.fill(self.QUANTITY_INPUT, quantity)
        logger.info(f"수량 변경: {quantity}개")
    
    def wait_for_page_load(self) -> None:
        """페이지 로드 대기"""
        logger.debug("페이지 로드 대기")
        self.page.wait_for_load_state("networkidle")
    
    def click_add_to_cart_button(self, timeout: int = 10000) -> None:
        """
        장바구니 추가 버튼 클릭
        
        Args:
            timeout: 타임아웃 (기본값: 10000ms)
        """
        logger.debug("장바구니 추가 버튼 클릭")
        self.click(self.ADD_TO_CART_BUTTON, timeout=timeout)

    def click_buy_now_button(self, timeout: int = 10000) -> None:
        """
        구매하기 버튼 클릭
        
        Args:
            timeout: 타임아웃 (기본값: 10000ms)
        """
        logger.debug("구매하기 버튼 클릭")
        # nth(0)으로 첫 번째 요소 명시적 선택
        buy_button = self.page.locator("#coreInsOrderBtn").nth(0)
        
        # 요소가 나타날 때까지 먼저 대기
        buy_button.wait_for(state="attached", timeout=timeout)
        logger.debug("구매하기 버튼이 DOM에 나타남")
        
        # 버튼이 화면에 보이도록 스크롤
        buy_button.scroll_into_view_if_needed(timeout=timeout)
        logger.debug("구매하기 버튼이 화면에 보이도록 스크롤 완료")
        
        # 버튼 클릭
        buy_button.click(timeout=timeout)
        logger.debug("구매하기 버튼 클릭 완료")

    def select_group_product(self, n: int, timeout: int = 10000) -> None:
        """
        n 번째 그룹상품 선택 
        
        Args:   
            n: 그룹상품 번호
            timeout: 타임아웃 (기본값: 10000ms)
        """
        if n < 10:
            n = f"0{n}"
        else:
            n = f"{n}"
        logger.debug("그룹 옵션레이어 클릭")
        # nth(0)으로 첫 번째 요소 명시적 선택
        group_product_layer = self.page.locator(".select-item_option").nth(0)
        
        # 요소가 나타날 때까지 먼저 대기
        group_product_layer.wait_for(state="attached", timeout=timeout)
        logger.debug("그룹 옵션레이어 DOM에 나타남")
        
        # 그룹 옵션레이어 화면에 보이도록 스크롤
        group_product_layer.scroll_into_view_if_needed(timeout=timeout)
        logger.debug("그룹 옵션레이어 화면에 보이도록 스크롤 완료")
        
        # 그룹 옵션레이어 클릭
        group_product_layer.click(timeout=timeout)
        logger.debug("그룹 옵션레이어 클릭 완료")

        #n번쨰 그룹상품 선택
        group_product = self.page.locator(f"#coreAnchor{n}")
        
        # 요소가 나타날 때까지 먼저 대기
        group_product.wait_for(state="attached", timeout=timeout)
        logger.debug("n번쨰 그룹상품 DOM에 나타남")
        
        # n번쨰 그룹상품 화면에 보이도록 스크롤
        group_product.scroll_into_view_if_needed(timeout=timeout)
        logger.debug("n번쨰 그룹상품 화면에 보이도록 스크롤 완료")
        
        # n번쨰 그룹상품 클릭
        group_product.click(timeout=timeout)

        # 선택 버튼 클릭
        self.page.get_by_text("선택", exact=True).nth(0).click()
        logger.debug("n번쨰 그룹상품 선택택 완료")

       
    # ============================================
    # 모듈 및 상품 관련 메서드 (Atomic POM)
    # ============================================
    
    def get_module_by_title(self, module_title: str) -> Locator:
        """
        모듈 타이틀로 모듈 요소 찾기
        
        Args:
            module_title: 모듈 타이틀 텍스트
            
        Returns:
            Locator 객체
        """
        logger.debug(f"모듈 찾기: {module_title}")
        return self.page.get_by_text(module_title, exact=True)
    
    def scroll_module_into_view(self, module_locator: Locator) -> None:
        """
        모듈을 뷰포트로 스크롤
        
        Args:
            module_locator: 모듈 Locator 객체
        """
        logger.debug("모듈 스크롤")
        module_locator.scroll_into_view_if_needed()
    
    def get_module_parent(self, module_locator: Locator) -> Locator:
        """
        모듈의 부모 요소 찾기
        
        Args:
            module_locator: 모듈 Locator 객체
            
        Returns:
            부모 Locator 객체
        """
        logger.debug("모듈 부모 요소 찾기")
        return module_locator.locator("xpath=../..")
    
    def get_product_in_module(self, parent_locator: Locator) -> Locator:
        """
        모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return parent_locator.locator("a")
    
    def scroll_product_into_view(self, product_locator: Locator) -> None:
        """
        상품 요소를 뷰포트로 스크롤
        
        Args:
            product_locator: 상품 Locator 객체
        """
        logger.debug("상품 요소 스크롤")
        product_locator.scroll_into_view_if_needed()

    
    def get_product_code(self, product_locator: Locator) -> Optional[str]:
        """
        상품 코드 가져오기
        
        Args:
            product_locator: 상품 Locator 객체
            
        Returns:
            상품 코드 (data-montelena-goodscode 속성 값)
        """
        logger.debug("상품 코드 가져오기")
        return product_locator.get_attribute("data-montelena-goodscode")
    
    def get_product_by_code(self, goodscode: str) -> Locator:
        """
        상품 번호로 상품 요소 찾기
        
        Args:
            goodscode: 상품 번호
            
        Returns:
            상품 Locator 객체
        """
        logger.debug(f"상품 번호로 상품 찾기: {goodscode}")
        return self.page.locator(f'a[data-montelena-goodscode="{goodscode}"]').nth(0)
    
    def wait_for_new_page(self):
        """
        새 페이지가 열릴 때까지 대기하는 컨텍스트 매니저
        
        Returns:
            새 페이지 정보를 담은 컨텍스트 매니저
        """
        logger.debug("새 페이지 대기")
        return self.page.context.expect_page()
    
    def click_product_and_wait_new_page(self, product_locator: Locator) -> Page:
        """
        상품 클릭하고 새 탭 대기 (새 탭 열림)
        
        Args:
            product_locator: 상품 Locator 객체
            
        Returns:
            새 탭의 Page 객체
        """
        logger.debug("상품 클릭 및 새 탭 대기")
        
        # 새 탭이 생성될 때까지 대기
        with self.page.context.expect_page() as new_page_info:
            product_locator.click()
        
        new_page = new_page_info.value
        logger.debug(f"새 탭 생성됨: {new_page.url}")
        
        # 새 탭을 포커스로 가져오기 (제어 가능하도록)
        new_page.bring_to_front()
        logger.debug("새 탭을 포커스로 가져옴")
        
        # 새 탭이 실제로 로드되고 제어 가능한 상태가 될 때까지 대기
        # 1. domcontentloaded: DOM이 로드되면 완료 (가장 빠름)
        try:
            new_page.wait_for_load_state("domcontentloaded", timeout=30000)
            logger.debug("새 탭 DOM 로드 완료")
        except Exception as e:
            logger.warning(f"domcontentloaded 대기 실패: {e}")
            raise
        
        # 2. URL이 실제로 변경되었는지 확인 (about:blank가 아닌지)
        max_retries = 5
        for i in range(max_retries):
            current_url = new_page.url
            if current_url and current_url != "about:blank":
                logger.debug(f"새 탭 URL 확인됨: {current_url}")
                break
            if i < max_retries - 1:
                new_page.wait_for_timeout(500)  # 0.5초 대기
            else:
                logger.warning(f"새 탭 URL이 about:blank 상태입니다: {current_url}")
        
        return new_page
    
    def verify_product_code_in_url(self, url: str, goodscode: str) -> None:
        """
        URL에 상품 번호가 포함되어 있는지 확인 (Assert)
        
        Args:
            url: 확인할 URL
            goodscode: 상품 번호
        """
        logger.debug(f"URL에 상품 번호 포함 확인: {goodscode}")
        assert goodscode in url, f"상품 번호 {goodscode}가 URL에 포함되어야 합니다"


