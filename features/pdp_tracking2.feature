Feature: G마켓 PDP 트래킹 로그 정합성 검증
  상품 상세 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.
  
  Scenario: 그룹 상품 상세 페이지에서 연관 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "3094794519"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "연관 상품"을 확인하고 클릭한다
    Then 레이어 "연관상품 상세보기"가 출력되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: C1166922)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: C1166923)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: C1166925)
    
  Scenario: 그룹 연관상품 상세보기 페이지에서 연관 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "3094794519"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "연관 상품"을 클릭한다
    And 사용자가 PDP에서 "연관상품 상세보기" 모듈 내 상품을 확인하고 클릭한다
    Then 레이어 "연관상품 상세보기"가 출력되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Product Click 로그가 정합성 검증을 통과해야 함 (TC: C1166927)
    And Product Minidetail 로그가 정합성 검증을 통과해야 함 (TC: C1166926)

  Scenario: 그룹 상품 상세 페이지에서 버튼 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "연관 상품"을 클릭한다
    And 사용자가 PDP에서 "<module_title>" 버튼을 확인하고 클릭한다
    Then 버튼 "<module_title>"가 클릭되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    And PDP Buynow Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_buynow_click>)
    And PDP ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)
    And PDP Gift Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_gift_click>)

    Examples:
      | goodscode  | module_title     | tc_buynow_click | tc_atc_click | tc_gift_click |
      | 4457587710 | 연관상품 구매하기 | C1166930        |              |               |
      | 4457587710 | 연관상품 장바구니 |                 | C1166929     |               |
      | 4457587710 | 연관상품 선물하기 |                 |              | C1166928      |

  Scenario: 상품 상세 페이지에서 버튼 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "<module_title>" 버튼을 확인하고 클릭한다
    Then 버튼 "<module_title>"가 클릭되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    And PDP Buynow Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_buynow_click>)
    And PDP ATC Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_atc_click>)
    And PDP Gift Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_gift_click>)

    Examples:
      | goodscode  | module_title     | tc_buynow_click | tc_atc_click | tc_gift_click |
      | 4448231882 | 일반상품 구매하기 | C1166905        |              |               |
      | 4448231882 | 일반상품 장바구니 |                 | C1166904     |               |
      | 4448231882 | 일반상품 선물하기 |                 |              | C1166903      |