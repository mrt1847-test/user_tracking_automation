"""
동작별 검증 규칙 정의
- 하드코딩 값: area_code 등 모듈별로 고정된 값
- 동적 값: price 등 프론트에서 읽어서 비교하는 값은 None으로 표시
- 이벤트 타입별로 구분: PV, Module Exposure, Product Exposure, Product Click, Product ATC Click
"""

SRP_VALIDATION_RULES = {
    "먼저 둘러보세요": {
        "module_exposure": {
            "required": True,  # 필수 이벤트인지
            "expected_values": {
                # @module.area_code 형식: JSON 파일에서 모듈별 값 자동 로드
                "gokey.params.params-exp.parsed.area_code": "@module.area_code",
            }
        },
        "product_exposure": {
            "required": True,
            "expected_values": {
                "gokey.params.params-exp.parsed.area_code": "@module.area_code",  # JSON에서 로드
                "gokey.params.params-exp.parsed._p_prod": None,  # goodscode로 동적 검증
            },
            "frontend_compare": {
                "price": "gokey.params.params-exp.parsed.price",  # 프론트에서 읽은 값과 비교
                "keyword": "gokey.params.params-exp.parsed.keyword"  # 검색어도 비교 가능
            }
        },
        "product_click": {
            "required": True,
            "expected_values": {
                "gokey.params.params-clk.parsed.area_code": "@module.area_code",  # JSON에서 로드
                "gokey.params.params-clk.parsed._p_prod": None,  # goodscode로 동적 검증
            }
        }
    },
    "추천 상품": {
        "module_exposure": {
            "required": True,
            "expected_values": {
                "gokey.params.params-exp.parsed.area_code": "@module.area_code",  # JSON에서 자동 로드
            }
        }
    }
}


