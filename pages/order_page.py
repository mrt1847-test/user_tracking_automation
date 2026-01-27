import time
import logging
import json
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator, expect
from utils.urls import product_url, cart_url, order_complete_url
from typing import Optional

logger = logging.getLogger(__name__)


class OrderPage(BasePage):
    def __init__(self, page: Page):
        """
        OrderPage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)

    def go_to_order_complete_page(self,cart_num):
        """
        주문완료 페이지로 이동
        
        Args:
            cart_num: 장바구니 번호
        """
        logger.debug("주문완료 페이지로 이동")
        self.page.goto(order_complete_url(cart_num), wait_until="domcontentloaded", timeout=30000)
        logger.info("주문완료 페이지 이동 완료")

    def is_order_complete_page_displayed(self):
        """
        주문완료 페이지가 표시되었는지 확인
        
        Returns:
            True: 주문완료 페이지가 표시되었음
            False: 주문완료 페이지가 표시되지 않았음
        """
        logger.debug("주문완료 페이지 표시 확인")
        return self.is_visible("h2.text__main-title:has-text('주문완료')")
    
    def get_spmc_by_module_title(self, module_title: str) -> str:
        """
        모듈 타이틀로 SPM 코드 가져오기
        
        Args:
            module_title: 모듈 타이틀
        
        Returns:
            SPM 코드
        """
        logger.debug(f"모듈 타이틀로 SPM 코드 가져오기: {module_title}")
        if module_title == "주문완료 BT":
            return "ordercompletebt"
        else:
            raise ValueError(f"모듈 타이틀 {module_title} SPM 코드 확인 불가")

    def find_option_select_button_in_module(self, module: Locator) -> Locator:
        """
        모듈 내 옵션선택 버튼 찾기
        
        Args:
            module: 모듈 Locator 객체
        
        Returns:
            옵션선택 버튼 Locator 객체
        """
        logger.debug(f"모듈 내 옵션선택 버튼 찾기: {module}")
        return module.get_by_text("옵션선택", exact=True).nth(0)

    def get_goodscode_in_product(self, product: Locator) -> str:
        """
        모듈 내 상품 코드 가져오기
        
        Args:
            product: 상품 Locator 객체
        
        Returns:
            상품 코드
        """
        logger.debug(f"모듈 내 상품 코드 가져오기")
        return product.get_attribute("data-montelena-goodscode")
    