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
    And PDP PV 로그가 정합성 검증을 통과해야 함 (TC: <tc_pdp_pv>)
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)
    Then 모든 로그 검증이 완료되었음

    Examples:
      | keyword | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | tc_pdp_pv | tc_atc_click |
      | 물티슈   | 오늘의 프라임상품     | C12345             | C12346              | C12347           | C12348    |             |
      | 물티슈   | 먼저 둘러보세요     | C12345             | C12346              | C12347           | C12348    |             |
      | 물티슈   | 인기 상품이에요     | C12345             | C12346              | C12347           | C12348    |             |
      | 물티슈   | 오늘의 상품이에요   | C12345             | C12346              | C12347           | C12348    |             |
      | 생수     | 오늘의 슈퍼딜      | C12345             | C12346              | C12347           | C12348    |             |
      | 생수     | 스타배송           | C12345             | C12346              | C12347           | C12348    |             |
      | 물티슈   | 일반상품           | C12345             | C12346              | C12347           | C12348    |             |
  
  Scenario: 검색 결과 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증
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
    And PDP PV 로그가 정합성 검증을 통과해야 함 (TC: <tc_pdp_pv>)
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)
    Then 모든 로그 검증이 완료되었음

    Examples:
      | keyword | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | tc_pdp_pv | tc_atc_click |
      | 아디다스   | 백화점 브랜드   | C12345             | C12346              | C12347           | C12348    |             |
      | 원피스   | 4.5 이상         | C12345             | C12346              | C12347           | C12348    |             |
      | LG전자   | 브랜드 인기상품    | C12345             | C12346              | C12347           | C12348    |             |
    