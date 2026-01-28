"""
공통 필드 분석 스크립트
여러 config JSON 파일들을 분석하여 경로, 필드명, 값이 모두 동일한 공통 필드를 찾습니다.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.google_sheets_sync import flatten_json


def load_all_configs(config_dir: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """
    모든 config JSON 파일을 로드
    
    Returns:
        [(파일명, config_data), ...] 리스트
    """
    configs = []
    for area_dir in config_dir.iterdir():
        if not area_dir.is_dir():
            continue
        for config_file in area_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 상대 경로로 저장 (예: "SRP/4.5 이상.json")
                    rel_path = f"{area_dir.name}/{config_file.name}"
                    configs.append((rel_path, data))
            except Exception as e:
                print(f"[WARNING] 파일 로드 실패: {config_file} - {e}")
    return configs


def extract_fields_by_event_type(config_data: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    이벤트 타입별로 필드 추출
    
    module_exposure의 경우 payload 구조를 유지하여 경로에 payload가 포함되도록 함
    
    Returns:
        {event_type: [{"path": "...", "field": "...", "value": "..."}, ...]}
    """
    result = {}
    for event_type, event_data in config_data.items():
        if not isinstance(event_data, dict):
            continue
        
        # payload 구조를 유지해야 하는 이벤트 타입들
        # module_exposure, product_atc_click, product_minidetail, pdp_pv 등은 payload 전체를 사용
        payload_preserving_types = ['module_exposure', 'product_atc_click', 'product_minidetail', 'pdp_pv']
        
        if event_type in payload_preserving_types and 'payload' in event_data:
            # payload 구조를 유지하여 평면화 (payload.decoded_gokey.params._w 형태)
            flattened = flatten_json(event_data, exclude_keys=['timestamp', 'method', 'url'])
        else:
            # payload가 있으면 payload를, 없으면 event_data 자체를 사용
            data_to_flatten = event_data.get('payload', event_data)
            flattened = flatten_json(data_to_flatten, exclude_keys=['timestamp', 'method', 'url'])
        
        result[event_type] = flattened
    return result


def _merge_array_fields(common_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    배열 인덱스가 포함된 경로들을 배열 필드로 합치기
    
    예: platformType[0], platformType[1] → platformType (값: ["pc", "mac"])
    
    Args:
        common_fields: 공통 필드 딕셔너리
    
    Returns:
        배열 필드가 합쳐진 공통 필드 딕셔너리
    """
    import re
    import json
    
    # 배열 인덱스 패턴: path[...] 형태
    array_pattern = re.compile(r'\[(\d+)\]$')
    
    # 배열 경로 그룹화: {base_path: {index: value}}
    array_groups: Dict[str, Dict[int, Any]] = defaultdict(dict)
    array_paths = set()
    
    for path, field_data in common_fields.items():
        match = array_pattern.search(path)
        if match:
            # 배열 인덱스가 있는 경로
            index = int(match.group(1))
            base_path = path[:match.start()]
            # 단순화된 구조 지원 (값만 저장된 경우)
            if isinstance(field_data, dict):
                value = field_data.get('value', '')
            else:
                value = field_data
            array_groups[base_path][index] = value
            array_paths.add(path)
    
    # 배열 필드로 합치기 (배열 인덱스가 없는 경로만 유지)
    merged_fields = {}
    for path, data in common_fields.items():
        if path not in array_paths:
            # 단순화된 구조: 값만 저장 (count, files는 내부 분석용이므로 제외)
            if isinstance(data, dict):
                merged_fields[path] = data.get('value', '')
            else:
                merged_fields[path] = data
    
    for base_path, index_values in array_groups.items():
        # 인덱스 순서대로 정렬
        sorted_indices = sorted(index_values.keys())
        array_values = [index_values[i] for i in sorted_indices]
        
        # 배열 값 중 하나라도 플레이스홀더(<...> 형태)가 포함되어 있으면 제외
        has_placeholder = any(
            isinstance(val, str) and val.strip().startswith('<') and val.strip().endswith('>')
            for val in array_values
        )
        if has_placeholder:
            continue
        
        # 필드명 추출 (경로의 마지막 부분)
        field_name = base_path.split('.')[-1]
        
        # 배열 값이 모두 동일한 타입이고 공통 필드 조건을 만족하면 합치기
        # 모든 파일에서 동일한 배열 구조를 가지는지 확인
        if len(array_values) > 0:
            # JSON 문자열로 변환하여 저장 (단순화된 구조: 값만 저장)
            # count와 files는 내부 분석용이므로 저장 시 제외
            merged_fields[base_path] = json.dumps(array_values, ensure_ascii=False)
    
    return merged_fields


def find_common_fields(configs: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """
    모든 config에서 공통 필드 찾기
    
    공통 필드 조건:
    1. 경로(path)가 동일
    2. 필드명(field)이 동일  
    3. 값(value)이 동일
    4. 모든 이벤트 타입에서 나타남 (또는 특정 이벤트 타입에서만 나타나지만 모든 config에서 동일)
    
    Returns:
        {event_type: {path: {"field": "...", "value": "...", "count": N, "files": [...]}}}
    """
    # 이벤트 타입별로 필드 수집
    event_type_fields: Dict[str, List[Dict[str, List[Dict[str, str]]]]] = defaultdict(list)
    
    for file_path, config_data in configs:
        fields_by_event = extract_fields_by_event_type(config_data)
        for event_type, fields in fields_by_event.items():
            event_type_fields[event_type].append({
                'file': file_path,
                'fields': fields
            })
    
    # 공통 필드 찾기
    common_fields_by_event: Dict[str, Dict[str, Any]] = {}
    
    for event_type, file_field_lists in event_type_fields.items():
        if not file_field_lists:
            continue
        
        # 각 필드를 (path, field, value) 튜플로 변환하여 집합으로 관리
        field_sets: Dict[Tuple[str, str, str], Set[str]] = defaultdict(set)
        
        for file_data in file_field_lists:
            file_path = file_data['file']
            for field_data in file_data['fields']:
                path = field_data.get('path', '')
                field = field_data.get('field', '')
                value = field_data.get('value', '')
                key = (path, field, value)
                field_sets[key].add(file_path)
        
        # 모든 파일에서 나타나는 필드만 공통 필드로 인정
        total_files = len(file_field_lists)
        common_fields = {}
        
        for (path, field, value), files in field_sets.items():
            if len(files) == total_files:
                # 플레이스홀더 값(<...> 형태)은 공통 필드에서 제외
                if isinstance(value, str) and value.strip().startswith('<') and value.strip().endswith('>'):
                    continue
                
                # 모든 파일에서 나타남
                if path not in common_fields:
                    common_fields[path] = {
                        'value': value,
                        'count': len(files),
                        'files': sorted(list(files))
                    }
        
        # 배열 필드를 하나로 합치기 (예: platformType[0], platformType[1] → platformType)
        common_fields = _merge_array_fields(common_fields)
        
        if common_fields:
            common_fields_by_event[event_type] = common_fields
    
    return common_fields_by_event


def find_global_common_fields(common_fields_by_event: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    모든 이벤트 타입에서 공통으로 나타나는 필드 찾기
    """
    if not common_fields_by_event:
        return {}
    
    # 첫 번째 이벤트 타입의 필드들을 기준으로 시작
    first_event_type = list(common_fields_by_event.keys())[0]
    base_fields = set(common_fields_by_event[first_event_type].keys())
    
    # 다른 이벤트 타입들과 교집합
    for event_type, fields in common_fields_by_event.items():
        if event_type == first_event_type:
            continue
        base_fields = base_fields.intersection(set(fields.keys()))
    
    # 교집합된 필드들 중에서 값도 동일한 것만 선택
    global_common = {}
    
    for path in base_fields:
        # 모든 이벤트 타입에서 동일한 값인지 확인
        values = {}
        for event_type in common_fields_by_event.keys():
            field_data = common_fields_by_event[event_type].get(path)
            if field_data:
                key = (field_data['field'], field_data['value'])
                if key not in values:
                    values[key] = []
                values[key].append(event_type)
        
        # 모든 이벤트 타입에서 동일한 값이면 공통 필드
        if len(values) == 1:
            field, value = list(values.keys())[0]
            global_common[path] = {
                'field': field,
                'value': value,
                'event_types': sorted(list(common_fields_by_event.keys()))
            }
    
    return global_common


def print_analysis_results(common_fields_by_event: Dict[str, Dict[str, Any]], 
                          global_common: Dict[str, Any],
                          configs: List[Tuple[str, Dict[str, Any]]]):
    """
    분석 결과 출력
    """
    print("=" * 80)
    print("공통 필드 분석 결과")
    print("=" * 80)
    print(f"\n분석한 config 파일 수: {len(configs)}")
    print(f"분석한 이벤트 타입 수: {len(common_fields_by_event)}")
    print(f"\n분석한 파일 목록:")
    for file_path, _ in configs:
        print(f"  - {file_path}")
    
    print("\n" + "=" * 80)
    print("1. 이벤트 타입별 공통 필드")
    print("=" * 80)
    
    for event_type in sorted(common_fields_by_event.keys()):
        fields = common_fields_by_event[event_type]
        print(f"\n[{event_type}]")
        print(f"  공통 필드 수: {len(fields)}")
        if fields:
            print(f"  필드 목록:")
            for path in sorted(fields.keys()):
                field_data = fields[path]
                # 경로에서 필드명 추출
                field_name = path.split('.')[-1]
                # 값 추출 (단순화된 구조 지원)
                if isinstance(field_data, dict):
                    value = field_data.get('value', '')
                    count = field_data.get('count', 0)
                else:
                    value = field_data
                    count = 0
                print(f"    - {path}")
                print(f"      필드명: {field_name}")
                print(f"      값: {value}")
                if count > 0:
                    print(f"      나타난 파일 수: {count}")
    
    print("\n" + "=" * 80)
    print("2. 전역 공통 필드 (모든 이벤트 타입에서 동일)")
    print("=" * 80)
    print(f"\n전역 공통 필드 수: {len(global_common)}")
    
    if global_common:
        print(f"\n필드 목록:")
        for path in sorted(global_common.keys()):
            field_data = global_common[path]
            print(f"  - {path}")
            print(f"    필드명: {field_data['field']}")
            print(f"    값: {field_data['value']}")
            print(f"    나타난 이벤트 타입: {', '.join(field_data['event_types'])}")
    else:
        print("\n  전역 공통 필드가 없습니다.")
    
    # 통계
    print("\n" + "=" * 80)
    print("3. 통계")
    print("=" * 80)
    
    total_common_by_event = sum(len(fields) for fields in common_fields_by_event.values())
    avg_common_per_event = total_common_by_event / len(common_fields_by_event) if common_fields_by_event else 0
    
    print(f"이벤트 타입별 평균 공통 필드 수: {avg_common_per_event:.1f}")
    print(f"전역 공통 필드 수: {len(global_common)}")
    
    # 전역 공통 필드를 JSON으로 저장
    if global_common:
        output_path = project_root / 'config' / '_common_fields.json'
        output_data = {}
        for path, field_data in global_common.items():
            output_data[path] = {
                'field': field_data['field'],
                'value': field_data['value']
            }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] 전역 공통 필드를 다음 파일에 저장했습니다: {output_path}")
    
    # 이벤트 타입별 공통 필드를 JSON으로 저장
    if common_fields_by_event:
        output_path = project_root / 'config' / '_common_fields_by_event.json'
        output_data = {}
        for event_type, fields in common_fields_by_event.items():
            output_data[event_type] = {}
            for path, field_data in fields.items():
                # 경로를 키로, 값만 저장 (field는 경로에서 추출 가능하므로 불필요)
                # 단순화된 구조 지원 (이미 값만 저장된 경우)
                if isinstance(field_data, dict):
                    output_data[event_type][path] = field_data.get('value', '')
                else:
                    output_data[event_type][path] = field_data
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] 이벤트 타입별 공통 필드를 다음 파일에 저장했습니다: {output_path}")
        print(f"    저장된 이벤트 타입: {', '.join(sorted(output_data.keys()))}")


def main():
    # Windows 콘솔 인코딩 설정
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    config_dir = project_root / 'config'
    
    if not config_dir.exists():
        print(f"[ERROR] config 디렉토리를 찾을 수 없습니다: {config_dir}")
        sys.exit(1)
    
    print("config 파일들을 로드하는 중...")
    configs = load_all_configs(config_dir)
    
    if not configs:
        print("[ERROR] config 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    print(f"[OK] {len(configs)}개의 config 파일 로드 완료")
    
    print("\n공통 필드를 분석하는 중...")
    common_fields_by_event = find_common_fields(configs)
    
    print("전역 공통 필드를 찾는 중...")
    global_common = find_global_common_fields(common_fields_by_event)
    
    print_analysis_results(common_fields_by_event, global_common, configs)


if __name__ == '__main__':
    main()
