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
    
    # payload 구조를 유지해야 하는 이벤트 타입들
    # module_exposure, product_atc_click, product_minidetail, pdp_pv 등은 payload 전체를 사용
    payload_preserving_types = ['module_exposure', 'product_atc_click', 'product_minidetail', 'pdp_pv']
    
    for config_key, flat_data in event_data_dict.items():
        if not flat_data:
            continue
        
        # 평면 데이터를 중첩 구조로 변환
        nested_data = unflatten_json(flat_data)
        
        # payload 구조를 유지해야 하는 이벤트 타입 처리
        if config_key in payload_preserving_types:
            # payload가 이미 최상위에 있으면 그대로 사용
            if 'payload' in nested_data:
                config[config_key] = nested_data
            else:
                # payload가 없으면 payload 객체로 감싸기
                # 이는 시트에 저장된 모듈 필드의 경로가 payload. prefix 없이 저장된 경우를 처리
                config[config_key] = {'payload': nested_data}
        else:
            # 다른 이벤트 타입은 그대로 사용
            config[config_key] = nested_data
    
    return config


def merge_module_with_common(
    event_data_dict: Dict[str, List[Dict[str, Any]]],
    common_fields_data: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    모듈 필드와 공통 필드를 병합 (payload prefix 등 처리 포함).
    """
    merged_event_data_dict = {}
    payload_preserving_types = ['module_exposure', 'product_atc_click', 'product_minidetail', 'pdp_pv']

    for config_key, module_fields in event_data_dict.items():
        event_type = None
        for et, ck in EVENT_TYPE_TO_CONFIG_KEY.items():
            if ck == config_key:
                event_type = et
                break

        if not event_type:
            merged_event_data_dict[config_key] = module_fields
            continue

        common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
        common_flat = []
        for path, field_data in common_fields.items():
            common_flat.append({
                'path': path,
                'value': str(field_data.get('value', ''))
            })

        module_paths = {item['path'] for item in module_fields}
        merged_flat = []
        is_payload_preserving = config_key in payload_preserving_types

        for item in common_flat:
            path = item['path']
            if is_payload_preserving:
                if not path.startswith('payload.'):
                    payload_path = f'payload.{path}'
                    if payload_path not in module_paths:
                        item = item.copy()
                        item['path'] = payload_path
                        merged_flat.append(item)
                else:
                    if path not in module_paths:
                        merged_flat.append(item)
            else:
                if path not in module_paths:
                    merged_flat.append(item)

        if is_payload_preserving:
            for item in module_fields:
                path = item['path']
                if not path.startswith('payload.'):
                    item = item.copy()
                    item['path'] = f'payload.{path}'
                merged_flat.append(item)
        else:
            merged_flat.extend(module_fields)

        merged_event_data_dict[config_key] = merged_flat

    return merged_event_data_dict


def convert_module_to_json(
    sync: GoogleSheetsSync,
    worksheet: Any,
    area: str,
    module: str,
    output_path: Path,
    overwrite: bool,
    common_fields_data: Dict[str, Any],
    verbose: bool = True,
) -> bool:
    """
    시트에서 한 모듈 데이터를 읽어 config JSON 파일로 저장.
    Returns:
        성공 시 True, 실패 시 False
    """
    if output_path.exists() and not overwrite:
        if verbose:
            print(f"  [건너뜀] 이미 존재: {output_path} (--overwrite 사용 시 덮어쓰기)")
        return False

    event_data_dict = sync.read_area_module_data(worksheet, module)
    if not event_data_dict:
        if verbose:
            print(f"  [건너뜀] 모듈 '{module}' 데이터 없음")
        return False

    merged = merge_module_with_common(event_data_dict, common_fields_data)
    config_json = create_config_json(merged)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, ensure_ascii=False, indent=2)
    if verbose:
        print(f"  [OK] {output_path} (섹션: {list(config_json.keys())})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='구글 시트 데이터를 읽어서 config JSON 파일 생성/업데이트'
    )
    parser.add_argument(
        '--sheet',
        action='store_true',
        help='시트 단위 변환: 해당 영역 시트 전체를 읽어 모듈별로 JSON 파일 생성 (--area만 필요)'
    )
    parser.add_argument(
        '--module',
        type=str,
        default=None,
        help='모듈명 (예: "먼저 둘러보세요"). --sheet 사용 시 무시됨'
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
        help='출력 JSON 파일 경로 (단일 모듈 모드에서만 사용, 기본값: config/{area}/{module}.json)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='기존 파일이 있으면 덮어쓰기 (기본값: False)'
    )

    args = parser.parse_args()

    # 시트 단위 변환 모드: --area만 필요
    if args.sheet:
        if args.output:
            print("경고: --sheet 모드에서는 --output이 무시됩니다. 각 모듈은 config/{area}/{모듈명}.json에 저장됩니다.")
        _run_sheet_mode(args)
        return

    # 단일 모듈 모드: --module 필수
    if not args.module:
        print("오류: 단일 모듈 변환 시 --module이 필요합니다. 시트 전체 변환은 --sheet 를 사용하세요.")
        sys.exit(1)

    _run_single_module_mode(args)


def _run_sheet_mode(args: Any) -> None:
    """시트 전체를 읽어 모듈별로 config JSON 파일 생성."""
    SPREADSHEET_ID = "1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E"
    CREDENTIALS_PATH = str(project_root / 'python-link-test-380006-2868d392d217.json')

    print(f"구글 시트 연결 중... (Spreadsheet ID: {SPREADSHEET_ID})")
    sync = GoogleSheetsSync(SPREADSHEET_ID, CREDENTIALS_PATH)

    print("공통 필드 읽는 중...")
    common_fields_data = sync.read_common_fields_by_event()
    if not common_fields_data:
        common_fields_data = load_common_fields_by_event()
    if common_fields_data:
        print(f"공통 필드 로드 완료: {len(common_fields_data)}개 이벤트 타입")
    else:
        print("공통 필드 없음. 모듈 필드만 사용합니다.")

    worksheet_name = args.area
    print(f"\n시트 '{worksheet_name}' 전체 변환 (모듈별 JSON 생성)...")
    try:
        worksheet = sync.get_or_create_worksheet(worksheet_name)
        modules = sync.list_area_modules(worksheet)
    except Exception as e:
        print(f"오류: 시트 접근 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not modules:
        print("해당 시트에 모듈 데이터가 없습니다.")
        sys.exit(0)

    print(f"모듈 {len(modules)}개 발견: {modules}")
    out_dir = project_root / 'config' / args.area
    out_dir.mkdir(parents=True, exist_ok=True)
    success = 0
    for module in modules:
        output_path = out_dir / f"{module}.json"
        if convert_module_to_json(
            sync, worksheet, args.area, module,
            output_path, args.overwrite, common_fields_data,
            verbose=True,
        ):
            success += 1
    print(f"\n완료: {success}/{len(modules)}개 모듈 JSON 생성 -> {out_dir}")


def _run_single_module_mode(args: Any) -> None:
    """기존처럼 단일 모듈만 변환."""
    SPREADSHEET_ID = "1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E"
    CREDENTIALS_PATH = str(project_root / 'python-link-test-380006-2868d392d217.json')

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / 'config' / args.area / f"{args.module}.json"

    if output_path.exists() and not args.overwrite:
        print(f"오류: 파일이 이미 존재합니다: {output_path}")
        print("덮어쓰려면 --overwrite 플래그를 사용하세요.")
        sys.exit(1)

    print(f"구글 시트 연결 중... (Spreadsheet ID: {SPREADSHEET_ID})")
    sync = GoogleSheetsSync(SPREADSHEET_ID, CREDENTIALS_PATH)

    print("공통 필드 읽는 중...")
    common_fields_data = sync.read_common_fields_by_event()
    if common_fields_data:
        print(f"공통 필드 읽기 완료: {len(common_fields_data)}개 이벤트 타입")
    else:
        common_fields_data = load_common_fields_by_event()
        if common_fields_data:
            print(f"파일에서 공통 필드 로드 완료: {len(common_fields_data)}개 이벤트 타입")

    worksheet_name = args.area
    print(f"\n시트 '{worksheet_name}'에서 모듈 '{args.module}' 데이터 읽는 중...")
    try:
        worksheet = sync.get_or_create_worksheet(worksheet_name)
        event_data_dict = sync.read_area_module_data(worksheet, args.module)
        for ck, rows in event_data_dict.items():
            print(f"  [{ck}]: {len(rows)}개 고유 필드 읽음")
    except Exception as e:
        print(f"오류: 시트에서 데이터 읽기 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not event_data_dict:
        print("오류: 시트에서 데이터를 읽을 수 없습니다.")
        print("  시트 이름: '%s', 모듈: '%s'" % (worksheet_name, args.module))
        sys.exit(1)

    print("\n공통 필드와 모듈 필드 병합 중...")
    merged_event_data_dict = merge_module_with_common(event_data_dict, common_fields_data)
    for config_key, merged_flat in merged_event_data_dict.items():
        module_fields = event_data_dict.get(config_key, [])
        common_count = len(merged_flat) - len(module_fields)
        print(f"  [{config_key}]: 공통 %s개 + 고유 %s개 = 총 %s개" % (common_count, len(module_fields), len(merged_flat)))

    print("\nconfig JSON 구조 생성 중...")
    config_json = create_config_json(merged_event_data_dict)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nJSON 파일 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, ensure_ascii=False, indent=2)
    print("완료: config JSON 생성 -> %s" % output_path)
    print("생성된 섹션: %s" % list(config_json.keys()))


if __name__ == '__main__':
    main()
