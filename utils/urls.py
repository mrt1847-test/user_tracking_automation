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


def _get_cart_base_url() -> str:
    """장바구니 기본 URL 반환"""
    # cart 도메인은 환경별로 다를 수 있으므로 base URL에서 도메인 추출
    base = _get_base_url()
    # www.gmarket.co.kr -> cart.gmarket.co.kr
    if 'www' in base:
        return base.replace('www', 'cart')
    # dev/stg 환경 처리
    if '-dev' in base:
        return base.replace('www-dev', 'cart-dev')
    if '-stg' in base:
        return base.replace('www-stg', 'cart-stg')
    return base.replace('www', 'cart')


def base_url() -> str:
    """기본 URL 반환"""
    return _get_base_url()


def item_base_url() -> str:
    """상품 페이지 기본 URL 반환"""
    return _get_item_base_url()


def cart_base_url() -> str:
    """장바구니 기본 URL 반환"""
    return _get_cart_base_url()


def search_url(keyword: str, spm: str = None) -> str:
    """검색 결과 페이지 URL
    
    Args:
        keyword: 검색 키워드
        spm: SPM 파라미터 (선택적)
    
    Returns:
        검색 결과 페이지 URL
    """
    base = f"{base_url()}/n/search"
    params = []
    
    if spm:
        params.append(f"spm={spm}")
    params.append(f"keyword={keyword}")
    
    return f"{base}?{'&'.join(params)}"


def product_url(goodscode: str, spm: str = None) -> str:
    """상품 상세 페이지 URL
    
    Args:
        goodscode: 상품 코드
        spm: SPM 파라미터 (선택적)
    
    Returns:
        상품 상세 페이지 URL
    """
    base = f"{item_base_url()}/Item"
    params = []
    
    if spm:
        params.append(f"spm={spm}")
    params.append(f"goodscode={goodscode}")
    
    return f"{base}?{'&'.join(params)}"


def cart_url(spm: str = None) -> str:
    """장바구니 URL 반환
    
    Args:
        spm: SPM 파라미터 (선택적)
    
    Returns:
        장바구니 URL (예: https://cart.gmarket.co.kr/ko/pc/cart/?spm=...#/)
    """
    base = f"{cart_base_url()}/ko/pc/cart/"
    
    if spm:
        return f"{base}?spm={spm}#/"
    return f"{base}#/"


def list_url(category_id: str, spm: str = None) -> str:
    """카테고리 리스트 페이지 URL
    
    Args:
        category_id: 카테고리 ID
        spm: SPM 파라미터 (선택적)
    
    Returns:
        카테고리 리스트 페이지 URL
    """
    base = f"{base_url()}/n/list"
    params = []
    
    if spm:
        params.append(f"spm={spm}")
    params.append(f"category={category_id}")
    
    return f"{base}?{'&'.join(params)}"


# 기본 URL 상수 (하위 호환성, 함수 호출)
BASE_URL = base_url()
CART_URL = cart_url()

