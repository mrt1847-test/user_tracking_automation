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
        # product_exposure는 decoded_gokey.params에서 필요한 부분 추출
        result = {}
        if 'decoded_gokey' in payload and isinstance(payload['decoded_gokey'], dict):
            decoded = payload['decoded_gokey']
            if 'params' in decoded:
                params = decoded['params']
                # 최상위 필드들 추출
                for key in ['channel_code', 'cguid', 'spm-url', 'spm-pre', 'spm-cnt', 'spm']:
                    if key in params:
                        result[key] = params[key]
                
                # params-exp 구조 추가
                if 'params-exp' in params:
                    result['params-exp'] = params['params-exp']
        
        return result if result else payload
    
    elif event_type == 'Product Click':
        # product_click도 유사하게 처리
        result = {}
        if 'decoded_gokey' in payload and isinstance(payload['decoded_gokey'], dict):
            decoded = payload['decoded_gokey']
            if 'params' in decoded:
                params = decoded['params']
                for key in ['channel_code', 'cguid', 'spm-url', 'spm-pre', 'spm-cnt', 'spm']:
                    if key in params:
                        result[key] = params[key]
                
                if 'params-clk' in params:
                    result['params-clk'] = params['params-clk']
        
        return result if result else payload
    
    elif event_type == 'Product ATC Click':
        # product_atc_click도 payload 전체 사용
        return {'payload': payload}
    
    elif event_type == 'PDP PV':
        # pdp_pv는 payload 전체 사용
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
    
    # 워크시트 가져오기 또는 생성
    worksheet_name = args.module
    print(f"워크시트 '{worksheet_name}' 준비 중...")
    worksheet = sync.get_or_create_worksheet(worksheet_name)
    
    # 워크시트 초기화 (기존 데이터 삭제)
    try:
        worksheet.clear()
        print("기존 데이터 삭제 완료")
    except Exception as e:
        print(f"기존 데이터 삭제 중 오류 (무시 가능): {e}")
    
    # 각 이벤트 타입별로 처리
    current_row = 1
    
    # 이벤트 타입 순서 정의 (config JSON 구조에 맞춤)
    event_type_order = [
        'Module Exposure',
        'Product Exposure',
        'Product Click',
        'Product ATC Click',
        'PDP PV',
        'PV',  # PV는 선택적
    ]
    
    for event_type in event_type_order:
        if event_type not in grouped:
            continue
        
        print(f"\n[{event_type}] 처리 중...")
        events = grouped[event_type]
        
        # 첫 번째 이벤트의 payload 사용 (대표값으로)
        if not events:
            continue
        
        # 이벤트 데이터를 config 형식으로 변환
        event_data = events[0]  # 첫 번째 이벤트 사용
        config_data = process_event_type_payload(event_data, event_type)
        
        # JSON 평면화
        flattened = flatten_json(config_data, exclude_keys=['timestamp', 'method', 'url'])
        
        if flattened:
            print(f"  {len(flattened)}개 필드 평면화 완료")
            current_row = sync.write_event_type_table(worksheet, event_type, flattened, current_row)
            print(f"  시트에 작성 완료 (다음 행: {current_row})")
        else:
            print(f"  데이터 없음, 건너뜀")
    
    print(f"\n✅ 완료! 시트 '{worksheet_name}'에 데이터 작성 완료")
    print(f"구글 시트 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == '__main__':
    main()
