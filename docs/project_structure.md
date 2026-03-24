# 프로젝트 구조 및 주요 사항

## 📁 프로젝트 구조

```
user_tracking_automation/
├── tracking_schemas/                # 트래킹 스키마 JSON
│   ├── SRP/                         # 영역별 설정 폴더
│   │   ├── 먼저 둘러보세요.json     # 모듈별 설정 파일
│   │   └── 일반상품.json
│   ├── PDP/                         # (향후 추가)
│   ├── HOME/                        # (향후 추가)
│   ├── CART/                        # (향후 추가)
│   ├── __init__.py
│   └── validation_rules.py
├── features/                        # BDD Feature 파일
│   └── srp_tracking.feature        # SRP 영역 테스트 시나리오
├── steps/                           # BDD Step Definitions
│   ├── home_steps.py               # 홈페이지 관련 스텝 (영역 추론 포함)
│   ├── srp_lp_steps.py             # SRP/LP 관련 스텝
│   ├── tracking_validation_steps.py # 트래킹 로그 검증 스텝
│   └── ...
├── pages/                           # Page Object Model
│   ├── home_page.py
│   ├── search_page.py
│   └── ...
├── utils/                           # 유틸리티 모듈
│   ├── NetworkTracker.py           # 네트워크 트래킹 로그 수집
│   ├── validation_helpers.py       # 정합성 검증 헬퍼 함수
│   └── ...
├── json/                            # 수집된 로그 저장 디렉토리
├── docs/                            # 문서
│   ├── project_structure.md        # 이 문서
│   └── flow_sequence_diagram.md
├── conftest.py                      # Pytest 설정 및 Fixture
├── pytest.ini                       # Pytest 설정
└── test_srp.py                      # 테스트 실행 파일
```

## 🏗️ 모듈 설정 파일 구조

### 영역별 폴더 구조

기존의 단일 `module_config.json` 파일을 영역별 폴더 구조로 분리했습니다:

```
tracking_schemas/
├── SRP/                             # Search Results Page
│   ├── 먼저 둘러보세요.json
│   └── 일반상품.json
├── PDP/                             # Product Detail Page (향후)
├── HOME/                            # Home Page (향후)
└── CART/                            # Shopping Cart (향후)
```

### 모듈 설정 파일 형식

각 모듈 설정 파일은 **common 섹션 없이** 각 이벤트별 섹션에 필요한 값들을 직접 포함합니다:

```json
{
  "module_exposure": {
    "channel_code": "200003514",
    "cguid": "11412244806446005562000000",
    "spm-url": "gmktpc.home.searchtop",
    "spm-pre": "",
    "spm-cnt": "gmktpc.searchlist",
    "spm": "gmktpc.searchlist.cpc",
    "params-exp": {
      "parsed": {
        "module_index": "3",
        "ab_buckets": "mandatory"
      }
    }
  },
  "product_exposure": {
    "channel_code": "200003514",
    "cguid": "11412244806446005562000000",
    "spm-url": "gmktpc.home.searchtop",
    "spm-pre": "",
    "spm-cnt": "gmktpc.searchlist",
    "spm": "gmktpc.searchlist.cpc",
    "params-exp": {
      "parsed": {
        ...
      }
    }
  },
  "product_click": {
    ...
  },
  "pdp_pv": {
    ...
  }
}
```

**주요 특징:**
- ❌ `common` 섹션 제거
- ✅ 각 이벤트별 섹션(`module_exposure`, `product_exposure` 등)에 필요한 값 직접 포함
- ✅ 동일한 값이라도 각 이벤트 섹션에 명시적으로 작성

### 영역 자동 추론

Feature 파일명에서 영역을 자동으로 추론합니다:

- `srp_tracking.feature` → `SRP` 영역
- `pdp_tracking.feature` → `PDP` 영역
- `home_tracking.feature` → `HOME` 영역
- `cart_tracking.feature` → `CART` 영역

영역 추론은 `steps/home_steps.py`의 `@given("G마켓 홈 페이지에 접속했음")` 스텝에서 수행되며, `bdd_context.store['area']`에 저장됩니다.

## 🔍 검증 로직

### 특수 값 처리

#### 1. `"mandatory"` - 필수 필드

```json
{
  "ab_buckets": "mandatory"
}
```

- **의미**: 해당 필드는 반드시 값이 있어야 함
- **동작**: 실제 로그에 값이 없거나 빈 문자열이면 검증 실패
- **내부 변환**: `"mandatory"` → `"__MANDATORY__"`

#### 2. `"skip"` - 검증 스킵

```json
{
  "spm-pre": "skip"
}
```

- **의미**: 해당 필드는 검증을 수행하지 않음
- **동작**: 실제 로그에 어떤 값이 있든 상관없이 검증 통과
- **내부 변환**: `"skip"` → `"__SKIP__"`

#### 3. 빈 문자열 `""` - 정확히 빈 값이어야 함

```json
{
  "spm-pre": ""
}
```

- **의미**: 해당 필드는 반드시 빈 문자열이어야 함
- **동작**: 실제 로그에 값이 있으면 검증 실패
- **예시**: 
  - Expected: `""`, Actual: `""` → ✅ 통과
  - Expected: `""`, Actual: `"something"` → ❌ 실패

#### 4. 리스트 값 - 허용 가능한 값 목록

```json
{
  "ab_buckets": ["#108^4#B", "#108^3#B"],
  "is_ad": ["Y", "N"]
}
```

- **의미**: 해당 필드는 리스트에 포함된 값 중 하나와 일치하면 통과
- **동작**: 실제 로그 값이 리스트 내 어느 값과든 일치하면 검증 통과 (부분 매칭, OR 조건)
- **예시**:
  - Expected: `["#108^4#B", "#108^3#B"]`, Actual: `"#108^4#B"` → ✅ 통과
  - Expected: `["#108^4#B", "#108^3#B"]`, Actual: `"#108^3#B"` → ✅ 통과
  - Expected: `["#108^4#B", "#108^3#B"]`, Actual: `"#108^5#B"` → ❌ 실패
  - Expected: `["Y", "N"]`, Actual: `"Y"` → ✅ 통과
  - Expected: `["Y", "N"]`, Actual: `"N"` → ✅ 통과

#### 5. 플레이스홀더 - 동적 값 대체

```json
{
  "_p_prod": "<상품번호>",
  "query": "<검색어>",
  "origin_price": "<원가>",
  "promotion_price": "<할인가>",
  "coupon_price": "<쿠폰적용가>",
  "server_env": "<environment>",
  "is_ad": "<is_ad>",
  "trafficType": "<trafficType>"
}
```

- **의미**: 실제 값으로 자동 대체됨
- **대체 소스**:
  - `<상품번호>`: `goodscode` 파라미터
  - `<검색어>`: `bdd_context`의 `keyword`
  - `<원가>`, `<할인가>`, `<쿠폰적용가>`: PDP PV 로그에서 추출한 가격 정보
  - `<environment>`: `config.json`의 `environment` 값 (예: `"prod"`, `"dev"`, `"stg"`)
  - `<is_ad>`: `bdd_context`의 `is_ad` (광고 상품 여부, 클릭한 상품이 광고 여부 — `"Y"`/`"N"` 등)
  - `<trafficType>`: `is_ad`에 따라 `"ad"` 또는 `"organic"` (is_ad가 Y/True/1 등이면 `"ad"`, 아니면 `"organic"`)
- **is_ad 연관**: `adProduct`, `adSubProduct` 필드는 `is_ad`가 `"Y"`일 때만 검증에 포함됨 (플레이스홀더 아님)

### 검증 프로세스

1. **모듈 설정 파일 로드**
   - Feature 파일명에서 영역 추론
   - `tracking_schemas/{area}/{module_title}.json` 파일 로드

2. **예상 값 생성**
   - 플레이스홀더를 실제 값으로 대체
   - `"mandatory"` → `"__MANDATORY__"` 변환
   - `"skip"` → `"__SKIP__"` 변환

3. **실제 로그 검증**
   - 트래킹 로그에서 필드값 추출
   - 예상 값과 실제 값 비교
   - `__SKIP__` 마커는 검증 스킵
   - 리스트 형태의 예상 값은 실제 값이 리스트 내 어느 값과든 일치하면 통과

## 📝 주요 컴포넌트

### 1. `utils/validation_helpers.py`

#### `load_module_config(area, module_title, feature_path)`
- 영역과 모듈명을 기반으로 설정 파일 로드
- Feature 파일명에서 영역 자동 추론 지원

#### `detect_area_from_feature_path(feature_path)`
- Feature 파일 경로에서 영역 추론
- `{area}_tracking.feature` 패턴 인식

#### `build_expected_from_module_config(module_config, event_type, ...)`
- 모듈 설정에서 예상 값 생성
- common 섹션 없이 이벤트 타입별 섹션만 처리

#### `validate_event_type_logs(tracker, event_type, ...)`
- 특정 이벤트 타입의 로그 검증 수행
- 이벤트 타입별 섹션에서 spm 값 추출

### 2. `utils/NetworkTracker.py`

#### `validate_payload(log, expected_data, ...)`
- 실제 로그와 예상 값 비교
- `__SKIP__`, `__MANDATORY__` 특수 마커 처리
- 포함 여부 매칭 (spm, spm-url, spm-pre, spm-cnt 필드)

### 3. `steps/home_steps.py`

#### `@given("G마켓 홈 페이지에 접속했음")`
- 홈 페이지 접속 및 영역 추론 수행
- Feature 파일 경로에서 영역 추론하여 `bdd_context.store['area']`에 저장

### 4. `steps/tracking_validation_steps.py`

#### `_get_common_context(bdd_context)`
- 공통 context 값 확인 및 반환
- `area` 값 검증 (없으면 오류 발생)

#### 검증 스텝들
- `@then("Module Exposure 로그가 정합성 검증을 통과해야 함")`
- `@then("Product Exposure 로그가 정합성 검증을 통과해야 함")`
- `@then("Product Click 로그가 정합성 검증을 통과해야 함")`
- 등등...

## ⚠️ 주의사항

### 1. 영역 추론 실패

- Feature 파일명이 `{area}_tracking.feature` 형식이 아니면 영역 추론 실패
- `bdd_context.store['area']`가 없으면 검증 시 `ValueError` 발생
- `steps/home_steps.py`의 기본값 사용 부분 확인 필요

### 2. 모듈 설정 파일 경로

- 파일명은 정확히 모듈 타이틀과 일치해야 함
- 예: 모듈 타이틀이 `"먼저 둘러보세요"`면 파일명도 `먼저 둘러보세요.json`이어야 함
- 파일 경로: `tracking_schemas/{area}/{module_title}.json`

### 3. 빈 문자열 vs skip

- 빈 문자열 `""`: 정확히 빈 값이어야 함 (값이 있으면 실패)
- `"skip"`: 어떤 값이든 상관없음 (검증 스킵)

### 4. 필드 검증 순서

1. `actual_value is None` → 값이 없으면 에러
2. `expected_value == "__SKIP__"` → 검증 스킵
3. `expected_value == "__MANDATORY__"` → 값이 있으면 통과, 없으면 에러
4. `isinstance(expected_value, list)` → **허용 값 목록 검증**: 실제 값이 리스트 내 어느 값과든 일치하면 통과 (OR 조건)
5. 포함 여부 매칭 (spm 관련 필드)
6. 정확 일치 비교

## 🔄 데이터 흐름

1. **Feature 파일 실행**
   ```
   features/srp_tracking.feature
   ↓
   steps/home_steps.py: @given("G마켓 홈 페이지에 접속했음")
   ↓
   영역 추론: "srp_tracking" → "SRP"
   ↓
   bdd_context.store['area'] = "SRP"
   ```

2. **모듈 설정 로드**
   ```
   steps/tracking_validation_steps.py: load_module_config()
   ↓
   area="SRP", module_title="먼저 둘러보세요"
   ↓
   tracking_schemas/SRP/먼저 둘러보세요.json 로드
   ```

3. **검증 수행**
   ```
   NetworkTracker.validate_payload()
   ↓
   실제 로그 vs 예상 값 비교
   ↓
   __SKIP__: 검증 스킵
   __MANDATORY__: 값 존재 여부 확인
   일반 값: 정확 일치 또는 포함 여부 매칭
   ```

## 📌 새 모듈 추가 방법

### 1. 설정 파일 생성

```
tracking_schemas/SRP/새모듈명.json
```

### 2. 설정 파일 작성

```json
{
  "module_exposure": {
    "channel_code": "...",
    "spm": "...",
    ...
  },
  "product_exposure": {
    ...
  },
  ...
}
```

### 3. Feature 파일에서 사용

```gherkin
Given 검색 결과 페이지에 "새모듈명" 모듈이 있다
When 사용자가 "새모듈명" 모듈 내 상품을 확인하고 클릭한다
Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: C12345)
```

## 🚀 향후 개선 사항

1. **다른 영역 지원**: PDP, HOME, CART 등
2. **설정 파일 검증**: JSON 스키마 검증
3. **자동 영역 감지 개선**: 더 정확한 추론 로직
4. **설정 파일 자동 생성**: 템플릿 기반
