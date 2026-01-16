"""
홈페이지 관련 Step Definitions
진입 / 초기 상태
"""
from pathlib import Path
from pytest_bdd import given, when, then, parsers
from pages.home_page import HomePage
from utils.validation_helpers import detect_area_from_feature_path
import logging

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
def given_gmarket_home_page_accessed(browser_session, feature, bdd_context):
    """G마켓 홈 페이지에 접속 및 영역 추론"""
    # Feature 파일 경로에서 영역 추론
    try:
        # pytest-bdd의 feature fixture에서 파일 경로 가져오기
        if feature and hasattr(feature, 'filename'):
            feature_path = feature.filename
            area = detect_area_from_feature_path(feature_path)
            bdd_context.store['area'] = area
            logger.info(f"영역 자동 감지: {area} (Feature: {feature_path})")
        else:
            # 기본값
            bdd_context.store['area'] = 'SRP'
            logger.info("영역 기본값 사용: SRP")
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
