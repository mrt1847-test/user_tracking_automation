"""
프론트엔드 동작 실패 처리 관련 헬퍼 함수
"""
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def capture_frontend_failure_screenshot(browser_session, bdd_context, error_message=None, step_name=None):
    """
    프론트 실패 시점에 즉시 스크린샷을 찍고 bdd_context에 저장
    
    Args:
        browser_session: BrowserSession 객체
        bdd_context: BDD context 객체
        error_message: 에러 메시지 (선택사항)
        step_name: 실패한 스텝 이름 (선택사항)
    
    Returns:
        스크린샷 파일 경로 또는 None
    """
    try:
        if browser_session and hasattr(browser_session, 'page'):
            page = browser_session.page
            if page and not page.is_closed():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 실패 스텝 이름으로 파일명 생성
                if not step_name:
                    step_name = bdd_context.get('failed_step_name', 'unknown_step') if hasattr(bdd_context, 'get') else 'unknown_step'
                safe_step_name = step_name.replace(' ', '_').replace('/', '_').replace('\\', '_')[:50]  # 파일명에 사용 불가능한 문자 제거
                screenshot_path = f"screenshots/frontend_fail_{safe_step_name}_{timestamp}.png"
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                page.screenshot(path=screenshot_path, timeout=2000)
                print(f"[TestRail] 프론트 실패 시점 스크린샷 저장: {screenshot_path}")
                
                # bdd_context에 스크린샷 경로 저장
                if hasattr(bdd_context, '__setitem__'):
                    bdd_context['frontend_failure_screenshot'] = screenshot_path
                elif hasattr(bdd_context, 'store'):
                    bdd_context.store['frontend_failure_screenshot'] = screenshot_path
                
                logger.info(f"프론트 실패 스크린샷 저장 완료: {screenshot_path}")
                return screenshot_path
    except Exception as e:
        print(f"[WARNING] 프론트 실패 스크린샷 저장 실패: {e}")
        logger.error(f"프론트 실패 스크린샷 저장 실패: {e}", exc_info=True)
    
    return None


def record_frontend_failure(browser_session, bdd_context, error_message, step_name):
    """
    프론트 실패를 기록하고 즉시 스크린샷을 찍는 헬퍼 함수
    
    Args:
        browser_session: BrowserSession 객체
        bdd_context: BDD context 객체
        error_message: 에러 메시지
        step_name: 실패한 스텝 이름
    """
    # 실패 플래그 및 정보 설정
    if hasattr(bdd_context, '__setitem__'):
        bdd_context['frontend_action_failed'] = True
        bdd_context['frontend_error_message'] = error_message
        bdd_context['failed_step_name'] = step_name
    elif hasattr(bdd_context, 'store'):
        bdd_context.store['frontend_action_failed'] = True
        bdd_context.store['frontend_error_message'] = error_message
        bdd_context.store['failed_step_name'] = step_name
    
    # 즉시 스크린샷 촬영
    capture_frontend_failure_screenshot(browser_session, bdd_context, error_message, step_name)
