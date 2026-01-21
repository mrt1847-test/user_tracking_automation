Feature: G마켓 SRP 트래킹 로그 정합성 검증
  검색 결과 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.

  Scenario: 최상단 클릭아이템 모듈 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가"세탁세재""3386025906" 최상단 클릭아이템 모듈 패이지로 이동한다
    Then 검색 결과 페이지가 표시된다
    Given 검색 결과 페이지에 "최상단 클릭아이템" 모듈이 있다
    When 사용자가 "최상단 클릭아이템" 모듈 내 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: C1166807)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: C1166808)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: C1166810)
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: C1166811)

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
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)

    Examples:
      | keyword | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | tc_atc_click |
      | 물티슈   | 오늘의 프라임상품     | C1166813         | C1166814            | C1166816         |              |
      | 물티슈   | 먼저 둘러보세요     | C1166817           | C1166818            | C1166820         | C1166821     |
      | 물티슈   | 인기 상품이에요     | C1166829            | 	C1166830             | C1166832          | C1166833    |
      | 물티슈   | 오늘의 상품이에요   | C1166823             | C1166824          | C1166826         | C1166827   |
      | 생수     | 오늘의 슈퍼딜      | C1166841             | C1166842            | C1166844           |     |
      | 생수     | 스타배송           |             |             |          |   |
      | 물티슈   | 일반상품           | C1166835           | C1166836              | C1166838        | C1166839    |
      | 메가커피 1만원   | 대체검색어           | C1166861           | C1166862             | C1166864        | C1166865    |

  Scenario: 검색 결과 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증 type2
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가 "<keyword>"을 검색한다
    Then 검색 결과 페이지가 표시된다
    Given 사용자가 "<keyword>"을 검색했다
    And 검색 결과 페이지에 "<module_title>" 모듈이 있다 (type2)
    When 사용자가 "<module_title>" 모듈 내 상품을 확인하고 클릭한다 (type2)
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)

    Examples:
      | keyword | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | 
      | 아디다스   | 백화점 브랜드   | C1166845	            | 	C1166846            | C1166848          | 
      | 원피스   | 4.5 이상         | C1166853             | C1166854             | C1166856         |
      | LG전자   | 브랜드 인기상품    | C1166849             | C1166850              | C1166852        | 
      | 쿤달   | MD's Pick       | C1166857            | C1166858              | C1166860        | 
    