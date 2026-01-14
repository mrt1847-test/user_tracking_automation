"""
BDD Step Definitions for SRP Tracking Tests
"""
import time
import logging
from pytest_bdd import given, when, parsers
from pom.SrpPage import Srp
from pom.Etc import Etc
from utils.NetworkTracker import NetworkTracker

logger = logging.getLogger(__name__)


@given("G마켓 홈 페이지에 접속했음")
def given_gmarket_home_page_accessed(page, bdd_context):
    """G마켓 홈 페이지에 접속"""
    logger.info("G마켓 홈 페이지 접속")
    etc = Etc(page)
    etc.goto()
    bdd_context['etc'] = etc
    bdd_context['page'] = page


@given("네트워크 트래킹이 시작되었음")
def given_network_tracking_started(page, bdd_context):
    """네트워크 트래킹 시작"""
    logger.info("네트워크 트래킹 시작")
    tracker = NetworkTracker(page)
    tracker.start()
    bdd_context['tracker'] = tracker


@when(parsers.parse('사용자가 "{keyword}"로 검색함'))
def when_user_searches_with_keyword(keyword, bdd_context):
    """사용자가 특정 키워드로 검색"""
    logger.info(f"검색 시작: keyword={keyword}")
    page = bdd_context['page']
    srp_page = Srp(page)
    srp_page.search_product(keyword)
    bdd_context['srp_page'] = srp_page
    bdd_context['keyword'] = keyword


@when(parsers.parse('"{module_title}" 모듈을 찾음'))
def when_find_module_by_title(module_title, bdd_context):
    """특정 모듈을 찾음"""
    logger.info(f"모듈 찾기: module_title={module_title}")
    srp_page = bdd_context['srp_page']
    srp_page.search_module_by_title(module_title)
    bdd_context['module_title'] = module_title


@when("모듈 내 상품을 확인함")
def when_check_item_in_module(bdd_context):
    """모듈 내 상품 확인 및 goodscode 추출"""
    logger.info("모듈 내 상품 확인")
    srp_page = bdd_context['srp_page']
    module_title = bdd_context['module_title']
    goodscode = srp_page.assert_item_in_module(module_title)
    bdd_context['goodscode'] = goodscode
    logger.info(f"확인된 상품 번호: {goodscode}")


@when("상품 가격 정보를 추출함")
def when_extract_product_price_info(bdd_context):
    """상품 가격 정보 추출"""
    logger.info("상품 가격 정보 추출")
    srp_page = bdd_context['srp_page']
    goodscode = bdd_context['goodscode']
    price_info = srp_page.get_product_price_info(goodscode)
    bdd_context['price_info'] = price_info
    logger.info(f"추출된 가격 정보: {price_info}")


@when("상품을 클릭함")
def when_click_product(bdd_context):
    """상품 클릭"""
    logger.info("상품 클릭")
    srp_page = bdd_context['srp_page']
    goodscode = bdd_context['goodscode']
    srp_page.montelena_goods_click(goodscode)


@when("네트워크 요청이 완료될 때까지 대기함")
def when_wait_for_network_request_completion():
    """네트워크 요청 완료 대기"""
    logger.info("네트워크 요청 완료 대기")
    time.sleep(2)
