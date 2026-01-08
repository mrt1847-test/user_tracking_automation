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
    'PDP PV': 'get_pdp_pv_logs_by_goodscode',
    'Module Exposure': 'get_module_exposure_logs_by_goodscode',
    'Product Exposure': 'get_product_exposure_logs_by_goodscode',
    'Product Click': 'get_product_click_logs_by_goodscode',
    'Product A2C Click': 'get_product_a2c_click_logs_by_goodscode',
}

# 최상위 필드 패턴 (gokey.params.* 경로에 직접 매핑되는 필드들)
TOP_LEVEL_FIELDS = {'channel_code', 'cguid', 'spm-url', 'spm-pre', 'spm-cnt', 'spm'}

# 이벤트 타입별 params 경로 매핑
EVENT_TYPE_PARAMS_MAP = {
    'Module Exposure': 'params-exp',
    'Product Exposure': 'params-exp',
    'Product Click': 'params-clk',
    'Product A2C Click': 'params-clk',
}

# 이벤트 타입별 module_config.json 키 매핑
EVENT_TYPE_CONFIG_KEY_MAP = {
    'Module Exposure': 'module_exposure',
    'Product Exposure': 'product_exposure',
    'Product Click': 'product_click',
    'Product A2C Click': 'product_click',  # Product Click과 동일한 구조
    'PDP PV': 'pdp_pv',
    'PV': 'pv',  # PV는 특별한 구조가 없을 수 있음
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


def get_module_value(module_title: str, key: str, config: Optional[Dict[str, Any]] = None, event_type: Optional[str] = None) -> Optional[Any]:
    """
    모듈별 설정값 가져오기 (common 섹션 또는 이벤트 타입별 섹션에서 검색)
    
    Args:
        module_title: 모듈 타이틀
        key: 가져올 키 이름 (예: 'spm', 'channel_code')
        config: 모듈 설정 딕셔너리 (None이면 자동 로드)
        event_type: 이벤트 타입 (이벤트 타입별 섹션에서도 검색하려는 경우)
    
    Returns:
        설정값 또는 None
    """
    if config is None:
        config = load_module_config()
    
    module_config = config.get(module_title, {})
    
    # 1. common 섹션에서 먼저 검색
    common_config = module_config.get('common', {})
    if key in common_config:
        return common_config.get(key)
    
    # 2. 이벤트 타입별 섹션에서 검색 (event_type이 제공된 경우)
    if event_type:
        event_config_key = EVENT_TYPE_CONFIG_KEY_MAP.get(event_type)
        if event_config_key:
            event_config = module_config.get(event_config_key, {})
            # params-exp/clk.parsed 내부에서도 검색
            for params_key in ['params-exp', 'params-clk']:
                if params_key in event_config and isinstance(event_config[params_key], dict):
                    parsed = event_config[params_key].get('parsed', {})
                    if key in parsed:
                        return parsed.get(key)
            # 직접 검색
            if key in event_config:
                return event_config.get(key)
    
    # 3. 이전 호환성을 위해 최상위에서도 검색
    return module_config.get(key)


def replace_placeholders(value: Any, goodscode: str, frontend_data: Optional[Dict[str, Any]] = None) -> Any:
    """
    플레이스홀더를 실제 값으로 대체
    
    Args:
        value: 대체할 값 (문자열 또는 다른 타입)
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
    
    Returns:
        플레이스홀더가 대체된 값
    """
    if not isinstance(value, str):
        return value
    
    # <상품번호> → goodscode
    if '<상품번호>' in value:
        value = value.replace('<상품번호>', goodscode)
    
    # <cguid>는 실제 로그에서 가져와야 하므로 그대로 유지 (나중에 비교 시 처리)
    
    # <검색어>, <원가>, <할인가>, <쿠폰적용가>는 frontend_data에서 가져오기
    if frontend_data:
        if '<검색어>' in value and 'keyword' in frontend_data:
            value = value.replace('<검색어>', str(frontend_data['keyword']))
        if '<원가>' in value and 'origin_price' in frontend_data:
            value = value.replace('<원가>', str(frontend_data['origin_price']))
        if '<할인가>' in value and 'promotion_price' in frontend_data:
            value = value.replace('<할인가>', str(frontend_data['promotion_price']))
        if '<쿠폰적용가>' in value and 'coupon_price' in frontend_data:
            value = value.replace('<쿠폰적용가>', str(frontend_data['coupon_price']))
    
    return value


def build_tracking_path(field_name: str, event_type: str) -> str:
    """
    필드명과 이벤트 타입을 기반으로 트래킹 로그 경로 생성
    
    Args:
        field_name: 필드명
        event_type: 이벤트 타입 ('Module Exposure', 'Product Exposure', 'Product Click' 등)
    
    Returns:
        트래킹 로그 경로 (예: 'gokey.params.channel_code' 또는 'gokey.params.params-exp.parsed.gmkt_area_code')
    """
    # 최상위 필드는 gokey.params.* 경로
    if field_name in TOP_LEVEL_FIELDS:
        return f'gokey.params.{field_name}'
    
    # 나머지 필드는 params-exp/clk.parsed.* 경로
    # (utLogMap은 build_expected_from_module_config에서 별도 처리)
    params_key = EVENT_TYPE_PARAMS_MAP.get(event_type, 'params-exp')
    return f'gokey.params.{params_key}.parsed.{field_name}'


def build_expected_from_module_config(
    module_config: Dict[str, Any],
    event_type: str,
    goodscode: str,
    frontend_data: Optional[Dict[str, Any]] = None,
    exclude_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    module_config.json의 이벤트 타입별 필드를 재귀적으로 순회하여 expected_values 딕셔너리 생성
    
    Args:
        module_config: 모듈 설정 딕셔너리 (common, module_exposure, product_exposure 등 포함)
        event_type: 이벤트 타입 ('Module Exposure', 'Product Exposure', 'Product Click' 등)
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
        exclude_fields: 제외할 필드 목록
    
    Returns:
        expected_values 딕셔너리 (경로: 값 형태)
    """
    if exclude_fields is None:
        exclude_fields = []
    
    expected = {}
    
    # 1. common 섹션 처리 (모든 이벤트에 공통)
    common_config = module_config.get('common', {})
    if common_config:
        _process_config_section(common_config, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=True)
    
    # 2. 이벤트 타입별 섹션 처리
    event_config_key = EVENT_TYPE_CONFIG_KEY_MAP.get(event_type)
    if event_config_key:
        event_config = module_config.get(event_config_key, {})
        if event_config:
            _process_config_section(event_config, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False)
    
    return expected


def _process_config_section(
    config_section: Dict[str, Any],
    event_type: str,
    goodscode: str,
    frontend_data: Optional[Dict[str, Any]],
    exclude_fields: List[str],
    expected: Dict[str, Any],
    is_common: bool = False,
    parent_path: str = '',
    is_utlogmap: bool = False
):
    """
    config 섹션을 재귀적으로 처리하여 expected 값 생성
    
    Args:
        config_section: 처리할 config 섹션
        event_type: 이벤트 타입
        goodscode: 상품 번호
        frontend_data: 프론트 데이터
        exclude_fields: 제외할 필드 목록
        expected: 결과를 저장할 딕셔너리 (in-place 수정)
        is_common: common 섹션인지 여부 (common은 최상위 필드로 처리)
        parent_path: 부모 경로 (예: 'params-exp.parsed')
        is_utlogmap: utLogMap 내부인지 여부
    """
    params_key = EVENT_TYPE_PARAMS_MAP.get(event_type, 'params-exp')
    
    for key, value in config_section.items():
        if key in exclude_fields:
            continue
        
        # PDP PV의 경우 payload 최상위에 직접 필드 존재 (pdp_pv 섹션인 경우)
        if event_type == 'PDP PV' and not is_common:
            if isinstance(value, dict):
                # 중첩된 딕셔너리: 재귀 처리 (단, pdp_pv는 평탄한 구조이므로 실제로는 리프 노드만 있을 것)
                _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=is_utlogmap)
            else:
                # 리프 노드: payload 최상위에 직접 필드 (validate_payload에서 payload.get(key)로 접근)
                tracking_path = key
                processed_value = replace_placeholders(value, goodscode, frontend_data)
                expected[tracking_path] = processed_value
            continue
        
        # params-exp/clk 구조 처리
        if key in ['params-exp', 'params-clk'] and isinstance(value, dict):
            parsed = value.get('parsed', {})
            if parsed:
                # params-exp.parsed 또는 params-clk.parsed 내부 처리
                _process_config_section(parsed, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path=key + '.parsed', is_utlogmap=False)
            continue
        
        # utLogMap 객체인 경우
        if key == 'utLogMap' and isinstance(value, dict):
            # utLogMap 내부 필드들을 재귀적으로 처리
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path=parent_path, is_utlogmap=True)
            continue
        
        # 중첩된 딕셔너리 처리
        if isinstance(value, dict):
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path=parent_path + '.' + key if parent_path else key, is_utlogmap=is_utlogmap)
            continue
        
        # 리프 노드: 경로 생성 및 값 처리
        if event_type == 'PDP PV' and not is_common:
            # PDP PV는 payload 최상위에 직접 필드 존재
            # validate_payload에서 payload.get(key)로 접근하므로 그냥 key만 사용
            tracking_path = key
        elif is_common:
            # common 필드는 gokey.params.* 경로
            if key in TOP_LEVEL_FIELDS:
                tracking_path = f'gokey.params.{key}'
            else:
                # common 필드 중 TOP_LEVEL_FIELDS가 아니면 params-exp/clk.parsed.* 경로
                tracking_path = f'gokey.params.{params_key}.parsed.{key}'
        elif is_utlogmap:
            # utLogMap 내부 필드: gokey.params.{params_key}.parsed.utLogMap.parsed.{필드명}
            tracking_path = f'gokey.params.{params_key}.parsed.utLogMap.parsed.{key}'
        elif parent_path:
            # parent_path가 있으면 해당 경로 사용 (예: params-exp.parsed.{필드명})
            if parent_path.startswith('params-'):
                tracking_path = f'gokey.params.{parent_path}.{key}'
            else:
                tracking_path = f'gokey.params.{params_key}.parsed.{parent_path}.{key}' if parent_path else f'gokey.params.{params_key}.parsed.{key}'
        else:
            # 일반 필드: build_tracking_path 사용
            tracking_path = build_tracking_path(key, event_type)
        
        # 플레이스홀더 대체
        processed_value = replace_placeholders(value, goodscode, frontend_data)
        expected[tracking_path] = processed_value


def validate_tracking_logs(
    tracker: NetworkTracker,
    goodscode: str,
    module_title: str,
    rules: Dict[str, Any],
    frontend_data: Optional[Dict[str, Any]] = None,
    module_config: Optional[Dict[str, Any]] = None,
    use_auto_validation: bool = True,
    exclude_fields: Optional[List[str]] = None
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
        use_auto_validation: module_config.json 자동 비교 사용 여부 (기본값: True)
        exclude_fields: 자동 검증에서 제외할 필드 목록
    
    Returns:
        (성공 여부, 에러 메시지 리스트)
    """
    errors = []
    module_rules = rules.get(module_title, {})
    
    # 모듈 설정 로드 (JSON 파일에서)
    if module_config is None:
        module_config = load_module_config()
    
    # 모듈별 설정 가져오기
    module_config_data = module_config.get(module_title, {})
    
    # 각 이벤트 타입별로 검증
    for event_type, rule_key in [
        ('PV', 'pv'),
        ('Module Exposure', 'module_exposure'),
        ('Product Exposure', 'product_exposure'),
        ('Product Click', 'product_click'),
        ('Product A2C Click', 'product_a2c_click'),
    ]:
        # 해당 이벤트 타입의 로그 가져오기
        method_name = EVENT_TYPE_METHODS.get(event_type)
        if not method_name:
            continue
        
        get_logs_method = getattr(tracker, method_name)
        
        # Product Exposure의 경우 spm으로 필터링 (module_config에서 가져온 spm 사용)
        if event_type == 'Product Exposure':
            # module_config의 common 섹션에서 spm 추출
            common_config = module_config_data.get('common', {})
            module_spm = common_config.get('spm') if common_config else None
            if module_spm:
                logs = get_logs_method(goodscode, module_spm)
            else:
                logs = get_logs_method(goodscode)
        else:
            logs = get_logs_method(goodscode)
        
        # validation_rules에서 required 체크
        event_rule = module_rules.get(rule_key, {})
        required = event_rule.get('required', False)
        
        # 필수 이벤트인데 로그가 없으면 에러
        if required and len(logs) == 0:
            errors.append(f"{event_type} 로그가 없습니다. goodscode: {goodscode}")
            continue
        
        # 로그가 없으면 검증 스킵
        if len(logs) == 0:
            continue
        
        # 각 로그에 대해 검증
        for log in logs:
            expected = {}
            
            # 1. 자동 검증: module_config.json의 이벤트 타입별 필드 자동 비교
            if use_auto_validation and module_config_data:
                auto_expected = build_expected_from_module_config(
                    module_config_data,
                    event_type,
                    goodscode,
                    frontend_data,
                    exclude_fields
                )
                expected.update(auto_expected)
            
            # 2. 기존 validation_rules 방식 (병행 지원)
            if 'expected_values' in event_rule:
                rule_expected = event_rule["expected_values"].copy()
                
                # goodscode로 동적 검증
                for key, value in rule_expected.items():
                    if value is None and "_p_prod" in key:
                        rule_expected[key] = goodscode
                    # JSON 파일에서 모듈별 값 가져오기 (예: area_code)
                    elif isinstance(value, str) and value.startswith('@module.'):
                        # @module.area_code 형식으로 지정된 경우
                        config_key = value.replace('@module.', '')
                        module_value = get_module_value(module_title, config_key, module_config, event_type)
                        if module_value is not None:
                            rule_expected[key] = module_value
                
                # 프론트 데이터와 비교
                if "frontend_compare" in event_rule:
                    for frontend_key, tracking_path in event_rule["frontend_compare"].items():
                        if frontend_data and frontend_key in frontend_data:
                            rule_expected[tracking_path] = frontend_data[frontend_key]
                
                # validation_rules의 expected_values가 우선순위가 높음 (덮어쓰기)
                expected.update(rule_expected)
            
            # 검증 수행
            if expected:
                try:
                    tracker.validate_payload(log, expected, goodscode, event_type)
                except AssertionError as e:
                    errors.append(f"{event_type} 로그 검증 실패: {e}")
    
    return len(errors) == 0, errors


