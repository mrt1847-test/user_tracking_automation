"""
기존 config 파일 마이그레이션 스크립트
이벤트 타입별 공통 필드를 제거하여 모듈별 고유 필드만 남김
"""
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.google_sheets_sync import flatten_json, unflatten_json
from utils.common_fields import (
    load_common_fields_by_event,
    get_common_fields_for_event_type,
    EVENT_TYPE_TO_CONFIG_KEY,
    normalize_path_for_common,
    common_paths_normalized,
)


def remove_common_fields_from_config(config_data: Dict[str, Any], 
                                     common_fields_data: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    config 데이터에서 공통 필드 제거
    
    Args:
        config_data: 원본 config 데이터
        common_fields_data: 공통 필드 데이터
    
    Returns:
        공통 필드가 제거된 config 데이터
    """
    result = {}
    
    for event_type_key, event_config in config_data.items():
        if not isinstance(event_config, dict):
            result[event_type_key] = event_config
            continue
        
        # 이벤트 타입 찾기
        event_type = None
        for et, ck in EVENT_TYPE_TO_CONFIG_KEY.items():
            if ck == event_type_key:
                event_type = et
                break
        
        if not event_type:
            # 알 수 없는 이벤트 타입이면 그대로 유지
            result[event_type_key] = event_config
            continue
        
        # 공통 필드 가져오기
        common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
        if not common_fields:
            # 공통 필드가 없으면 그대로 유지
            result[event_type_key] = event_config
            continue
        
        # 평면화
        data_to_flatten = event_config.get('payload', event_config)
        flattened = flatten_json(data_to_flatten, exclude_keys=['timestamp', 'method', 'url'])
        
        # 공통 필드 제외 (배열 인덱스 무시하고 비교)
        common_paths_norm = common_paths_normalized(common_fields)
        unique_flat = [item for item in flattened if normalize_path_for_common(item.get('path')) not in common_paths_norm]
        
        # 중첩 구조로 재구성
        if unique_flat:
            unique_nested = unflatten_json(unique_flat)
            # payload 구조 유지
            if 'payload' in event_config:
                result[event_type_key] = {'payload': unique_nested}
            else:
                result[event_type_key] = unique_nested
        else:
            # 고유 필드가 없으면 빈 딕셔너리
            result[event_type_key] = {}
    
    return result


def migrate_config_file(config_path: Path, 
                       common_fields_data: Dict[str, Dict[str, Dict[str, Any]]],
                       backup: bool = True) -> bool:
    """
    단일 config 파일 마이그레이션
    
    Args:
        config_path: config 파일 경로
        common_fields_data: 공통 필드 데이터
        backup: 백업 파일 생성 여부
    
    Returns:
        성공 여부
    """
    try:
        # 원본 파일 읽기
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 백업 생성
        if backup:
            backup_path = config_path.with_suffix('.json.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print(f"  백업 생성: {backup_path}")
        
        # 공통 필드 제거
        migrated_data = remove_common_fields_from_config(config_data, common_fields_data)
        
        # 마이그레이션된 파일 저장
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(migrated_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"  [ERROR] 마이그레이션 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='기존 config 파일에서 이벤트 타입별 공통 필드 제거'
    )
    parser.add_argument(
        '--config-dir',
        type=str,
        default=None,
        help='config 디렉토리 경로 (기본값: config/)'
    )
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='단일 파일만 마이그레이션 (예: SRP/4.5 이상.json)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='백업 파일 생성 안 함'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제로 변경하지 않고 시뮬레이션만 수행'
    )
    
    args = parser.parse_args()
    
    # 공통 필드 로드
    print("공통 필드 로드 중...")
    common_fields_data = load_common_fields_by_event()
    if not common_fields_data:
        print("[ERROR] 공통 필드 파일을 찾을 수 없습니다.")
        print("먼저 scripts/analyze_common_fields.py를 실행하여 공통 필드를 추출하세요.")
        sys.exit(1)
    print(f"공통 필드 로드 완료: {len(common_fields_data)}개 이벤트 타입")
    
    # config 디렉토리 결정
    if args.config_dir:
        config_dir = Path(args.config_dir)
    else:
        config_dir = project_root / 'config'
    
    if not config_dir.exists():
        print(f"[ERROR] config 디렉토리를 찾을 수 없습니다: {config_dir}")
        sys.exit(1)
    
    # 마이그레이션할 파일 목록
    files_to_migrate = []
    
    if args.file:
        # 단일 파일
        file_path = config_dir / args.file
        if file_path.exists():
            files_to_migrate.append(file_path)
        else:
            print(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}")
            sys.exit(1)
    else:
        # 모든 config 파일
        for area_dir in config_dir.iterdir():
            if not area_dir.is_dir() or area_dir.name.startswith('_'):
                continue
            for config_file in area_dir.glob("*.json"):
                if config_file.name.startswith('_'):
                    continue
                files_to_migrate.append(config_file)
    
    if not files_to_migrate:
        print("[ERROR] 마이그레이션할 파일이 없습니다.")
        sys.exit(1)
    
    print(f"\n마이그레이션할 파일 수: {len(files_to_migrate)}")
    
    if args.dry_run:
        print("\n[DRY RUN] 실제로 변경하지 않고 시뮬레이션만 수행합니다.")
    
    # 마이그레이션 수행
    success_count = 0
    for config_file in files_to_migrate:
        rel_path = config_file.relative_to(config_dir)
        print(f"\n처리 중: {rel_path}")
        
        if args.dry_run:
            # 시뮬레이션: 원본 파일 읽어서 제거될 필드 수 계산
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                total_fields = 0
                removed_fields = 0
                
                for event_type_key, event_config in config_data.items():
                    if not isinstance(event_config, dict):
                        continue
                    
                    # 이벤트 타입 찾기
                    event_type = None
                    for et, ck in EVENT_TYPE_TO_CONFIG_KEY.items():
                        if ck == event_type_key:
                            event_type = et
                            break
                    
                    if not event_type:
                        continue
                    
                    # 평면화
                    data_to_flatten = event_config.get('payload', event_config)
                    flattened = flatten_json(data_to_flatten, exclude_keys=['timestamp', 'method', 'url'])
                    total_fields += len(flattened)
                    
                    # 공통 필드 수 (배열 인덱스 무시하고 비교)
                    common_fields = get_common_fields_for_event_type(event_type, common_fields_data)
                    common_paths_norm = common_paths_normalized(common_fields)
                    removed_fields += sum(1 for item in flattened if normalize_path_for_common(item.get('path')) in common_paths_norm)
                
                print(f"  총 필드: {total_fields}개, 제거될 공통 필드: {removed_fields}개, 남을 고유 필드: {total_fields - removed_fields}개")
                success_count += 1
            except Exception as e:
                print(f"  [ERROR] 시뮬레이션 실패: {e}")
        else:
            # 실제 마이그레이션
            if migrate_config_file(config_file, common_fields_data, backup=not args.no_backup):
                success_count += 1
                print(f"  [OK] 마이그레이션 완료")
    
    print(f"\n{'='*60}")
    print(f"마이그레이션 완료: {success_count}/{len(files_to_migrate)}개 파일")
    if not args.dry_run and not args.no_backup:
        print(f"백업 파일은 .json.backup 확장자로 저장되었습니다.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
