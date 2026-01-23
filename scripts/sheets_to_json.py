"""
구글 시트 → JSON 변환 스크립트
구글 시트 데이터를 읽어서 config JSON 파일 생성/업데이트
"""
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.google_sheets_sync import (
    GoogleSheetsSync,
    unflatten_json,
    TRACKING_TYPE_TO_CONFIG_KEY
)


def build_config_structure(
    event_type_data: Dict[str, Dict[str, Any]],
    event_type: str
) -> Dict[str, Any]:
    """
    평면화된 데이터를 config JSON 구조로 변환
    
    Args:
        event_type_data: 이벤트 타입별 평면화된 데이터
        event_type: 이벤트 타입 (예: "Module Exposure")
        
    Returns:
        config JSON 섹션 구조
    """
    if not event_type_data:
        return {}
    
    # 평면화된 데이터를 중첩 구조로 변환
    unflattened = unflatten_json(event_type_data)
    
    return unflattened


def read_all_event_types(
    sync: GoogleSheetsSync,
    worksheet_name: str
) -> Dict[str, Dict[str, Any]]:
    """
    시트에서 모든 이벤트 타입의 데이터 읽기
    
    Args:
        sync: GoogleSheetsSync 인스턴스
        worksheet_name: 워크시트 이름
        
    Returns:
        {config_key: {path: value}} 형태의 딕셔너리
    """
    worksheet = sync.get_or_create_worksheet(worksheet_name)
    
    result = {}
    
    # 모든 이벤트 타입 순회
    tracking_types = [
        'Module Exposure',
        'Product Exposure',
        'Product Click',
        'Product ATC Click',
        'PDP PV',
        'PV',
    ]
    
    current_row = 1
    
    # 디버깅: 시트의 모든 값 확인
    all_values = worksheet.get_all_values()
    print(f"  [디버깅] 시트 총 행 수: {len(all_values)}")
    if len(all_values) > 0:
        print(f"  [디버깅] 첫 5개 행 샘플:")
        for i, row in enumerate(all_values[:5], 1):
            print(f"    행 {i}: {row[:3]}")  # 처음 3개 컬럼만 출력
    
    for tracking_type in tracking_types:
        # config 키로 변환 (올바른 매핑 사용)
        config_key = TRACKING_TYPE_TO_CONFIG_KEY.get(tracking_type)
        if not config_key:
            print(f"  [디버깅] [{tracking_type}]: config 키를 찾을 수 없음 (건너뜀)")
            continue
        
        print(f"  [디버깅] [{tracking_type}] 검색 시작 (현재 행: {current_row})...")
        # 이벤트 타입 테이블 읽기
        data, next_row = sync.read_event_type_table(worksheet, tracking_type, current_row)
        
        if data:
            result[config_key] = data
            print(f"  ✅ [{tracking_type}] → [{config_key}]: {len(data)}개 필드 읽음")
        else:
            print(f"  ⚠️  [{tracking_type}]: 데이터 없음 (헤더를 찾지 못했거나 데이터가 비어있음)")
        
        current_row = next_row
    
    return result


def create_config_json(
    event_data_dict: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    이벤트 타입별 데이터를 config JSON 구조로 변환
    
    Args:
        event_data_dict: {config_key: [{path, value}]} 형태의 딕셔너리
        
    Returns:
        config JSON 구조
    """
    config = {}
    
    for config_key, flat_data in event_data_dict.items():
        if not flat_data:
            continue
        
        # 평면 데이터를 중첩 구조로 변환
        nested_data = unflatten_json(flat_data)
        
        # config에 추가 (모든 이벤트 타입은 동일하게 처리)
        config[config_key] = nested_data
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description='구글 시트 데이터를 읽어서 config JSON 파일 생성/업데이트'
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
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 JSON 파일 경로 (선택, 기본값: config/{area}/{module}.json)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='기존 파일이 있으면 덮어쓰기 (기본값: False)'
    )
    
    args = parser.parse_args()
    
    # 하드코딩된 값 설정
    SPREADSHEET_ID = "1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E"
    CREDENTIALS_PATH = str(project_root / 'python-link-test-380006-2868d392d217.json')
    
    # 출력 파일 경로 결정
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / 'config' / args.area / f"{args.module}.json"
    
    # 기존 파일 확인
    if output_path.exists() and not args.overwrite:
        print(f"❌ 오류: 파일이 이미 존재합니다: {output_path}")
        print("덮어쓰려면 --overwrite 플래그를 사용하세요.")
        sys.exit(1)
    
    # 구글 시트 연동 객체 생성
    print(f"구글 시트 연결 중... (Spreadsheet ID: {SPREADSHEET_ID})")
    sync = GoogleSheetsSync(SPREADSHEET_ID, CREDENTIALS_PATH)
    
    # 시트에서 데이터 읽기 (시트명: {영역}-{모듈명})
    worksheet_name = f"{args.area}-{args.module}"
    print(f"시트 '{worksheet_name}'에서 데이터 읽는 중...")
    try:
        event_data_dict = read_all_event_types(sync, worksheet_name)
    except Exception as e:
        print(f"❌ 오류: 시트에서 데이터를 읽는 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if not event_data_dict:
        print("❌ 오류: 시트에서 데이터를 읽을 수 없습니다.")
        print("   가능한 원인:")
        print("   1. 시트가 비어있거나")
        print("   2. 이벤트 타입 헤더([Module Exposure] 등)를 찾을 수 없거나")
        print("   3. 시트 이름이 올바르지 않습니다")
        print(f"   시트 이름 확인: '{worksheet_name}'")
        sys.exit(1)
    
    # config JSON 구조 생성
    print("\nconfig JSON 구조 생성 중...")
    config_json = create_config_json(event_data_dict)
    
    # 출력 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON 파일 저장
    print(f"\nJSON 파일 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 완료! config JSON 파일 생성 완료: {output_path}")
    print(f"\n생성된 섹션: {list(config_json.keys())}")


if __name__ == '__main__':
    main()
