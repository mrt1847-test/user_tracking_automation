Feature: G마켓 SRP 트래킹 로그 정합성 검증
  검색 결과 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.

  Scenario: 검색 결과 페이지에서 정렬후 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가 "<keyword>"을 검색한다
    Then 검색 결과 페이지가 표시된다
    Given 사용자가 "<keyword>"을 검색했다
    When 검색 결과 페이지에서 "<module_title>" 정렬을 선택한다
    When 사용자가 "<module_title>" 모듈 내 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)

    Examples:
      | keyword          | module_title      | tc_module_exposure | tc_product_exposure | tc_product_click | tc_atc_click   |
      | 물티슈            | 판매 인기순     | C1228806           | 	C1413801            | C1413802         | C1413803      |
      | 물티슈            | 상품평 많은순     | C1228846           | C1413804            | C1413805         | C1413806       |
      | 물티슈            | 신규 상품순     | C1228902           | C1413807            | C1413808        | C1413809       |

  Scenario: 검색 결과 페이지에서 정렬후 필터적용시시 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    When 사용자가 "<keyword>"을 검색한다
    Then 검색 결과 페이지가 표시된다
    Given 사용자가 "<keyword>"을 검색했다
    When 검색 결과 페이지에서 "<module_title>" 정렬을 선택한다
    And 사용자가 "content 필터" 필터 1번째를 적용한다
    When 사용자가 "<module_title>" 모듈 내 <n>번째 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
    And Product ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)

    Examples:
      | keyword          | module_title   | n | tc_module_exposure | tc_product_exposure | tc_product_click | tc_atc_click   |
      | 물티슈            | 판매 인기순     | 2 | C1228806           | C1413810            | C1413811         | C1413812       |
      | 물티슈            | 상품평 많은순   | 2 | C1228846           | C1413813            | C1413814         | C1413815       |
      | 물티슈            | 신규 상품순     | 2 | C1228902           | C1413816            | C1413817         | C1413818       |

     