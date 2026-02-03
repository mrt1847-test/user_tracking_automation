Feature: G마켓 PDP 트래킹 로그 정합성 검증
  상품 상세 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.
  
  Scenario: 가입 상품 상세 페이지에서 버튼 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 상품 옵션을 입력한다
    And 사용자가 PDP에서 "<module_title>" 버튼을 확인하고 클릭한다
    Then 버튼 "<module_title>"가 클릭되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    And PDP Join Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_join_click>)
    Examples:
      | goodscode  | module_title     | tc_join_click |
      | 2529094051 | 가입신청          | C1166932      | 

  Scenario: 상담 상품 상세 페이지에서 버튼 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "<module_title>" 버튼을 확인하고 클릭한다
    Then 버튼 "<module_title>"가 클릭되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    And PDP Rental Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_rental_click>)
    Examples:
      | goodscode  | module_title     | tc_rental_click |
      | 2698619898 | 상담신청          | C1166931      |
