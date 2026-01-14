Feature: G마켓 SRP 트래킹 로그 정합성 검증
  검색 결과 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.

  Scenario: 검색 결과 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가 "<keyword>"로 검색함
    And "<module_title>" 모듈을 찾음
    And 모듈 내 상품을 확인함
    And 상품 가격 정보를 추출함
    And 상품을 클릭함
    And 네트워크 요청이 완료될 때까지 대기함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
    And PDP PV 로그가 정합성 검증을 통과해야 함 (TC: <tc_pdp_pv>)

    Examples:
      | keyword | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | tc_pdp_pv |
      | 물티슈   | 먼저 둘러보세요     | C12345             | C12346              | C12347           | C12348    |
      | 물티슈   | 일반상품           | C12345             | C12346              | C12347           | C12348    |