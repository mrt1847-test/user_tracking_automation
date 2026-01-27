"""
상품 관련 Step Definitions
상품 선택 / 상세
"""
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import expect
from pages.product_page import ProductPage
from utils.urls import product_url
import logging
import time

# 프론트 실패 처리 헬퍼 함수 import
from utils.frontend_helpers import record_frontend_failure


logger = logging.getLogger(__name__)

@given(parsers.parse('상품 "{goodscode}"의 상세페이지로 접속했음'))
def go_to_product_page(browser_session, goodscode, bdd_context):
    """특정 상품번호의 상품 상세페이지로 접속
    실패 시에도 다음 스텝으로 진행"""
    try:
        product_page = ProductPage(browser_session.page)
        # browser_session.page.goto(f"https://item.gmarket.co.kr/Item?goodscode={goodscode}")
        product_page.go_to_product_page(goodscode)
        logger.info("상품 페이지로 이동")
    except Exception as e:
        logger.error(f"페이지 이동 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"페이지 이동 실패: {str(e)}", "상품 상품번호의 상세페이지로 접속했음")
     
@then("상품 상세 페이지가 표시된다")
def product_detail_page_is_displayed(browser_session, bdd_context):
    """상품 상세 페이지가 표시되는지 확인
    실패 시에도 다음 스텝으로 진행"""
    try:
        product_page = ProductPage(browser_session.page)
        product_page.wait_for_page_load()
        logger.info("상품 상세 페이지 표시 확인")
    except Exception as e:
        logger.error(f"상품 상세 페이지 표시 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"상품 상세 페이지 표시 확인 실패: {str(e)}", "상품 상세 페이지가 표시된다")


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

@then('상품 페이지로 이동되었다')
def product_page_is_opened(browser_session, bdd_context):
    """
    상품 페이지 이동 확인 (검증)
    PDP PV 로그 수집 관련 로그가 뜰 때까지 대기 (tracker 있으면 수집 확인, 없으면 load 대기)
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        product_page = ProductPage(browser_session.page)
        
        # bdd context에서 값 가져오기 (store 또는 딕셔너리 방식 모두 지원)
        goodscode = bdd_context.store.get('goodscode') or bdd_context.get('goodscode')
        url = bdd_context.store.get('product_url') or browser_session.page.url
        
        if not goodscode:
            # goodscode가 없으면 이전 스텝에서 실패했을 가능성
            logger.warning("goodscode가 설정되지 않았습니다. 이전 스텝에서 실패했을 수 있습니다.")
            bdd_context['frontend_action_failed'] = True
            bdd_context['frontend_error_message'] = "goodscode가 설정되지 않았습니다."
            return
        
        # 검증 (실패 시 예외 발생)
        try:
            if url:
                product_page.verify_product_code_in_url(url, goodscode)
            else:
                # URL이 없으면 현재 페이지 URL에서 확인
                current_url = browser_session.page.url
                product_page.verify_product_code_in_url(current_url, goodscode)
        except AssertionError as e:
            logger.error(f"상품 페이지 이동 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 페이지 이동 확인 실패: {str(e)}", "상품 페이지로 이동되었다")
            # 계속 진행 (PDP PV 로그 수집은 시도)
        
        # 🔥 PDP PV 로그 수집 관련 로그가 뜰 때까지 대기 (tracker 있으면 수집 확인, 없으면 load 대기)
        tracker = bdd_context.get("tracker") or bdd_context.store.get("tracker")

        try:
            browser_session.page.wait_for_load_state("networkidle", timeout=10000)
            logger.debug("networkidle 상태 대기 완료 (tracker 없음, PDP PV 대체 대기)")
        except Exception as e:
            logger.warning(f"networkidle 대기 실패, load 상태로 대기: {e}")
            try:
                browser_session.page.wait_for_load_state("load", timeout=30000)
                logger.debug("load 상태 대기 완료")
            except Exception as e2:
                logger.warning(f"load 상태 대기도 실패: {e2}")
        time.sleep(2)
        logger.info(f"상품 페이지 이동 확인 완료: {goodscode} (PDP PV 로그 수집 대기 완료)")
        
    except Exception as e:
        logger.error(f"상품 페이지 이동 확인 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "상품 페이지로 이동되었다")


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
    try:
        product_page = ProductPage(browser_session.page)

        # 모듈로 이동
        module = product_page.get_module_by_title(module_title)
        product_page.scroll_module_into_view(module)
        ad_check = product_page.check_ad_item_in_module(module_title)
  
        # 모듈 내 상품 찾기
        parent = product_page.get_module_parent(module, 2)
        product = product_page.get_product_in_module(parent)
        product_page.scroll_product_into_view(product)
    
        # 상품 노출 확인 (실패 시 예외 발생)
        try:
            expect(product.first).to_be_visible()
        except AssertionError as e:
            # 실패 정보 저장하되 예외는 다시 발생시키지 않음
            logger.error(f"상품 노출 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 노출 확인 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
    
        # 상품 코드 가져오기
        goodscode = product_page.get_product_code(product)

        # 모듈별 광고상품 여부 저장장
        if ad_check == "F":
            is_ad = product_page.check_ad_tag_in_product(product)
        else:
            is_ad = ad_check
        # 상품 클릭
        try:
            if module_title == "이 판매자의 인기상품이에요":
            
                # 상품 클릭하고 새 탭 대기
                new_page = product_page.click_product_and_wait_new_page(product)
            
                # 🔥 명시적 페이지 전환 (상태 관리자 패턴)
                browser_session.switch_to(new_page)
                # bdd context에 저장 (product_url)
                bdd_context.store['product_url'] = new_page.url

            else :
                product_page.click_product(product)
                # bdd context에 저장 (product_url)
                bdd_context.store['product_url'] = browser_session.page.url
                

            # bdd context에 저장 (module_title, goodscode)        
            bdd_context.store['module_title'] = module_title
            bdd_context.store['is_ad'] = is_ad
            bdd_context.store['goodscode'] = goodscode

            logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")
        except Exception as e:
            logger.error(f"상품 클릭 실패: {e}", exc_info=True)
            record_frontend_failure(browser_session, bdd_context, f"상품 클릭 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            # goodscode는 저장 (일부 정보라도 보존)
            if 'goodscode' in locals():
                bdd_context.store['goodscode'] = goodscode
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
                
    except Exception as e:
        # 예상치 못한 예외 처리
        logger.error(f"프론트 동작 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@when(parsers.parse('사용자가 이마트몰 PDP에서 "{module_title}" 모듈 내 상품을 확인하고 클릭한다'))
def user_confirms_and_clicks_product_in_emart_pdp_module(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        product_page = ProductPage(browser_session.page)

        # 모듈로 이동
        module = product_page.get_module_by_title(module_title)
        product_page.scroll_module_into_view(module)
        ad_check = product_page.check_ad_item_in_module(module_title)

        # 모듈 내 상품 찾기
        parent = product_page.get_module_parent(module, 2)
        product = product_page.get_product_in_emart_module(parent, module_title)
        product_page.scroll_product_into_view(product)
    
        # 상품 노출 확인 (실패 시 예외 발생)
        try:
            expect(product.first).to_be_visible()
        except AssertionError as e:
            # 실패 정보 저장하되 예외는 다시 발생시키지 않음
            logger.error(f"상품 노출 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 노출 확인 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
    
        # 상품 코드 가져오기
        goodscode = product_page.get_product_code(product)

        # 모듈별 광고상품 여부 저장장
        if ad_check == "F":
            is_ad = product_page.check_ad_tag_in_product(product)
        else:
            is_ad = ad_check
        # 상품 클릭
        try:            
            product_page.click_product(product)
            
            # bdd context에 저장 (product_url, module_title, goodscode)
            bdd_context.store['product_url'] = browser_session.page.url        
            bdd_context.store['module_title'] = f"이마트몰 {module_title}"
            bdd_context.store['is_ad'] = is_ad
            bdd_context.store['goodscode'] = goodscode

            logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")
        except Exception as e:
            logger.error(f"상품 클릭 실패: {e}", exc_info=True)
            record_frontend_failure(browser_session, bdd_context, f"상품 클릭 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            # goodscode는 저장 (일부 정보라도 보존)
            if 'goodscode' in locals():
                bdd_context.store['goodscode'] = goodscode
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
                
    except Exception as e:
        # 예상치 못한 예외 처리
        logger.error(f"프론트 동작 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@when(parsers.parse('사용자가 PDP에서 연관상품 상세보기를 확인하고 클릭한다'))
def user_confirms_and_clicks_product_in_pdp_related_module(browser_session, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    module_title = "연관 상품"
    try:
        product_page = ProductPage(browser_session.page)

        # 모듈로 이동
        module = product_page.get_module_by_spm("relateditem")
        product_page.scroll_module_into_view(module)
        
        # 모듈 내 상품 찾기
        product = product_page.get_product_in_related_module(module)
        product_page.scroll_product_into_view(product)

        # 상품 내 상세보기 버튼 찾기
        button = product_page.get_product_in_related_btn_module(product)

        # 상품 노출 확인 (실패 시 예외 발생)
        try:
            expect(product.first).to_be_visible()
        except AssertionError as e:
            # 실패 정보 저장하되 예외는 다시 발생시키지 않음
            logger.error(f"상품 노출 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 노출 확인 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
    
        # 상품 코드 가져오기
        goodscode = product_page.get_product_code(button)

        try:
            # 상품 클릭
            product_page.hover_product(product)
            product_page.click_product(button)
            
            # bdd context에 저장 (product_url, module_title, goodscode)
            bdd_context.store['product_url'] = browser_session.page.url        
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode

            logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")
        except Exception as e:
            logger.error(f"상품 클릭 실패: {e}", exc_info=True)
            record_frontend_failure(browser_session, bdd_context, f"상품 클릭 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
            # goodscode는 저장 (일부 정보라도 보존)
            if 'goodscode' in locals():
                bdd_context.store['goodscode'] = goodscode
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
                
    except Exception as e:
        # 예상치 못한 예외 처리
        logger.error(f"프론트 동작 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "사용자가 모듈 내 상품을 확인하고 클릭한다 (type2)")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title
