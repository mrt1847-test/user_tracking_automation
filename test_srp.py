import time
import logging
from pom.SrpPage import Srp
from pom.Etc import Etc
import json
from utils.NetworkTracker import NetworkTracker
from utils.validation_helpers import validate_tracking_logs, EVENT_TYPE_METHODS, load_module_config
from config.validation_rules import SRP_VALIDATION_RULES
import pytest
import io
import contextlib
from datetime import datetime, timedelta
from pathlib import Path


# 로거 설정
logger = logging.getLogger(__name__)


def test_01_srp_1(page):
    # TestRail 케이스 ID를 현재 실행 노드에 저장

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
    srp_page.search_product("물티슈")
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
    
    # 프론트에서 데이터 읽기 (사용자가 직접 구현)
    # 예시: frontend_data = {"price": "50000", "keyword": keyword, "goodscode": goodscode}
    frontend_data = None  # 사용자가 직접 구현한 함수로 프론트 데이터 추출
    
    # 모듈 설정 로드
    module_config = load_module_config()
    module_title = "먼저 둘러보세요"
    module_spm = None
    if module_title in module_config:
        module_spm = module_config[module_title].get('spm')
        logger.info(f"모듈 '{module_title}'의 SPM 값: {module_spm}")
    
    # 정합성 검증 (간결하게)
    # module_config는 None이면 자동으로 JSON 파일에서 로드됨
    success, errors = validate_tracking_logs(
        tracker=tracker,
        goodscode=goodscode,
        module_title=module_title,
        rules=SRP_VALIDATION_RULES,
        frontend_data=frontend_data
    )
    
    # assert success, f"트래킹 데이터 정합성 검증 실패:\n" + "\n".join(errors)
    
    # 디버깅용: 필터링된 트래킹 로그를 JSON 파일로 저장 (유지)
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 각 이벤트 타입별 로그 저장
        # PV와 Module Exposure는 goodscode와 무관하므로 전체 로그를 가져옴
        event_configs = [
            ('pv', 'get_pv_logs', None),  # goodscode 없이 전체 PV 로그 (PDP PV 제외)
            ('pdp_pv', 'get_pdp_pv_logs', None),  # goodscode 없이 전체 PDP PV 로그
            ('module_exposure', 'get_logs', 'Module Exposure'),  # goodscode 없이 전체 Module Exposure 로그
            ('product_exposure', 'get_product_exposure_logs_by_goodscode', None),
            ('product_click', 'get_product_click_logs_by_goodscode', None),
            ('product_a2c_click', 'get_product_a2c_click_logs_by_goodscode', None),
        ]
        
        for event_type, method_name, method_arg in event_configs:
            get_logs_method = getattr(tracker, method_name)
            # PV, PDP PV, Module Exposure는 goodscode 없이 호출, 나머지는 goodscode로 필터링
            if method_arg:
                logs = get_logs_method(method_arg)  # Module Exposure
            elif method_name in ['get_pv_logs', 'get_pdp_pv_logs']:
                logs = get_logs_method()  # PV, PDP PV
            else:
                logs = get_logs_method(goodscode)  # 나머지는 goodscode로 필터링
            
            if len(logs) > 0:
                filepath = Path(f'json/tracking_{event_type}_{goodscode}_{timestamp}.json')
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"{event_type} 로그 저장 완료: {filepath.resolve()} (로그 개수: {len(logs)})")
        
        # 전체 로그 저장 (goodscode 필터링된 Product Exposure/Click/PDP PV + 전체 PV + spm 필터링된 Module Exposure)
        all_logs = []
        
        # PV는 goodscode와 무관하므로 전체 로그를 가져옴
        all_logs.extend(tracker.get_pv_logs())
        
        # Module Exposure는 spm 값으로 필터링 (모듈별 config에서 가져온 spm 사용)
        if module_spm:
            module_exposure_logs = tracker.get_module_exposure_logs_by_spm(module_spm)
            all_logs.extend(module_exposure_logs)
            logger.info(f"SPM '{module_spm}'로 필터링된 Module Exposure 로그: {len(module_exposure_logs)}개")
        else:
            # spm이 없으면 전체 Module Exposure 로그 사용
            all_logs.extend(tracker.get_logs('Module Exposure'))
            logger.warning(f"모듈 '{module_title}'의 SPM 값이 없어 전체 Module Exposure 로그를 사용합니다.")
        
        # PDP PV, Product 관련 이벤트는 goodscode로 필터링
        all_logs.extend(tracker.get_pdp_pv_logs_by_goodscode(goodscode))
        all_logs.extend(tracker.get_product_exposure_logs_by_goodscode(goodscode))
        all_logs.extend(tracker.get_product_click_logs_by_goodscode(goodscode))
        all_logs.extend(tracker.get_product_a2c_click_logs_by_goodscode(goodscode))
        
        if len(all_logs) > 0:
            all_filepath = Path(f'json/tracking_all_{goodscode}_{timestamp}.json')
            all_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(all_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"전체 트래킹 로그 저장 완료: {all_filepath.resolve()} (로그 개수: {len(all_logs)})")
    except Exception as e:
        logger.error(f"트래킹 로그 JSON 저장 중 오류 발생: {e}", exc_info=True)
            
