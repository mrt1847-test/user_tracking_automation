import time
import logging
import json
import re
from urllib.parse import unquote, parse_qs, urlparse

from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class Srp():
    def __init__(self, page):
        self.page = page

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
                        product_url = f"https://item.gmarket.co.kr{product_url}"
                    
                    # URL 파싱
                    parsed_url = urlparse(product_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    # utparam-url 파라미터 추출
                    if 'utparam-url' in query_params:
                        utparam_url = query_params['utparam-url'][0]
                        # URL 디코딩
                        decoded_utparam = unquote(utparam_url)
                        
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