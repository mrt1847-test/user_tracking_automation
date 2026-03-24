"""
BDD Step Definitions for SRP Tracking Tests
"""
import logging
import time
from pytest_bdd import given, when, then, parsers
from playwright.sync_api import expect
from pages.search_page import SearchPage
from pages.home_page import HomePage
from pages.list_page import ListPage

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
    """bdd_context의 keyword로 data-montelena-keyword=keyword 요소 존재 검증
    실패 시에도 다음 스텝으로 진행"""
    try:
        keyword = bdd_context.store.get("keyword") or bdd_context.get("keyword")
        if not keyword:
            raise ValueError("bdd_context에 keyword가 없습니다.")
        search_page = SearchPage(browser_session.page)
        search_page.verify_keyword_element_exists(keyword)
        logger.info(f"검색 결과 페이지 표시 확인 (data-montelena-keyword={keyword})")
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
        search_page = SearchPage(browser_session.page)
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


@when(parsers.parse('검색 결과 페이지에서 "{module_title}" 정렬을 선택한다'))
def when_user_selects_sort_tab_typo(browser_session, module_title, bdd_context):
    """Feature 문구 호환(에서서). dweb SRP 정렬/탭 클릭"""
    try:
        search_page = SearchPage(browser_session.page)
        try:
            search_page.close_popup()
        except Exception as e:
            pass
        search_page.select_srp_sort_tab(module_title)
        bdd_context.store['module_title'] = module_title
        logger.info(f"정렬/탭 선택 완료: {module_title}")
    except Exception as e:
        logger.error(f"정렬/탭 선택 실패: {e}", exc_info=True)
        record_frontend_failure(
            browser_session, bdd_context, f"정렬/탭 선택 실패: {str(e)}",
            '검색 결과 페이지에서서 정렬을 선택한다',
        )
        if 'module_title' not in bdd_context.store:
            bdd_context.store['module_title'] = module_title


@when(parsers.parse('사용자가 "{filter_name}" 필터 {nth:d}번째를 적용한다'))
def select_filter(browser_session, filter_name, nth, bdd_context):
    """
    검색 결과 페이지에서 필터를 적용한다.
    """
    try:
        search_page = SearchPage(browser_session.page)
        search_page.select_filter(filter_name, nth)
    except Exception as e:
        logger.error(f"필터 적용 실패: {e}", exc_info=True)
        record_frontend_failure(
            browser_session,
            bdd_context,
            f"필터 적용 실패: {str(e)}",
            "사용자가 필터를 적용한다",
        )


@when(parsers.parse('사용자가 "{module_title}" 모듈 내 {product_index}번째 상품을 확인하고 클릭한다'))
def user_confirms_and_clicks_nth_product_in_module(browser_session, module_title, product_index, bdd_context):
    """
    n번째 상품 클릭 + 스키마/아티팩트용 bdd_context['nth'] 설정 (클릭 성공 여부와 무관하게 먼저 설정).
    """
    bdd_context['nth'] = product_index
    try:
        idx_int = int(product_index)
    except (TypeError, ValueError):
        logger.error("product_index는 정수(또는 정수 문자열)여야 합니다: %s", product_index)
        record_frontend_failure(
            browser_session, bdd_context,
            f"product_index 파싱 실패: {product_index}",
            '사용자가 모듈 내 n번째 상품을 확인하고 클릭한다',
        )
        bdd_context.store['module_title'] = module_title
        return

    try:
        search_page = SearchPage(browser_session.page)
        module = search_page.get_module_by_title(module_title)
        search_page.scroll_module_into_view(module)
        ad_check = search_page.check_ad_item_in_srp_lp_module(module_title)
        parent = search_page.get_module_parent(module, 2)
        product = search_page.get_product_in_module_at(parent, idx_int)
        search_page.scroll_product_into_view(product)
        try:
            expect(product.first).to_be_visible()
        except AssertionError as e:
            logger.error(f"상품 노출 확인 실패: {e}")
            record_frontend_failure(
                browser_session, bdd_context, f"상품 노출 확인 실패: {str(e)}",
                '사용자가 모듈 내 n번째 상품을 확인하고 클릭한다',
            )
            bdd_context.store['module_title'] = module_title
            return

        goodscode = search_page.get_product_code(product)
        if search_page.is_add_to_cart_button_visible(parent, goodscode):
            try:
                search_page.click_add_to_cart_button(parent, goodscode)
            except Exception as e:
                logger.warning(f"장바구니 담기 버튼 클릭 실패 (계속 진행): {e}")

        if ad_check == "F":
            is_ad = search_page.check_ad_tag_in_srp_lp_product(product)
        else:
            is_ad = ad_check

        try:
            new_page = search_page.click_product_and_wait_new_page(product)
            browser_session.switch_to(new_page)
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['is_ad'] = is_ad
            bdd_context.store['product_url'] = new_page.url
            logger.info(f"{module_title} 모듈 내 {idx_int}번째 상품 클릭 완료: {goodscode}")
        except Exception as e:
            logger.error(f"상품 클릭 실패: {e}", exc_info=True)
            record_frontend_failure(
                browser_session, bdd_context, f"상품 클릭 실패: {str(e)}",
                '사용자가 모듈 내 n번째 상품을 확인하고 클릭한다',
            )
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['module_title'] = module_title
    except Exception as e:
        logger.error(f"프론트 동작 중 예외 발생: {e}", exc_info=True)
        record_frontend_failure(
            browser_session, bdd_context, str(e),
            '사용자가 모듈 내 n번째 상품을 확인하고 클릭한다',
        )
        bdd_context.store['module_title'] = module_title


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
        ad_check = search_page.check_ad_item_in_srp_lp_module(module_title)
        
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
        
        if ad_check == "F":
            is_ad = search_page.check_ad_tag_in_srp_lp_product(product)
        else:
            is_ad =ad_check
        
        # 상품 클릭
        try:
            new_page = search_page.click_product_and_wait_new_page(product)
            
            # 명시적 페이지 전환 (상태 관리자 패턴)
            browser_session.switch_to(new_page)
            
            # bdd context에 저장 (module_title, goodscode, product_url 등)
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['is_ad'] = is_ad
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
        ad_check = search_page.check_ad_item_in_srp_lp_module(module_title)
        
        # 모듈 내 상품 찾기
        parent = search_page.get_module_parent(module, 3)
        if module_title == "4.5 이상" or module_title == "MD's Pick":
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

        # 모듈별 광고상품 여부 저장장
        if ad_check == "F":
            is_ad = search_page.check_ad_tag_in_srp_lp_product(product)
        else:
            is_ad =ad_check
        # 상품 클릭s
        try:
            new_page = search_page.click_product_and_wait_new_page(product)
            
            # 명시적 페이지 전환 (상태 관리자 패턴)
            browser_session.switch_to(new_page)
            
            # bdd context에 저장 (module_title, goodscode, product_url 등)
            bdd_context.store['module_title'] = module_title
            bdd_context.store['goodscode'] = goodscode
            bdd_context.store['is_ad'] = is_ad
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


@when(parsers.parse('사용자가 카테고리 아이디 "{category_id}" 로 이동한다'))
def when_user_goes_to_category(browser_session, category_id, bdd_context):
    """
    사용자가 카테고리 아이디로 LP 페이지 이동
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        category_id: 카테고리 ID
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        logger.info(f"LP 페이지 이동 시작: category_id={category_id}")
        list_page = ListPage(browser_session.page)
        list_page.go_to_list_page(category_id)
        bdd_context.store['category_id'] = category_id
        logger.info(f"LP 페이지 이동 완료: category_id={category_id}")
    except Exception as e:
        logger.error(f"LP 페이지 이동 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"LP 페이지 이동 실패: {str(e)}", "사용자가 카테고리 아이디로 이동한다")
        if 'category_id' not in bdd_context.store:
            bdd_context.store['category_id'] = category_id


@given(parsers.parse('사용자가 카테고리 아이디 "{category_id}" 로 이동했다'))
def given_user_went_to_category(browser_session, category_id, bdd_context):
    """
    사용자가 이미 카테고리 아이디로 이동한 상태 (Given)
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        category_id: 카테고리 ID
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        logger.info(f"LP 페이지 상태 확인: category_id={category_id}")
        list_page = ListPage(browser_session.page)
        # 이미 리스트 페이지에 있는지 확인
        current_url = browser_session.page.url
        # 리스트 페이지 URL인지 먼저 확인
        if '/n/list' in current_url:
            try:
                # list_page의 검증 함수 사용
                list_page.verify_category_id_in_url(current_url, category_id)
                # 검증 통과 시 이미 올바른 페이지에 있음
                bdd_context.store['category_id'] = category_id
                logger.info(f"이미 LP 페이지에 있음: category_id={category_id}")
            except AssertionError:
                # 다른 카테고리면 이동 수행
                when_user_goes_to_category(browser_session, category_id, bdd_context)
                # 이동 스텝에서 실패했을 경우 플래그가 설정됨
        else:
            # 리스트 페이지가 아니면 이동 수행
            when_user_goes_to_category(browser_session, category_id, bdd_context)
            # 이동 스텝에서 실패했을 경우 플래그가 설정됨
    except Exception as e:
        logger.error(f"LP 페이지 상태 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"LP 페이지 상태 확인 실패: {str(e)}", "사용자가 카테고리 아이디로 이동했다")
        if 'category_id' not in bdd_context.store:
            bdd_context.store['category_id'] = category_id


@then("리스트 페이지가 표시된다")
def then_list_page_is_displayed(browser_session, bdd_context):
    """
    리스트 페이지가 표시되는지 확인 (검증)
    실패 시에도 다음 스텝으로 진행
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
        bdd_context: BDD context (step 간 데이터 공유용)
    """
    try:
        list_page = ListPage(browser_session.page)
        # list_page의 로드 대기 함수 사용
        list_page.wait_for_list_page_load()
        
        # URL에 리스트 페이지 패턴이 있는지 확인
        current_url = browser_session.page.url
        if '/n/list' not in current_url:
            raise AssertionError(f"리스트 페이지 URL이 아닙니다: {current_url}")
        
        logger.info("리스트 페이지 표시 확인")
    except Exception as e:
        logger.error(f"리스트 페이지 표시 확인 실패: {e}", exc_info=True)
        record_frontend_failure(browser_session, bdd_context, f"리스트 페이지 표시 확인 실패: {str(e)}", "리스트 페이지가 표시된다")

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
        search_page = SearchPage(browser_session.page)
        
        # bdd context에서 값 가져오기 (store 또는 딕셔너리 방식 모두 지원)
        goodscode = bdd_context.store.get('goodscode') or bdd_context.get('goodscode')

        if not goodscode:
            # goodscode가 없으면 이전 스텝에서 실패했을 가능성
            logger.warning("goodscode가 설정되지 않았습니다. 이전 스텝에서 실패했을 수 있습니다.")
            bdd_context['frontend_action_failed'] = True
            bdd_context['frontend_error_message'] = "goodscode가 설정되지 않았습니다."
            return
        
        # 먼저 상품 페이지로 이동할 때까지 대기 (클릭 직후 검증하면 아직 주문내역 URL이라 실패함)
        try:
            browser_session.page.wait_for_url(f"*{goodscode}*", timeout=15000)
            logger.debug("상품 페이지 URL 전환 대기 완료")
        except Exception as e:
            logger.warning(f"URL 전환 대기 실패: {e}")
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

        # 검증 (실패 시 예외 발생) — 네비게이션 대기 후 현재 URL로 확인
        try:
            current_url = browser_session.page.url
            search_page.verify_product_code_in_url(current_url, goodscode)
        except AssertionError as e:
            logger.error(f"상품 페이지 이동 확인 실패: {e}")
            record_frontend_failure(browser_session, bdd_context, f"상품 페이지 이동 확인 실패: {str(e)}", "상품 페이지로 이동되었다")
            # 계속 진행 (PDP PV 로그 수집은 시도)
        logger.info(f"상품 페이지 이동 확인 완료: {goodscode} (PDP PV 로그 수집 대기 완료)")
        
    except Exception as e:
        logger.error(f"상품 페이지 이동 확인 중 예외 발생: {e}", exc_info=True)
