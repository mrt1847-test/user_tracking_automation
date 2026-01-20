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

# 프론트 실패 처리 헬퍼 함수 import
from utils.frontend_helpers import record_frontend_failure

logger = logging.getLogger(__name__)


@when(parsers.parse('사용자가 "{keyword}"을 검색한다'))
def when_user_searches_keyword(browser_session, keyword, bdd_context):
    """사용자가 특정 키워드로 검색
    실패 시에도 다음 스텝으로 진행"""
    try:
        logger.info(f"검색 시작: keyword={keyword}")
        home_page = HomePage(browser_session.page)
        home_page.fill_search_input(keyword)
        home_page.click_search_button()
        home_page.wait_for_search_results()
        bdd_context.store['keyword'] = keyword
        logger.info(f"검색 완료: keyword={keyword}")
    except Exception as e:
        logger.error(f"검색 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"검색 실패: {str(e)}", "사용자가 키워드를 검색한다")
        if 'keyword' not in bdd_context.store:
            bdd_context.store['keyword'] = keyword


@then("검색 결과 페이지가 표시된다")
def then_search_results_page_is_displayed(browser_session, bdd_context):
    """검색 결과 페이지가 표시되는지 확인
    실패 시에도 다음 스텝으로 진행"""
    try:
        search_page = SearchPage(browser_session.page)
        search_page.wait_for_search_results_load()
        logger.info("검색 결과 페이지 표시 확인")
    except Exception as e:
        logger.error(f"검색 결과 페이지 표시 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"검색 결과 페이지 표시 확인 실패: {str(e)}", "검색 결과 페이지가 표시된다")


@given(parsers.parse('사용자가 "{keyword}"을 검색했다'))
def given_user_searched_keyword(browser_session, keyword, bdd_context):
    """사용자가 이미 검색한 상태 (Given)
    실패 시에도 다음 스텝으로 진행"""
    try:
        logger.info(f"검색 상태 확인: keyword={keyword}")
        # 이미 검색 결과 페이지에 있는지 확인
        current_url = browser_session.page.url
        if 'search' not in current_url.lower():
            # 검색 결과 페이지가 아니면 검색 수행
            when_user_searches_keyword(browser_session, keyword, bdd_context)
            # 검색 스텝에서 실패했을 경우 플래그가 설정됨
        else:
            bdd_context.store['keyword'] = keyword
            logger.info(f"이미 검색 결과 페이지에 있음: keyword={keyword}")
    except Exception as e:
        logger.error(f"검색 상태 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"검색 상태 확인 실패: {str(e)}", "사용자가 키워드를 검색했다")
        if 'keyword' not in bdd_context.store:
            bdd_context.store['keyword'] = keyword


@given(parsers.parse('검색 결과 페이지에 "{module_title}" 모듈이 있다'))
def module_exists_in_search_results(browser_session, module_title, request, bdd_context):
    """
    검색 결과 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 현재 시나리오만 skip
    모듈이 있지만 보이지 않으면 실패 플래그만 설정하고 다음으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        request: pytest request 객체 (fixture 접근용)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        search_page = SearchPage(browser_session.page)
        
        # 모듈 찾기
        module = search_page.get_module_by_title(module_title)
        
        # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
        module_count = module.count()
        if module_count == 0:
            # 모듈이 없으면 skip 플래그 설정 (시나리오는 계속 진행)
            skip_reason = f"'{module_title}' 모듈이 검색 결과에 없습니다."
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
            record_frontend_failure(browser_session, bdd_context, f"모듈 존재 확인 실패: {str(e)}", "검색 결과 페이지에 모듈이 있다")
            # module_title은 저장 (다음 스텝에서 사용 가능하도록)
            bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
        
        # bdd_context에 module_title 저장 (다음 step에서 사용)
        bdd_context.store['module_title'] = module_title
        
        logger.info(f"{module_title} 모듈 존재 확인 완료")
    except Exception as e:
        logger.error(f"모듈 확인 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "검색 결과 페이지에 모듈이 있다")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@given(parsers.parse('검색 결과 페이지에 "{module_title}" 모듈이 있다 (type2)'))
def module_exists_in_search_results_type2(browser_session, module_title, request, bdd_context):
    """
    검색 결과 페이지에 특정 모듈이 존재하는지 확인하고 보장 (Given)
    모듈이 없으면 현재 시나리오만 skip
    모듈이 있지만 보이지 않으면 실패 플래그만 설정하고 다음으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        request: pytest request 객체 (fixture 접근용)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        search_page = SearchPage(browser_session.page)
        
        # 모듈 찾기
        module = search_page.get_module_by_title(module_title)
        
        # 모듈이 존재하는지 확인 (count == 0이면 모듈이 없음)
        module_count = module.count()
        if module_count == 0:
            # 모듈이 없으면 skip 플래그 설정 (시나리오는 계속 진행)
            skip_reason = f"'{module_title}' 모듈이 검색 결과에 없습니다."
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
            record_frontend_failure(browser_session, bdd_context, f"모듈 존재 확인 실패: {str(e)}", "검색 결과 페이지에 모듈이 있다 (type2)")
            # module_title은 저장 (다음 스텝에서 사용 가능하도록)
            bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
        
        # bdd_context에 module_title 저장 (다음 step에서 사용)
        bdd_context.store['module_title'] = module_title
        
        logger.info(f"{module_title} 모듈 존재 확인 완료")
    except Exception as e:
        logger.error(f"모듈 확인 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "검색 결과 페이지에 모듈이 있다 (type2)")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@when(parsers.parse('사용자가"{keyword}""{goodscode}" 최상단 클릭아이템 모듈 패이지로 이동한다'))
def user_goes_to_top_search_module_page(browser_session, keyword, goodscode, bdd_context):
    """
    최상단 클릭아이템 모듈 페이지로 이동
    실패 시에도 다음 스텝으로 진행
    """
    try:
        search_page = SearchPage(browser_session.page)
        search_page.go_to_top_search_module_page(keyword, goodscode)
        logger.info("최상단 클릭아이템 모듈 페이지로 이동 완료")
        bdd_context.store['module_title'] = "최상단 클릭아이템"
        bdd_context.store['keyword'] = keyword
    except Exception as e:
        logger.error(f"최상단 클릭아이템 모듈 페이지 이동 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"최상단 클릭아이템 모듈 페이지 이동 실패: {str(e)}", "사용자가 최상단 클릭아이템 모듈 페이지로 이동한다")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = "최상단 클릭아이템"
        if 'keyword' not in bdd_context.store:
            bdd_context.store['keyword'] = keyword


@when(parsers.parse('사용자가 "{module_title}" 모듈 내 상품을 확인하고 클릭한다'))
def user_confirms_and_clicks_product_in_module(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        search_page = SearchPage(browser_session.page)
        
        # 모듈로 이동
        module = search_page.get_module_by_title(module_title)
        search_page.scroll_module_into_view(module)
        
        # 모듈 내 상품 찾기
        parent = search_page.get_module_parent(module, 2)
        product = search_page.get_product_in_module(parent)
        search_page.scroll_product_into_view(product)
        
        # 상품 노출 확인 (실패 시 예외 발생)
        try:
            expect(product.first).to_be_visible()
        except AssertionError as e:
            # 실패 정보 저장하되 예외는 다시 발생시키지 않음
            logger.error(f"상품 노출 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 노출 확인 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다")
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
            return  # 여기서 종료 (다음 스텝으로 진행)
        
        # 상품 코드 가져오기
        goodscode = search_page.get_product_code(product)
        
        # 장바구니 담기 버튼 존재할 경우 클릭
        if search_page.is_add_to_cart_button_visible(parent, goodscode):
            try:
                search_page.click_add_to_cart_button(parent, goodscode)
                logger.info(f"장바구니 담기 버튼 클릭 완료: {goodscode}")
            except Exception as e:
                logger.warning(f"장바구니 담기 버튼 클릭 실패 (계속 진행): {e}")
        else:
            logger.info(f"장바구니 담기 버튼이 존재하지 않습니다: {goodscode}")
        
        # 상품 클릭
        try:
            new_page = search_page.click_product_and_wait_new_page(product)
            
            # 명시적 페이지 전환 (상태 관리자 패턴)
            browser_session.switch_to(new_page)
            
            # bdd context에 저장 (module_title, goodscode, product_url 등)
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['product_url'] = new_page.url
            
            logger.info(f"{module_title} 모듈 내 상품 확인 및 클릭 완료: {goodscode}")
        except Exception as e:
            logger.error(f"상품 클릭 실패: {e}", exc_info=True)
            record_frontend_failure(browser_session, bdd_context, f"상품 클릭 실패: {str(e)}", "사용자가 모듈 내 상품을 확인하고 클릭한다")
            # goodscode는 저장 (일부 정보라도 보존)
            if 'goodscode' in locals():
                bdd_context.store['goodscode'] = goodscode
            if 'module_title' not in bdd_context.store:
                bdd_context.store['module_title'] = module_title
            
    except Exception as e:
        # 예상치 못한 예외 처리
        logger.error(f"프론트 동작 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "사용자가 모듈 내 상품을 확인하고 클릭한다")
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title

@when(parsers.parse('사용자가 "{module_title}" 모듈 내 상품을 확인하고 클릭한다 (type2)'))
def user_confirms_and_clicks_product_in_module_type2(browser_session, module_title, bdd_context):
    """
    모듈 내 상품 노출 확인하고 클릭 (Atomic POM 조합)
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        module_title: 모듈 타이틀
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        search_page = SearchPage(browser_session.page)
        
        # 모듈로 이동
        module = search_page.get_module_by_title(module_title)
        search_page.scroll_module_into_view(module)
        
        # 모듈 내 상품 찾기
        parent = search_page.get_module_parent(module, 3)
        if module_title == "4.5 이상":
            product = search_page.get_product_in_module_type3(parent)
        else:
            product = search_page.get_product_in_module_type2(parent)
        search_page.scroll_product_into_view(product)
        
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
        goodscode = search_page.get_product_code(product)
        
        # 🔥 가격 정보는 이제 PDP PV 로그에서 추출하므로 프론트엔드에서 수집하지 않음
        # (PDP PV 로그는 상품 페이지 이동 후 수집됨)
        
        # 상품 클릭
        try:
            new_page = search_page.click_product_and_wait_new_page(product)
            
            # 명시적 페이지 전환 (상태 관리자 패턴)
            browser_session.switch_to(new_page)
            
            # bdd context에 저장 (module_title, goodscode, product_url 등)
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['product_url'] = new_page.url
            
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


@then('상품 페이지로 이동되었다')
def product_page_is_opened(browser_session, bdd_context):
    """
    상품 페이지 이동 확인 (검증)
    PDP PV 로그 수집을 위해 networkidle 상태까지 대기
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    import time
    
    try:
        search_page = SearchPage(browser_session.page)
        
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
                search_page.verify_product_code_in_url(url, goodscode)
            else:
                # URL이 없으면 현재 페이지 URL에서 확인
                current_url = browser_session.page.url
                search_page.verify_product_code_in_url(current_url, goodscode)
        except AssertionError as e:
            logger.error(f"상품 페이지 이동 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 페이지 이동 확인 실패: {str(e)}", "상품 페이지로 이동되었다")
            # 계속 진행 (PDP PV 로그 수집은 시도)
        
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
        
    except Exception as e:
        logger.error(f"상품 페이지 이동 확인 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, str(e), "상품 페이지로 이동되었다")
