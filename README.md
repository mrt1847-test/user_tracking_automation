# User Tracking Automation

G마켓 웹사이트의 사용자 트래킹 로그를 자동으로 수집하고 정합성을 검증하는 테스트 자동화 프로젝트입니다.

## 📋 목차

- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [설정 파일](#설정-파일)
- [주요 컴포넌트](#주요-컴포넌트)
- [사용 방법](#사용-방법)

## 🎯 주요 기능

1. **트래킹 로그 수집**
   - `aplus.gmarket.co.kr` 도메인의 POST 요청을 실시간으로 감지
   - 이벤트 타입별 분류 (PV, Module Exposure, Product Exposure, Product Click, PDP PV 등)
   - SPM(Search Parameter Map) 기반 필터링

2. **정합성 검증**
   - HTML에서 추출한 가격 정보와 트래킹 로그의 가격 정보 비교
   - `module_config.json` 기반 자동 검증
   - 이벤트 타입별 필드 검증

3. **가격 정보 추출**
   - HTML 요소에서 원가, 판매가, 할인률 추출
   - URL 파라미터에서 프로모션가, 쿠폰적용가 추출

## 📁 프로젝트 구조

```
user_tracking_automation/
├── config/                    # 설정 파일
│   ├── module_config.json     # 모듈별 트래킹 필드 설정
│   └── validation_rules.py    # 검증 규칙 정의
├── pom/                       # Page Object Model
│   ├── SrpPage.py            # 검색 결과 페이지
│   ├── Etc.py                # 공통 기능
│   ├── HomePage.py           # 홈 페이지
│   └── VipPage.py            # VIP 페이지
├── utils/                     # 유틸리티 모듈
│   ├── NetworkTracker.py     # 네트워크 트래킹 로그 수집
│   └── validation_helpers.py # 정합성 검증 헬퍼 함수
├── json/                      # 수집된 로그 저장 디렉토리
├── conftest.py               # Pytest 설정 및 Fixture
├── pytest.ini                # Pytest 설정
├── test_srp.py               # 메인 테스트 파일
└── README.md                 # 프로젝트 문서
```

## 🚀 설치 및 실행

### 필수 요구사항

- Python 3.8 이상
- Playwright
- pytest

### 설치

```bash
# 의존성 설치
pip install playwright pytest

# Playwright 브라우저 설치
playwright install chromium
```

### 실행

```bash
# 테스트 실행
pytest test_srp.py -v

# 로그 레벨 설정하여 실행
pytest test_srp.py -v --log-cli-level=INFO
```

## ⚙️ 설정 파일

### `config/module_config.json`

모듈별 트래킹 필드 설정 파일입니다. 이벤트 타입별로 구분되어 있습니다.

```json
{
  "먼저 둘러보세요": {
    "common": {
      "channel_code": "200003514",
      "spm": "gmktpc.searchlist.cpc"
    },
    "product_exposure": {
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
    }
  }
}
```

**플레이스홀더:**
- `<상품번호>`: 실제 상품 번호로 자동 대체
- `<검색어>`: 검색 키워드로 자동 대체
- `<원가>`, `<할인가>`, `<쿠폰적용가>`: HTML에서 추출한 가격 정보로 자동 대체

### `pytest.ini`

Pytest 실행 설정 파일입니다.

```ini
[pytest]
log_cli = true
log_cli_level = INFO
```

## 🔧 주요 컴포넌트

### 1. NetworkTracker (`utils/NetworkTracker.py`)

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
- `PV`: 페이지 뷰
- `Module Exposure`: 모듈 노출
- `Product Exposure`: 상품 노출
- `Product Click`: 상품 클릭
- `PDP PV`: 상품 상세 페이지 뷰

### 2. SrpPage (`pom/SrpPage.py`)

검색 결과 페이지의 상호작용을 담당하는 Page Object Model입니다.

**주요 메서드:**
- `search_product(keyword)`: 키워드로 상품 검색
- `search_module_by_title(module_title)`: 모듈 타이틀로 모듈 찾기
- `assert_item_in_module(module_title)`: 모듈 내 상품 노출 확인 및 상품번호 반환
- `get_product_price_info(goodscode)`: 상품의 가격 정보 추출
- `montelena_goods_click(goodscode)`: 상품 클릭 및 새 페이지 이동

**가격 정보 추출:**
```python
price_info = srp_page.get_product_price_info(goodscode)
# 반환 형식:
# {
#     "origin_price": "38000",      # 원가
#     "seller_price": "15390",      # 판매가
#     "discount_rate": "59",         # 할인률
#     "promotion_price": "16390",   # 프로모션가
#     "coupon_price": "13290"       # 쿠폰적용가
# }
```

### 3. validation_helpers (`utils/validation_helpers.py`)

트래킹 로그의 정합성을 검증하는 헬퍼 함수들입니다.

**주요 함수:**
- `validate_tracking_logs()`: 트래킹 로그 정합성 검증
- `build_expected_from_module_config()`: `module_config.json`에서 예상 값 생성
- `replace_placeholders()`: 플레이스홀더를 실제 값으로 대체

## 📖 사용 방법


테스트 실행 후 `json/` 디렉토리에 다음 파일들이 생성됩니다:

- `tracking_pv_{goodscode}_{timestamp}.json`: PV 로그
- `tracking_module_exposure_{goodscode}_{timestamp}.json`: Module Exposure 로그
- `tracking_product_exposure_{goodscode}_{timestamp}.json`: Product Exposure 로그
- `tracking_product_click_{goodscode}_{timestamp}.json`: Product Click 로그
- `tracking_pdp_pv_{goodscode}_{timestamp}.json`: PDP PV 로그
- `tracking_all_{goodscode}_{timestamp}.json`: 전체 트래킹 로그

## 🔍 정합성 검증 프로세스

1. **HTML에서 가격 정보 추출**
   - 상품 클릭 전에 HTML 요소에서 원가, 판매가, 할인률 추출
   - URL 파라미터에서 프로모션가, 쿠폰적용가 추출

2. **트래킹 로그 수집**
   - `NetworkTracker`가 `aplus.gmarket.co.kr`의 POST 요청을 감지
   - 이벤트 타입별로 분류 및 필터링

3. **예상 값 생성**
   - `module_config.json`의 플레이스홀더를 실제 값으로 대체
   - `frontend_data`의 가격 정보와 검색어 사용

4. **검증 수행**
   - 트래킹 로그의 실제 값과 예상 값 비교
   - 불일치 시 에러 메시지 반환

## 📝 주의사항

1. **상품 클릭 전 가격 정보 추출**
   - `get_product_price_info()`는 상품 클릭 전에 호출해야 합니다.
   - 상품 클릭 후에는 페이지가 이동하여 HTML 요소에 접근할 수 없습니다.

2. **SPM 필터링**
   - Module Exposure와 Product Exposure 로그는 SPM 값으로 필터링됩니다.
   - `module_config.json`에 올바른 SPM 값이 설정되어 있어야 합니다.

3. **로그 저장**
   - 테스트 실행 중 네트워크 요청이 완료될 때까지 충분한 대기 시간을 확보해야 합니다.
   - `time.sleep(2)` 또는 `page.wait_for_load_state('networkidle')` 사용을 권장합니다.

## 🐛 문제 해결

### 로그가 수집되지 않는 경우

1. 네트워크 트래킹이 시작되었는지 확인 (`tracker.start()`)
2. 페이지 로딩이 완료되었는지 확인
3. `aplus.gmarket.co.kr` 도메인으로의 요청이 발생하는지 확인

### 정합성 검증 실패

1. `module_config.json`의 플레이스홀더가 올바르게 설정되었는지 확인
2. `frontend_data`에 필요한 가격 정보가 포함되어 있는지 확인
3. SPM 값이 올바른지 확인

## 📄 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

