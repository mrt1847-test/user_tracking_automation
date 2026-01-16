import time
import logging
import json
from pages.base_page import BasePage
from playwright.sync_api import Page, Locator, expect
from utils.urls import item_base_url
from typing import Optional

logger = logging.getLogger(__name__)


class SearchPage(BasePage):
    def __init__(self, page: Page):
        """
        SearchPage 초기화
        
        Args:
            page: Playwright Page 객체
        """
        super().__init__(page)
    
    def search_product(self, keyword: str):
        """
        홈화면에서 특정 keyword로 검색
        :param (str) keyword : 검색어
        :example:
        """
        logger.debug(f'검색 시작: keyword={keyword}')
        self.page.fill("input[name='keyword']", keyword)
        self.page.press("input[name='keyword']", "Enter")
        logger.info(f'검색 완료: keyword={keyword}')

    def search_module_by_title(self, module_title):
        """
        특정 모듈의 타이틀 텍스트를 통해 해당 모듈 노출 확인하고 그 모듈 엘리먼트를 반환
        :param (str) module_title : 모듈 타이틀
        :return: 해당 모듈 element
        :example:
        """
        logger.debug(f'모듈 검색 시작: module_title={module_title}')
        child = self.page.get_by_text(module_title, exact=True)
        child.scroll_into_view_if_needed()
        parent = child.locator("xpath=../../..")
        expect(parent).to_be_visible()
        logger.info(f'모듈 노출 확인 완료: module_title={module_title}')

        return parent


    def assert_item_in_module(self, module_title):

        """
        특정 모듈의 타이틀 텍스트를 통해 해당 모듈내 상품 노출 확인하고 그상품번호 반환
        :param (str) module_title : 모듈 타이틀
        :return: 해당 모듈 노출 상품 번호
        :example:
        """
        logger.debug(f'모듈 내 상품 노출 확인 시작: module_title={module_title}')
        child = self.page.get_by_text(module_title, exact=True)
        parent = child.locator("xpath=../..")
        target = parent.locator("div.box__item-container > div.box__image > a")
        target.scroll_into_view_if_needed()
        expect(target).to_be_visible()
        goodscode = target.get_attribute("data-montelena-goodscode")
        logger.info(f'상품 노출 확인 완료: module_title={module_title}, goodscode={goodscode}')
        
        return goodscode

    def get_product_price_info(self, goodscode):
        """
        특정 상품 번호의 가격 정보를 HTML과 URL에서 추출
        :param (str) goodscode : 상품 번호
        :return (dict) price_info: 가격 정보 딕셔너리
        :example:
            {
                "origin_price": "38000",  # 원가 (HTML에서 추출)
                "seller_price": "15390",   # 판매가 (HTML에서 추출)
                "discount_rate": "59",     # 할인률 (HTML에서 추출, % 제거)
                "promotion_price": "16390", # 프로모션가 (URL에서 추출)
                "coupon_price": "13290"    # 쿠폰적용가 (URL에서 추출)
            }
        """
        logger.debug(f'가격 정보 추출 시작: goodscode={goodscode}')
        price_info = {}
        
        try:
            # goodscode로 상품 요소 찾기
            product_element = self.page.locator(f'a[data-montelena-goodscode="{goodscode}"]').first
            product_element.scroll_into_view_if_needed()
            
            # 상품 요소의 부모 컨테이너에서 가격 정보 추출
            item_container = product_element.locator("xpath=ancestor::div[contains(@class, 'box__item-container')]")
            
            # HTML에서 가격 정보 추출
            try:
                # 원가 추출
                original_price_elem = item_container.locator('.box__price-original .text__value').first
                if original_price_elem.count() > 0:
                    original_price_text = original_price_elem.inner_text().strip()
                    # 쉼표 제거
                    price_info['origin_price'] = original_price_text.replace(',', '').replace('원', '').strip()
                    logger.debug(f'원가 추출: {price_info["origin_price"]}')
            except Exception as e:
                logger.warning(f'원가 추출 실패: {e}')
            
            try:
                # 판매가 추출
                seller_price_elem = item_container.locator('.box__price-seller .text__value').first
                if seller_price_elem.count() > 0:
                    seller_price_text = seller_price_elem.inner_text().strip()
                    # 쉼표 제거
                    price_info['seller_price'] = seller_price_text.replace(',', '').replace('원', '').strip()
                    logger.debug(f'판매가 추출: {price_info["seller_price"]}')
            except Exception as e:
                logger.warning(f'판매가 추출 실패: {e}')
            
            try:
                # 할인률 추출
                discount_rate_elem = item_container.locator('.box__discount .text__value').first
                if discount_rate_elem.count() > 0:
                    discount_rate_text = discount_rate_elem.inner_text().strip()
                    # % 제거
                    price_info['discount_rate'] = discount_rate_text.replace('%', '').strip()
                    logger.debug(f'할인률 추출: {price_info["discount_rate"]}')
            except Exception as e:
                logger.warning(f'할인률 추출 실패: {e}')
            
            # URL에서 가격 정보 추출
            try:
                product_url = product_element.get_attribute('href')
                if product_url:
                    # 상대 경로인 경우 절대 경로로 변환
                    if product_url.startswith('/'):
                        product_url = f"{item_base_url()}{product_url}"
                    
                    # URL 파싱 (BasePage의 헬퍼 메서드 사용)
                    query_params = self.parse_query_params(product_url)
                    
                    # utparam-url 파라미터 추출
                    if 'utparam-url' in query_params:
                        utparam_url = query_params['utparam-url'][0]
                        # URL 디코딩 (BasePage의 헬퍼 메서드 사용)
                        decoded_utparam = self.decode_url(utparam_url)
                        
                        # JSON 파싱 시도
                        try:
                            utparam_data = json.loads(decoded_utparam)
                            
                            # 가격 정보 추출
                            if 'origin_price' in utparam_data:
                                price_info['origin_price_url'] = str(utparam_data['origin_price'])
                                logger.debug(f'URL에서 원가 추출: {price_info["origin_price_url"]}')
                            
                            if 'promotion_price' in utparam_data:
                                price_info['promotion_price'] = str(utparam_data['promotion_price'])
                                logger.debug(f'프로모션가 추출: {price_info["promotion_price"]}')
                            
                            if 'coupon_price' in utparam_data:
                                price_info['coupon_price'] = str(utparam_data['coupon_price'])
                                logger.debug(f'쿠폰적용가 추출: {price_info["coupon_price"]}')
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f'utparam-url JSON 파싱 실패: {e}')
                            
            except Exception as e:
                logger.warning(f'URL에서 가격 정보 추출 실패: {e}')
            
            # origin_price가 HTML에서 추출되지 않았고 URL에서 추출된 경우, origin_price_url을 origin_price로 사용
            if 'origin_price' not in price_info and 'origin_price_url' in price_info:
                price_info['origin_price'] = price_info.pop('origin_price_url')
                logger.debug(f'URL에서 추출한 원가를 origin_price로 사용: {price_info["origin_price"]}')
            
            logger.info(f'가격 정보 추출 완료: goodscode={goodscode}, price_info={price_info}')
            
        except Exception as e:
            logger.error(f'가격 정보 추출 중 오류 발생: {e}', exc_info=True)
        
        return price_info

    def montelena_goods_click(self, goodscode):
        """
        특정 상품 번호 아이템 클릭
        :param (str) goodscode : 상품 번호
        :return (str) url: 클릭한 상품 url
        :example:
        """
        logger.debug(f'상품 클릭 시작: goodscode={goodscode}')
        element = self.page.locator(f'a[data-montelena-goodscode="{goodscode}"]').nth(0)
        # 새 페이지 대기
        time.sleep(5)
        with self.page.context.expect_page() as new_page_info:
            element.click()
        new_page = new_page_info.value
        
        # 새 페이지가 완전히 로드될 때까지 대기 (네트워크 요청이 완료될 때까지)
        try:
            new_page.wait_for_load_state('networkidle', timeout=5000)
            logger.debug(f'새 페이지 네트워크 로딩 완료: {goodscode}')
        except Exception as e:
            # networkidle이 타임아웃되면 load 상태만 확인
            logger.debug(f'networkidle 대기 실패, load 상태로 대기: {e}')
            new_page.wait_for_load_state('load', timeout=30000)
            logger.debug(f'새 페이지 로딩 완료: {goodscode}')
        
        url = new_page.url
        logger.info(f'상품 클릭 완료: goodscode={goodscode}')

        logger.debug(f'상품 이동 확인 시작: goodscode={goodscode}')
        assert goodscode in url, f"상품 번호 {goodscode}가 URL에 포함되어야 합니다"
        logger.info(f'상품 이동 확인 완료: goodscode={goodscode}, url={url}')

        return url

    def hybrid_ratio_check(self, parent):
        """
        특정 모듈의 타이틀 텍스트를 통해 해당 모듈 노출 확인하고 그 모듈 엘리먼트를 반환
        :param (element) parent : 모듈의 element
        :return:
        :example:
        """
        logger.debug('일반상품 광고상품 비율 확인 시작')
        container_divs = parent.locator("> div").all()

        for idx, div in enumerate(container_divs[:10], start=1):
            has_ads = div.locator("div.box__ads-layer").count() > 0
            div.scroll_into_view_if_needed()
            if idx % 2 == 0:  # 짝수 번째
                if has_ads:
                    logger.debug(f"{idx}번째 div: 광고 레이어 존재 (정상)")
                else:
                    logger.error(f"{idx}번째 div: 광고 레이어 없음 (오류)")
                    raise AssertionError(f"{idx}번째 div에 광고 레이어가 없습니다")
            else:  # 홀수 번째
                if has_ads:
                    logger.error(f"{idx}번째 div: 광고 레이어가 있으면 안 됨 (오류)")
                    raise AssertionError(f"{idx}번째 div에 광고 레이어가 있어서는 안 됩니다")
                else:
                    logger.debug(f"{idx}번째 div: 광고 레이어 없음 (정상)")
        logger.info('일반상품 광고상품 비율 확인 완료 (10개 검증)')


    def assert_ad_item_in_hybrid(self, parent):

        """
        특정 모듈의 타이틀 텍스트를 통해 해당 모듈내 상품 노출 확인하고 그상품번호 반환
        :param (element) parent : 모듈의 element
        :return (str) goodscode: 상품번호
        :example:
        """
        logger.debug('모듈 내 광고상품 노출 확인 시작')
        container_divs = parent.locator("> div").all()
        first_div_with_ads = None

        for idx, div in enumerate(container_divs[:10], start=1):
            if div.locator("div.box__ads-layer").count() > 0:
                first_div_with_ads = div
                logger.debug(f"{idx}번째 div에 box__ads-layer 발견")
                break  # 첫 번째 div만 찾고 루프 종료

        if first_div_with_ads:
            # box__ads-layer 포함한 상품의 번호 가져오기
            target = first_div_with_ads.locator("div.box__item-container > div.box__image > a")
            target.scroll_into_view_if_needed()
            expect(target).to_be_visible()
            goodscode = target.get_attribute("data-montelena-goodscode")
            logger.info(f'광고상품 노출 확인 완료: goodscode={goodscode}')

        else:
            logger.error('box__ads-layer가 존재하는 div가 없음')
            raise AssertionError('모듈 내 광고상품을 찾을 수 없습니다')

        return goodscode

    def wait_for_search_results_load(self) -> None:
        """검색 결과 페이지 로드 대기"""
        logger.debug("검색 결과 페이지 로드 대기")
        self.page.wait_for_load_state("networkidle")
    
    def click_first_product(self, timeout: int = 10000) -> Optional[Page]:
        """
        첫 번째 상품 클릭하고 새 탭 대기 (새 탭 열림)
        
        Args:
            timeout: 타임아웃 (기본값: 10000ms)
        
        Returns:
            새 탭의 Page 객체 (새 탭이 열리지 않으면 None)
        """
        logger.debug("첫 번째 상품 클릭 및 새 탭 대기")
        
        # 새 탭이 열리는지 확인
        try:
            with self.page.context.expect_page(timeout=timeout) as new_page_info:
                self.click(self.FIRST_PRODUCT, timeout=timeout)
            
            new_page = new_page_info.value
            if new_page:
                logger.debug(f"새 탭 생성됨: {new_page.url}")
                
                # 새 탭을 포커스로 가져오기 (제어 가능하도록)
                new_page.bring_to_front()
                logger.debug("새 탭을 포커스로 가져옴")
                
                # 새 탭이 실제로 로드되고 제어 가능한 상태가 될 때까지 대기
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=30000)
                    logger.debug("새 탭 DOM 로드 완료")
                except Exception as e:
                    logger.warning(f"domcontentloaded 대기 실패: {e}")
                    raise
                
                # URL이 실제로 변경되었는지 확인 (about:blank가 아닌지)
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
            else:
                logger.debug("새 탭이 열리지 않음 (같은 페이지에서 이동)")
                return None
        except Exception as e:
            logger.warning(f"새 탭 대기 중 오류 발생 (같은 페이지에서 이동했을 수 있음): {e}")
            return None
    
    
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
        if module_title == "오늘의 슈퍼딜":
            return self.page.get_by_text("오늘의", exact=True)
        return self.page.get_by_text(module_title, exact=True)

    def get_module_by_title_type2(self, module_title: str) -> Locator:
        """
        모듈 타이틀로 모듈 요소 찾기
        
        Args:
            module_title: 모듈 타이틀 텍스트
            
        Returns:
            Locator 객체
        """
        logger.debug(f"모듈 찾기: {module_title}")
        if module_title == "4.5 이상":
            return self.page.locator(".text__title", has_text="이상 만족도 높은 상품이에요")
        elif module_title == "백화점 브랜드":
            return self.page.locator(".text__title", has_text="의 비슷한 인기브랜드에요")
        elif module_title == "브랜드 인기상품":
            return self.page.locator(".text__title", has_text="인기상품")
    
    def scroll_module_into_view(self, module_locator: Locator) -> None:
        """
        모듈을 뷰포트로 스크롤
        
        Args:
            module_locator: 모듈 Locator 객체
        """
        logger.debug("모듈 스크롤")
        module_locator.scroll_into_view_if_needed()
    
    def get_module_parent(self, module_locator: Locator, n) -> Locator:
        """
        모듈의 부모 요소 찾기
        
        Args:
            module_locator: 모듈 Locator 객체
            
        Returns:
            부모 Locator 객체
        """
        logger.debug("모듈 부모 요소 찾기")
        if n == 1:
            return module_locator.locator("xpath=..")
        elif n == 2:
            return module_locator.locator("xpath=../..")
        elif n == 3:
            return module_locator.locator("xpath=../../..")
        elif n == 4:
            return module_locator.locator("xpath=../../../..")
        elif n == 5:
            return module_locator.locator("xpath=../../../../..")
    
    def get_product_in_module(self, parent_locator: Locator) -> Locator:
        """
        모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return parent_locator.locator("div.box__item-container > div.box__image > a").first
    
    def get_product_in_module_type2(self, parent_locator: Locator) -> Locator:
        """
        모듈 내 상품 요소 찾기
        
        Args:
            parent_locator: 모듈 부모 Locator 객체
            
        Returns:
            상품 Locator 객체
        """
        logger.debug("모듈 내 상품 요소 찾기")
        return parent_locator.locator(".box__itemcard-img > a").first
    
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

