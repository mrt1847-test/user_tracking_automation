"""
홈페이지 관련 Step Definitions
진입 / 초기 상태
"""
from pathlib import Path
from pytest_bdd import given, when, then, parsers
from pages.home_page import HomePage
from utils.validation_helpers import detect_area_from_feature_path
import logging
import pytest

logger = logging.getLogger(__name__)


@given("사용자가 G마켓 홈페이지에 접속한다")
def user_navigates_to_homepage(browser_session):
    """
    사용자가 G마켓 홈페이지에 접속
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    home_page = HomePage(browser_session.page)
    home_page.navigate()
    logger.info("홈페이지 접속 완료")


@given("G마켓 홈 페이지에 접속했음")
def given_gmarket_home_page_accessed(browser_session, request, bdd_context):
    """G마켓 홈 페이지에 접속 및 영역 추론"""
    # Feature 파일 경로 또는 테스트 파일 경로에서 영역 추론
    try:
        area = None
        
        # 방법 1: feature fixture에서 feature 파일 경로 가져오기
        if hasattr(request, 'getfixturevalue'):
            try:
                feature = request.getfixturevalue('feature')
                if feature and hasattr(feature, 'filename'):
                    feature_path = str(feature.filename)
                    area = detect_area_from_feature_path(feature_path)
                    if area:
                        bdd_context.store['area'] = area
                        logger.info(f"영역 자동 감지: {area} (Feature: {feature_path})")
            except (pytest.FixtureLookupError, AttributeError):
                pass
        
        # 방법 2: request.node에서 테스트 파일 경로 가져오기 (test_*.py)
        if not area and hasattr(request, 'node'):
            try:
                # request.node.path 또는 request.node.fspath 사용
                test_file_path = None
                if hasattr(request.node, 'path'):
                    test_file_path = request.node.path
                elif hasattr(request.node, 'fspath'):
                    test_file_path = request.node.fspath
                
                if test_file_path:
                    test_file_path = Path(test_file_path)
                    test_file_name = test_file_path.stem  # 파일명에서 확장자 제거
                    
                    # test_*.py 패턴에서 영역 추론 (예: test_srp.py -> SRP, test_lp.py -> LP)
                    if test_file_name.startswith('test_'):
                        area_name = test_file_name.replace('test_', '').upper()
                        # valid_areas 제한 제거 - 모든 영역명 허용
                        area = area_name
                        bdd_context.store['area'] = area
                        logger.info(f"영역 자동 감지: {area} (Test 파일: {test_file_path})")
            except (AttributeError, Exception) as e:
                logger.debug(f"테스트 파일 경로에서 영역 추론 실패: {e}")
        
        # 방법 3: 기본값 사용
        if not area:
            bdd_context.store['area'] = 'SRP'
            logger.warning("영역 기본값 사용: SRP (feature 파일 및 test 파일 경로에서 추론 실패)")
            
    except Exception as e:
        # 오류 발생 시 기본값 사용
        bdd_context.store['area'] = 'SRP'
        logger.warning(f"영역 추론 실패, 기본값 사용: {e}")
    
    home_page = HomePage(browser_session.page)
    home_page.navigate()
    logger.info("G마켓 홈 페이지 접속 완료")


@then("홈페이지가 표시된다")
def homepage_is_displayed(browser_session):
    """
    홈페이지가 올바르게 표시되는지 확인
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    # TODO: 홈페이지 특정 요소 확인 로직 구현
    logger.info("홈페이지 표시 확인")


@given("브라우저가 실행되었다")
def browser_is_launched(browser_session):
    """
    브라우저가 실행된 상태 (자동으로 fixture에서 처리됨)
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    logger.info("브라우저 실행 확인")


@then("페이지가 로드되었다")
def page_is_loaded(browser_session):
    """
    페이지가 완전히 로드되었는지 확인
    
    Args:
        browser_session: BrowserSession 객체 (page 참조 관리)
    """
    browser_session.page.wait_for_load_state("networkidle")
    logger.info("페이지 로드 완료 확인")
