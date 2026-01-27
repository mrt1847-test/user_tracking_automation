"""
주문 확인 관련 Step Definitions
주문 완료 / 내역 확인
"""
from pages.order_page import OrderPage
from pytest_bdd import given, when, then, parsers
import logging
from playwright.sync_api import expect
# 프론트 실패 처리 헬퍼 함수 import
from utils.frontend_helpers import record_frontend_failure

logger = logging.getLogger(__name__)


@when(parsers.parse('장바구니 번호 "{cart_num}" 인 주문완료 페이지에 접속했음'))
def goes_to_order_complete_page(browser_session, cart_num, bdd_context):
    """
    장바구니 번호 "{cart_num}" 인 주문완료 페이지에 접속했음
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        cart_num: 장바구니 번호
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    
    try:
        order_page = OrderPage(browser_session.page)
        # 주문완료 페이지로 이동
        order_page.go_to_order_complete_page(cart_num) 
        logger.info(f"주문완료 페이지 이동 완료: {cart_num}")
    except Exception as e:
        logger.error(f"주문완료 페이지 이동 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"주문완료 페이지 이동 실패: {e}", "장바구니 번호 '{cart_num}' 인 주문완료 페이지에 접속했음")

@then("주문완료 페이지가 표시된다")
def order_complete_page_is_displayed(browser_session, bdd_context):
    """
    주문완료 페이지가 표시되는지 확인
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        order_page = OrderPage(browser_session.page)
        assert order_page.is_order_complete_page_displayed(), "주문완료 페이지가 표시되지 않았습니다"
        logger.info("주문완료 페이지 표시 확인")
    except Exception as e:
        logger.error(f"주문완료 페이지 표시 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"주문완료 페이지 표시 확인 실패: {e}", "주문완료 페이지가 표시된다")

@given(parsers.parse('주문완료 페이지에 "{module_title}" 모듈이 있다'))
def module_exists_in_order_complete_page(browser_session, module_title, bdd_context):
    """
    주문완료 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 현재 시나리오만 skip
    모듈이 있지만 보이지 않으면 실패 플래그만 설정하고 다음으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        order_page = OrderPage(browser_session.page)
        
        # 모듈 찾기
        module_spmc = order_page.get_spmc_by_module_title(module_title)
        module = order_page.get_module_by_spmc(module_spmc)
        
        # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
        module_count = module.count()
        if module_count == 0:
            # 모듈이 없으면 skip 플래그 설정 (시나리오는 계속 진행)
            skip_reason = f"'{module_title}' 모듈이 주문완료 페이지에 없습니다."
            logger.warning(skip_reason)
            if hasattr(bdd_context, '__setitem__'):
                bdd_context['skip_reason'] = skip_reason
            elif hasattr(bdd_context, 'store'):
                bdd_context.store['skip_reason'] = skip_reason
            # module_title은 저장 (다음 스텝에서 사용 가능하도록)
            bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행하되 skip 상태로 기록됨)
        
        # 모듈이 있으면 visibility 확인 (실패 시 플래그만 설정)
        try:
            expect(module.first).to_be_attached()
        except AssertionError as e:
            logger.error(f"모듈 존재 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"모듈 존재 확인 실패: {str(e)}", "주문완료 페이지에 모듈이 있다")
            # module_title은 저장 (다음 스텝에서 사용 가능하도록)
            bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
        
        # bdd_context에 module_title 저장 (다음 step에서 사용)
        bdd_context.store['module_title'] = module_title
        
        logger.info(f"{module_title} 모듈 존재 확인 완료")
    except Exception as e:
        logger.error(f"모듈 확인 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "주문완료 페이지에 모듈이 있다")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@when(parsers.parse('사용자가 "{module_title}" 모듈 내 상품을 확인하고 옵션선택을 클릭한다'))
def user_confirms_and_clicks_product_in_module(browser_session, module_title, bdd_context):
    """
    주문완료 페이지에 특정 모듈 내 옵션선택 버튼 클릭 (비즈니스 로직)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        order_page = OrderPage(browser_session.page)
        # 모듈 찾기
        module_spmc = order_page.get_spmc_by_module_title(module_title)
        module = order_page.get_module_by_spmc(module_spmc)
        # 옵션선택 버튼 찾기 및 클릭
        option_select_button = order_page.find_option_select_button_in_module(module)
        goodscode = order_page.get_goodscode_in_product(option_select_button)
        option_select_button.click()
        # goodscode 저장 (다음 스텝에서 사용)
        bdd_context.store['goodscode'] = goodscode
        logger.info(f"{module_title} 모듈 내 옵션선택 버튼 클릭 완료: goodscode={goodscode}")
    except Exception as e:
        logger.error(f"{module_title} 모듈 내 옵션선택 버튼 클릭 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"{module_title} 모듈 내 옵션선택 버튼 클릭 실패: {e}", "사용자가 모듈 내 상품을 확인하고 옵션선택을 클릭한다")
        