# User Tracking Automation

G마켓 웹사이트의 사용자 트래킹 로그를 자동으로 수집하고 정합성을 검증하는 **BDD(Behavior-Driven Development) 기반 테스트 자동화 프로젝트**입니다.

## 📋 목차

- [주요 기능](#-주요-기능)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 및 실행](#-설치-및-실행)
- [설정 파일](#️-설정-파일)
- [주요 컴포넌트](#-주요-컴포넌트)
- [사용 방법](#-사용-방법)
- [TestRail 연동](#-testrail-연동)
- [Google Sheets 데이터 관리](#-google-sheets-데이터-관리)
- [문제 해결](#-문제-해결)

## 🎯 주요 기능

1. **BDD 기반 테스트 시나리오 작성**
   - `pytest-bdd`를 사용한 Gherkin 문법 기반 시나리오 작성
   - Feature 파일을 통한 비즈니스 로직 중심 테스트 정의
   - 재사용 가능한 Step Definitions

2. **네트워크 트래킹 로그 수집**
   - `aplus.gmarket.co.kr` 도메인의 POST 요청을 실시간으로 감지
   - 이벤트 타입별 자동 분류 (PV, Module Exposure, Product Exposure, Product Click, PDP PV, Product ATC Click 등)
   - SPM(Search Parameter Map) 기반 필터링
   - 다중 페이지/탭 지원

3. **트래킹 로그 정합성 검증**
   - HTML에서 추출한 가격 정보와 트래킹 로그의 가격 정보 비교
   - 영역별 설정 파일 기반 자동 검증
   - 이벤트 타입별 필드 검증
   - 특수 값 처리 (mandatory, skip, 리스트 값 등)

4. **TestRail 연동**
   - 테스트 실행 시 자동으로 TestRail Run 생성
   - 각 스텝 실행 결과를 TestRail에 자동 기록
   - 실패 시 스크린샷 자동 첨부
   - 실행 로그 자동 수집 및 첨부
   - 프론트엔드 실패 처리 및 Soft Assertion 지원

5. **Google Sheets를 통한 데이터 관리**
   - tracking_all JSON 파일을 Google Sheets로 변환
   - Google Sheets에서 설정 파일 편집 후 JSON으로 변환
   - 영역별 설정 파일 관리 (SRP, PDP, HOME, CART)
   - 상세 내용은 `docs/google_sheets_sync.md` 참고

## 📁 프로젝트 구조

```
user_tracking_automation/
├── config/                          # 설정 파일
│   ├── SRP/                         # 영역별 설정 폴더
│   │   ├── 먼저 둘러보세요.json     # 모듈별 설정 파일
│   │   ├── 일반상품.json
│   │   └── ...
│   ├── PDP/                         # (향후 추가)
│   ├── HOME/                        # (향후 추가)
│   ├── CART/                        # (향후 추가)
│   ├── __init__.py
│   └── validation_rules.py          # 검증 규칙 정의
├── features/                        # BDD Feature 파일
│   ├── srp_tracking.feature         # SRP 영역 테스트 시나리오
│   └── srp_tracking2.feature
├── steps/                           # BDD Step Definitions
│   ├── home_steps.py                # 홈페이지 관련 스텝
│   ├── login_steps.py               # 로그인 관련 스텝
│   ├── srp_lp_steps.py              # SRP/LP 관련 스텝
│   ├── product_steps.py             # 상품 관련 스텝
│   ├── cart_steps.py                # 장바구니 관련 스텝
│   ├── checkout_steps.py            # 결제 관련 스텝
│   ├── order_steps.py               # 주문 관련 스텝
│   ├── tracking_steps.py            # 트래킹 로그 수집 스텝
│   └── tracking_validation_steps.py # 트래킹 로그 검증 스텝
├── pages/                           # Page Object Model
│   ├── base_page.py                 # 기본 페이지 클래스
│   ├── home_page.py                 # 홈 페이지
│   ├── login_page.py                # 로그인 페이지
│   ├── search_page.py               # 검색 결과 페이지
│   ├── product_page.py              # 상품 상세 페이지
│   ├── Etc.py                       # 공통 기능
│   └── VipPage.py                   # VIP 페이지
├── utils/                           # 유틸리티 모듈
│   ├── NetworkTracker.py            # 네트워크 트래킹 로그 수집
│   ├── validation_helpers.py        # 정합성 검증 헬퍼 함수
│   ├── frontend_helpers.py          # 프론트엔드 실패 처리 헬퍼
│   ├── google_sheets_sync.py        # Google Sheets 동기화
│   ├── credentials.py               # 인증 정보 관리
│   └── urls.py                      # URL 관리
├── scripts/                          # 스크립트
│   ├── json_to_sheets.py            # JSON → Google Sheets 변환
│   └── sheets_to_json.py             # Google Sheets → JSON 변환
├── docs/                             # 문서
│   ├── project_structure.md          # 프로젝트 구조 상세 설명
│   ├── google_sheets_sync.md         # Google Sheets 동기화 가이드
│   └── flow_sequence_diagram.md      # 플로우 시퀀스 다이어그램
├── json/                             # 수집된 로그 저장 디렉토리
├── conftest.py                       # Pytest 설정 및 Fixture
├── pytest.ini                        # Pytest 설정
├── config.json                       # 프로젝트 설정 파일
├── requirements.txt                  # Python 의존성 목록
└── README.md                         # 프로젝트 문서
```

## 🚀 설치 및 실행

### 필수 요구사항

- Python 3.8 이상
- Playwright
- pytest
- pytest-bdd

### 설치

#### pip 사용

```bash
# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

#### pipenv 사용

```bash
# 의존성 설치 (Pipfile 기반)
pipenv install

# Playwright 브라우저 설치
pipenv run playwright install chromium
```

### 실행

#### pip 사용

```bash
# 모든 Feature 파일 실행
pytest features/ -v

# 특정 Feature 파일 실행
pytest features/srp_tracking.feature -v

# 로그 레벨 설정하여 실행
pytest features/ -v --log-cli-level=INFO

# 특정 시나리오만 실행
pytest features/srp_tracking.feature::Scenario -v
```

#### pipenv 사용

```bash
# 가상환경 활성화 후 실행
pipenv shell
pytest features/ -v

# 또는 pipenv run으로 직접 실행
pipenv run pytest features/ -v
pipenv run pytest features/srp_tracking.feature -v
pipenv run pytest features/ -v --log-cli-level=INFO
pipenv run pytest features/srp_tracking.feature::Scenario -v
```

## ⚙️ 설정 파일

### config.json

프로젝트 루트의 `config.json` 파일에 다음 정보를 설정합니다:

```json
{
  "tr_url": "http://172.30.2.20",
  "project_id": "212",
  "suite_id": "1999",
  "section_id": "69751",
  "milestone_id": "1564",
  "environment": "prod",
  "urls": {
    "dev": {
      "base": "https://www-dev.gmarket.co.kr",
      "item": "https://item-dev.gmarket.co.kr"
    },
    "stg": {
      "base": "https://www-stg.gmarket.co.kr",
      "item": "https://item-staging.gmarket.co.kr"
    },
    "prod": {
      "base": "https://www.gmarket.co.kr",
      "item": "https://item.gmarket.co.kr"
    }
  }
}
```

### 영역별 설정 파일 구조

프로젝트는 영역별로 설정 파일을 분리하여 관리합니다:

```
config/
├── SRP/                    # Search Results Page
│   ├── 먼저 둘러보세요.json
│   ├── 일반상품.json
│   └── ...
├── PDP/                    # Product Detail Page (향후)
├── HOME/                   # Home Page (향후)
└── CART/                   # Shopping Cart (향후)
```

### 모듈 설정 파일 형식

각 모듈 설정 파일은 이벤트 타입별 섹션으로 구성됩니다:

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
    "spm": "gmktpc.searchlist.cpc",
    "params-exp": {
      "parsed": {
        "_p_prod": "<상품번호>",
        "utLogMap": {
          "query": "<검색어>",
          "origin_price": "<원가>",
          "promotion_price": "<할인가>",
          "coupon_price": "<쿠폰적용가>"
        }
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

### 플레이스홀더 및 특수 값 처리

#### 플레이스홀더

다음 플레이스홀더는 실제 값으로 자동 대체됩니다:

- `<상품번호>`: 실제 상품 번호로 대체
- `<검색어>`: 검색 키워드로 대체
- `<원가>`, `<할인가>`, `<쿠폰적용가>`: HTML에서 추출한 가격 정보로 대체
- `<environment>`: `config.json`의 `environment` 값 (예: `"prod"`, `"dev"`, `"stg"`)

#### 특수 값

- **`"mandatory"`**: 해당 필드는 반드시 값이 있어야 함 (값이 없으면 검증 실패)
- **`"skip"`**: 해당 필드는 검증을 수행하지 않음 (어떤 값이든 통과)
- **빈 문자열 `""`**: 정확히 빈 값이어야 함 (값이 있으면 검증 실패)
- **리스트 값 `["값1", "값2"]`**: 실제 값이 리스트 내 어느 값과든 일치하면 통과 (OR 조건)

자세한 내용은 `docs/project_structure.md`를 참고하세요.

## 🔧 주요 컴포넌트

### NetworkTracker (`utils/NetworkTracker.py`)

네트워크 요청을 감지하고 트래킹 로그를 분류하는 클래스입니다.

**주요 메서드:**
- `start()`: 트래킹 시작
- `stop()`: 트래킹 중지
- `get_logs()`: 전체 로그 조회
- `get_module_exposure_logs_by_spm(spm)`: SPM으로 필터링된 Module Exposure 로그
- `get_product_exposure_logs_by_goodscode(goodscode, spm)`: 상품번호와 SPM으로 필터링된 Product Exposure 로그
- `get_product_click_logs_by_goodscode(goodscode)`: 상품번호로 필터링된 Product Click 로그
- `get_pdp_pv_logs_by_goodscode(goodscode)`: 상품번호로 필터링된 PDP PV 로그

**지원하는 이벤트 타입:**
- `PV`, `Module Exposure`, `Product Exposure`, `Product Click`, `Product ATC Click`, `PDP PV`

### SearchPage (`pages/search_page.py`)

검색 결과 페이지의 상호작용을 담당하는 Page Object Model입니다.

**주요 메서드:**
- `search_product(keyword)`: 키워드로 상품 검색
- `search_module_by_title(module_title)`: 모듈 타이틀로 모듈 찾기
- `assert_item_in_module(module_title)`: 모듈 내 상품 노출 확인 및 상품번호 반환
- `get_product_price_info(goodscode)`: 상품의 가격 정보 추출 (원가, 판매가, 할인률, 프로모션가, 쿠폰적용가)
- `click_product(goodscode)`: 상품 클릭 및 새 페이지 이동

### validation_helpers (`utils/validation_helpers.py`)

트래킹 로그의 정합성을 검증하는 헬퍼 함수들입니다.

**주요 함수:**
- `load_module_config(area, module_title, feature_path)`: 영역과 모듈명을 기반으로 설정 파일 로드
- `build_expected_from_module_config(module_config, event_type, ...)`: 모듈 설정에서 예상 값 생성
- `validate_event_type_logs(tracker, event_type, ...)`: 특정 이벤트 타입의 로그 검증 수행
- `replace_placeholders(expected_data, ...)`: 플레이스홀더를 실제 값으로 대체

### BrowserSession (`conftest.py`)

브라우저 세션 관리 클래스로, 현재 active page 참조를 관리합니다.

**주요 기능:**
- 페이지 스택을 통한 탭 전환 추적
- `page` 속성으로 현재 active page 접근
- `switch_to(page)`: 새 페이지로 전환
- `restore()`: 이전 페이지로 복귀

## 📖 사용 방법

### BDD Feature 파일 작성

Feature 파일은 Gherkin 문법을 사용하여 작성합니다:

```gherkin
Feature: G마켓 SRP 트래킹 로그 정합성 검증
  검색 결과 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.

  Scenario: 검색 결과 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가 "<keyword>"을 검색한다
    Then 검색 결과 페이지가 표시된다
    Given 사용자가 "<keyword>"을 검색했다
    And 검색 결과 페이지에 "<module_title>" 모듈이 있다
    When 사용자가 "<module_title>" 모듈 내 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
```

### 테스트 결과

테스트 실행 후 `json/` 디렉토리에 다음 파일들이 생성됩니다:

- `tracking_pv_{goodscode}_{timestamp}.json`: PV 로그
- `tracking_module_exposure_{goodscode}_{timestamp}.json`: Module Exposure 로그
- `tracking_product_exposure_{goodscode}_{timestamp}.json`: Product Exposure 로그
- `tracking_product_click_{goodscode}_{timestamp}.json`: Product Click 로그
- `tracking_pdp_pv_{goodscode}_{timestamp}.json`: PDP PV 로그
- `tracking_all_{module_title}.json`: 전체 트래킹 로그 (모듈 타이틀 사용, 공백 등은 `_`로 치환)

## 🔗 TestRail 연동

프로젝트는 TestRail과 자동으로 연동되어 테스트 결과를 기록합니다.

### 주요 기능

1. **자동 Run 생성**: 테스트 세션 시작 시 `config.json`의 `section_id` 기반으로 TestRail Run 자동 생성
2. **스텝별 결과 기록**: 각 BDD 스텝 실행 후 TestRail에 결과 자동 기록
3. **TC 번호 추출**: 스텝 파라미터에서 TC 번호 (예: `C12345`) 자동 추출
4. **스크린샷 첨부**: 실패 시 자동으로 스크린샷 캡처 및 첨부
5. **로그 첨부**: 실행 로그를 TestRail 결과에 자동 첨부
6. **Soft Assertion 지원**: 프론트엔드 실패나 검증 실패를 구분하여 기록

### 설정

TestRail 연동을 위해서는 `config.json`에 TestRail 설정이 필요합니다:

```json
{
  "tr_url": "http://172.30.2.20",
  "project_id": "212",
  "suite_id": "1999",
  "section_id": "69751",
  "milestone_id": "1564"
}
```

**참고**: TestRail 인증 설정 방법은 내부 문서를 참고하세요.

## 📊 Google Sheets 데이터 관리

프로젝트는 Google Sheets를 통한 설정 파일 관리를 지원합니다.

### 주요 기능

1. **JSON → Google Sheets**: tracking_all JSON 파일을 Google Sheets로 변환하여 편집 가능한 형태로 제공
2. **Google Sheets → JSON**: Google Sheets에서 편집한 데이터를 config JSON 파일로 변환

### 사용 방법

```bash
# JSON → Google Sheets
python scripts/json_to_sheets.py \
  --input json/tracking_all_먼저_둘러보세요.json \
  --module "먼저 둘러보세요"

# Google Sheets → JSON
python scripts/sheets_to_json.py \
  --module "먼저 둘러보세요" \
  --area SRP \
  --overwrite
```

상세한 사용 방법은 `docs/google_sheets_sync.md`를 참고하세요.

## 📝 주의사항

1. **상품 클릭 전 가격 정보 추출**
   - `get_product_price_info()`는 상품 클릭 전에 호출해야 합니다.
   - 상품 클릭 후에는 페이지가 이동하여 HTML 요소에 접근할 수 없습니다.

2. **SPM 필터링**
   - Module Exposure와 Product Exposure 로그는 SPM 값으로 필터링됩니다.
   - 영역별 설정 파일에 올바른 SPM 값이 설정되어 있어야 합니다.

3. **로그 저장**
   - 테스트 실행 중 네트워크 요청이 완료될 때까지 충분한 대기 시간을 확보해야 합니다.
   - `time.sleep(2)` 또는 `page.wait_for_load_state('networkidle')` 사용을 권장합니다.

4. **영역 추론**
   - Feature 파일명이 `{area}_tracking.feature` 형식이어야 영역 자동 추론이 작동합니다.
   - 예: `srp_tracking.feature` → `SRP` 영역

## 🐛 문제 해결

### 로그가 수집되지 않는 경우

1. 네트워크 트래킹이 시작되었는지 확인 (`tracker.start()`)
2. 페이지 로딩이 완료되었는지 확인
3. `aplus.gmarket.co.kr` 도메인으로의 요청이 발생하는지 확인

### 정합성 검증 실패

1. 영역별 설정 파일의 플레이스홀더가 올바르게 설정되었는지 확인
2. `frontend_data`에 필요한 가격 정보가 포함되어 있는지 확인
3. SPM 값이 올바른지 확인
4. 특수 값 처리 (`mandatory`, `skip`, 리스트 값) 확인

### TestRail 연동 문제

1. `config.json`의 TestRail 설정이 올바른지 확인
2. TestRail 인증 설정이 올바른지 확인 (내부 문서 참고)

### Google Sheets 동기화 문제

1. 서비스 계정 JSON 파일이 프로젝트 루트에 있는지 확인
2. 구글 시트에 서비스 계정 이메일이 공유되어 있는지 확인
3. 상세 내용은 `docs/google_sheets_sync.md`의 "문제 해결" 섹션 참고

## 📚 참고 문서

- `docs/project_structure.md`: 프로젝트 구조 상세 설명
- `docs/google_sheets_sync.md`: Google Sheets 데이터 관리 상세 가이드
- `docs/flow_sequence_diagram.md`: 플로우 시퀀스 다이어그램

## 📄 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.
