"""
상품 상세 페이지 객체
"""
from pages.base_page import BasePage
from playwright.sync_api import Page
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
