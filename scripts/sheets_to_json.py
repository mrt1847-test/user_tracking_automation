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
)
from utils.common_fields import (
    load_common_fields_by_event,
    get_common_fields_for_event_type,
    EVENT_TYPE_TO_CONFIG_KEY,
)


def create_config_json(
    event_data_dict: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    이벤트 타입별 데이터를 config JSON 구조로 변환
    
    Args:
        event_data_dict: {config_key: [{"path":..., "value":...}, ...]} 형태
        
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
    
    # 공통 필드 읽기
    print("공통 필드 읽는 중...")
    common_fields_data = sync.read_common_fields_by_event()
    if common_fields_data:
        print(f"공통 필드 읽기 완료: {len(common_fields_data)}개 이벤트 타입")
    else:
        print("공통 필드 시트가 비어있거나 없습니다. 파일에서 로드 시도...")
        common_fields_data = load_common_fields_by_event()
        if common_fields_data:
            print(f"파일에서 공통 필드 로드 완료: {len(common_fields_data)}개 이벤트 타입")
    
    # 영역 시트에서 모듈 데이터 읽기 (시트명: 영역만, 예: SRP)
    worksheet_name = args.area
    print(f"\n시트 '{worksheet_name}'에서 모듈 '{args.module}' 데이터 읽는 중...")
    try:
        worksheet = sync.get_or_create_worksheet(worksheet_name)
        event_data_dict = sync.read_area_module_data(worksheet, args.module)
        for ck, rows in event_data_dict.items():
            print(f"  ✅ [{ck}]: {len(rows)}개 고유 필드 읽음")
    except Exception as e:
        print(f"❌ 오류: 시트에서 데이터를 읽는 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if not event_data_dict:
        print("❌ 오류: 시트에서 데이터를 읽을 수 없습니다.")
        print("   가능한 원인:")
        print("   1. 시트가 비어있거나")
        print("   2. 해당 모듈 행이 없거나 (모듈명·영역 확인)")
        print("   3. 시트 이름이 올바르지 않습니다")
        print(f"   시트 이름: '{worksheet_name}', 모듈: '{args.module}'")
        sys.exit(1)
    
    # 공통 필드와 모듈 필드 병합
    print("\n공통 필드와 모듈 필드 병합 중...")
    merged_event_data_dict = {}
    for config_key, module_fields in event_data_dict.items():
        # config_key를 이벤트 타입으로 변환
        event_type = None
        for et, ck in EVENT_TYPE_TO_CONFIG_KEY.items():
            if ck == config_key:
                event_type = et
                break
        
        if not event_type:
            # 알 수 없는 이벤트 타입이면 모듈 필드만 사용
            merged_event_data_dict[config_key] = module_fields
            continue
        
        # 공통 필드 가져오기
        common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
        
        # 공통 필드를 평면화된 형태로 변환
        common_flat = []
        for path, field_data in common_fields.items():
            common_flat.append({
                'path': path,
                'value': str(field_data.get('value', ''))
            })
        
        # 모듈 필드와 병합 (모듈 필드가 우선)
        module_paths = {item['path'] for item in module_fields}
        merged_flat = []
        
        # 공통 필드 추가 (모듈 필드에 없는 것만)
        for item in common_flat:
            if item['path'] not in module_paths:
                merged_flat.append(item)
        
        # 모듈 필드 추가 (모든 모듈 필드는 우선)
        merged_flat.extend(module_fields)
        
        merged_event_data_dict[config_key] = merged_flat
        print(f"  ✅ [{config_key}]: 공통 필드 {len(common_flat)}개 + 고유 필드 {len(module_fields)}개 = 총 {len(merged_flat)}개")
    
    # config JSON 구조 생성
    print("\nconfig JSON 구조 생성 중...")
    config_json = create_config_json(merged_event_data_dict)
    
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
