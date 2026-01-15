"""
BDD Step Definitions for SRP Tracking Tests
"""
import logging
import pytest
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import expect
from pages.search_page import SearchPage
from pages.Etc import Etc

logger = logging.getLogger(__name__)



@given(parsers.parse('검색 결과 페이지에 "{module_title}" 모듈이 있다'))
def module_exists_in_search_results(browser_session, module_title, request):
    """
    검색 결과 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 skip (같은 feature 파일 내 다음 시나리오 모두 skip)
    모듈이 있지만 보이지 않으면 fail
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        request: pytest request 객체 (fixture 접근용)
    """
    from conftest import PlaywrightSharedState
    
    search_page = SearchPage(browser_session.page)
    
    # 모듈 찾기
    module = search_page.get_module_by_title(module_title)
    
    # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
    module_count = module.count()
    if module_count == 0:
        # 모듈이 없으면 skip (현재 feature 파일의 나머지 시나리오도 skip하도록 플래그 설정)
        PlaywrightSharedState.skip_current_feature = True
        PlaywrightSharedState.skip_feature_name = PlaywrightSharedState.current_feature_name
        pytest.skip(f"'{module_title}' 모듈이 검색 결과에 없습니다. 현재 feature의 나머지 시나리오를 skip합니다.")
    
    # 모듈이 있으면 visibility 확인 (실패하면 fail)
    expect(module.first).to_be_visible()
    
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
    parent = search_page.get_module_parent(module)
    product = search_page.get_product_in_module(parent)
    search_page.scroll_product_into_view(product)
    
    # 상품 노출 확인
    expect(product.first).to_be_visible()
    
    # 상품 코드 가져오기
    goodscode = search_page.get_product_code(product)
    
    # 상품 클릭
    new_page = search_page.click_product_and_wait_new_page(product)
    
    # 🔥 명시적 페이지 전환 (상태 관리자 패턴)
    browser_session.switch_to(new_page)
    
    # bdd context에 저장 (goodscode, product_url 등 다른 데이터는 유지)
    bdd_context.store['goodscode'] = goodscode
    bdd_context.store['product_url'] = new_page.url
    
    logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")


@then('상품 페이지로 이동되었다')
def product_page_is_opened(browser_session, bdd_context):
    """
    상품 페이지 이동 확인 (검증)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
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
    
    logger.info(f"상품 페이지 이동 확인 완료: {goodscode}")
