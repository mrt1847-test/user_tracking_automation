"""
상품 관련 Step Definitions
상품 선택 / 상세
"""
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import expect
from pages.product_page import ProductPage
from pages.search_page import SearchPage
from pages.home_page import HomePage
from utils.urls import product_url
import logging
import pytest

logger = logging.getLogger(__name__)

@given(parsers.parse('상품 "{goodscode}"의 상세페이지로 접속했음'))
def go_to_product_page(browser_session, goodscode):
    """
    특정 상품 페이지 접속
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        goodscode: 상품번호
    """
    product_page = ProductPage(browser_session.page)
    # browser_session.page.goto(f"https://item.gmarket.co.kr/Item?goodscode={goodscode}")
    product_page.go_to_product_page(goodscode)
    # product_page.wait_for_page_load()
    logger.info("상품 페이지로 이동")
    
    # 이동 후 확인
    assert product_page.is_product_detail_displayed(), "상품 상세 페이지 생성 실패"
    logger.info("상품 상세 페이지 상태 보장 완료")

@then("상품 상세 페이지가 표시된다")
def product_detail_page_is_displayed(browser_session):
    """
    상품 상세 페이지가 표시되는지 확인 (증명)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    product_page = ProductPage(browser_session.page)
    assert product_page.is_product_detail_displayed(), "상품 상세 페이지가 표시되지 않았습니다"
    logger.info("상품 상세 페이지 표시 확인")


@given("상품 상세 페이지가 표시된다")
def product_detail_page_is_displayed_given(browser_session, bdd_context):
    """
    상품 상세 페이지 상태 보장 (확인 + 필요시 생성)
    
    bdd_context.store['goodscode']에 저장된 상품번호를 기준으로
    현재 URL에 goodscode가 없으면 상품 상세 페이지 URL로 이동
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    goodscode = bdd_context.store.get('goodscode')
    if not goodscode:
        logger.warning("bdd_context.store에 goodscode가 없습니다")
        return
    
    current_url = browser_session.page.url
    if goodscode in current_url:
        logger.info(f"현재 URL에 goodscode({goodscode})가 이미 포함되어 있음")
        return
    
    product_url_value = product_url(goodscode)
    product_page = ProductPage(browser_session.page)
    product_page.goto(product_url_value)
    logger.info(f"상품 상세 페이지로 이동: {product_url_value}")
    
    # 이동 후 확인
    assert product_page.is_product_detail_displayed(), "상품 상세 페이지 생성 실패"
    logger.info("상품 상세 페이지 상태 보장 완료")


@then(parsers.parse('상품명에 "{product_name}"이 포함되어 있다'))
def product_name_contains(browser_session, product_name):
    """
    상품 상세 페이지의 상품명 확인
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        product_name: 확인할 상품명
    """
    product_page = ProductPage(browser_session.page)
    assert product_page.contains_product_name(product_name), f"상품명에 '{product_name}'이 포함되어 있지 않습니다"
    logger.info(f"상품명 확인: {product_name}")


@when("사용자가 상품 옵션을 선택한다")
def user_selects_product_option(browser_session):
    """
    사용자가 상품 옵션(색상, 사이즈 등) 선택
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    product_page = ProductPage(browser_session.page)
    product_page.select_option()
    logger.info("상품 옵션 선택")


@when(parsers.parse('사용자가 "{option_name}" 옵션을 선택한다'))
def user_selects_specific_option(browser_session, option_name):
    """
    사용자가 특정 옵션 선택
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        option_name: 옵션명
    """
    product_page = ProductPage(browser_session.page)
    product_page.select_specific_option(option_name)
    logger.info(f"옵션 선택: {option_name}")


@when("사용자가 수량을 변경한다")
def user_changes_quantity(browser_session):
    """
    사용자가 상품 수량 변경
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    product_page = ProductPage(browser_session.page)
    product_page.change_quantity()
    logger.info("수량 변경")


@when(parsers.parse('사용자가 수량을 "{quantity}"개로 변경한다'))
def user_changes_quantity_to(browser_session, quantity):
    """
    사용자가 상품 수량을 특정 개수로 변경
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        quantity: 수량
    """
    product_page = ProductPage(browser_session.page)
    product_page.change_quantity_to(quantity)
    logger.info(f"수량 변경: {quantity}개")


@then(parsers.parse('상품 가격이 "{price}"로 표시된다'))
def product_price_is_displayed(browser_session, price):
    """
    상품 가격이 올바르게 표시되는지 확인
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        price: 예상 가격
    """
    product_page = ProductPage(browser_session.page)
    assert product_page.is_price_displayed(price), f"상품 가격이 '{price}'로 표시되지 않았습니다"
    logger.info(f"상품 가격 확인: {price}")

@when("사용자가 구매하기 버튼을 클릭한다")
def user_clicks_buy_now_button(browser_session):
    """
    사용자가 구매하기 버튼을 클릭한다
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    product_page = ProductPage(browser_session.page)
    try:
        product_page.select_group_product(1)
    except:
        logger.debug(f"그룹상품 선택 실패")
        pass
    product_page.click_buy_now_button()
    logger.info("구매하기 클릭 완료")


@when(parsers.parse('사용자가 PDP에서 "{module_title}" 모듈 내 상품을 확인하고 클릭한다'))
def user_confirms_and_clicks_product_in_pdp_module(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    product_page = ProductPage(browser_session.page)
    
    # 모듈로 이동
    module = product_page.get_module_by_title(module_title)
    product_page.scroll_module_into_view(module)
    
    # 모듈 내 상품 찾기
    parent = product_page.get_module_parent(module)
    product = product_page.get_product_in_module(parent)
    product_page.scroll_product_into_view(product)
    
    # 상품 노출 확인
    expect(product.first).to_be_visible()
    
    # 상품 코드 가져오기
    goodscode = product_page.get_product_code(product)
    
    # 🔥 가격 정보는 이제 PDP PV 로그에서 추출하므로 프론트엔드에서 수집하지 않음
    # (PDP PV 로그는 상품 페이지 이동 후 수집됨)
    
    # 상품 클릭
    new_page = product_page.click_product_and_wait_new_page(product)
    
    # 🔥 명시적 페이지 전환 (상태 관리자 패턴)
    browser_session.switch_to(new_page)
    
    # bdd context에 저장 (module_title, goodscode, product_url 등)
    bdd_context.store['module_title'] = module_title
    bdd_context.store['goodscode'] = goodscode
    bdd_context.store['product_url'] = new_page.url
    
    logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")

