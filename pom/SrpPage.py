import time
import logging

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
        url = new_page.url
        time.sleep(2)
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