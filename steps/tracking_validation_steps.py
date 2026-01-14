"""
BDD Step Definitions for Tracking Validation
트래킹 로그 정합성 검증을 위한 재사용 가능한 스텝 정의 (module_config.json만 사용)
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from pytest_bdd import then, parsers
from utils.validation_helpers import validate_event_type_logs, load_module_config

logger = logging.getLogger(__name__)


def _get_common_context(bdd_context):
    """공통 context 값 확인 및 반환"""
    tracker = bdd_context.get('tracker')
    if not tracker:
        raise ValueError("bdd_context에 'tracker'가 없습니다. 네트워크 트래킹을 시작해주세요.")
    
    goodscode = bdd_context.get('goodscode')
    if not goodscode:
        raise ValueError("bdd_context에 'goodscode'가 없습니다.")
    
    module_title = bdd_context.get('module_title')
    if not module_title:
        raise ValueError("bdd_context에 'module_title'가 없습니다.")
    
    price_info = bdd_context.get('price_info', {})
    keyword = bdd_context.get('keyword', '')
    
    frontend_data = price_info.copy() if price_info else {}
    if keyword:
        frontend_data['keyword'] = keyword
    
    return tracker, goodscode, module_title, frontend_data if frontend_data else None


@then("PV 로그가 정합성 검증을 통과해야 함")
def then_pv_logs_should_pass_validation(bdd_context):
    """PV 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # module_config.json에서 PV가 정의되어 있는지 확인
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'pv'
    
    if event_config_key not in module_config_data:
        logger.info(f"모듈 '{module_title}'에 PV가 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info("PV 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='PV',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = "PV 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info("PV 로그 정합성 검증 통과")


@then(parsers.parse('PDP PV 로그가 정합성 검증을 통과해야 함 (TC: {tc_id})'))
def then_pdp_pv_logs_should_pass_validation(tc_id, bdd_context):
    """PDP PV 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    logger.info(f"[TestRail TC: {tc_id}] PDP PV 로그 정합성 검증 시작")
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # TestRail TC 번호를 context에 저장
    bdd_context['testrail_tc_id'] = tc_id
    
    # module_config.json에서 pdp_pv가 정의되어 있는지 확인
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'pdp_pv'
    
    if event_config_key not in module_config_data:
        logger.info(f"[TestRail TC: {tc_id}] 모듈 '{module_title}'에 PDP PV가 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info(f"[TestRail TC: {tc_id}] PDP PV 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='PDP PV',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = f"[TestRail TC: {tc_id}] PDP PV 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info(f"[TestRail TC: {tc_id}] PDP PV 로그 정합성 검증 통과")


@then(parsers.parse('Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: {tc_id})'))
def then_module_exposure_logs_should_pass_validation(tc_id, bdd_context):
    """Module Exposure 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    logger.info(f"[TestRail TC: {tc_id}] Module Exposure 로그 정합성 검증 시작")
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # TestRail TC 번호를 context에 저장
    bdd_context['testrail_tc_id'] = tc_id
    
    # module_config.json에서 module_exposure가 정의되어 있는지 확인
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'module_exposure'
    
    if event_config_key not in module_config_data:
        logger.info(f"[TestRail TC: {tc_id}] 모듈 '{module_title}'에 Module Exposure가 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info(f"[TestRail TC: {tc_id}] Module Exposure 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='Module Exposure',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = f"[TestRail TC: {tc_id}] Module Exposure 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info(f"[TestRail TC: {tc_id}] Module Exposure 로그 정합성 검증 통과")


@then(parsers.parse('Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: {tc_id})'))
def then_product_exposure_logs_should_pass_validation(tc_id, bdd_context):
    """Product Exposure 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    logger.info(f"[TestRail TC: {tc_id}] Product Exposure 로그 정합성 검증 시작")
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # TestRail TC 번호를 context에 저장
    bdd_context['testrail_tc_id'] = tc_id
    
    # module_config.json에서 product_exposure가 정의되어 있는지 확인
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'product_exposure'
    
    if event_config_key not in module_config_data:
        logger.info(f"[TestRail TC: {tc_id}] 모듈 '{module_title}'에 Product Exposure가 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info(f"[TestRail TC: {tc_id}] Product Exposure 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='Product Exposure',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = f"[TestRail TC: {tc_id}] Product Exposure 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info(f"[TestRail TC: {tc_id}] Product Exposure 로그 정합성 검증 통과")


@then(parsers.parse('Product Click 로그가 정합성 검증을 통과해야 함 (TC: {tc_id})'))
def then_product_click_logs_should_pass_validation(tc_id, bdd_context):
    """Product Click 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    logger.info(f"[TestRail TC: {tc_id}] Product Click 로그 정합성 검증 시작")
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # TestRail TC 번호를 context에 저장
    bdd_context['testrail_tc_id'] = tc_id
    
    # module_config.json에서 product_click이 정의되어 있는지 확인
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'product_click'
    
    if event_config_key not in module_config_data:
        logger.info(f"[TestRail TC: {tc_id}] 모듈 '{module_title}'에 Product Click이 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info(f"[TestRail TC: {tc_id}] Product Click 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='Product Click',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = f"[TestRail TC: {tc_id}] Product Click 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info(f"[TestRail TC: {tc_id}] Product Click 로그 정합성 검증 통과")


@then("Product A2C Click 로그가 정합성 검증을 통과해야 함")
def then_product_a2c_click_logs_should_pass_validation(bdd_context):
    """Product A2C Click 로그 정합성 검증 (module_config.json에 정의된 경우만)"""
    tracker, goodscode, module_title, frontend_data = _get_common_context(bdd_context)
    
    # module_config.json에서 product_click이 정의되어 있는지 확인 (Product A2C Click은 product_click과 동일한 구조)
    module_config = load_module_config()
    module_config_data = module_config.get(module_title, {})
    event_config_key = 'product_click'
    
    if event_config_key not in module_config_data:
        logger.info(f"모듈 '{module_title}'에 Product A2C Click이 정의되어 있지 않아 검증을 스킵합니다.")
        return
    
    logger.info("Product A2C Click 로그 정합성 검증 시작")
    success, errors = validate_event_type_logs(
        tracker=tracker,
        event_type='Product A2C Click',
        goodscode=goodscode,
        module_title=module_title,
        frontend_data=frontend_data,
        module_config=module_config
    )
    
    if not success:
        error_message = "Product A2C Click 로그 정합성 검증 실패:\n" + "\n".join(errors)
        logger.error(error_message)
        raise AssertionError(error_message)
    
    logger.info("Product A2C Click 로그 정합성 검증 통과")


@then("모든 트래킹 로그를 JSON 파일로 저장함")
def then_save_all_tracking_logs_to_json(bdd_context):
    """모든 트래킹 로그를 JSON 파일로 저장"""
    tracker = bdd_context.get('tracker')
    if not tracker:
        raise ValueError("bdd_context에 'tracker'가 없습니다.")
    
    goodscode = bdd_context.get('goodscode')
    if not goodscode:
        raise ValueError("bdd_context에 'goodscode'가 없습니다.")
    
    module_title = bdd_context.get('module_title')
    if not module_title:
        raise ValueError("bdd_context에 'module_title'가 없습니다.")
    
    _save_tracking_logs(bdd_context, tracker, goodscode, module_title)


def _save_tracking_logs(bdd_context, tracker, goodscode, module_title):
    """트래킹 로그를 JSON 파일로 저장"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        module_config = load_module_config()
        
        # 모듈별 설정에서 SPM 가져오기
        module_spm = None
        if module_title in module_config:
            common_config = module_config[module_title].get('common', {})
            if common_config:
                module_spm = common_config.get('spm')
        
        # 각 이벤트 타입별 로그 저장
        event_configs = [
            ('pv', 'get_pv_logs', None),
            ('pdp_pv', 'get_pdp_pv_logs', None),
            ('module_exposure', 'get_module_exposure_logs_by_spm', None),
            ('product_exposure', 'get_product_exposure_logs_by_goodscode', None),
            ('product_click', 'get_product_click_logs_by_goodscode', None),
            ('product_a2c_click', 'get_product_a2c_click_logs_by_goodscode', None),
        ]
        
        for event_type, method_name, method_arg in event_configs:
            get_logs_method = getattr(tracker, method_name)
            
            # PV, PDP PV는 goodscode 없이 호출
            if method_name in ['get_pv_logs', 'get_pdp_pv_logs']:
                if method_name == 'get_pv_logs':
                    logs = get_logs_method()
                else:
                    logs = tracker.get_pdp_pv_logs_by_goodscode(goodscode)
            elif method_name == 'get_module_exposure_logs_by_spm':
                # Module Exposure는 spm으로 필터링
                if module_spm:
                    logs = get_logs_method(module_spm)
                else:
                    logs = tracker.get_logs('Module Exposure')
                    logger.warning(f"모듈 '{module_title}'의 SPM 값이 없어 전체 Module Exposure 로그를 사용합니다.")
            elif method_name == 'get_product_exposure_logs_by_goodscode':
                # Product Exposure는 spm으로 추가 필터링
                if module_spm:
                    logs = get_logs_method(goodscode, module_spm)
                else:
                    logs = get_logs_method(goodscode)
            elif method_name == 'get_product_click_logs_by_goodscode':
                # Product Click은 goodscode로만 필터링
                logs = get_logs_method(goodscode)
            else:
                logs = get_logs_method(goodscode)
            
            # 로그 저장
            filepath = Path(f'json/tracking_{event_type}_{goodscode}_{timestamp}.json')
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2, default=str)
            
            if len(logs) > 0:
                logger.info(f"{event_type} 로그 저장 완료: {filepath.resolve()} (로그 개수: {len(logs)})")
            else:
                logger.warning(f"{event_type} 로그가 없어 빈 파일로 저장했습니다: {filepath.resolve()}")
        
        # 전체 로그 저장
        all_logs = []
        all_logs.extend(tracker.get_pv_logs())
        
        if module_spm:
            module_exposure_logs = tracker.get_module_exposure_logs_by_spm(module_spm)
            all_logs.extend(module_exposure_logs)
            logger.info(f"SPM '{module_spm}'로 필터링된 Module Exposure 로그: {len(module_exposure_logs)}개")
        else:
            all_logs.extend(tracker.get_logs('Module Exposure'))
            logger.warning(f"모듈 '{module_title}'의 SPM 값이 없어 전체 Module Exposure 로그를 사용합니다.")
        
        all_logs.extend(tracker.get_pdp_pv_logs_by_goodscode(goodscode))
        if module_spm:
            all_logs.extend(tracker.get_product_exposure_logs_by_goodscode(goodscode, module_spm))
        else:
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
