"""
상품 상세 페이지 객체
"""
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator, TimeoutError, expect
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
        logger.debug(f'페이지 이동 시작: goodscode={goodscode}')
        self.page.goto(product_url(goodscode), wait_until="domcontentloaded")
        logger.info(f'페이지 이동 완료: goodscode={goodscode}')

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
       
    def wait_for_page_load(self) -> None:
        """페이지 로드 대기"""
        logger.debug("페이지 로드 대기")
        self.page.wait_for_load_state("networkidle")
    
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

    def select_button_click_in_detail_page(self) -> None:
        """
        연관상품 상세보기 선택 버튼 클릭
        
        """

        # 선택 버튼 클릭
        self.page.locator(".vip-detailoption_wrap").locator(".bt_select").click()
        logger.debug("연관상품 상세보기 선택 버튼 클릭 완료")
       
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
        if module_title == "연관 상품":
            return self.get_module_by_spmc("relateditem")
        elif module_title == "이마트몰VT":
            return self.get_module_by_spmc("emartvt").filter(visible=True)
        elif module_title == "이마트몰BT":
            return self.get_module_by_spmc("emartbt")
        elif module_title == "일반상품 구매하기":
            return self.page.locator("#coreInsOrderBtn")
        elif module_title == "일반상품 장바구니":
            return self.page.locator("#coreAddCartBtn")
        elif module_title == "일반상품 선물하기":
            return self.page.locator("#coreGiftBtn")
        elif module_title == "연관상품 구매하기":
            return self.page.locator("#wingInsOrderBtn")
        elif module_title == "연관상품 장바구니":
            return self.page.locator("#wingAddCartBtn")
        elif module_title == "연관상품 선물하기":
            return self.page.locator("#wingGiftBtn")
        elif module_title == "가입신청" or module_title == "상담신청":
            return self.page.locator("#coreInsOrderBtn")        
        else:
            return self.page.get_by_text(module_title)

    def get_product_in_module(self, parent_locator: Locator) -> Locator:
        """
        모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return parent_locator.locator("li").nth(0).locator("a")

    def get_product_in_related_module(self, parent_locator: Locator) -> Locator:
        """
        연관상품 모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return parent_locator.locator("li").nth(1).locator(".btn_detail")

    def get_product_in_emart_module(self, parent_locator: Locator, module_title) -> Locator:
        """
        모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        if module_title == "이마트몰VT" or module_title == "이마트몰BT":
            return parent_locator.locator("li").nth(6)
        return parent_locator.locator("li").nth(6).locator("a").nth(0)
  
    def wait_for_new_page(self):
        """
        새 페이지가 열릴 때까지 대기하는 컨텍스트 매니저
        
        Returns:
            새 페이지 정보를 담은 컨텍스트 매니저
        """
        logger.debug("새 페이지 대기")
        return self.page.context.expect_page()
    
    def hover_product(self, product_locator: Locator) -> None:
        """
        상품 호버
        
        Args:
            product_locator: 상품 Locator 객체
        """
        logger.debug("상품 호버")
        product_locator.hover()

    def click_product(self, product_locator: Locator) -> None:
        """
        상품 클릭
        
        Args:
            product_locator: 상품 Locator 객체
        """
        logger.debug("상품 클릭")
        product_locator.click()

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
            "함께 보면 좋은 상품이에요": "Y",
            "이 판매자의 인기상품이에요": "N",
            "함께 구매하면 좋은 상품이에요": "F",
            "이마트몰VT": "N",
            "이마트몰BT": "N",
            "이 브랜드의 인기상품": "N",
            "점포 행사 상품이에요": "N",
            "연관 상품": "N",
            "연관상품 상세보기": "N",
        }
        
        if modulel_title not in MODULE_AD_CHECK:
            raise ValueError(f"모듈 타이틀 {modulel_title} 확인 불가")
        
        return MODULE_AD_CHECK[modulel_title]

    def check_ad_tag_in_product(self, product_locator: Locator) -> str:
        """
        상품 내 광고 태그 노출 확인
        
        Args:
            product_locator: 상품 Locator 객체
        
        Returns:
            "Y", "N"(광고 상품 여부)
        """
        logger.debug(f"상품 내 광고 태그 노출 확인: {product_locator}")
        
        try:
            # 상품 요소의 조상 요소에서 div.box__ads-layer 찾기
            ads_layer = product_locator.locator("div.box__ads-tag")
            
            if ads_layer.count() > 0:
                logger.debug("광고 태그 발견: Y")
                return "Y"
            else:
                logger.debug("광고 태그 없음: N")
                return "N"
        except Exception as e:
            logger.warning(f"광고 태그 확인 중 오류 발생: {e}")
            return "N"

    def get_product_code_in_detail_page(self) -> Optional[str]:
        """
        연관상품 상세보기 상품 코드 가져오기
        
        Returns:
            상품 코드 (data-montelena-goodscode 속성 값)
        """
        logger.debug("상품 코드 가져오기")
        return self.page.locator(".relate-item_detail_info_area").locator(".add-interest").get_attribute("data-montelena-goodscode")
    
    def verify_display_layer(self, module_title: str) -> None:
        """
        레이어가 출력되었는지 확인
        """
        logger.debug(f"레이어 출력 여부 확인: {module_title}")
        if module_title == "장바구니":
            layer = self.page.locator("#layer_mycart")
        elif module_title == "상담신청":
            layer = self.page.locator("#box__layer-iframe--rental-counsel")
        else:
            logger.warning(f"지원되지 않는 레이어 타이틀: {module_title}")
            return
        
        try:
            expect(layer).to_be_visible()
            logger.info(f"{module_title} 레이어가 표시됨")
        except Exception:
            logger.warning(f"{module_title} 레이어가 표시되지 않음")

    def fill_in_text_option(self, locator: Locator, cnt: int, option_text: str) -> None:
        """
        텍스트 옵션 입력
        
        Args:
            cnt: 옵션 번호 (1부터 시작)
            option_text: 입력할 옵션 텍스트
        """
        logger.debug(f"옵션 입력: {cnt} - {option_text}")
        option_selector = locator.locator(f"#optOrderTxtOptValue_{cnt}")
        option_selector.fill(option_text)
        logger.info("옵션 입력 완료")

    def is_in_text_option(self, locator: Locator, cnt: int) -> bool:
        """
        텍스트 입력 옵션 있는지 확인
        
        Args:
            cnt: 옵션 번호 (1부터 시작)
            
        Returns:
            True: 텍스트 입력 옵션 있음
            False: 텍스트 입력 옵션 없음
        """
        logger.debug(f"텍스트 입력 옵션 있는지 확인: {cnt}")
        option_box = locator.locator(f"#optOrderTxtOptValue_{cnt}")
        if option_box.count() > 0:
            logger.info(f"{cnt}번 텍스트 입력 옵션 있음")
            return True
        else:
            logger.info(f"{cnt}번 텍스트 입력 옵션 없음")
            return False
    
    def select_option_box(self, locator: Locator,cnt: int) -> None:
        """
        셀렉트 박스 옵션 선택
        
        Args:
            cnt: 옵션 번호 (1부터 시작)
            option_value: 선택할 옵션 값
        """
        logger.debug(f"셀렉트 박스 옵션 선택: {cnt}")
        option_box = locator.locator(f"#optOrderSelOptNo_{cnt}").locator("xpath=/..")
        option_selector = option_box.locator("li").nth(0)
        option_box.click()
        option_selector.click()
        logger.info("셀렉트 박스 옵션 선택 완료")

    def is_in_select_option(self, locator: Locator, cnt: int) -> bool:
        """
        셀렉트 박스 옵션 있는지 확인
        
        Args:
            cnt: 옵션 번호 (1부터 시작)
            
        Returns:
            True: 셀렉트 박스 옵션 있음
            False: 셀렉트 박스 옵션 없음
        """
        logger.debug(f"셀렉트 박스 옵션 있는지 확인: {cnt}")
        option_box = locator.locator(f"#optOrderSelOptNo_{cnt}")
        if option_box.count() > 0:
            logger.info(f"{cnt}번 셀렉트 박스 옵션 있음")
            return True
        else:
            logger.info(f"{cnt}번 셀렉트 박스 옵션 없음")
            return False
        
    def option_area_locator(self, cnt: int) -> Locator:
        """
        옵션 영역 Locator 반환
        
        Args:
            cnt: 옵션 번호 (0부터 시작)
        
        Returns:
            옵션 영역 Locator 객체
        """
        logger.debug("옵션 영역 Locator 반환")
        return self.page.locator(".item_option_area").nth(cnt)
    
    def get_by_text_and_click_where(self, text: str, exact: bool = False, timeout: Optional[int] = None, cnt: int = 0) -> None:
        """
        텍스트 기반 로케이터로 요소 찾아서 클릭
        
        Args:
            text: 텍스트
            exact: 정확히 일치해야 하는지
            timeout: 타임아웃 (기본값: self.timeout)
        """
        timeout = timeout or self.timeout
        logger.debug(f"텍스트 기반 클릭: text={text}")
        self.get_by_text(text, exact=exact).nth(cnt).click(timeout=timeout)