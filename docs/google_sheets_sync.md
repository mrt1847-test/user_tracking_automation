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
  --input json/tracking_all_2809108578_20260121_123834.json \
  --module "먼저 둘러보세요"
```

### 인자 설명

- `--input`: 입력 tracking_all JSON 파일 경로 (필수)
- `--module`: 모듈명 (필수, 예: "먼저 둘러보세요")

**참고**: Spreadsheet ID와 Credentials 파일 경로는 스크립트에 하드코딩되어 있습니다.

### 동작 방식

1. tracking_all JSON 파일 로드
2. 이벤트 타입별로 데이터 그룹화:
   - Module Exposure
   - Product Exposure
   - Product Click
   - Product ATC Click
   - PDP PV
   - PV (선택적)
3. 각 이벤트 타입의 첫 번째 이벤트 payload 사용 (대표값)
4. 중첩된 JSON 구조를 평면화
5. 구글 시트에 모듈명으로 시트 생성
6. 각 시트 내에 이벤트 타입별 테이블 구성

### 시트 구조

각 시트 내부 구조:

```
[Module Exposure]
| 경로 | 값 |
|------|-----|
| payload.gmkey | EXP |
| payload.decoded_gokey.params.channel_code | 200003514 |
...

[Product Exposure]
| 경로 | 값 |
|------|-----|
| channel_code | 200003514 |
...
```

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

**참고**: Spreadsheet ID와 Credentials 파일 경로는 스크립트에 하드코딩되어 있습니다.

### 동작 방식

1. 구글 시트에서 모듈명 시트 선택
2. 이벤트 타입별 테이블 읽기:
   - Module Exposure → `module_exposure`
   - Product Exposure → `product_exposure`
   - Product Click → `product_click`
   - Product ATC Click → `product_atc_click`
   - PDP PV → `pdp_pv`
   - PV → `pv`
3. 평면화된 데이터를 중첩 JSON 구조로 변환
4. config JSON 파일 생성/업데이트

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

## 예시

### 전체 워크플로우

1. **tracking_all JSON 생성** (테스트 실행 후 자동 생성)

2. **구글 시트로 변환**:
```bash
python scripts/json_to_sheets.py \
  --input json/tracking_all_2809108578_20260121_123834.json \
  --module "먼저 둘러보세요"
```

3. **구글 시트에서 데이터 편집** (웹 브라우저에서)

4. **config JSON 생성**:
```bash
python scripts/sheets_to_json.py \
  --module "먼저 둘러보세요" \
  --area SRP \
  --overwrite
```

5. **생성된 config JSON 사용** (테스트 실행)

## 참고

- [Google Sheets API 문서](https://developers.google.com/sheets/api)
- [gspread 문서](https://gspread.readthedocs.io/)
- 프로젝트 내 `utils/google_sheets_sync.py` 소스 코드 참고
