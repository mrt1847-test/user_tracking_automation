import time
import logging
import json
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator, expect
from utils.urls import my_url
from typing import Optional

logger = logging.getLogger(__name__)


class MyPage(BasePage):
    def __init__(self, page: Page):
        """
        MyPage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)

    def go_to_my_page_by_url(self):
        """
        마이 페이지 URL로 이동
        """
        logger.debug("마이 페이지로 이동")
        self.page.goto(my_url(), wait_until="domcontentloaded", timeout=30000)
        logger.info("v 페이지 이동 완료")

    def is_my_page_displayed(self):
        """
        마이페이지가 표시되었는지 확인
        """
        logger.debug("마이페이지 표시 확인")
        return self.is_visible(".link__mypage:has-text('나의 G마켓')")

    def click_order_history(self):
        """
        주문내역 버튼 클릭
        """
        logger.info("주문내역 버튼 클릭")
        self.page.locator(".text__menu:has-text('주문내역')").click()

    def is_order_history_page_displayed(self):
        """
        주문내역 페이지가 표시되었는지 확인
        """
        logger.debug("주문내역 페이지 표시 확인")
        return self.is_visible(".text__title:has-text('주문내역')")

    def get_goods_code_from_order_history(self):
        """
        주문내역에서 상품코드 가져오기
        """
        logger.debug("주문내역에서 상품코드 가져오기")
        goodscode = self.page.locator(".box__order-item box__thumbnail img").get_attribute("data-montelena-goodscode")
        return goodscode

    def click_atc_in_order_history_by_goodscode(self, goodscode: str):
        """
        주문내역에서 상품코드로 담기버튼 클릭
        """
        logger.debug(f"주문내역에서 상품코드로 담기버튼 클릭: {goodscode}")
        self.page.locator(f".button__cart[data-montelena-goodscode='{goodscode}']").click()

    def atc_alert_close(self):
        """
        담기 얼럿 닫기
        """
        logger.debug("담기 얼럿 닫기")
        self.page.locator(".button__close[aria-label='레이어 닫기']").click()

    def click_product_in_order_history_by_goodscode(self, goodscode: str):
        """
        주문내역에서 상품코드로 상품 클릭
        """
        logger.debug(f"주문내역에서 상품코드로 상품 클릭: {goodscode}")
        self.page.locator(f".box__order-item box__thumbnail img[data-montelena-goodscode='{goodscode}']").click()

    def get_order_history_product_locator(self, goodscode: str) -> Locator:
        """
        주문내역에서 상품코드에 해당하는 상품 Locator 반환 (ad 태그 확인 등에 사용)
        """
        return self.page.locator(
            f".box__order-item box__thumbnail img[data-montelena-goodscode='{goodscode}']"
        )

    def check_ad_item_in_order_history_module(self, module_title: str) -> str:
        """
        주문내역 등 My 페이지 모듈 내 광고상품 노출 여부 확인
        (SearchPage.check_ad_item_in_srp_lp_module과 형식 통일)

        Args:
            module_title: 모듈 타이틀 (예: "주문내역")

        Returns:
            "Y", "N", 또는 "F" (F인 경우 상품별 check_ad_tag 필요)
        """
        logger.debug(f"주문내역 모듈 내 광고상품 노출 확인: {module_title}")
        MODULE_AD_CHECK = {
            "주문내역": "N",
        }
        if module_title not in MODULE_AD_CHECK:
            raise ValueError(f"모듈 타이틀 {module_title} 확인 불가")
        return MODULE_AD_CHECK[module_title]

    def check_ad_tag_in_order_history_product(self, product_locator: Locator) -> str:
        """
        주문내역 상품 내 광고 태그 노출 확인
        (SearchPage.check_ad_tag_in_srp_lp_product와 형식 통일)

        Args:
            product_locator: 상품 Locator 객체 (주문내역 내 상품)

        Returns:
            "Y" 또는 "N"
        """
        logger.debug("주문내역 상품 내 광고 태그 노출 확인")
        try:
            # 주문내역 상품 컨테이너에서 광고 레이어 등 확인 (DOM 구조에 맞게 추후 구현)
            item_container = product_locator.locator(
                "xpath=ancestor::div[contains(@class, 'box__order-item')]"
            )
            ads_layer = item_container.locator("div.box__ads-layer")
            if ads_layer.count() > 0:
                return "Y"
            return "N"
        except Exception as e:
            logger.warning(f"주문내역 광고 태그 확인 중 오류: {e}")
            return "N"

