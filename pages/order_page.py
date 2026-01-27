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
        """
        logger.debug("주문완료 페이지로 이동")
        self.page.goto(order_complete_url(cart_num), wait_until="domcontentloaded", timeout=30000)
        logger.info("주문완료 페이지 이동 완료")

    def is_order_complete_page_displayed(self):
        """
        주문완료 페이지가 표시되었는지 확인
        """
        logger.debug("주문완료 페이지 표시 확인")
        return self.is_visible("h2.text__main-title:has-text('주문완료')")
    
    def get_module_by_spmc(self, module_spmc: str) -> Locator:
        """
        특정 모듈을 spmc로 찾아 반환
        
        Args:
            module_spmc: 모듈 SPM 코드
        
        Returns:
            모듈 Locator 객체
        """
        logger.debug(f"주문완료 페이지에 모듈 찾기: {module_spmc}")
        return self.page.locator(f".module-exp-spm-c[data-spm='{module_spmc}']")