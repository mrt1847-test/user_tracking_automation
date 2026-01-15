"""
G마켓 URL 관리
config.json에서 환경 설정을 읽어 환경별 URL 반환
"""
import json
import os
from typing import Dict


def _load_config() -> Dict:
    """config.json 파일 로드"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _get_environment_urls() -> Dict[str, str]:
    """현재 환경의 URL 설정 반환"""
    config = _load_config()
    environment = config.get('environment', 'prod')
    urls = config.get('urls', {})
    
    if environment not in urls:
        raise ValueError(f"config.json에 '{environment}' 환경 설정이 없습니다.")
    
    return urls[environment]


# 환경별 URL 캐싱
_env_urls = None


def _get_base_url() -> str:
    """기본 URL 반환"""
    global _env_urls
    if _env_urls is None:
        _env_urls = _get_environment_urls()
    return _env_urls['base']


def _get_item_base_url() -> str:
    """상품 페이지 기본 URL 반환"""
    global _env_urls
    if _env_urls is None:
        _env_urls = _get_environment_urls()
    return _env_urls['item']


def search_url(keyword: str) -> str:
    """검색 결과 페이지 URL"""
    return f"{_get_base_url()}/n/search?keyword={keyword}"


def product_url(goodscode: str) -> str:
    """상품 상세 페이지 URL"""
    return f"{_get_item_base_url()}/Item?goodscode={goodscode}"


def base_url() -> str:
    """기본 URL 반환"""
    return _get_base_url()


def item_base_url() -> str:
    """상품 페이지 기본 URL 반환"""
    return _get_item_base_url()


def cart_url() -> str:
    """장바구니 URL 반환"""
    return f"{_get_base_url()}/ko/pc/cart"


# 기본 URL 상수 (하위 호환성, 함수 호출)
BASE_URL = base_url()
CART_URL = cart_url()

