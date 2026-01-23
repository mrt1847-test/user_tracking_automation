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


def module_title_to_filename(module_title: str) -> str:
    """
    모듈 타이틀을 파일명에 사용 가능한 문자열로 변환.
    공백, 따옴표, Windows에서 불가한 문자 등 치환.
    """
    if not module_title:
        return "unknown"
    s = str(module_title).strip()
    for old, new in [
        (" ", "_"), ("'", ""), ("/", "_"), ("\\", "_"),
        (":", "_"), ("*", "_"), ("?", "_"), ('"', "_"),
        ("<", "_"), (">", "_"), ("|", "_"),
    ]:
        s = s.replace(old, new)
    return s or "unknown"


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
        config_file_path = config_base_path / f"{module_title}.json"
        if config_file_path.exists():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
    
    # module_title이 None이면 전체 영역의 모든 모듈 로드
    config_dict = {}
    if config_base_path.exists():
        for config_file in config_base_path.glob("*.json"):
            module_name = config_file.stem
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict[module_name] = json.load(f)
    
    return config_dict


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
        # coupon_price가 빈 문자열이거나 None이어도 추가 (빈 값도 유효한 값)
        coupon_price_value = payload['coupon_price']
        price_info['coupon_price'] = str(coupon_price_value) if coupon_price_value is not None else ''
    
    return price_info if price_info else None


def get_event_logs(tracker: NetworkTracker, event_type: str, goodscode: str, module_config_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    이벤트 타입별 로그 수집
    
    Args:
        tracker: NetworkTracker 인스턴스
        event_type: 이벤트 타입
        goodscode: 상품 번호
        module_config_data: 모듈 설정 데이터
    
    Returns:
        로그 리스트
    """
    event_config_key = EVENT_TYPE_CONFIG_KEY_MAP.get(event_type)
    
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
        logs = []
    
    return logs


def _find_spm_recursive(config_section: Dict[str, Any]) -> Optional[str]:
    """
    config 섹션에서 spm 값을 재귀적으로 찾기
    
    Args:
        config_section: 설정 섹션 딕셔너리
    
    Returns:
        spm 값 또는 None
    """
    if isinstance(config_section, dict):
        # 직접 'spm' 키가 있는지 확인
        if 'spm' in config_section:
            spm_value = config_section['spm']
            if isinstance(spm_value, str) and spm_value:
                return spm_value
        
        # 재귀적으로 탐색
        for value in config_section.values():
            if isinstance(value, dict):
                result = _find_spm_recursive(value)
                if result:
                    return result
    
    return None


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
    config 섹션을 재귀적으로 처리하여 expected_values 딕셔너리 생성
    
    Args:
        config_section: 처리할 config 섹션
        event_type: 이벤트 타입
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터
        exclude_fields: 제외할 필드 목록
        expected: 결과를 저장할 딕셔너리
        is_common: 공통 필드인지 여부
        parent_path: 부모 경로 (디버깅용)
        is_utlogmap: utLogMap 섹션인지 여부
    """
    if not isinstance(config_section, dict):
        return
    
    for key, value in config_section.items():
        # exclude_fields에 포함된 필드는 제외
        if key in exclude_fields:
            continue
        
        # utLogMap은 특별 처리 (재귀적으로 처리하되 필드명만 저장)
        if key == 'utLogMap' and isinstance(value, dict):
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common, f"{parent_path}.{key}", is_utlogmap=True)
            continue
        
        # 값이 딕셔너리인 경우 재귀 처리
        if isinstance(value, dict):
            _process_config_section(value, event_type, goodscode, frontend_data, exclude_fields, expected, is_common, f"{parent_path}.{key}", is_utlogmap)
        else:
            # 리프 노드: expected에 추가
            # utLogMap 내부 필드는 그대로 사용, 그 외는 key만 사용
            field_name = key if is_utlogmap else key
            
            # 값 처리 (placeholder 치환)
            processed_value = replace_placeholders(value, goodscode, frontend_data)
            
            expected[field_name] = processed_value


def _load_config() -> Dict[str, Any]:
    """config.json 파일 로드"""
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # config.json이 없으면 기본값 반환
        return {'environment': 'prod'}


def replace_placeholders(value: Any, goodscode: str, frontend_data: Optional[Dict[str, Any]] = None) -> Any:
    """
    값에서 placeholder를 실제 값으로 치환
    
    Args:
        value: 치환할 값
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터 (keyword, origin_price, promotion_price, coupon_price 등)
    
    Returns:
        치환된 값
    """
    if isinstance(value, str):
        # mandatory 값 처리: "mandatory" → "__MANDATORY__"
        if value.strip() == "mandatory":
            return "__MANDATORY__"
        
        # skip 값 처리: "skip" → "__SKIP__"
        if value.strip() == "skip":
            return "__SKIP__"
        
        # <상품번호> placeholder 치환
        if '<상품번호>' in value:
            value = value.replace('<상품번호>', goodscode)
        
        # {goodscode} placeholder 치환 (기존 형식 유지)
        if '{goodscode}' in value:
            value = value.replace('{goodscode}', goodscode)
        
        # <environment> placeholder 치환 (config.json에서 읽어옴)
        if '<environment>' in value:
            config = _load_config()
            environment = config.get('environment', 'prod')
            value = value.replace('<environment>', environment)
        
        # frontend_data에서 값 가져오기
        if frontend_data:
            # <검색어> placeholder 치환 (keyword 또는 category_id 사용)
            if '<검색어>' in value:
                # keyword가 있으면 우선 사용, 없으면 category_id 사용
                search_value = None
                if 'keyword' in frontend_data and frontend_data['keyword']:
                    search_value = str(frontend_data['keyword'])
                elif 'category_id' in frontend_data and frontend_data['category_id']:
                    search_value = str(frontend_data['category_id'])
                
                if search_value:
                    value = value.replace('<검색어>', search_value)
            
            # <원가> placeholder 치환
            if '<원가>' in value and 'origin_price' in frontend_data:
                value = value.replace('<원가>', str(frontend_data['origin_price']))
            
            # <할인가> placeholder 치환
            if '<할인가>' in value and 'promotion_price' in frontend_data:
                value = value.replace('<할인가>', str(frontend_data['promotion_price']))
            
            # <쿠폰적용가> placeholder 치환
            if '<쿠폰적용가>' in value:
                # coupon_price가 frontend_data에 없거나 None이면 빈 문자열로 치환
                coupon_price = frontend_data.get('coupon_price', '')
                value = value.replace('<쿠폰적용가>', str(coupon_price) if coupon_price is not None else '')
            

    return value


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


def find_value_recursive(data: Dict[str, Any], target_key: str) -> Optional[Any]:
    """
    딕셔너리에서 재귀적으로 키를 찾아 값 반환
    
    Args:
        data: 탐색할 딕셔너리
        target_key: 찾을 키
    
    Returns:
        찾은 값 또는 None
    """
    if not isinstance(data, dict):
        return None
    
    # 직접 키가 있는지 확인
    if target_key in data:
        return data[target_key]
    
    # 재귀적으로 탐색
    for value in data.values():
        if isinstance(value, dict):
            result = find_value_recursive(value, target_key)
            if result is not None:
                return result
    
    return None


def validate_event_type_logs(
    tracker: NetworkTracker,
    event_type: str,
    goodscode: str,
    module_title: str,
    frontend_data: Optional[Dict[str, Any]] = None,
    module_config: Optional[Dict[str, Any]] = None,
    exclude_fields: Optional[List[str]] = None
) -> Tuple[bool, List[str], Dict[str, Any]]:
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
        (성공 여부, 에러 메시지 리스트, 통과한 필드와 기대값 딕셔너리)
    """
    errors = []
    all_passed_fields = {}  # 모든 로그에서 통과한 필드와 값 딕셔너리
    
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
            return True, [], {}  # 알 수 없는 이벤트 타입은 스킵
    
    # module_config.json에 이벤트 타입별 섹션이 없으면 검증 스킵
    if event_config_key and event_config_key not in module_config_data:
        return True, [], {}  # config에 정의되지 않은 이벤트는 검증하지 않음
    
    # 로그 가져오기
    logs = get_event_logs(tracker, event_type, goodscode, module_config_data)
    
    # 로그가 없고 config에도 정의되지 않은 경우는 스킵 (정상)
    if len(logs) == 0:
        return True, [], {}
    
    # module_config.json에서 expected 값 생성
    expected = build_expected_from_module_config(
        module_config_data,
        event_type,
        goodscode,
        frontend_data,
        exclude_fields
    )
    
    # 각 로그에 대해 검증
    for log in logs:
        # expected 값 검증 (AssertionError를 잡아서 에러 리스트에 추가)
        # validate_payload는 전체 로그 객체를 받아 내부에서 log.get('payload')로 추출함
        try:
            result = tracker.validate_payload(log, expected, goodscode, event_type)
            # result가 튜플인 경우 (성공 여부, 통과한 필드와 값 딕셔너리)
            if isinstance(result, tuple) and len(result) == 2:
                _, passed_fields_dict = result
                # 통과한 필드와 값 딕셔너리에 병합 (나중 로그의 값이 우선)
                if isinstance(passed_fields_dict, dict):
                    all_passed_fields.update(passed_fields_dict)
        except AssertionError as e:
            errors.append(str(e))
    
    # 에러가 있으면 실패
    if errors:
        return False, errors, all_passed_fields
    
    return True, [], all_passed_fields
