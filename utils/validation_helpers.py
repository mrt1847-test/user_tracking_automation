"""
공통 검증 로직을 헬퍼 함수로 제공
이벤트 타입별로 검증 수행
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from utils.NetworkTracker import NetworkTracker

# 이벤트 타입과 메서드 이름 매핑
EVENT_TYPE_METHODS = {
    'PV': 'get_pv_logs_by_goodscode',
    'Module Exposure': 'get_module_exposure_logs_by_goodscode',
    'Product Exposure': 'get_product_exposure_logs_by_goodscode',
    'Product Click': 'get_product_click_logs_by_goodscode',
    'Product A2C Click': 'get_product_a2c_click_logs_by_goodscode',
}


def load_module_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    모듈별 설정을 JSON 파일에서 로드
    
    Args:
        config_path: JSON 파일 경로 (기본값: config/module_config.json)
    
    Returns:
        모듈별 설정 딕셔너리
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'module_config.json'
    else:
        config_path = Path(config_path)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"모듈 설정 JSON 파싱 실패: {e}")
        return {}


def get_module_value(module_title: str, key: str, config: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    모듈별 설정값 가져오기
    
    Args:
        module_title: 모듈 타이틀
        key: 가져올 키 이름 (예: 'area_code')
        config: 모듈 설정 딕셔너리 (None이면 자동 로드)
    
    Returns:
        설정값 또는 None
    """
    if config is None:
        config = load_module_config()
    
    module_config = config.get(module_title, {})
    return module_config.get(key)


def validate_tracking_logs(
    tracker: NetworkTracker,
    goodscode: str,
    module_title: str,
    rules: Dict[str, Any],
    frontend_data: Optional[Dict[str, Any]] = None,
    module_config: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    트래킹 로그 정합성 검증 (이벤트 타입별)
    
    Args:
        tracker: NetworkTracker 인스턴스
        goodscode: 상품 번호
        module_title: 모듈 타이틀 (검증 규칙 선택용)
        rules: 검증 규칙 딕셔너리
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
        module_config: 모듈별 설정 딕셔너리 (None이면 JSON 파일에서 자동 로드)
    
    Returns:
        (성공 여부, 에러 메시지 리스트)
    """
    errors = []
    module_rules = rules.get(module_title, {})
    
    # 모듈 설정 로드 (JSON 파일에서)
    if module_config is None:
        module_config = load_module_config()
    
    # 각 이벤트 타입별로 검증
    for event_type, rule_key in [
        ('PV', 'pv'),
        ('Module Exposure', 'module_exposure'),
        ('Product Exposure', 'product_exposure'),
        ('Product Click', 'product_click'),
        ('Product A2C Click', 'product_a2c_click'),
    ]:
        if rule_key not in module_rules:
            continue
        
        event_rule = module_rules[rule_key]
        required = event_rule.get('required', False)
        
        # 해당 이벤트 타입의 로그 가져오기
        method_name = EVENT_TYPE_METHODS.get(event_type)
        if not method_name:
            continue
        
        get_logs_method = getattr(tracker, method_name)
        logs = get_logs_method(goodscode)
        
        # 필수 이벤트인데 로그가 없으면 에러
        if required and len(logs) == 0:
            errors.append(f"{event_type} 로그가 없습니다. goodscode: {goodscode}")
            continue
        
        # 각 로그에 대해 검증
        if 'expected_values' in event_rule:
            for log in logs:
                expected = event_rule["expected_values"].copy()
                
                # goodscode로 동적 검증
                for key, value in expected.items():
                    if value is None and "_p_prod" in key:
                        expected[key] = goodscode
                    # JSON 파일에서 모듈별 값 가져오기 (예: area_code)
                    elif isinstance(value, str) and value.startswith('@module.'):
                        # @module.area_code 형식으로 지정된 경우
                        config_key = value.replace('@module.', '')
                        module_value = get_module_value(module_title, config_key, module_config)
                        if module_value is not None:
                            expected[key] = module_value
                
                # 프론트 데이터와 비교
                if "frontend_compare" in event_rule:
                    for frontend_key, tracking_path in event_rule["frontend_compare"].items():
                        if frontend_data and frontend_key in frontend_data:
                            expected[tracking_path] = frontend_data[frontend_key]
                
                try:
                    tracker.validate_payload(log, expected)
                except AssertionError as e:
                    errors.append(f"{event_type} 로그 검증 실패: {e}")
    
    return len(errors) == 0, errors


