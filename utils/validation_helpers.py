"""
공통 검증 로직을 헬퍼 함수로 제공
이벤트 타입별로 검증 수행
"""
import json
import os
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
    'Product ATC Click': 'get_product_atc_click_logs_by_goodscode',
}

# 최상위 필드 패턴 (gokey.params.* 경로에 직접 매핑되는 필드들)
TOP_LEVEL_FIELDS = {'channel_code', 'cguid', 'spm-url', 'spm-pre', 'spm-cnt', 'spm'}

# 이벤트 타입별 params 경로 매핑
EVENT_TYPE_PARAMS_MAP = {
    'Module Exposure': 'params-exp',
    'Product Exposure': 'params-exp',
    'Product Click': 'params-clk',
    'Product ATC Click': 'params-clk',
}

# 이벤트 타입별 module_config.json 키 매핑
EVENT_TYPE_CONFIG_KEY_MAP = {
    'Module Exposure': 'module_exposure',
    'Product Exposure': 'product_exposure',
    'Product Click': 'product_click',
    'Product ATC Click': 'product_atc_click',  # 별도 섹션으로 분리
    'PDP PV': 'pdp_pv',
    'PV': 'pv',  # PV는 특별한 구조가 없을 수 있음
}


def detect_area_from_feature_path(feature_path: Optional[str] = None) -> str:
    """
    Feature 파일 경로에서 영역(SRP, PDP, HOME, CART 등) 추론
    
    Args:
        feature_path: Feature 파일 경로. None이면 pytest 현재 실행 중인 feature 파일에서 추론 시도
    
    Returns:
        영역명 (예: 'SRP', 'PDP', 'HOME', 'CART')
    """
    if feature_path is None:
        # pytest의 request fixture를 통해 현재 feature 파일 경로 가져오기 시도
        try:
            import pytest
            # pytest의 현재 실행 컨텍스트에서 feature 파일 경로 가져오기
            # pytest_bdd는 request.fixturenames에 'feature'를 포함할 수 있음
            # 하지만 직접 접근이 어려우므로 환경변수나 다른 방법 사용
            # 일단 기본값으로 'SRP' 반환 (나중에 bdd_context에서 전달받도록 수정)
            return 'SRP'
        except:
            return 'SRP'
    
    feature_path = Path(feature_path)
    feature_name = feature_path.stem  # 파일명에서 확장자 제거
    
    # 파일명 패턴: {area}_tracking.feature -> {area}
    if '_tracking' in feature_name:
        area = feature_name.replace('_tracking', '').upper()
        return area
    
    # 기본값
    return 'SRP'


def load_module_config(
    area: Optional[str] = None,
    module_title: Optional[str] = None,
    feature_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    모듈별 설정을 JSON 파일에서 로드
    
    Args:
        area: 영역명 (SRP, PDP, HOME, CART 등). None이면 feature_path에서 추론
        module_title: 모듈 타이틀. None이면 전체 영역의 모든 모듈 로드
        feature_path: Feature 파일 경로 (영역 추론용)
    
    Returns:
        모듈별 설정 딕셔너리 (module_title이 None이면 {module_title: config} 형태)
    """
    # 영역 추론
    if area is None:
        area = detect_area_from_feature_path(feature_path)
    
    config_base_path = Path(__file__).parent.parent / 'config' / area
    
    # module_title이 지정된 경우 해당 파일만 로드
    if module_title:
        config_path = config_base_path / f"{module_title}.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"모듈 설정 파일을 찾을 수 없습니다: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"모듈 설정 JSON 파싱 실패: {e}")
            return {}
    
    # module_title이 None인 경우 해당 영역의 모든 모듈 파일 로드
    result = {}
    if config_base_path.exists():
        for config_file in config_base_path.glob("*.json"):
            module_name = config_file.stem
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    result[module_name] = json.load(f)
            except json.JSONDecodeError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"모듈 설정 JSON 파싱 실패 ({config_file}): {e}")
    
    return result


def get_module_value(module_title: str, key: str, config: Optional[Dict[str, Any]] = None, event_type: Optional[str] = None) -> Optional[Any]:
    """
    모듈별 설정값 가져오기 (이벤트 타입별 섹션에서 검색)
    
    Args:
        module_title: 모듈 타이틀
        key: 가져올 키 이름 (예: 'spm', 'channel_code')
        config: 모듈 설정 딕셔너리 (None이면 자동 로드)
        event_type: 이벤트 타입 (이벤트 타입별 섹션에서 검색)
    
    Returns:
        설정값 또는 None
    """
    if config is None:
        config = load_module_config()
    
    # config가 {module_title: config} 형태인 경우 처리
    if module_title in config and isinstance(config[module_title], dict):
        module_config = config[module_title]
    else:
        # 이미 모듈 설정이 직접 전달된 경우
        module_config = config if isinstance(config, dict) else {}
    
    # 이벤트 타입별 섹션에서 검색 (event_type이 제공된 경우)
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
            # 직접 검색 (이벤트 섹션 최상위에서)
            if key in event_config:
                return event_config.get(key)
    
    # 이전 호환성을 위해 최상위에서도 검색
    return module_config.get(key)


def extract_price_info_from_pdp_pv(tracker: NetworkTracker, goodscode: str) -> Optional[Dict[str, Any]]:
    """
    PDP PV 로그에서 가격 정보 추출
    
    Args:
        tracker: NetworkTracker 인스턴스
        goodscode: 상품 번호
    
    Returns:
        가격 정보 딕셔너리 (origin_price, promotion_price, coupon_price) 또는 None
    """
    pdp_pv_logs = tracker.get_pdp_pv_logs_by_goodscode(goodscode)
    
    if not pdp_pv_logs or len(pdp_pv_logs) == 0:
        return None
    
    # 첫 번째 PDP PV 로그에서 가격 정보 추출
    first_log = pdp_pv_logs[0]
    payload = first_log.get('payload', {})
    
    price_info = {}
    
    # payload 최상위에서 직접 가격 정보 추출
    if 'origin_price' in payload:
        price_info['origin_price'] = str(payload['origin_price'])
    if 'promotion_price' in payload:
        price_info['promotion_price'] = str(payload['promotion_price'])
    if 'coupon_price' in payload:
        price_info['coupon_price'] = str(payload['coupon_price'])
    
    return price_info if price_info else None


def _load_global_config() -> Dict[str, Any]:
    """
    config.json 파일 로드 (환경 설정 등)
    
    Returns:
        config.json 내용 (없으면 빈 딕셔너리)
    """
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _find_spm_recursive(obj: Any, visited: Optional[set] = None) -> Optional[str]:
    """
    재귀적으로 딕셔너리/리스트를 탐색하여 'spm' 키를 찾음
    순환 참조 방지를 위해 visited set 사용
    
    Args:
        obj: 탐색할 객체 (dict, list, 또는 기타)
        visited: 방문한 객체 ID 집합 (순환 참조 방지)
    
    Returns:
        찾은 spm 값의 문자열 변환 또는 None
    """
    if visited is None:
        visited = set()
    
    # 순환 참조 방지 (dict와 list만 체크)
    if isinstance(obj, (dict, list)):
        obj_id = id(obj)
        if obj_id in visited:
            return None
        visited.add(obj_id)
    
    # 딕셔너리인 경우
    if isinstance(obj, dict):
        # 'spm' 키가 있고 값이 있으면 반환
        if 'spm' in obj and obj['spm']:
            return str(obj['spm'])
        
        # 모든 값에 대해 재귀적으로 탐색
        for value in obj.values():
            result = _find_spm_recursive(value, visited)
            if result is not None:
                return result
    
    # 리스트인 경우
    elif isinstance(obj, list):
        for item in obj:
            result = _find_spm_recursive(item, visited)
            if result is not None:
                return result
    
    # 순환 참조 방지를 위해 방문 기록 제거
    if isinstance(obj, (dict, list)):
        visited.discard(id(obj))
    
    return None


def replace_placeholders(value: Any, goodscode: str, frontend_data: Optional[Dict[str, Any]] = None) -> Any:
    """
    플레이스홀더를 실제 값으로 대체
    
    Args:
        value: 대체할 값 (문자열 또는 다른 타입)
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
                     또는 PDP PV 로그에서 추출한 가격 정보
    
    Returns:
        플레이스홀더가 대체된 값
    """
    if not isinstance(value, str):
        return value
    
    # <상품번호> → goodscode
    if '<상품번호>' in value:
        value = value.replace('<상품번호>', goodscode)
    
    # <environment> → config.json의 environment 값
    if '<environment>' in value:
        global_config = _load_global_config()
        environment = global_config.get('environment', '')
        value = value.replace('<environment>', str(environment))
    
    # <cguid>는 실제 로그에서 가져와야 하므로 그대로 유지 (나중에 비교 시 처리)
    
    # <검색어>, <원가>, <할인가>, <쿠폰적용가>는 frontend_data에서 가져오기
    # frontend_data는 이제 PDP PV 로그에서 추출한 가격 정보를 포함할 수 있음
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


# 더 이상 사용하지 않음: 재귀적 탐색으로 전환하여 경로 생성 불필요
# def build_tracking_path(field_name: str, event_type: str) -> str:
#     """
#     필드명과 이벤트 타입을 기반으로 트래킹 로그 경로 생성
#     
#     Args:
#         field_name: 필드명
#         event_type: 이벤트 타입 ('Module Exposure', 'Product Exposure', 'Product Click' 등)
#     
#     Returns:
#         트래킹 로그 경로 (예: 'gokey.params.channel_code' 또는 'gokey.params.params-exp.parsed.gmkt_area_code')
#     """
#     # 최상위 필드는 gokey.params.* 경로
#     if field_name in TOP_LEVEL_FIELDS:
#         return f'gokey.params.{field_name}'
#     
#     # 나머지 필드는 params-exp/clk.parsed.* 경로
#     # (utLogMap은 build_expected_from_module_config에서 별도 처리)
#     params_key = EVENT_TYPE_PARAMS_MAP.get(event_type, 'params-exp')
#     return f'gokey.params.{params_key}.parsed.{field_name}'


def build_expected_from_module_config(
    module_config: Dict[str, Any],
    event_type: str,
    goodscode: str,
    frontend_data: Optional[Dict[str, Any]] = None,
    exclude_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    module_config.json의 이벤트 타입별 필드를 재귀적으로 순회하여 expected_values 딕셔너리 생성
    필드명만 저장하여 validate_payload에서 재귀 탐색으로 찾을 수 있도록 함
    
    Args:
        module_config: 모듈 설정 딕셔너리 (module_exposure, product_exposure 등 포함)
        event_type: 이벤트 타입 ('Module Exposure', 'Product Exposure', 'Product Click' 등)
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
        exclude_fields: 제외할 필드 목록
    
    Returns:
        expected_values 딕셔너리 (필드명: 값 형태)
    """
    if exclude_fields is None:
        exclude_fields = []
    
    expected = {}
    
    # 이벤트 타입별 섹션 처리
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
    필드명만 저장하여 validate_payload에서 재귀 탐색으로 찾을 수 있도록 함
    
    Args:
        config_section: 처리할 config 섹션
        event_type: 이벤트 타입
        goodscode: 상품 번호
        frontend_data: 프론트 데이터
        exclude_fields: 제외할 필드 목록
        expected: 결과를 저장할 딕셔너리 (in-place 수정)
        is_common: common 섹션인지 여부 (사용하지 않지만 호환성을 위해 유지)
        parent_path: 부모 경로 (사용하지 않지만 호환성을 위해 유지)
        is_utlogmap: utLogMap 내부인지 여부 (사용하지 않지만 호환성을 위해 유지)
    """
    for key, value in config_section.items():
        if key in exclude_fields:
            continue
        
        # PDP PV의 경우 payload 최상위에 직접 필드 존재 (pdp_pv 섹션인 경우)
        if event_type == 'PDP PV' and not is_common:
            # payload 키는 건너뛰고 내부 필드만 처리
            if key == 'payload' and isinstance(value, dict):
                # payload 내부 필드들을 재귀적으로 처리 (payload 키는 포함하지 않음)
                _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=is_utlogmap)
            elif isinstance(value, dict):
                # 다른 중첩된 딕셔너리: 재귀 처리
                _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=is_utlogmap)
            else:
                # 리프 노드: payload 최상위에 직접 필드 (validate_payload에서 payload.get(key)로 접근)
                # mandatory/skip 변환 처리
                if isinstance(value, list):
                    # 리스트인 경우 각 요소에 대해 플레이스홀더 대체
                    processed_value = [replace_placeholders(item, goodscode, frontend_data) for item in value]
                elif isinstance(value, str) and value.lower() == "mandatory":
                    processed_value = "__MANDATORY__"  # 특별한 마커
                elif isinstance(value, str) and value.lower() == "skip":
                    processed_value = "__SKIP__"  # 특별한 마커 (검증 스킵)
                else:
                    processed_value = replace_placeholders(value, goodscode, frontend_data)
                expected[key] = processed_value
            continue
        
        # params-exp/clk 구조 처리
        if key in ['params-exp', 'params-clk'] and isinstance(value, dict):
            parsed = value.get('parsed', {})
            if parsed:
                # params-exp.parsed 또는 params-clk.parsed 내부 처리
                _process_config_section(parsed, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=False)
            continue
        
        # utLogMap 객체인 경우
        if key == 'utLogMap' and isinstance(value, dict):
            # utLogMap 내부 필드들을 재귀적으로 처리
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=True)
            continue
        
        # 중첩된 딕셔너리 처리
        if isinstance(value, dict):
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common=False, parent_path='', is_utlogmap=is_utlogmap)
            continue
        
        # 리프 노드: 필드명만 저장 (경로 생성 제거)
        # validate_payload에서 재귀 탐색으로 찾을 수 있도록 필드명만 키로 사용
        if isinstance(value, list):
            # 리스트인 경우 각 요소에 대해 플레이스홀더 대체
            processed_value = [replace_placeholders(item, goodscode, frontend_data) for item in value]
        else:
            # "mandatory" 문자열인 경우 특별한 마커로 저장
            if isinstance(value, str) and value.lower() == "mandatory":
                processed_value = "__MANDATORY__"  # 특별한 마커
            # "skip" 문자열인 경우 특별한 마커로 저장 (검증 스킵)
            elif isinstance(value, str) and value.lower() == "skip":
                processed_value = "__SKIP__"  # 특별한 마커 (검증 스킵)
            else:
                processed_value = replace_placeholders(value, goodscode, frontend_data)
        expected[key] = processed_value


def validate_event_type_logs(
    tracker: NetworkTracker,
    event_type: str,
    goodscode: str,
    module_title: str,
    frontend_data: Optional[Dict[str, Any]] = None,
    module_config: Optional[Dict[str, Any]] = None,
    exclude_fields: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    특정 이벤트 타입의 트래킹 로그 정합성 검증 (module_config.json만 사용)
    
    Args:
        tracker: NetworkTracker 인스턴스
        event_type: 이벤트 타입 ('PV', 'Module Exposure', 'Product Exposure' 등)
        goodscode: 상품 번호
        module_title: 모듈 타이틀
        frontend_data: 프론트에서 읽은 데이터 (price, keyword 등)
        module_config: 모듈별 설정 딕셔너리 (None이면 JSON 파일에서 자동 로드)
        exclude_fields: 검증에서 제외할 필드 목록
    
    Returns:
        (성공 여부, 에러 메시지 리스트)
    """
    errors = []
    
    # 모듈 설정 로드
    if module_config is None:
        module_config = load_module_config()
    
    # 모듈별 설정 가져오기
    # module_config가 {module_title: config} 형태인 경우와 이미 모듈 설정 딕셔너리인 경우 모두 처리
    if module_title in module_config and isinstance(module_config[module_title], dict):
        module_config_data = module_config[module_title]
    else:
        # 이미 모듈 설정 딕셔너리인 경우
        module_config_data = module_config if isinstance(module_config, dict) else {}
    
    # 이벤트 타입별 config 키 확인
    event_config_key = EVENT_TYPE_CONFIG_KEY_MAP.get(event_type)
    if not event_config_key:
        # PV는 특별한 구조가 없을 수 있음
        if event_type != 'PV':
            return True, []  # 알 수 없는 이벤트 타입은 스킵
    
    # module_config.json에 이벤트 타입별 섹션이 없으면 검증 스킵
    if event_config_key and event_config_key not in module_config_data:
        return True, []  # config에 정의되지 않은 이벤트는 검증하지 않음
    
    # 로그 가져오기
    # 이벤트 타입별 섹션에서 spm 값 가져오기 (재귀적으로 탐색)
    module_spm = None
    if event_config_key:
        event_config = module_config_data.get(event_config_key, {})
        module_spm = _find_spm_recursive(event_config)
    
    if event_type == 'PV':
        logs = tracker.get_pv_logs()
    elif event_type == 'PDP PV':
        logs = tracker.get_pdp_pv_logs_by_goodscode(goodscode)
    elif event_type == 'Module Exposure':
        if module_spm:
            logs = tracker.get_module_exposure_logs_by_spm(module_spm)
        else:
            logs = tracker.get_logs('Module Exposure')
    elif event_type == 'Product Exposure':
        if module_spm:
            logs = tracker.get_product_exposure_logs_by_goodscode(goodscode, module_spm)
        else:
            logs = tracker.get_product_exposure_logs_by_goodscode(goodscode)
    elif event_type == 'Product Click':
        logs = tracker.get_product_click_logs_by_goodscode(goodscode)
    elif event_type == 'Product ATC Click':
        logs = tracker.get_product_atc_click_logs_by_goodscode(goodscode)
    else:
        return True, []  # 알 수 없는 이벤트 타입
    
    # module_config.json에 이벤트가 정의되어 있는데 로그가 없으면 실패
    # (프론트엔드 동작 실패로 인한 이벤트 수집 실패)
    if event_config_key and event_config_key in module_config_data:
        if len(logs) == 0:
            error_msg = (
                f"{event_type} 이벤트가 module_config.json에 정의되어 있으나, "
                f"실제 로그가 수집되지 않았습니다. "
                f"프론트엔드 동작이 실패했을 가능성이 있습니다. "
                f"(모듈: {module_title}, goodscode: {goodscode})"
            )
            return False, [error_msg]
    
    # 로그가 없고 config에도 정의되지 않은 경우는 스킵 (정상)
    if len(logs) == 0:
        return True, []
    
    # module_config.json에서 expected 값 생성
    expected = build_expected_from_module_config(
        module_config_data,
        event_type,
        goodscode,
        frontend_data,
        exclude_fields
    )
    
    # expected 값이 없으면 검증 스킵
    if not expected:
        return True, []
    
    # 각 로그에 대해 검증
    for log in logs:
        try:
            tracker.validate_payload(log, expected, goodscode, event_type)
        except AssertionError as e:
            errors.append(f"{event_type} 로그 검증 실패: {e}")
    
    return len(errors) == 0, errors


