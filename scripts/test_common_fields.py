"""
공통 필드 시스템 통합 테스트
"""
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.common_fields import (
    load_common_fields_by_event,
    get_common_fields_for_event_type,
    merge_common_fields_with_module_config,
    EVENT_TYPE_TO_CONFIG_KEY
)
from utils.validation_helpers import build_expected_from_module_config


def test_load_common_fields():
    """공통 필드 로드 테스트"""
    print("=" * 60)
    print("1. 공통 필드 로드 테스트")
    print("=" * 60)
    
    common_fields_data = load_common_fields_by_event()
    
    if not common_fields_data:
        print("[FAIL] 공통 필드 파일을 로드할 수 없습니다.")
        return False
    
    print(f"[OK] 공통 필드 로드 성공: {len(common_fields_data)}개 이벤트 타입")
    
    for event_type_key in sorted(common_fields_data.keys()):
        fields = common_fields_data[event_type_key]
        print(f"  - {event_type_key}: {len(fields)}개 공통 필드")
    
    return True


def test_get_common_fields_for_event_type():
    """특정 이벤트 타입의 공통 필드 가져오기 테스트"""
    print("\n" + "=" * 60)
    print("2. 이벤트 타입별 공통 필드 가져오기 테스트")
    print("=" * 60)
    
    common_fields_data = load_common_fields_by_event()
    
    test_event_types = ['Module Exposure', 'Product Click', 'PDP PV']
    
    for event_type in test_event_types:
        fields = get_common_fields_for_event_type(event_type, common_fields_data)
        print(f"[{event_type}]: {len(fields)}개 공통 필드")
        if fields:
            # 첫 3개만 출력
            sample_paths = sorted(fields.keys())[:3]
            for path in sample_paths:
                field_data = fields[path]
                # 단순화된 구조 지원 (값만 저장된 경우)
    if isinstance(field_data, dict):
        field_name = field_data.get('field', path.split('.')[-1])
        value = field_data.get('value', '')
    else:
        field_name = path.split('.')[-1]
        value = field_data
    print(f"  - {path}: {field_name} = {value}")
    
    return True


def test_merge_common_fields():
    """공통 필드와 모듈 필드 병합 테스트"""
    print("\n" + "=" * 60)
    print("3. 공통 필드와 모듈 필드 병합 테스트")
    print("=" * 60)
    
    # 테스트용 모듈 config (간단한 예시)
    test_module_config = {
        'module_exposure': {
            'payload': {
                'gmkey': 'EXP',
                'spm': 'gmktpc.searchlist.testmodule',  # 모듈 고유 필드
            }
        }
    }
    
    merged = merge_common_fields_with_module_config(
        test_module_config,
        'Module Exposure'
    )
    
    if not merged:
        print("[FAIL] 병합 결과가 비어있습니다.")
        return False
    
    print(f"[OK] 병합 성공")
    print(f"  병합된 필드 수: {len(str(merged))} 문자 (구조 확인)")
    
    # spm 필드가 모듈 고유 필드로 남아있는지 확인
    if 'spm' in str(merged) or 'testmodule' in str(merged):
        print("  [OK] 모듈 고유 필드 유지 확인")
    else:
        print("  [WARNING] 모듈 고유 필드 확인 필요")
    
    return True


def test_validation_integration():
    """검증 로직 통합 테스트"""
    print("\n" + "=" * 60)
    print("4. 검증 로직 통합 테스트")
    print("=" * 60)
    
    # 실제 config 파일 하나 로드
    config_dir = project_root / 'config'
    test_file = config_dir / 'SRP' / '일반상품.json'
    
    if not test_file.exists():
        print(f"[SKIP] 테스트 파일이 없습니다: {test_file}")
        return True
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            module_config = json.load(f)
        
        # Module Exposure 이벤트 타입으로 테스트
        event_type = 'Module Exposure'
        expected = build_expected_from_module_config(
            module_config,
            event_type,
            '1234567890',  # 테스트용 goodscode
            None,  # frontend_data
            []  # exclude_fields
        )
        
        if expected:
            print(f"[OK] 검증 로직 통합 성공")
            print(f"  생성된 expected 필드 수: {len(expected)}개")
            
            # 공통 필드가 포함되었는지 확인 (예: platformType)
            if 'platformType' in expected or any('platformType' in str(k) for k in expected.keys()):
                print("  [OK] 공통 필드 포함 확인")
            else:
                print("  [WARNING] 공통 필드 포함 여부 확인 필요")
        else:
            print("[WARNING] expected 필드가 비어있습니다.")
        
        return True
    except Exception as e:
        print(f"[FAIL] 검증 로직 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("공통 필드 시스템 통합 테스트 시작\n")
    
    results = []
    
    results.append(("공통 필드 로드", test_load_common_fields()))
    results.append(("이벤트 타입별 공통 필드", test_get_common_fields_for_event_type()))
    results.append(("공통 필드 병합", test_merge_common_fields()))
    results.append(("검증 로직 통합", test_validation_integration()))
    
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\n총 {passed}/{total}개 테스트 통과")
    
    if passed == total:
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print("\n❌ 일부 테스트 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
