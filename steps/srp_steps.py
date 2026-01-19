"""
BDD Step Definitions for SRP Tracking Tests
"""
import logging
import pytest
from pathlib import Path
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import expect
from pages.search_page import SearchPage
from pages.home_page import HomePage
from pages.Etc import Etc

logger = logging.getLogger(__name__)


@when(parsers.parse('사용자가 "{keyword}"을 검색한다'))
def when_user_searches_keyword(browser_session, keyword, bdd_context):
    """사용자가 특정 키워드로 검색"""
    logger.info(f"검색 시작: keyword={keyword}")
    home_page = HomePage(browser_session.page)
    home_page.fill_search_input(keyword)
    home_page.click_search_button()
    home_page.wait_for_search_results()
    bdd_context.store['keyword'] = keyword
    logger.info(f"검색 완료: keyword={keyword}")


@then("검색 결과 페이지가 표시된다")
def then_search_results_page_is_displayed(browser_session):
    """검색 결과 페이지가 표시되는지 확인"""
    search_page = SearchPage(browser_session.page)
    search_page.wait_for_search_results_load()
    logger.info("검색 결과 페이지 표시 확인")


@given(parsers.parse('사용자가 "{keyword}"을 검색했다'))
def given_user_searched_keyword(browser_session, keyword, bdd_context):
    """사용자가 이미 검색한 상태 (Given)"""
    logger.info(f"검색 상태 확인: keyword={keyword}")
    # 이미 검색 결과 페이지에 있는지 확인
    current_url = browser_session.page.url
    if 'search' not in current_url.lower():
        # 검색 결과 페이지가 아니면 검색 수행
        when_user_searches_keyword(browser_session, keyword, bdd_context)
    else:
        bdd_context.store['keyword'] = keyword
        logger.info(f"이미 검색 결과 페이지에 있음: keyword={keyword}")


@given(parsers.parse('검색 결과 페이지에 "{module_title}" 모듈이 있다'))
def module_exists_in_search_results(browser_session, module_title, request, bdd_context):
    """
    검색 결과 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 현재 시나리오만 skip
    모듈이 있지만 보이지 않으면 fail
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        request: pytest request 객체 (fixture 접근용)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    search_page = SearchPage(browser_session.page)
    
    # 모듈 찾기
    module = search_page.get_module_by_title(module_title)
    
    # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
    module_count = module.count()
    if module_count == 0:
        # 모듈이 없으면 현재 시나리오만 skip
        pytest.skip(f"'{module_title}' 모듈이 검색 결과에 없습니다.")
    
    # 모듈이 있으면 visibility 확인 (실패하면 fail)
    expect(module.first).to_be_visible()
    
    # bdd_context에 module_title 저장 (다음 step에서 사용)
    bdd_context.store['module_title'] = module_title
    
    logger.info(f"{module_title} 모듈 존재 확인 완료")

@given(parsers.parse('검색 결과 페이지에 "{module_title}" 모듈이 있다 (type2)'))
def module_exists_in_search_results_type2(browser_session, module_title, request, bdd_context):
    """
    검색 결과 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 현재 시나리오만 skip
    모듈이 있지만 보이지 않으면 fail
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        request: pytest request 객체 (fixture 접근용)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    search_page = SearchPage(browser_session.page)
    
    # 모듈 찾기
    module = search_page.get_module_by_title_type2(module_title)
    
    # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
    module_count = module.count()
    if module_count == 0:
        # 모듈이 없으면 현재 시나리오만 skip
        pytest.skip(f"'{module_title}' 모듈이 검색 결과에 없습니다.")
    
    # 모듈이 있으면 visibility 확인 (실패하면 fail)
    expect(module.first).to_be_visible()
    
    # bdd_context에 module_title 저장 (다음 step에서 사용)
    bdd_context.store['module_title'] = module_title
    
    logger.info(f"{module_title} 모듈 존재 확인 완료")



@when(parsers.parse('사용자가 "{module_title}" 모듈 내 상품을 확인하고 클릭한다'))
def user_confirms_and_clicks_product_in_module(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    search_page = SearchPage(browser_session.page)
    
    # 모듈로 이동
    module = search_page.get_module_by_title(module_title)
    search_page.scroll_module_into_view(module)
    
    # 모듈 내 상품 찾기
    parent = search_page.get_module_parent(module, 2)
    product = search_page.get_product_in_module(parent)
    search_page.scroll_product_into_view(product)
    
    # 상품 노출 확인
    expect(product.first).to_be_visible()
    
    # 상품 코드 가져오기
    goodscode = search_page.get_product_code(product)
    
    # 장바구니 담기 버튼 존재할 경우 클릭
    if search_page.is_add_to_cart_button_visible(module, goodscode):
        search_page.click_add_to_cart_button(module, goodscode)
        logger.info(f"장바구니 담기 버튼 클릭 완료: {goodscode}")
    else:
        logger.info(f"장바구니 담기 버튼이 존재하지 않습니다: {goodscode}")
    
    # 상품 클릭
    new_page = search_page.click_product_and_wait_new_page(product)
    
    # 🔥 명시적 페이지 전환 (상태 관리자 패턴)
    browser_session.switch_to(new_page)
    
    # bdd context에 저장 (module_title, goodscode, product_url 등)
    bdd_context.store['module_title'] = module_title
    bdd_context.store['goodscode'] = goodscode
    bdd_context.store['product_url'] = new_page.url
    
    logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")

@when(parsers.parse('사용자가 "{module_title}" 모듈 내 상품을 확인하고 클릭한다 (type2)'))
def user_confirms_and_clicks_product_in_module_type2(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    search_page = SearchPage(browser_session.page)
    
    # 모듈로 이동
    module = search_page.get_module_by_title_type2(module_title)
    search_page.scroll_module_into_view(module)
    
    # 모듈 내 상품 찾기
    parent = search_page.get_module_parent(module, 3)
    if module_title == "4.5 이상":
        product = search_page.get_product_in_module_type3(parent)
    else:
        product = search_page.get_product_in_module_type2(parent)
    search_page.scroll_product_into_view(product)
    
    # 상품 노출 확인
    expect(product.first).to_be_visible()
    
    # 상품 코드 가져오기
    goodscode = search_page.get_product_code(product)
    
    # 🔥 가격 정보는 이제 PDP PV 로그에서 추출하므로 프론트엔드에서 수집하지 않음
    # (PDP PV 로그는 상품 페이지 이동 후 수집됨)
    
    # 상품 클릭
    new_page = search_page.click_product_and_wait_new_page(product)
    
    # 🔥 명시적 페이지 전환 (상태 관리자 패턴)
    browser_session.switch_to(new_page)
    
    # bdd context에 저장 (module_title, goodscode, product_url 등)
    bdd_context.store['module_title'] = module_title
    bdd_context.store['goodscode'] = goodscode
    bdd_context.store['product_url'] = new_page.url
    
    logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")


@then('상품 페이지로 이동되었다')
def product_page_is_opened(browser_session, bdd_context):
    """
    상품 페이지 이동 확인 (검증)
    PDP PV 로그 수집을 위해 networkidle 상태까지 대기
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    import time
    
    search_page = SearchPage(browser_session.page)
    
    # bdd context에서 값 가져오기 (store 또는 딕셔너리 방식 모두 지원)
    goodscode = bdd_context.store.get('goodscode') or bdd_context.get('goodscode')
    url = bdd_context.store.get('product_url') or browser_session.page.url
    
    if not goodscode:
        raise ValueError("goodscode가 설정되지 않았습니다.")
    
    # 검증
    if url:
        search_page.verify_product_code_in_url(url, goodscode)
    else:
        # URL이 없으면 현재 페이지 URL에서 확인
        current_url = browser_session.page.url
        search_page.verify_product_code_in_url(current_url, goodscode)
    
    # 🔥 PDP PV 로그 수집을 위해 networkidle 상태까지 대기
    try:
        browser_session.page.wait_for_load_state("networkidle", timeout=10000)
        logger.debug("networkidle 상태 대기 완료 (PDP PV 로그 수집 대기)")
    except Exception as e:
        logger.warning(f"networkidle 대기 실패, load 상태로 대기: {e}")
        try:
            browser_session.page.wait_for_load_state("load", timeout=30000)
            logger.debug("load 상태 대기 완료")
        except Exception as e2:
            logger.warning(f"load 상태 대기도 실패: {e2}")
    
    # 추가 안전 대기 (PDP PV 로그가 비동기로 전송될 수 있음)
    time.sleep(2)
    logger.info(f"상품 페이지 이동 확인 완료: {goodscode} (PDP PV 로그 수집 대기 완료)")
