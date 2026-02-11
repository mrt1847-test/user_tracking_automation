"""
JSON → 구글 시트 변환 스크립트
tracking_all JSON 파일을 구글 시트로 변환하여 기본 틀 생성
"""
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.google_sheets_sync import (
    GoogleSheetsSync,
    flatten_json,
    group_by_event_type,
    TRACKING_TYPE_TO_CONFIG_KEY
)
from utils.common_fields import (
    load_common_fields_by_event,
    get_common_fields_for_event_type,
    normalize_path_for_common,
    common_paths_normalized,
)


# 시트에서 제외할 필드명 목록
EXCLUDE_FIELDS = [
    # 여기에 제외할 필드명을 추가하세요
    # 예: 'timestamp', 'method', 'url' 등
]

# SPM 필드별 점(.) 개수 설정 (해당 개수까지만 유지)
SPM_DOT_COUNT = {
    'spm-cnt': 3,  # spm-cnt는 점 2개까지 유지 (예: gmktpc.searchlist)
    'spm-url': 3,  # spm-url은 점 3개까지 유지 (예: gmktpc.home.searchtop)
    'spm-pre': 3,  # spm-pre는 점 3개까지 유지 (예: gmktpc.home)
}

def truncate_spm_value(value: str, max_dots: int) -> str:
    """
    SPM 값을 점(.)으로 구분하여 지정된 개수까지만 유지
    
    Args:
        value: 원본 SPM 값 (예: 'gmktpc.home.searchtop.dsearchbox.1fbf486aNeD7nd')
        max_dots: 유지할 점(.)의 최대 개수 (예: 3이면 'gmktpc.home.searchtop' 반환)
    
    Returns:
        잘린 SPM 값
    """
    if not isinstance(value, str):
        return value
    
    parts = value.split('.')
    # max_dots 개의 점을 유지하려면 max_dots + 1 개의 부분을 가져와야 함
    # 예: max_dots=3이면 4개 부분 (gmktpc, home, searchtop, dsearchbox) -> 점 3개
    truncated_parts = parts[:max_dots + 1]
    return '.'.join(truncated_parts)

def replace_value_with_placeholder(field_name: str, value: Any) -> Any:
    """
    필드명에 따라 실제 값을 placeholder로 치환
    
    Args:
        field_name: 필드명 (예: 'keyword', 'origin_price', '_p_prod' 등)
        value: 치환할 값
    
    Returns:
        placeholder로 치환된 값 또는 원본 값 (리스트는 JSON 문자열로 변환)
    """
    # SPM 필드의 경우 점 개수에 따라 자르기
    if field_name in SPM_DOT_COUNT:
        max_dots = SPM_DOT_COUNT[field_name]
        return truncate_spm_value(value, max_dots)
    
    # 필드명에 따라 placeholder로 치환
    field_placeholder_map = {
        'query': '<검색어>',
        'origin_price': '<원가>',
        'promotion_price': '<할인가>',
        'coupon_price': '<쿠폰적용가>',
        'server_env': '<environment>',
        '_p_prod': '<상품번호>',
        'x_object_id': '<상품번호>',
        "is_ad": "<is_ad>",
        "trafficType": "<trafficType>",
        "ts": "mandatory",
        "rd": "mandatory",
        "scr": "mandatory",
        "gokey": "mandatory",
        "cna": "mandatory",
        "_p_url": "mandatory",
        "decoded_gokey": "mandatory",
        "pguid": "skip",
        "sguid": "skip",
        "st_page_id": "mandatory",
        "_w": "mandatory",
        "_h": "mandatory",
        "_x": "mandatory",
        "_y": "mandatory",
        "_rate": "mandatory",
        "raw" : "mandatory",
        "params-exp": "mandatory",
        "module_index": "mandatory",
        "ab_buckets": "skip",
        "cache": "mandatory",
        "platformType": ["pc", "mac"],
        "device_model": ["Windows", "Macintosh"],
        "os": ["Windows", "Mac OS X"],
        "os_version": ["win10", "10.15.7"],
        "language": ["ko-KR", "en-US"],
        "o": ["win10", "mac"],
        "w": ["webkit", "chrome"],
        "s": "1280x720",
        "m": "360ee",
        "ism": ["pc", "mac"],
        "b": "mandatory",
        "pvid" : "skip",
        "_p_catalog" : "skip",
        "_p_group" : "skip",
        "utparam-url" : "mandatory",
        "search_session_id" : "skip",
        "_pkgSize" : "skip",
        "pageSize" : "mandatory",
        "match_type" : "skip",
        "cate_leaf_id" : "skip",
        "self_ab_id" : "skip",
    }
    
    if field_name in field_placeholder_map:
        result = field_placeholder_map[field_name]
        # 리스트나 딕셔너리는 JSON 문자열로 변환 (Google Sheets API 호환성)
        if isinstance(result, (list, dict)):
            return json.dumps(result, ensure_ascii=False)
        return result
    
    # 원본 값도 리스트나 딕셔너리인 경우 JSON 문자열로 변환
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    
    return value


def load_tracking_json(file_path: str) -> List[Dict[str, Any]]:
    """
    tracking_all JSON 파일 로드
    
    Args:
        file_path: JSON 파일 경로
        
    Returns:
        트래킹 데이터 배열
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError(f"JSON 파일은 배열 형태여야 합니다: {file_path}")
    
    return data




def process_event_type_payload(event_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    """
    이벤트 타입별로 payload 구조를 config 형식에 맞게 변환
    
    Args:
        event_data: tracking_all JSON의 단일 이벤트 항목
        event_type: 이벤트 타입
        
    Returns:
        config JSON 형식의 데이터 구조
    """
    payload = event_data.get('payload', {})
    
    # 이벤트 타입에 따라 다른 구조 처리
    if event_type == 'Module Exposure':
        # module_exposure는 payload 전체를 사용
        return {'payload': payload}
    
    elif event_type == 'Product Exposure':
        # product_exposure는 decoded_gokey.params + payload 최상위 필드 포함
        result = {}
        
        # payload 최상위 필드 중 단순 값 필드들 추가 (dict/list 제외)
        for key, value in payload.items():
            if key != 'decoded_gokey' and not isinstance(value, (dict, list)):
                result[key] = value
        
        # decoded_gokey.params의 모든 필드 추가 (params 값이 우선)
        if 'decoded_gokey' in payload and isinstance(payload['decoded_gokey'], dict):
            decoded = payload['decoded_gokey']
            if 'params' in decoded:
                params = decoded['params']
                result.update(params)
        
        return result if result else payload
    
    elif event_type == 'Product Click':
        # product_click도 decoded_gokey.params + payload 최상위 필드 포함
        result = {}
        
        # payload 최상위 필드 중 단순 값 필드들 추가 (dict/list 제외)
        for key, value in payload.items():
            if key != 'decoded_gokey' and not isinstance(value, (dict, list)):
                result[key] = value
        
        # decoded_gokey.params의 모든 필드 추가 (params 값이 우선)
        if 'decoded_gokey' in payload and isinstance(payload['decoded_gokey'], dict):
            decoded = payload['decoded_gokey']
            if 'params' in decoded:
                params = decoded['params']
                result.update(params)
        
        return result if result else payload
    
    elif event_type == 'Product Minidetail':
        # product_minidetail은 pdp_pv와 동일하게 payload 전체 사용
        return {'payload': payload}
    
    elif event_type == 'Product ATC Click':
        # product_atc_click도 payload 전체 사용
        return {'payload': payload}
    
    elif event_type == 'PDP PV':
        # pdp_pv는 payload 전체 사용
        return {'payload': payload}
    
    elif event_type in ('PDP Buynow Click', 'PDP ATC Click', 'PDP Gift Click', 'PDP Join Click', 'PDP Rental Click'):
        # PDP 클릭 5종: payload 전체 사용 (gokey, decoded_gokey, _p_url 등)
        return {'payload': payload}
    
    else:
        # 기본적으로 payload 전체 사용
        return {'payload': payload} if payload else {}


def main():
    parser = argparse.ArgumentParser(
        description='tracking_all JSON 파일을 구글 시트로 변환하여 기본 틀 생성'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='입력 tracking_all JSON 파일 경로'
    )
    parser.add_argument(
        '--module',
        type=str,
        required=True,
        help='모듈명 (예: "먼저 둘러보세요")'
    )
    parser.add_argument(
        '--area',
        type=str,
        required=True,
        help='영역명 (SRP, PDP, HOME, CART 등)'
    )
    args = parser.parse_args()
    
    # 하드코딩된 값 설정
    SPREADSHEET_ID = "1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E"
    CREDENTIALS_PATH = str(project_root / 'python-link-test-380006-2868d392d217.json')
    
    # JSON 파일 로드
    print(f"JSON 파일 로드 중: {args.input}")
    tracking_data = load_tracking_json(args.input)
    print(f"총 {len(tracking_data)}개의 이벤트 로드됨")
    
    # 이벤트 타입별로 그룹화
    grouped = group_by_event_type(tracking_data)
    print(f"이벤트 타입: {list(grouped.keys())}")
    
    # 구글 시트 연동 객체 생성
    print(f"구글 시트 연결 중... (Spreadsheet ID: {SPREADSHEET_ID})")
    sync = GoogleSheetsSync(SPREADSHEET_ID, CREDENTIALS_PATH)
    
    # 영역 시트 가져오기 또는 생성 (시트명: 영역만, 예: SRP)
    worksheet_name = args.area
    print(f"워크시트 '{worksheet_name}' 준비 중...")
    worksheet = sync.get_or_create_worksheet(worksheet_name)
    
    # 표 생성 전에 기존 데이터 읽기 (addTable 시 범위 변경 가능성 대비)
    all_values = worksheet.get_all_values()
    data_rows = all_values[1:] if len(all_values) > 1 else []
    kept = [r for r in data_rows if len(r) >= 1 and (r[0].strip() != args.module)]
    
    table_created = sync.ensure_area_table(worksheet, args.area)
    if not table_created:
        print("⚠️ 표(Native Table) 생성 실패/건너뜀. 1행 헤더만 쓰고 데이터는 A2:E에 기록합니다. (위 traceback 확인)")
        sync.ensure_area_header(worksheet)
    
    # 공통 필드 로드
    print("공통 필드 로드 중...")
    common_fields_data = load_common_fields_by_event()
    print(f"공통 필드 로드 완료: {len(common_fields_data)}개 이벤트 타입")
    
    # 이벤트 타입 순서 (config JSON 구조에 맞춤)
    event_type_order = [
        'Module Exposure',
        'Product Exposure',
        'Product Click',
        'Product ATC Click',
        'Product Minidetail',
        'PDP PV',
        'PDP Buynow Click',
        'PDP ATC Click',
        'PDP Gift Click',
        'PDP Join Click',
        'PDP Rental Click',
        'PV',
    ]
    
    # 등록에서 제외할 이벤트 타입 (관련 로직은 유지)
    EXCLUDED_EVENT_TYPES = ['PDP PV', 'PV']
    
    event_type_rows = []
    for event_type in event_type_order:
        if event_type not in grouped:
            continue
        # 등록에서 제외할 이벤트 타입은 건너뛰기
        if event_type in EXCLUDED_EVENT_TYPES:
            print(f"[{event_type}] 등록에서 제외됨 (관련 로직은 유지)")
            continue
        events = grouped[event_type]
        if not events:
            continue
        event_data = events[0]
        config_data = process_event_type_payload(event_data, event_type)
        flattened = flatten_json(config_data, exclude_keys=['timestamp', 'method', 'url'])
        if not flattened:
            continue
        
        # 공통 필드 제외 (모듈별 고유 필드만 남김, 배열 인덱스 무시하고 비교)
        common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
        common_paths_norm = common_paths_normalized(common_fields)
        flattened = [item for item in flattened if normalize_path_for_common(item.get('path')) not in common_paths_norm]
        
        if EXCLUDE_FIELDS:
            flattened = [item for item in flattened if item.get('field') not in EXCLUDE_FIELDS]
        for item in flattened:
            if 'field' in item and 'value' in item:
                item['value'] = replace_value_with_placeholder(item['field'], item['value'])
        event_type_rows.append((event_type, flattened))
        print(f"[{event_type}] {len(flattened)}개 고유 필드 평면화 완료 (공통 필드 제외)")
    
    # 데이터만 A2:E에 기록 (1행은 표 헤더, 건드리지 않음)
    ncols = sync.AREA_NCOLS
    # 컬럼 수를 정확히 ncols로 맞춤 (부족하면 채우고, 초과하면 자름)
    trim = lambda r: (r + [''] * (ncols - len(r)))[:ncols]
    new_rows = sync.build_area_module_rows(args.module, event_type_rows)
    to_write = [trim(r) for r in kept] + [trim(r) for r in new_rows]
    
    sync.clear_area_data_range(worksheet)
    if to_write:
        worksheet.update(to_write, range_name='A2', value_input_option='RAW')
    
    last_row = 1 + len(to_write)
    sync.format_area_data_as_text(worksheet, last_row)
    
    # 공통 필드 시트에 기록 (이미 있으면 업데이트)
    if common_fields_data:
        print("\n공통 필드 시트에 기록 중...")
        sync.write_common_fields_by_event(common_fields_data)
        print("공통 필드 시트 기록 완료")
    
    print(f"\n✅ 완료! 시트 '{worksheet_name}'에 모듈 '{args.module}' Upsert 완료")
    print(f"구글 시트 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == '__main__':
    main()
