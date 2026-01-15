"""
로그인 계정 정보 관리
.env 파일에서 회원 종류별 계정 정보를 읽어옴
config.json의 환경 설정에 따라 dev와 stg/prod로 분기
"""
import os
import json
from dotenv import load_dotenv
from typing import Dict

# .env 파일 로드
load_dotenv()


class MemberType:
    """회원 종류 상수"""
    NORMAL = "normal"  # 일반회원
    CLUB = "club"  # 클럽회원
    BUSINESS = "business"  # 사업자회원


def _load_config() -> Dict:
    """config.json 파일 로드"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _get_environment() -> str:
    """config.json에서 현재 환경 반환 (dev/stg/prod)"""
    config = _load_config()
    return config.get('environment', 'prod')


def _get_env_prefix() -> str:
    """
    환경에 따른 환경 변수 접두사 반환
    
    Returns:
        dev: "DEV_"
        stg/prod: "" (접두사 없음)
    """
    environment = _get_environment()
    
    # stg/prod는 하나의 분기로 처리 (접두사 없음)
    if environment == 'dev':
        return "DEV_"
    elif environment in ['stg', 'prod']:
        return ""
    else:
        raise ValueError(f"지원하지 않는 환경입니다: {environment}. (dev/stg/prod)")


def get_credentials(member_type: str) -> Dict[str, str]:
    """
    회원 종류별 계정 정보 반환
    config.json의 환경 설정에 따라 dev와 stg/prod로 분기
    
    Args:
        member_type: 회원 종류 (normal/club/business)
    
    Returns:
        {"username": str, "password": str}
    
    Raises:
        ValueError: 회원 종류가 잘못되었거나 계정 정보가 없을 때
    """
    member_type_map = {
        MemberType.NORMAL: {
            "base_id_key": "NORMAL_MEMBER_ID",
            "base_password_key": "NORMAL_MEMBER_PASSWORD",
            "name": "일반회원"
        },
        MemberType.CLUB: {
            "base_id_key": "CLUB_MEMBER_ID",
            "base_password_key": "CLUB_MEMBER_PASSWORD",
            "name": "클럽회원"
        },
        MemberType.BUSINESS: {
            "base_id_key": "BUSINESS_MEMBER_ID",
            "base_password_key": "BUSINESS_MEMBER_PASSWORD",
            "name": "사업자회원"
        }
    }
    
    if member_type not in member_type_map:
        raise ValueError(f"지원하지 않는 회원 종류입니다: {member_type}. (normal/club/business)")
    
    # 환경에 따른 접두사 가져오기
    env_prefix = _get_env_prefix()
    environment = _get_environment()
    
    config = member_type_map[member_type]
    
    # 환경 변수 키 생성 (접두사 추가)
    id_key = f"{env_prefix}{config['base_id_key']}" if env_prefix else config['base_id_key']
    password_key = f"{env_prefix}{config['base_password_key']}" if env_prefix else config['base_password_key']
    
    username = os.getenv(id_key)
    password = os.getenv(password_key)
    
    if not username or not password:
        raise ValueError(
            f"{config['name']} 계정 정보가 .env 파일에 설정되지 않았습니다. "
            f"환경: {environment}, 키: {id_key}, {password_key}"
        )
    
    return {
        "username": username,
        "password": password
    }

