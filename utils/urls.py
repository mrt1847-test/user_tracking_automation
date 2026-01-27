"""
G마켓 URL 관리
환경별 URL 설정을 직접 관리
"""
import json
import os
from typing import Dict
from pathlib import Path


# 환경별 URL 설정
_URLS = {
    "dev": {
        "base": "https://www-dev.gmarket.co.kr",
        "item": "https://item-dev.gmarket.co.kr",
        "cart": "https://cart-dev.gmarket.co.kr",
        "checkout": "https://checkout-dev.gmarket.co.kr"
    },
    "stg": {
        "base": "https://www-stg.gmarket.co.kr",
        "item": "https://item-stg.gmarket.co.kr",
        "cart": "https://cart-av.gmarket.co.kr",
        "checkout": "https://checkout-av.gmarket.co.kr"
    },
    "prod": {
        "base": "https://www.gmarket.co.kr",
        "item": "https://item.gmarket.co.kr",
        "cart": "https://cart.gmarket.co.kr",
        "checkout": "https://checkout.gmarket.co.kr"
    }
}


def _get_environment() -> str:
    """config.json에서 현재 환경 반환 (dev/stg/prod)"""
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('environment', 'prod')
    except (FileNotFoundError, json.JSONDecodeError):
        # config.json이 없거나 읽을 수 없으면 기본값 'prod' 반환
        return 'prod'


def _get_environment_urls() -> Dict[str, str]:
    """현재 환경의 URL 설정 반환"""
    environment = _get_environment()
    
    if environment not in _URLS:
        raise ValueError(f"지원하지 않는 환경입니다: {environment}. (dev/stg/prod)")
    
    return _URLS[environment]


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
    global _env_urls
    if _env_urls is None:
        _env_urls = _get_environment_urls()
    return _env_urls['cart']


def _get_checkout_base_url() -> str:
    """주문/결제 기본 URL 반환"""
    global _env_urls
    if _env_urls is None:
        _env_urls = _get_environment_urls()
    return _env_urls['checkout']


def base_url() -> str:
    """기본 URL 반환"""
    return _get_base_url()


def item_base_url() -> str:
    """상품 페이지 기본 URL 반환"""
    return _get_item_base_url()


def cart_base_url() -> str:
    """장바구니 기본 URL 반환"""
    return _get_cart_base_url()


def checkout_base_url() -> str:
    """주문/결제 기본 URL 반환"""
    return _get_checkout_base_url()


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


def order_complete_url(pno: str, spm: str = None) -> str:
    """주문 완료 페이지 URL
    
    Args:
        pno: 주문번호 (pno 파라미터)
        spm: SPM 파라미터 (선택적)
    
    Returns:
        주문 완료 페이지 URL (예: https://checkout-dev.gmarket.co.kr/ko/pc/complete?pno=4228111871&spm=gmktpc.ordersheet.order.d0#/)
    """
    base = f"{checkout_base_url()}/ko/pc/complete"
    params = []
    
    params.append(f"pno={pno}")
    if spm:
        params.append(f"spm={spm}")
    
    return f"{base}?{'&'.join(params)}#/"


# 기본 URL 상수 (하위 호환성, 함수 호출)
BASE_URL = base_url()
CART_URL = cart_url()

