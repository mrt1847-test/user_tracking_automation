Feature: G마켓 PDP 트래킹 로그 정합성 검증
  상품 상세 페이지에서 상품 클릭 시 트래킹 로그의 정합성을 검증합니다.

  Scenario: 이마트몰 상품 상세 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 이마트몰 PDP에서 "<module_title>" 모듈 내 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
        
    Examples:
      | goodscode  | module_title                | tc_module_exposure | tc_product_exposure | tc_product_click |
      | 3714977969 | 함께 보면 좋은 상품이에요     | C1165044           | C1165045            | C1165047         |
      | 2519122999 | 함께 구매하면 좋은 상품이에요 | C1165052           | C1165053            | C1165055         |
      | 2519122999 | 이 브랜드의 인기상품         | C1165060           | C1165061            | C1165064         |
      | 2519122999 | 점포 행사 상품이에요         | C1165056           | C1165057            | C1165059         |
  
  
  Scenario: 상품 상세 페이지에서 모듈별 상품 클릭 시 트래킹 로그 검증
    Given G마켓 홈 페이지에 접속했음
    And 네트워크 트래킹이 시작되었음
    And 상품 "<goodscode>"의 상세페이지로 접속했음
    When 사용자가 PDP에서 "<module_title>" 모듈 내 상품을 확인하고 클릭한다
    Then 상품 페이지로 이동되었다
    Then 모든 트래킹 로그를 JSON 파일로 저장함
    Then Module Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_module_exposure>)
    And Product Exposure 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_exposure>)
    And Product Click 로그가 정합성 검증을 통과해야 함 (TC: <tc_product_click>)
        

    Examples:
      | goodscode  | module_title                | tc_module_exposure | tc_product_exposure | tc_product_click |
      | 4448231882 | 함께 보면 좋은 상품이에요     | C1164945           | C1164946            | C1164948         |
      | 4448231882 | 함께 구매하면 좋은 상품이에요 | C1164949           | C1164950            | C1164952         |
      | 4448231882 | 이 판매자의 인기상품이에요    | C1164953           |	C1164954            | C1164956         |

