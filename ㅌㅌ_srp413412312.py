import time
import logging
from pages.search_page import SearchPage
from pages.Etc import Etc
import json
from utils.NetworkTracker import NetworkTracker
from utils.validation_helpers import validate_tracking_logs, EVENT_TYPE_METHODS, load_module_config, _find_spm_recursive
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
    srp_page = SearchPage(page)  
    # 네트워크 트래킹 시작 (기존 tracking 로그용)
    tracker = NetworkTracker(page)
    tracker.start()
    
    # testrail 결과 기록시 로그 포함 위해 로그 수집
    output_content = io.StringIO()
    
    # g마켓 홈 으로 이동
    etc.goto()
    # 일반회원 로그인
    # etc.login("t4adbuy01", "Gmkt1004!!")
    # keyword 로 검색창에 검색
    keyword = "물티슈"
    srp_page.search_product(keyword)
    # 먼저 둘러보세요 모듈로 이동 후 확인
    srp_page.search_module_by_title("먼저 둘러보세요")
    # 먼저 둘러보세요 모듈내 광고 상품 곽인
    goodscode = srp_page.assert_item_in_module("먼저 둘러보세요")
    
    # 가격 정보 추출 (상품 클릭 전에 추출해야 함)
    price_info = srp_page.get_product_price_info(goodscode)
    logger.info(f"추출된 가격 정보: {price_info}")
    
    # 상품 클릭후 해당 vip 이동 확인
    srp_page.montelena_goods_click(goodscode)
    
    # 네트워크 요청이 완료될 때까지 대기
    time.sleep(2)
    
    # 네트워크 로그 정합성 검증 (goodscode 기준)
    all_logs = tracker.get_logs()
    logger.info(f"수집된 전체 로그 개수: {len(all_logs)}")
    logger.info(f"검색할 goodscode: {goodscode}")
    
    # 디버깅: 모든 로그 타입별 개수 출력
    log_types = {}
    for log in all_logs:
        log_type = log.get('type', 'Unknown')
        log_types[log_type] = log_types.get(log_type, 0) + 1
    logger.info(f"로그 타입별 개수: {log_types}")
    
    # Module Exposure 관련 URL 확인
    exposure_urls = [log.get('url', '') for log in all_logs if 'exposure' in log.get('url', '').lower() or 'module' in log.get('url', '').lower()]
    if exposure_urls:
        logger.info(f"Exposure/Module 관련 URL 발견: {len(exposure_urls)}개")
        for url in exposure_urls[:5]:  # 최대 5개만 출력
            logger.info(f"  - {url}")
    else:
        logger.warning("Exposure/Module 관련 URL이 수집되지 않았습니다.")
    
    # 프론트에서 데이터 읽기 (가격 정보 및 검색어 포함)
    frontend_data = price_info.copy() if price_info else {}
    frontend_data['keyword'] = keyword
    if frontend_data:
        logger.info(f"정합성 검증에 사용할 frontend_data: {frontend_data}")
    
    # 모듈 설정 로드
    module_config = load_module_config()
    module_title = "먼저 둘러보세요"
    event_spm_map = {}
    gmkt_area_code = None
    if module_title in module_config:
        module_config_data = module_config[module_title]
        
        # Module Exposure: module_exposure 섹션에서 SPM 재귀적으로 찾기
        module_exposure = module_config_data.get('module_exposure', {})
        if module_exposure:
            event_spm_map['module_exposure'] = _find_spm_recursive(module_exposure)
        
        # Product Exposure: product_exposure 섹션에서 SPM 재귀적으로 찾기
        product_exposure = module_config_data.get('product_exposure', {})
        if product_exposure:
            event_spm_map['product_exposure'] = _find_spm_recursive(product_exposure)
        
        # product_exposure 섹션에서 gmkt_area_code 가져오기
        if product_exposure:
            params_exp = product_exposure.get('params-exp', {})
            if params_exp:
                parsed = params_exp.get('parsed', {})
                if parsed:
                    gmkt_area_code = parsed.get('gmkt_area_code')
        
        logger.info(f"모듈 '{module_title}'의 Module Exposure SPM 값: {event_spm_map.get('module_exposure')}")
        logger.info(f"모듈 '{module_title}'의 Product Exposure SPM 값: {event_spm_map.get('product_exposure')}")
        logger.info(f"모듈 '{module_title}'의 gmkt_area_code 값: {gmkt_area_code}")
    
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
            ('module_exposure', 'get_module_exposure_logs_by_spm', None),  # spm으로 필터링된 Module Exposure 로그
            ('product_exposure', 'get_product_exposure_logs_by_goodscode', None),
            ('product_click', 'get_product_click_logs_by_goodscode', None),
            ('product_atc_click', 'get_product_atc_click_logs_by_goodscode', None),
        ]
        
        for event_type, method_name, method_arg in event_configs:
            get_logs_method = getattr(tracker, method_name)
            # PV, PDP PV는 goodscode 없이 호출
            if method_name in ['get_pv_logs', 'get_pdp_pv_logs']:
                logs = get_logs_method()  # PV, PDP PV
            elif method_name == 'get_module_exposure_logs_by_spm':
                # Module Exposure는 해당 섹션에서 찾은 spm으로 필터링
                event_spm = event_spm_map.get('module_exposure')
                if event_spm:
                    logs = get_logs_method(event_spm)
                else:
                    # spm이 없으면 전체 Module Exposure 로그 사용
                    logs = tracker.get_logs('Module Exposure')
                    logger.warning(f"모듈 '{module_title}'의 Module Exposure SPM 값이 없어 전체 Module Exposure 로그를 사용합니다.")
            elif method_name == 'get_product_exposure_logs_by_goodscode':
                # Product Exposure는 product_exposure 섹션에서 찾은 spm으로 필터링 (재귀적으로 찾은 값 사용)
                event_spm = event_spm_map.get('product_exposure')
                if event_spm:
                    logs = get_logs_method(goodscode, event_spm)
                else:
                    logs = get_logs_method(goodscode)
                    logger.warning(f"모듈 '{module_title}'의 Product Exposure SPM 값이 없어 goodscode로만 필터링합니다.")
            elif method_name == 'get_product_click_logs_by_goodscode':
                # Product Click은 goodscode로만 필터링
                logs = get_logs_method(goodscode)
            else:
                logs = get_logs_method(goodscode)  # 나머지는 goodscode로 필터링
            
            # 로그 저장 (0개여도 파일 생성)
            filepath = Path(f'json/tracking_{event_type}_{goodscode}_{timestamp}.json')
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2, default=str)
            if len(logs) > 0:
                logger.info(f"{event_type} 로그 저장 완료: {filepath.resolve()} (로그 개수: {len(logs)})")
            else:
                logger.warning(f"{event_type} 로그가 없어 빈 파일로 저장했습니다: {filepath.resolve()}")
                if event_type == 'module_exposure' and event_spm_map.get('module_exposure'):
                    # Module Exposure 로그가 없을 때 디버깅 정보 출력
                    all_module_logs = tracker.get_logs('Module Exposure')
                    logger.warning(f"전체 Module Exposure 로그 개수: {len(all_module_logs)}")
                    if len(all_module_logs) > 0:
                        # 모든 Module Exposure 로그의 spm 추출하여 출력
                        for idx, log in enumerate(all_module_logs[:5]):  # 최대 5개만 출력
                            log_spm = tracker._extract_spm_from_log(log)
                            logger.warning(f"Module Exposure 로그 #{idx+1}의 spm: {log_spm}")
                        logger.warning(f"필터링하려는 spm: {event_spm_map.get('module_exposure')}")
                        
                        # 필터링 테스트
                        filtered_test = tracker.get_module_exposure_logs_by_spm(event_spm_map.get('module_exposure'))
                        logger.warning(f"필터링 후 Module Exposure 로그 개수: {len(filtered_test)}")
                    else:
                        logger.warning(f"전체 Module Exposure 로그가 없습니다.")
        
        # 전체 로그 저장 (goodscode 필터링된 Product Exposure/Click/PDP PV + 전체 PV + spm 필터링된 Module Exposure)
        all_logs = []
        
        # PV는 goodscode와 무관하므로 전체 로그를 가져옴
        all_logs.extend(tracker.get_pv_logs())
        
        # Module Exposure는 해당 섹션에서 찾은 SPM으로 필터링
        module_exposure_spm = event_spm_map.get('module_exposure')
        if module_exposure_spm:
            module_exposure_logs = tracker.get_module_exposure_logs_by_spm(module_exposure_spm)
            all_logs.extend(module_exposure_logs)
            logger.info(f"SPM '{module_exposure_spm}'로 필터링된 Module Exposure 로그: {len(module_exposure_logs)}개")
        else:
            # spm이 없으면 전체 Module Exposure 로그 사용
            all_logs.extend(tracker.get_logs('Module Exposure'))
            logger.warning(f"모듈 '{module_title}'의 Module Exposure SPM 값이 없어 전체 Module Exposure 로그를 사용합니다.")
        
        # PDP PV, Product 관련 이벤트는 goodscode로 필터링
        all_logs.extend(tracker.get_pdp_pv_logs_by_goodscode(goodscode))
        
        # Product Exposure는 product_exposure 섹션에서 찾은 SPM으로 필터링 (재귀적으로 찾은 값)
        product_exposure_spm = event_spm_map.get('product_exposure')
        if product_exposure_spm:
            product_exposure_logs = tracker.get_product_exposure_logs_by_goodscode(goodscode, product_exposure_spm)
            logger.info(f"SPM '{product_exposure_spm}'로 필터링된 Product Exposure 로그: {len(product_exposure_logs)}개")
        else:
            product_exposure_logs = tracker.get_product_exposure_logs_by_goodscode(goodscode)
            logger.warning(f"모듈 '{module_title}'의 Product Exposure SPM 값이 없어 goodscode로만 필터링합니다.")
        all_logs.extend(product_exposure_logs)
        # Product Click은 goodscode로만 필터링
        all_logs.extend(tracker.get_product_click_logs_by_goodscode(goodscode))
        all_logs.extend(tracker.get_product_atc_click_logs_by_goodscode(goodscode))
        
        if len(all_logs) > 0:
            all_filepath = Path(f'json/tracking_all_{goodscode}_{timestamp}.json')
            all_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(all_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"전체 트래킹 로그 저장 완료: {all_filepath.resolve()} (로그 개수: {len(all_logs)})")
    except Exception as e:
        logger.error(f"트래킹 로그 JSON 저장 중 오류 발생: {e}", exc_info=True)
            
