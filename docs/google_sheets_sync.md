# 구글 시트 동기화 가이드

JSON 파일과 구글 시트 간 양방향 동기화 기능 사용 가이드

## 개요

이 프로젝트는 `tracking_all` JSON 파일과 구글 시트 간의 양방향 동기화를 제공합니다:

1. **JSON → 구글 시트**: tracking_all JSON 파일을 구글 시트로 변환하여 기본 틀 생성
2. **구글 시트 → JSON**: 구글 시트 데이터를 읽어서 config JSON 파일 생성/업데이트

## 사전 준비

### 1. Google Sheets API 인증 설정

구글 시트 API를 사용하기 위해 서비스 계정 인증이 필요합니다.

#### 서비스 계정 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 프로젝트 생성 또는 선택
3. "API 및 서비스" → "사용 설정된 API" → "Google Sheets API" 활성화
4. "사용자 인증 정보" → "사용자 인증 정보 만들기" → "서비스 계정" 선택
5. 서비스 계정 생성 후 JSON 키 다운로드

#### 서비스 계정 JSON 파일 설정

서비스 계정 JSON 파일은 프로젝트 루트에 `python-link-test-380006-2868d392d217.json`로 저장되어 있으며, 스크립트에 하드코딩되어 있습니다.

#### 구글 시트 공유 설정

1. 구글 시트를 열기
2. 우측 상단 "공유" 버튼 클릭
3. 서비스 계정 이메일 주소 추가 (서비스 계정 JSON 파일의 `client_email` 필드 값)
4. 편집 권한 부여

### 2. 구글 시트 정보

구글 시트 ID는 스크립트에 하드코딩되어 있습니다:
- **Spreadsheet ID**: `1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E`
- **Credentials 파일**: `python-link-test-380006-2868d392d217.json` (프로젝트 루트)

## 기능 1: JSON → 구글 시트

tracking_all JSON 파일을 구글 시트로 변환하여 기본 틀 생성

### 사용법

```bash
python scripts/json_to_sheets.py \
  --input json/tracking_all_먼저_둘러보세요.json \
  --module "먼저 둘러보세요" \
  --area SRP
```

(전체 로그 파일명: `tracking_all_{module_title}.json`. 모듈 타이틀의 공백·특수문자는 파일명용으로 치환됨.)

### 인자 설명

- `--input`: 입력 tracking_all JSON 파일 경로 (필수)
- `--module`: 모듈명 (필수, 예: "먼저 둘러보세요")
- `--area`: 영역명 (필수, SRP, PDP, HOME, CART 등)

**시트명 형식**: 시트는 **영역만** 사용합니다 (예: `SRP`, `LP`, `CART`, `ORDER`). 동일 영역의 여러 모듈이 한 시트에 모여 있습니다.

**참고**: Spreadsheet ID와 Credentials 파일 경로는 스크립트에 하드코딩되어 있습니다.

### 동작 방식

1. tracking_all JSON 파일 로드
2. 이벤트 타입별로 데이터 그룹화 (Module Exposure, Product Exposure, Product Click 등)
3. 각 이벤트 타입의 첫 번째 이벤트 payload 사용 (대표값)
4. 중첩된 JSON 구조를 평면화
5. 영역 시트(`SRP` 등)를 가져오거나 생성
6. **기존 데이터 먼저 읽기** (표 생성 전에 보존할 행 확보)
7. **Native Table 생성**: 시트에 표가 없으면 `addTable`로 `A1:E2000` 구간에 표 생성 (5열 모두 TEXT, 헤더는 표가 관리). 이미 있으면 건너뜀.
8. **Upsert**: **데이터만** `A2:E`에 기록. 1행(헤더)은 건드리지 않음. `A2:E` clear 후, (현재 모듈 제외 유지 + 이번 모듈) 행을 한 번에 `value_input_option='RAW'`로 update.
9. 데이터 범위 `A2:E`를 텍스트 포맷으로 지정 (값 입력 오류 방지)

### 시트 구조

**영역별 시트** (SRP, LP, CART, ORDER) 하나에 **Native Table** (구글 시트 "표"):

- **1행**: 표 헤더. 스크립트가 쓰지 않으며, `addTable` 시 열 이름(모듈, 이벤트 타입, 경로, 필드명, 값)으로 설정됨.
- **2행~**: 데이터만 기록. `json_to_sheets`는 `A2:E`만 clear/update.

| 모듈 | 이벤트 타입 | 경로 | 필드명 | 값 |
|------|-------------|------|--------|-----|
| 먼저 둘러보세요 | Module Exposure | payload.gmkey | gmkey | EXP |
| 먼저 둘러보세요 | Module Exposure | payload.decoded_gokey.params.channel_code | channel_code | 200003514 |
| ... | ... | ... | ... | ... |
| MD's Pick | Module Exposure | payload.gmkey | gmkey | EXP |
| ... | ... | ... | ... | ... |

- **필드명**: 경로의 마지막 키(리프 필드)를 분리한 값. 필터·검색 시 유용.
- **필터 뷰**: "데이터" → "필터 뷰 만들기" 후 **모듈**, **이벤트 타입**, **필드명** 등으로 필터하면 보기 편합니다.

## 기능 2: 구글 시트 → JSON

구글 시트 데이터를 읽어서 config JSON 파일 생성/업데이트

### 사용법

```bash
python scripts/sheets_to_json.py \
  --module "먼저 둘러보세요" \
  --area SRP \
  [--output config/SRP/먼저\ 둘러보세요.json] \
  [--overwrite]
```

### 인자 설명

- `--module`: 모듈명 (필수, 예: "먼저 둘러보세요")
- `--area`: 영역명 (필수, SRP, PDP, HOME, CART 등)
- `--output`: 출력 JSON 파일 경로 (선택, 기본값: `config/{area}/{module}.json`)
- `--overwrite`: 기존 파일이 있으면 덮어쓰기 (기본값: False)

**시트명 형식**: 영역 시트(`SRP`, `LP` 등)를 읽습니다. `--module`으로 지정한 모듈에 해당하는 행만 추출하여 `config/{area}/{module}.json` 파일을 생성합니다.

**참고**: Spreadsheet ID와 Credentials 파일 경로는 스크립트에 하드코딩되어 있습니다.

### 동작 방식

1. 구글 시트에서 **영역 시트** 선택 (예: `SRP`)
2. **모듈** 컬럼이 `--module`과 같은 행만 필터
3. **이벤트 타입**별로 그룹하여 평면 데이터 복원 (Module Exposure → `module_exposure` 등)
4. 평면화된 데이터를 중첩 JSON 구조로 변환
5. config JSON 파일 생성/업데이트

### 출력 파일 구조

생성되는 JSON 파일 구조:

```json
{
  "module_exposure": {
    "payload": {
      "gmkey": "EXP",
      ...
    }
  },
  "product_exposure": {
    "channel_code": "200003514",
    ...
  },
  ...
}
```

## 이벤트 타입 매핑

| tracking_all JSON | config JSON |
|------------------|-------------|
| `PV` | `pv` |
| `PDP PV` | `pdp_pv` |
| `Module Exposure` | `module_exposure` |
| `Product Exposure` | `product_exposure` |
| `Product Click` | `product_click` |
| `Product ATC Click` | `product_atc_click` |
| `Product Minidetail` | `product_minidetail` |

## 데이터 변환 규칙

### JSON → 시트 (평면화)

1. **중첩 구조**: `parent.child.grandchild` 형식으로 경로 생성
2. **배열 처리**:
   - 빈 배열: `[]` 문자열
   - 단일 요소 배열: 배열 제거하고 값만 저장
   - 다중 요소/중첩 배열: JSON 문자열로 저장
3. **특수 값 유지**: `"mandatory"`, `"<상품번호>"`, `"skip"` 같은 플레이스홀더 보존

### 시트 → JSON (재구성)

1. **경로 파싱**: 점(`.`)으로 구분된 경로를 중첩 구조로 재구성
2. **타입 추론**:
   - JSON 배열/객체: JSON 파싱 시도
   - 불리언: `true`/`false` 문자열 변환
   - 숫자: 정수/실수 변환 시도
   - 문자열: 그대로 유지

## 주의사항

### 1. 한글 파일명 처리

Windows에서 한글 파일명을 사용할 때:
- PowerShell에서 경로 지정 시 따옴표 사용: `"먼저 둘러보세요"`
- 또는 이스케이프 사용: `먼저\ 둘러보세요`

### 2. 배열 데이터

복잡한 배열 구조는 JSON 문자열로 저장됩니다. 시트에서 편집 시 주의:
- 배열 전체를 하나의 셀에서 관리
- JSON 형식 유지 (따옴표, 쉼표 등)

### 3. 데이터 타입

구글 시트는 모든 값을 문자열로 저장합니다:
- 숫자는 자동으로 변환되지만, 명시적으로 따옴표로 감싸면 문자열로 처리됨
- JSON 재구성 시 타입 추론을 시도하지만, 명확하지 않은 경우 문자열로 유지

### 4. 시트 크기 제한

Google Sheets API 제한:
- 최대 1000만 셀
- 시트당 최대 500만 셀
- 매우 큰 JSON 파일의 경우 분할 필요

### 5. 권한

서비스 계정에 적절한 권한이 필요합니다:
- 시트 읽기 권한: 데이터 읽기
- 시트 편집 권한: 데이터 작성

## 문제 해결

### 인증 오류

```
ValueError: 인증 정보를 찾을 수 없습니다.
```

**해결 방법:**
1. 프로젝트 루트에 `python-link-test-380006-2868d392d217.json` 파일이 있는지 확인
2. 서비스 계정 JSON 파일이 올바른지 확인
3. 파일 경로가 올바른지 확인

### 시트 접근 오류

```
gspread.exceptions.APIError: 403 Forbidden
```

**해결 방법:**
1. 서비스 계정 이메일을 시트에 공유했는지 확인 (Spreadsheet ID: `1Hmrpoz1EVACFY5lHW7r4v8bEtRRFu8eay7grCojRr3E`)
2. 편집 권한이 있는지 확인
3. 서비스 계정 JSON 파일의 `client_email` 필드 값을 확인하여 시트에 공유했는지 확인

### 데이터 변환 오류

**문제**: 시트에서 읽은 데이터가 JSON으로 제대로 변환되지 않음

**해결 방법:**
1. 시트의 데이터 형식 확인 (특히 배열 데이터)
2. 경로 형식 확인 (점으로 구분된 경로)
3. 특수 문자 이스케이프 확인

### 표 및 값 입력

**현재 동작**: `json_to_sheets` 실행 시 영역 시트에 **처음부터 Native Table(표)** 를 `addTable`로 생성합니다. 5열 모두 **TEXT** 타입이라 `mandatory`, `skip`, `<상품번호>`, JSON 문자열 등이 정상 입력됩니다. 별도 "데이터 → 표로 변환"은 필요 없습니다.

**표 생성이 안 될 때**: `addTable` 호출이 실패하면(권한, API 제한, Workspace 정책 등) 콘솔에 traceback이 출력됩니다. 이때는 **1행에 헤더만 쓰고** 데이터는 A2:E에 그대로 기록합니다. 시트 활용에는 지장 없고, "데이터 → 필터 뷰 만들기"로 모듈/이벤트별 보기 가능합니다.

**이전에 수동으로 표로 변환한 시트**에서 값 입력 오류가 나면: 표를 해제한 뒤 **경로**, **필드명**, **값** 열을 **일반 텍스트**로 설정하고 다시 표로 변환하거나, **필터 뷰만 사용** ("데이터 → 필터 뷰 만들기")하면 표 없이도 모듈/이벤트별 보기가 가능합니다.

## 예시

### 전체 워크플로우

1. **tracking_all JSON 생성** (테스트 실행 후 자동 생성)

2. **구글 시트로 변환**:
```bash
python scripts/json_to_sheets.py \
  --input json/tracking_all_먼저_둘러보세요.json \
  --module "먼저 둘러보세요" \
  --area SRP
```
   → 시트 `SRP`에 모듈 "먼저 둘러보세요" Upsert (기존 동일 모듈 행 갱신)

3. **구글 시트에서 데이터 편집** (웹 브라우저에서). 모듈/이벤트 타입 필터 뷰로 보기 편하게 확인 가능.

4. **config JSON 생성**:
```bash
python scripts/sheets_to_json.py \
  --module "먼저 둘러보세요" \
  --area SRP \
  --overwrite
```
   → 시트 `SRP`에서 모듈 "먼저 둘러보세요" 행만 읽어 → `config/SRP/먼저 둘러보세요.json` 생성

5. **생성된 config JSON 사용** (테스트 실행)

### SRP 모듈별 명령어 예시

`config/SRP/` 폴더의 각 파일에 대한 명령어. 모두 **시트 `SRP`**를 사용합니다.

#### 1. 4.5 이상

```bash
# JSON → 구글 시트 (시트 SRP에 모듈 Upsert)
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "4.5 이상" --area SRP

# 구글 시트 → JSON (시트 SRP에서 모듈 읽기 → config/SRP/4.5 이상.json)
python scripts/sheets_to_json.py --module "4.5 이상" --area SRP --overwrite
```

#### 2. MD's Pick

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "MD's Pick" --area SRP
python scripts/sheets_to_json.py --module "MD's Pick" --area SRP --overwrite
```

#### 3. 대체검색어

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "대체검색어" --area SRP
python scripts/sheets_to_json.py --module "대체검색어" --area SRP --overwrite
```

#### 4. 먼저 둘러보세요

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "먼저 둘러보세요" --area SRP
python scripts/sheets_to_json.py --module "먼저 둘러보세요" --area SRP --overwrite
```

#### 5. 백화점 브랜드

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "백화점 브랜드" --area SRP
python scripts/sheets_to_json.py --module "백화점 브랜드" --area SRP --overwrite
```

#### 6. 브랜드 인기상품

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "브랜드 인기상품" --area SRP
python scripts/sheets_to_json.py --module "브랜드 인기상품" --area SRP --overwrite
```

#### 7. 스타배송

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "스타배송" --area SRP
python scripts/sheets_to_json.py --module "스타배송" --area SRP --overwrite
```

#### 8. 오늘의 상품이에요

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "오늘의 상품이에요" --area SRP
python scripts/sheets_to_json.py --module "오늘의 상품이에요" --area SRP --overwrite
```

#### 9. 오늘의 슈퍼딜

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "오늘의 슈퍼딜" --area SRP
python scripts/sheets_to_json.py --module "오늘의 슈퍼딜" --area SRP --overwrite
```

#### 10. 오늘의 프라임상품

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "오늘의 프라임상품" --area SRP
python scripts/sheets_to_json.py --module "오늘의 프라임상품" --area SRP --overwrite
```

#### 11. 인기 상품이에요

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "인기 상품이에요" --area SRP
python scripts/sheets_to_json.py --module "인기 상품이에요" --area SRP --overwrite
```

#### 12. 일반상품

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "일반상품" --area SRP
python scripts/sheets_to_json.py --module "일반상품" --area SRP --overwrite
```

#### 13. 최상단 클릭아이템

```bash
python scripts/json_to_sheets.py --input <tracking_all_json_file> --module "최상단 클릭아이템" --area SRP
python scripts/sheets_to_json.py --module "최상단 클릭아이템" --area SRP --overwrite
```

**참고**: `<tracking_all_json_file>` 부분은 실제 tracking_all JSON 파일 경로로 교체해야 합니다 (예: `json/tracking_all_먼저_둘러보세요.json`).

### 마이그레이션 (기존 시트 구조에서 전환 시)

- **이전**: 모듈당 시트 `{영역}-{모듈명}` (예: `SRP-먼저 둘러보세요`).
- **현재**: 영역당 시트 `SRP`, `LP`, `CART`, `ORDER` 하나씩, **Native Table** 단일 표(모듈 | 이벤트 타입 | 경로 | 필드명 | 값). 표는 `addTable`로 생성되며, 데이터는 `A2:E`에만 기록됩니다.

기존 `SRP-…`, `LP-…` 등 시트는 새 구조 전환 후 사용하지 않습니다. 필요 시 **사용자가 직접** 구글 시트에서 삭제하거나, 보관용으로 시트 이름을 변경해 두면 됩니다. 데이터는 `json_to_sheets`로 다시 올리면 새 영역 시트에 표가 생성·유지된 채 Upsert됩니다.

## 참고

- [Google Sheets API 문서](https://developers.google.com/sheets/api)
- [gspread 문서](https://gspread.readthedocs.io/)
- 프로젝트 내 `utils/google_sheets_sync.py` 소스 코드 참고
