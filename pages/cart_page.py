import time
import logging
import json
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator, expect
from utils.urls import product_url, search_url, cart_url
from typing import Optional

logger = logging.getLogger(__name__)


class CartPage(BasePage):
    def __init__(self, page: Page):
        """
        CartPage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)

    def go_to_cart_page(self):
        """
        장바구니 페이지로 이동
        """
        logger.debug("장바구니 페이지로 이동")
        self.page.goto(cart_url(), wait_until="domcontentloaded", timeout=30000)
        logger.info("장바구니 페이지 이동 완료")
    
    def go_to_product_page(self, goodscode: str):
        """
        상품 페이지로 이동
        """
        logger.debug("장바구니 페이지로 이동")
        self.page.goto(product_url(goodscode), wait_until="domcontentloaded", timeout=30000)
        logger.info("장바구니 페이지 이동 완료")

    def click_add_cart_button(self, timeout: int = 10000) -> None:
        """
        장바구니 버튼 클릭
        
        Args:
            timeout: 타임아웃 (기본값: 10000ms)
        """
        logger.debug("장바구니 버튼 클릭")
        # nth(0)으로 첫 번째 요소 명시적 선택
        buy_button = self.page.locator("#coreAddCartBtn").nth(0)
        
        # 요소가 나타날 때까지 먼저 대기
        buy_button.wait_for(state="attached", timeout=timeout)
        logger.debug("장바구니 버튼이 DOM에 나타남")
        
        # 버튼이 화면에 보이도록 스크롤
        buy_button.scroll_into_view_if_needed(timeout=timeout)
        logger.debug("장바구니 버튼이 화면에 보이도록 스크롤 완료")
        
        # 버튼 클릭
        buy_button.click(timeout=timeout)
        logger.info("장바구니 버튼 클릭 완료")

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
        logger.info("n번쨰 그룹상품 선택택 완료")


    def wait_for_cart_page_load(self) -> None:
        """
        장바구니 페이지 로드 대기
        <h3 class="title">장바구니</h3> 요소가 보일 때까지 대기
        """
        logger.debug("장바구니 페이지 로드 대기 (h3.title '장바구니' 확인)")
        loc = self.page.locator('h3.title:has-text("장바구니")')
        loc.wait_for(state="visible", timeout=self.timeout)
        logger.info("장바구니 페이지 로드 확인됨")
        
    def select_all_and_delete(self) -> None:
        """
        전체 선택 후 선택삭제 수행.
        전체 선택 체크박스를 체크한 뒤, 선택삭제(btn_del) 버튼을 클릭하고
        확인 얼럿에서 '확인'을 눌러 선택된 상품을 삭제한다.
        """
        loc = self.page.locator("#item_all_select")
        if not loc.is_checked():
            loc.check()
            logger.debug("전체 선택 체크 완료")
        else:
            logger.debug("전체 선택 이미 체크됨")

        self.click_and_expect_dialog(selector="button.btn_del:has-text('선택삭제')")
        logger.debug("선택삭제 버튼 클릭, 확인 얼럿 수락")

    def click_go_to_cart_page(self, timeout: int = 10000) -> None:
        """
        장바구니 페이지로 이동.
        1) '장바구니로' 버튼(다중 로케이터) 클릭 시도.
        2) 실패 시 헤더의 장바구니 링크( a[title="장바구니"] / data-montelena-acode=200003389 ) 클릭.

        Args:
            timeout: 타임아웃 (기본값: 10000ms)
        """
        btn = (
            self.page.locator("button.btn_round.btn_blue")
            .or_(self.page.locator('button[data-montelena-acode="200000545"]'))
            .or_(self.page.locator('button:has-text("장바구니로")'))
        )
        link = (
            self.page.locator('a[data-montelena-acode="200003389"]')
            .or_(self.page.locator('a[title="장바구니"]'))
        )

        try:
            logger.debug("장바구니로 버튼 클릭 시도")
            btn.wait_for(state="attached", timeout=timeout)
            btn.scroll_into_view_if_needed(timeout=timeout)
            btn.click(timeout=timeout)
        except Exception as e:
            logger.debug("장바구니로 버튼 클릭 실패, 헤더 장바구니 링크로 대체: %s", e)
            link.wait_for(state="attached", timeout=timeout)
            link.scroll_into_view_if_needed(timeout=timeout)
            link.click(timeout=timeout)

        logger.info("장바구니 페이지로 이동 완료")

    def check_module_in_cart(self, module_title: str, timeout: Optional[int] = None) -> Locator:
        """
        장바구니 페이지에 모듈이 있는지 확인하고 나타날 때까지 대기
        
        Args:
            module_title: 모듈 타이틀
            timeout: 타임아웃 (기본값: self.timeout)
        
        Returns:
            모듈 Locator 객체
        """
        timeout = timeout or self.timeout
        logger.debug(f"모듈 찾기: {module_title} (timeout: {timeout}ms)")
        
        if module_title == "장바구니 최저가":
            locator = self.page.locator(".text__title strong", has_text="최저가")
        else:
            locator = self.page.locator(".text__title", has_text=module_title)
        
        # 모듈이 나타날 때까지 대기
        logger.debug(f"모듈 노출 대기 중: {module_title}")
        locator.wait_for(state="visible", timeout=timeout)
        logger.info(f"모듈 노출 확인됨: {module_title}")
        
        return locator

    def check_ad_item_in_module(self, modulel_title: str) -> str:
        """
        모듈 내 광고상품 노출 확인
        
        Args:
            modulel_title: 모듈 타이틀
        
        Returns:
            "Y", "N", 또는 "F" (광고 상품 여부)
        
        Raises:
            ValueError: 알 수 없는 모듈 타이틀인 경우
        """
        logger.debug(f"모듈 내 광고상품 노출 확인: {modulel_title}")

        MODULE_AD_CHECK = {
            "장바구니 최저가": "N",
        }
        
        if modulel_title not in MODULE_AD_CHECK:
            raise ValueError(f"모듈 타이틀 {modulel_title} 확인 불가")
        
        return MODULE_AD_CHECK[modulel_title]

    def get_product_in_module(self, module_locator: Locator) -> Locator:
        """
        모듈 내 상품 요소 찾기
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return module_locator.locator("a").first

    def check_ad_tag_in_product(self, product_locator: Locator) -> str:
        """
        상품 내 광고 태그 노출 확인
        """
        logger.debug(f"상품 내 광고 태그 노출 확인: {product_locator}")
        
        try:
            # 상품 요소의 조상 요소에서 div.box__ads-layer 찾기
            item_container = product_locator.locator("")
            ads_layer = item_container.locator("")
            
            if ads_layer.count() > 0:
                logger.debug("광고 태그 발견: Y")
                return "Y"
            else:
                logger.debug("광고 태그 없음: N")
                return "N"
        except Exception as e:
            logger.warning(f"광고 태그 확인 중 오류 발생: {e}")
            return "N"

    def click_product_and_wait_pdp_pv(self, product_locator: Locator) -> None:
        """
        상품 클릭
        """
        logger.debug(f"상품 클릭: {product_locator}")
        product_locator.click()
        logger.info("상품 클릭 완료")

    def click_cart_button_in_module(self, goodscode: str) -> None:
        """
        모듈 내 장바구니 버튼 클릭
        """
        logger.debug(f"모듈 내 장바구니 버튼 클릭: {goodscode}")
        self.page.locator(f'.button__cart[data-montelena-goodscode="{goodscode}"]').nth(0).click()
        logger.info("모듈 내 장바구니 버튼 클릭 완료")

    def check_cart_added(self, goodscode: str, timeout: int = 10000) -> None:
        """
        장바구니 담기 완료 확인
        해당 goodscode의 장바구니 버튼이 보이지 않으면 장바구니 담기가 완료된 것으로 확인
        
        Args:
            goodscode: 상품 번호
            timeout: 타임아웃 (기본값: 10000ms)
        
        Raises:
            AssertionError: 장바구니 버튼이 여전히 보이는 경우 (담기 미완료)
        """
        logger.debug(f"장바구니 담기 완료 확인: {goodscode}")
        button_locator = self.page.locator(f'.button__cart[data-montelena-goodscode="{goodscode}"]')
        
        # 버튼이 존재하지 않으면 성공
        if button_locator.count() == 0:
            logger.info(f"장바구니 담기 완료 확인됨: {goodscode} (버튼 없음)")
            # ATC 이벤트 수집을 위한 대기 시간
            time.sleep(1.5)
            return
        
        # 버튼이 보이지 않을 때까지 대기 (또는 이미 숨겨져 있으면 성공)
        try:
            button_locator.first.wait_for(state="hidden", timeout=timeout)
            logger.info(f"장바구니 담기 완료 확인됨: {goodscode} (버튼 숨김)")
            # ATC 이벤트 수집을 위한 대기 시간
            time.sleep(1.5)
        except Exception:
            # 타임아웃 후에도 버튼이 보이면 실패
            if button_locator.first.is_visible():
                raise AssertionError(f"장바구니 버튼이 여전히 보입니다: {goodscode}")
            # 보이지 않으면 성공
            logger.info(f"장바구니 담기 완료 확인됨: {goodscode}")
            # ATC 이벤트 수집을 위한 대기 시간
            time.sleep(1.5)