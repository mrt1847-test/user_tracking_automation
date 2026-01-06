import time
import logging
from pom.SrpPage import Srp
from pom.Etc import Etc
import json
from utils.NetworkTracker import NetworkTracker
import pytest
import io
import contextlib
from datetime import datetime, timedelta
from pathlib import Path

# 로거 설정
logger = logging.getLogger(__name__)

#--
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_01_srp_1(page, keyword, case_id, request):
    # TestRail 케이스 ID를 현재 실행 노드에 저장
    request.node._testrail_case_id = case_id
    etc = Etc(page)
    srp_page = Srp(page)  
    # 네트워크 트래킹 시작
    tracker = NetworkTracker(page)
    tracker.start()
    
    # testrail 결과 기록시 로그 포함 위해 로그 수집
    output_content = io.StringIO()
    
    # g마켓 홈 으로 이동
    etc.goto()
    # 일반회원 로그인
    # etc.login("t4adbuy01", "Gmkt1004!!")
    # keyword 로 검색창에 검색
    srp_page.search_product(keyword)
    # 먼저 둘러보세요 모듈로 이동 후 확인
    srp_page.search_module_by_title("먼저 둘러보세요")
    # 먼저 둘러보세요 모듈내 광고 상품 곽인
    goodscode = srp_page.assert_item_in_module("먼저 둘러보세요")
    # 상품 클릭후 해당 vip 이동 확인
    srp_page.montelena_goods_click(goodscode)
    
    # 네트워크 요청이 완료될 때까지 대기
    time.sleep(2)
    
    # 네트워크 로그 정합성 검증 (goodscode 기준)
    logger.info(f"수집된 전체 로그 개수: {len(tracker.get_logs())}")
    logger.info(f"검색할 goodscode: {goodscode}")
    
    # goodscode 기준으로 PV 로그 확인
    pv_logs = tracker.get_pv_logs_by_goodscode(goodscode)
    logger.info(f"goodscode={goodscode}의 PV 로그 개수: {len(pv_logs)}")
    if len(pv_logs) > 0:
        logger.info(f"PV 로그 예시 URL: {pv_logs[0].get('url')}")
        # 필요시 payload 정합성 검증
        # tracker.validate_payload(pv_logs[0], {"pageId": "expected_value"})
    
    # goodscode 기준으로 Exposure 로그 확인
    exposure_logs = tracker.get_exposure_logs_by_goodscode(goodscode)
    logger.info(f"goodscode={goodscode}의 Exposure 로그 개수: {len(exposure_logs)}")
    if len(exposure_logs) > 0:
        logger.info(f"Exposure 로그 예시 URL: {exposure_logs[0].get('url')}")
    
    # goodscode 기준으로 Click 로그 확인
    click_logs = tracker.get_click_logs_by_goodscode(goodscode)
    logger.info(f"goodscode={goodscode}의 Click 로그 개수: {len(click_logs)}")
    if len(click_logs) > 0:
        logger.info(f"Click 로그 예시 URL: {click_logs[0].get('url')}")
    
    # 최소한 Exposure 또는 Click 로그는 발생해야 함 (해당 상품 관련 로그)
    assert len(exposure_logs) > 0 or len(click_logs) > 0, \
        f"goodscode={goodscode}에 대한 Exposure 또는 Click 로그가 발생해야 합니다. keyword: {keyword}"
    
    # 필터링된 트래킹 로그를 JSON 파일로 저장 (디버깅용 임시)
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Exposure 로그 저장
        if len(exposure_logs) > 0:
            exposure_filepath = Path(f'json/tracking_exposure_{goodscode}_{timestamp}.json')
            exposure_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(exposure_filepath, 'w', encoding='utf-8') as f:
                json.dump(exposure_logs, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Exposure 로그 저장 완료: {exposure_filepath.resolve()}")
        
        # Click 로그 저장
        if len(click_logs) > 0:
            click_filepath = Path(f'json/tracking_click_{goodscode}_{timestamp}.json')
            click_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(click_filepath, 'w', encoding='utf-8') as f:
                json.dump(click_logs, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Click 로그 저장 완료: {click_filepath.resolve()}")
        
        # 전체 로그 저장 (Exposure + Click)
        all_logs = exposure_logs + click_logs
        if len(all_logs) > 0:
            all_filepath = Path(f'json/tracking_all_{goodscode}_{timestamp}.json')
            all_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(all_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"전체 트래킹 로그 저장 완료: {all_filepath.resolve()}")
    except Exception as e:
        logger.error(f"트래킹 로그 JSON 저장 중 오류 발생: {e}", exc_info=True)
            
