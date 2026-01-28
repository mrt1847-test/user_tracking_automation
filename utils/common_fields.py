"""
이벤트 타입별 공통 필드 관리 유틸리티
공통 필드를 로드하고 모듈별 고유 필드와 병합하는 기능 제공
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.google_sheets_sync import unflatten_json


# 이벤트 타입 매핑: tracking_all JSON의 type → config JSON의 섹션 키
EVENT_TYPE_TO_CONFIG_KEY = {
    'Module Exposure': 'module_exposure',
    'Product Exposure': 'product_exposure',
    'Product Click': 'product_click',
    'Product ATC Click': 'product_atc_click',
    'Product Minidetail': 'product_minidetail',
    'PDP PV': 'pdp_pv',
    'PV': 'pv',
}

# 역매핑: config JSON의 섹션 키 → tracking_all JSON의 type
CONFIG_KEY_TO_EVENT_TYPE = {v: k for k, v in EVENT_TYPE_TO_CONFIG_KEY.items()}


def load_common_fields_by_event(common_fields_path: Optional[Path] = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    이벤트 타입별 공통 필드 파일 로드
    
    Args:
        common_fields_path: 공통 필드 파일 경로 (None이면 기본 경로 사용)
    
    Returns:
        {event_type: {path: {"field": "...", "value": "..."}}}
    """
    if common_fields_path is None:
        # 프로젝트 루트 찾기
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        common_fields_path = project_root / 'config' / '_common_fields_by_event.json'
    
    if not common_fields_path.exists():
        return {}
    
    try:
        with open(common_fields_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARNING] 공통 필드 파일 로드 실패: {common_fields_path} - {e}")
        return {}


def get_common_fields_for_event_type(event_type: str, 
                                     common_fields_data: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None) -> Dict[str, Dict[str, Any]]:
    """
    특정 이벤트 타입의 공통 필드 가져오기
    
    Args:
        event_type: 이벤트 타입 ('Module Exposure', 'Product Click' 등)
        common_fields_data: 공통 필드 데이터 (None이면 파일에서 로드)
    
    Returns:
        {path: {"field": "...", "value": "..."}}
    """
    if common_fields_data is None:
        common_fields_data = load_common_fields_by_event()
    
    # 이벤트 타입을 config 키로 변환
    config_key = EVENT_TYPE_TO_CONFIG_KEY.get(event_type)
    if not config_key:
        return {}
    
    return common_fields_data.get(config_key, {})


def merge_common_fields_with_module_config(module_config: Dict[str, Any],
                                          event_type: str,
                                          common_fields_data: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """
    이벤트 타입별 공통 필드와 모듈별 고유 필드를 병합
    
    병합 순서:
    1. 이벤트 타입별 공통 필드를 먼저 로드
    2. 모듈별 고유 필드로 덮어쓰기 (고유 필드가 우선)
    3. 중첩 구조로 재구성
    
    Args:
        module_config: 모듈별 config 딕셔너리 (이벤트 타입별 섹션 포함)
        event_type: 이벤트 타입 ('Module Exposure', 'Product Click' 등)
        common_fields_data: 공통 필드 데이터 (None이면 파일에서 로드)
    
    Returns:
        병합된 config 딕셔너리
    """
    # 이벤트 타입을 config 키로 변환
    config_key = EVENT_TYPE_TO_CONFIG_KEY.get(event_type)
    if not config_key:
        # 알 수 없는 이벤트 타입이면 모듈 config 그대로 반환
        return module_config.get(config_key, {}) if config_key in module_config else {}
    
    # 공통 필드 가져오기
    common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
    
    # 모듈별 고유 필드 가져오기
    module_event_config = module_config.get(config_key, {})
    
    # 공통 필드를 평면화된 형태로 변환
    common_flat = []
    for path, field_value in common_fields.items():
        # 파일 구조가 단순화되어 값만 저장된 경우와 기존 구조 모두 지원
        if isinstance(field_value, dict):
            value = field_value.get('value', '')
        else:
            value = field_value
        
        common_flat.append({
            'path': path,
            'field': path.split('.')[-1] if '.' in path else path,  # 경로에서 필드명 추출
            'value': value
        })
    
    # 모듈별 고유 필드를 평면화
    from utils.google_sheets_sync import flatten_json
    module_flat = []
    if module_event_config:
        # payload 구조를 유지해야 하는 이벤트 타입들
        # module_exposure, product_atc_click, product_minidetail, pdp_pv 등은 payload 전체를 사용
        payload_preserving_types = ['module_exposure', 'product_atc_click', 'product_minidetail', 'pdp_pv']
        
        if config_key in payload_preserving_types and 'payload' in module_event_config:
            # payload 구조를 유지하여 평면화 (payload.decoded_gokey.params._w 형태)
            module_flat = flatten_json(module_event_config, exclude_keys=['timestamp', 'method', 'url'])
        else:
            # payload가 있으면 payload를, 없으면 event_config 자체를 사용
            data_to_flatten = module_event_config.get('payload', module_event_config)
            module_flat = flatten_json(data_to_flatten, exclude_keys=['timestamp', 'method', 'url'])
    
    # 병합: 모듈 필드가 있으면 모듈 필드 우선, 없으면 공통 필드 사용
    merged_flat = []
    module_paths = {item['path'] for item in module_flat}
    
    # 공통 필드 추가 (모듈 필드에 없는 것만)
    for item in common_flat:
        if item['path'] not in module_paths:
            merged_flat.append(item)
    
    # 모듈 필드 추가 (모든 모듈 필드는 우선)
    merged_flat.extend(module_flat)
    
    # 평면화된 데이터를 중첩 구조로 재구성
    merged_config = unflatten_json(merged_flat)
    
    return merged_config


def build_expected_with_common_fields(module_config: Dict[str, Any],
                                     event_type: str,
                                     goodscode: str,
                                     frontend_data: Optional[Dict[str, Any]] = None,
                                     exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    공통 필드와 모듈 필드를 병합하여 expected_values 딕셔너리 생성
    
    이 함수는 validation_helpers.py의 build_expected_from_module_config와 유사하지만,
    공통 필드를 먼저 병합한 후 expected_values를 생성합니다.
    
    Args:
        module_config: 모듈별 설정 딕셔너리
        event_type: 이벤트 타입
        goodscode: 상품 번호
        frontend_data: 프론트에서 읽은 데이터
        exclude_fields: 제외할 필드 목록
    
    Returns:
        expected_values 딕셔너리
    """
    # 공통 필드와 모듈 필드 병합
    merged_config = merge_common_fields_with_module_config(module_config, event_type)
    
    # 병합된 config에서 expected_values 생성
    from utils.validation_helpers import _process_config_section, replace_placeholders
    
    expected = {}
    exclude_fields = exclude_fields or []
    
    # 병합된 config를 재귀적으로 처리
    _process_config_section(
        merged_config,
        event_type,
        goodscode,
        frontend_data,
        exclude_fields,
        expected,
        is_common=False,
        parent_path='',
        is_utlogmap=False
    )
    
    return expected
