import re
import json
import time
import logging
from urllib.parse import unquote
from typing import Dict, List, Optional, Any
from playwright.sync_api import Page, Request

# 로거 설정
logger = logging.getLogger(__name__)


class NetworkTracker:
    """
    aplus.gmarket 도메인의 POST 요청을 실시간으로 감지하고 분류하는 클래스
    """
    
    def __init__(self, page: Page):
        """
        NetworkTracker 초기화
        
        Args:
            page: Playwright Page 객체
        """
        self.page = page
        self.logs: List[Dict[str, Any]] = []
        self.is_tracking = False
        
        # 타겟 도메인 패턴
        self.domain_pattern = re.compile(r'aplus\.gmarket\.co(\.kr|m)')
    
    def _classify_request_type(self, url: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """
        URL 패턴과 payload를 분석하여 이벤트 타입을 세분화하여 분류
        
        Args:
            url: 요청 URL
            payload: 파싱된 payload (선택사항)
            
        Returns:
            'PV', 'Module Exposure', 'Product Exposure', 'Product Click', 'Product A2C Click', 또는 'Unknown'
        """
        url_lower = url.lower()
        
        # PV: gif 요청
        if 'gif' in url_lower:
            return 'PV'
        
        # Exposure 타입 구분
        elif 'exposure' in url_lower:
            # payload를 분석하여 Module Exposure vs Product Exposure 구분
            if payload and isinstance(payload, dict):
                decoded_gokey = payload.get('decoded_gokey', {})
                params = decoded_gokey.get('params', {})
                
                # expdata가 있고 모듈 정보가 있으면 Module Exposure
                if 'expdata' in params:
                    return 'Module Exposure'
                # _p_prod가 있으면 Product Exposure
                elif self._has_product_info(params):
                    return 'Product Exposure'
            
            return 'Exposure'  # 기본값
        
        # Click 타입 구분
        elif 'click' in url_lower:
            if payload and isinstance(payload, dict):
                decoded_gokey = payload.get('decoded_gokey', {})
                params = decoded_gokey.get('params', {})
                
                # A2C 관련 파라미터가 있으면 Product A2C Click
                if self._is_a2c_click(params):
                    return 'Product A2C Click'
                # _p_prod가 있으면 Product Click
                elif self._has_product_info(params):
                    return 'Product Click'
            
            return 'Click'  # 기본값
        
        return 'Unknown'
    
    def _has_product_info(self, params: Dict[str, Any]) -> bool:
        """
        params에 상품 정보(_p_prod)가 있는지 확인
        
        Args:
            params: decoded_gokey의 params 딕셔너리
        
        Returns:
            _p_prod가 있으면 True, 없으면 False
        """
        def find_value_recursive(obj: Any, target_key: str, visited: Optional[set] = None) -> bool:
            """재귀적으로 _p_prod 찾기"""
            if visited is None:
                visited = set()
            
            if isinstance(obj, (dict, list)):
                obj_id = id(obj)
                if obj_id in visited:
                    return False
                visited.add(obj_id)
            
            if isinstance(obj, dict):
                if target_key in obj:
                    return True
                
                if 'parsed' in obj and isinstance(obj['parsed'], (dict, list)):
                    if find_value_recursive(obj['parsed'], target_key, visited):
                        return True
                
                for value in obj.values():
                    if find_value_recursive(value, target_key, visited):
                        return True
            
            elif isinstance(obj, list):
                for item in obj:
                    if find_value_recursive(item, target_key, visited):
                        return True
            
            if isinstance(obj, (dict, list)):
                visited.discard(id(obj))
            
            return False
        
        return find_value_recursive(params, '_p_prod')
    
    def _is_a2c_click(self, params: Dict[str, Any]) -> bool:
        """
        A2C 클릭인지 확인 (구매 버튼 관련 파라미터 확인)
        
        Args:
            params: decoded_gokey의 params 딕셔너리
        
        Returns:
            A2C 클릭이면 True, 아니면 False
        """
        # A2C 관련 키워드 확인
        a2c_keywords = ['add_to_cart', 'buy_now', 'a2c', 'purchase', 'addtocart']
        
        def check_in_value(obj: Any, keywords: List[str], visited: Optional[set] = None) -> bool:
            """재귀적으로 A2C 키워드 찾기"""
            if visited is None:
                visited = set()
            
            if isinstance(obj, (dict, list)):
                obj_id = id(obj)
                if obj_id in visited:
                    return False
                visited.add(obj_id)
            
            if isinstance(obj, dict):
                # 키 이름 확인
                for key in obj.keys():
                    key_lower = str(key).lower()
                    if any(keyword in key_lower for keyword in keywords):
                        return True
                
                # 값 확인
                for value in obj.values():
                    if isinstance(value, str):
                        value_lower = value.lower()
                        if any(keyword in value_lower for keyword in keywords):
                            return True
                    elif check_in_value(value, keywords, visited):
                        return True
            
            elif isinstance(obj, list):
                for item in obj:
                    if check_in_value(item, keywords, visited):
                        return True
            
            elif isinstance(obj, str):
                obj_lower = obj.lower()
                if any(keyword in obj_lower for keyword in keywords):
                    return True
            
            if isinstance(obj, (dict, list)):
                visited.discard(id(obj))
            
            return False
        
        return check_in_value(params, a2c_keywords)
    
    def _decode_utlogmap(self, utlogmap_str: str) -> Optional[Dict[str, Any]]:
        """
        utLogMap 문자열을 디코딩하고 JSON 파싱
        
        Args:
            utlogmap_str: URL 인코딩된 utLogMap 문자열
        
        Returns:
            파싱된 JSON 객체 또는 None
        """
        try:
            # 여러 번 디코딩 시도 (다중 인코딩 가능)
            decoded = utlogmap_str
            for _ in range(3):  # 최대 3번 디코딩 시도
                try:
                    decoded = unquote(decoded)
                    # JSON 파싱 시도
                    try:
                        return json.loads(decoded)
                    except json.JSONDecodeError:
                        continue
                except:
                    break
            return None
        except Exception as e:
            logger.debug(f'utLogMap 디코딩 실패: {e}')
            return None
    
    def _decode_params_exp_or_clk(self, params_str: str) -> Dict[str, Any]:
        """
        params-exp 또는 params-clk 문자열을 디코딩하고 파싱
        
        Args:
            params_str: URL 인코딩된 params-exp/clk 문자열
        
        Returns:
            디코딩된 파라미터 딕셔너리
        """
        decoded_params = {}
        
        if not params_str:
            return decoded_params
        
        try:
            # URL 디코딩
            decoded = unquote(params_str)
            
            # &로 분리하여 각 파라미터 파싱
            for item in decoded.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    decoded_key = unquote(key)
                    decoded_value = unquote(value)
                    
                    # utLogMap은 별도로 JSON 파싱
                    if decoded_key == 'utLogMap':
                        parsed_utlogmap = self._decode_utlogmap(decoded_value)
                        decoded_params[decoded_key] = {
                            'raw': decoded_value,
                            'parsed': parsed_utlogmap
                        }
                    else:
                        decoded_params[decoded_key] = decoded_value
                        
        except Exception as e:
            logger.debug(f'params-exp/clk 디코딩 중 오류: {e}')
            decoded_params['_raw'] = params_str
        
        return decoded_params
    
    def _decode_expdata(self, expdata_str: str) -> Optional[List[Dict[str, Any]]]:
        """
        expdata JSON 문자열을 파싱하고 내부 params-exp 디코딩
        
        Args:
            expdata_str: JSON 문자열
        
        Returns:
            디코딩된 expdata 배열 또는 None
        """
        try:
            # JSON 파싱
            expdata = json.loads(expdata_str)
            
            if not isinstance(expdata, list):
                return None
            
            # 각 아이템의 exargs.params-exp 디코딩
            decoded_items = []
            for item in expdata:
                decoded_item = item.copy() if isinstance(item, dict) else {}
                
                if isinstance(item, dict) and 'exargs' in item:
                    exargs = item['exargs']
                    if isinstance(exargs, dict):
                        decoded_exargs = exargs.copy()
                        
                        # params-exp 디코딩
                        if 'params-exp' in exargs:
                            params_exp_raw = exargs['params-exp']
                            decoded_params = self._decode_params_exp_or_clk(str(params_exp_raw))
                            decoded_exargs['params-exp'] = {
                                'raw': params_exp_raw,
                                'parsed': decoded_params
                            }
                        
                        # params-clk 디코딩 (혹시 있을 경우)
                        if 'params-clk' in exargs:
                            params_clk_raw = exargs['params-clk']
                            decoded_params = self._decode_params_exp_or_clk(str(params_clk_raw))
                            decoded_exargs['params-clk'] = {
                                'raw': params_clk_raw,
                                'parsed': decoded_params
                            }
                        
                        decoded_item['exargs'] = decoded_exargs
                
                decoded_items.append(decoded_item)
            
            return decoded_items
            
        except Exception as e:
            logger.debug(f'expdata 디코딩 중 오류: {e}')
            return None
    
    def _decode_gokey(self, gokey: str) -> Dict[str, Any]:
        """
        gokey 문자열을 디코딩하고 파싱 (다단계 중첩 구조 지원)
        
        구조:
        - Payload (최상위)
        - gokey (1차 중첩 - URL 인코딩)
        - expdata (2차 중첩 - JSON 문자열)
        - params-exp (3차 중첩 - URL 인코딩, expdata 내부)
        - utLogMap (4차 중첩 - 다중 인코딩된 JSON)
        
        Args:
            gokey: URL 인코딩된 gokey 문자열
            
        Returns:
            디코딩된 gokey 정보를 담은 딕셔너리
        """
        decoded_data = {}
        
        try:
            # 1. 전체 gokey 디코딩
            decoded_gokey = unquote(gokey)
            decoded_data['decoded_gokey'] = decoded_gokey
            
            # 2. gokey를 &로 분리하여 각 파라미터 파싱
            params = {}
            for item in decoded_gokey.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    decoded_key = unquote(key)
                    decoded_value = unquote(value)
                    
                    # expdata는 JSON 파싱 및 내부 디코딩 필요
                    if decoded_key == 'expdata':
                        decoded_expdata = self._decode_expdata(decoded_value)
                        params[decoded_key] = {
                            'raw': decoded_value,
                            'parsed': decoded_expdata
                        }
                    # params-clk 또는 params-exp 같은 파라미터는 추가 디코딩 필요
                    elif decoded_key in ['params-clk', 'params-exp']:
                        decoded_params = self._decode_params_exp_or_clk(decoded_value)
                        params[decoded_key] = {
                            'raw': decoded_value,
                            'parsed': decoded_params
                        }
                    else:
                        params[decoded_key] = decoded_value
            
            decoded_data['params'] = params
            
        except Exception as e:
            logger.warning(f'gokey 디코딩 중 오류 발생: {e}')
            decoded_data['error'] = str(e)
            decoded_data['raw'] = gokey
        
        return decoded_data
    
    def _decode_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload에서 gokey를 디코딩하여 decoded_payload에 추가
        
        Args:
            payload: 원본 payload 딕셔너리
            
        Returns:
            디코딩된 정보가 추가된 payload 딕셔너리
        """
        if not isinstance(payload, dict):
            return payload
        
        decoded_payload = payload.copy()
        
        # gokey가 있으면 디코딩
        if 'gokey' in payload and payload['gokey']:
            try:
                decoded_gokey_info = self._decode_gokey(str(payload['gokey']))
                decoded_payload['decoded_gokey'] = decoded_gokey_info
                logger.debug(f'gokey 디코딩 완료: {list(decoded_gokey_info.get("params", {}).keys())}')
            except Exception as e:
                logger.warning(f'gokey 디코딩 실패: {e}')
        
        return decoded_payload
    
    def _parse_payload(self, post_data: Optional[str]) -> Any:
        """
        POST Body 데이터를 파싱
        
        Args:
            post_data: POST Body 문자열
            
        Returns:
            파싱된 데이터 (dict 또는 str)
        """
        if not post_data:
            return None
        
        # JSON 파싱 시도
        try:
            parsed = json.loads(post_data)
            # dict인 경우 gokey 디코딩 수행
            if isinstance(parsed, dict):
                return self._decode_payload(parsed)
            return parsed
        except (json.JSONDecodeError, TypeError):
            # JSON이 아니면 raw string 반환
            return post_data
    
    def _on_request(self, request: Request):
        """
        네트워크 요청 이벤트 핸들러
        
        Args:
            request: Playwright Request 객체
        """
        if not self.is_tracking:
            return
        
        try:
            url = request.url()
            method = request.method()
            
            # 도메인 필터링
            if not self.domain_pattern.search(url):
                return
            
            # POST 메소드만 수집
            if method != 'POST':
                return
            
            # POST Body 가져오기
            post_data = request.post_data()
            parsed_payload = self._parse_payload(post_data)
            
            # 요청 타입 분류 (payload 포함하여 세분화)
            request_type = self._classify_request_type(url, parsed_payload)
            
            # 로그 저장
            log_entry = {
                'type': request_type,
                'url': url,
                'payload': parsed_payload,
                'timestamp': time.time(),
                'method': method
            }
            
            self.logs.append(log_entry)
            logger.info(f'{request_type} 요청 감지: {url}')
            
        except Exception as e:
            # 에러 발생 시에도 트래킹은 계속 진행
            logger.error(f'요청 처리 중 오류 발생: {e}', exc_info=True)
    
    def start(self):
        """
        네트워크 트래킹 시작
        """
        if self.is_tracking:
            logger.warning('이미 트래킹이 시작되어 있습니다.')
            return
        
        self.is_tracking = True
        self.page.on('request', self._on_request)
        logger.info('네트워크 트래킹 시작')
    
    def stop(self):
        """
        네트워크 트래킹 중지
        """
        if not self.is_tracking:
            logger.warning('트래킹이 시작되지 않았습니다.')
            return
        
        self.is_tracking = False
        # Playwright sync_api에서는 같은 핸들러를 off()에 전달하여 제거
        try:
            self.page.off('request', self._on_request)
        except Exception as e:
            # off()가 실패하더라도 is_tracking 플래그로 제어되므로 계속 진행
            logger.warning(f'리스너 제거 시도 중 오류 (무시됨): {e}')
        logger.info('네트워크 트래킹 중지')
    
    def get_logs(self, request_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        수집된 로그 조회
        
        Args:
            request_type: 필터링할 타입 ('PV', 'Exposure', 'Click', 'Unknown')
                         None이면 모든 로그 반환
        
        Returns:
            로그 리스트
        """
        if request_type:
            return [log for log in self.logs if log['type'] == request_type]
        return self.logs.copy()
    
    def get_pv_logs(self) -> List[Dict[str, Any]]:
        """
        PV 타입 로그만 반환
        
        Returns:
            PV 로그 리스트
        """
        return self.get_logs('PV')
    
    def get_exposure_logs(self) -> List[Dict[str, Any]]:
        """
        Exposure 타입 로그만 반환
        
        Returns:
            Exposure 로그 리스트
        """
        return self.get_logs('Exposure')
    
    def get_click_logs(self) -> List[Dict[str, Any]]:
        """
        Click 타입 로그만 반환
        
        Returns:
            Click 로그 리스트
        """
        return self.get_logs('Click')
    
    def _extract_goodscode_from_log(self, log: Dict[str, Any]) -> Optional[str]:
        """
        로그에서 goodscode 추출 (다단계 중첩 구조 지원)
        - Exposure: expdata -> exargs -> params-exp -> _p_prod 또는 utLogMap.x_object_id
        - Click: params-clk -> _p_prod 또는 utLogMap.x_object_id
        
        _p_prod와 x_object_id 둘 다 확인하여, 둘 중 하나라도 존재하면 반환
        
        Args:
            log: 로그 딕셔너리
        
        Returns:
            추출된 goodscode (_p_prod 우선, 없으면 x_object_id) 또는 None
        """
        def find_value_recursive(obj: Any, target_keys: List[str], visited: Optional[set] = None) -> Optional[str]:
            """
            재귀적으로 딕셔너리/리스트를 탐색하여 target_keys 중 하나를 찾음
            순환 참조 방지를 위해 visited set 사용
            
            Args:
                obj: 탐색할 객체 (dict, list, 또는 기타)
                target_keys: 찾을 키 목록 (우선순위 순서)
                visited: 방문한 객체 ID 집합 (순환 참조 방지)
            
            Returns:
                찾은 값의 문자열 변환 또는 None
            """
            if visited is None:
                visited = set()
            
            # 순환 참조 방지 (dict와 list만 체크)
            if isinstance(obj, (dict, list)):
                obj_id = id(obj)
                if obj_id in visited:
                    return None
                visited.add(obj_id)
            
            # 딕셔너리인 경우
            if isinstance(obj, dict):
                # 우선순위에 따라 키 확인 (_p_prod 우선)
                for key in target_keys:
                    if key in obj:
                        value = obj[key]
                        if value:
                            return str(value)
                
                # 'parsed' 키가 있으면 우선적으로 탐색 (디코딩된 데이터 구조)
                if 'parsed' in obj and isinstance(obj['parsed'], (dict, list)):
                    result = find_value_recursive(obj['parsed'], target_keys, visited)
                    if result:
                        return result
                
                # 모든 값에 대해 재귀 탐색
                for value in obj.values():
                    result = find_value_recursive(value, target_keys, visited)
                    if result:
                        return result
            
            # 리스트인 경우
            elif isinstance(obj, list):
                for item in obj:
                    result = find_value_recursive(item, target_keys, visited)
                    if result:
                        return result
            
            # 방문 기록 제거 (재귀 종료 시)
            if isinstance(obj, (dict, list)):
                visited.discard(id(obj))
            
            return None
        
        payload = log.get('payload')
        
        if not isinstance(payload, dict):
            return None
        
        # 1. payload 최상위에서 x_object_id 확인
        if 'x_object_id' in payload:
            value = payload['x_object_id']
            if value:
                return str(value)
        
        # 2. payload에서 직접 확인 (다양한 키 이름 시도)
        for key in ['goodscode', 'goodsCode', 'goods_code', 'goodscd', 'goodsCd']:
            if key in payload:
                value = payload[key]
                if value:
                    return str(value)
        
        # 3. decoded_gokey 내부를 재귀적으로 탐색
        # _p_prod를 우선적으로 찾고, 없으면 x_object_id 찾기
        decoded_gokey = payload.get('decoded_gokey', {})
        if decoded_gokey:
            # _p_prod 우선 탐색
            result = find_value_recursive(decoded_gokey, ['_p_prod'])
            if result:
                return result
            
            # x_object_id 탐색
            result = find_value_recursive(decoded_gokey, ['x_object_id'])
            if result:
                return result
        
        # 4. decoded_gokey의 params에서 직접 확인 (다양한 키 이름 시도)
        params = decoded_gokey.get('params', {})
        for key in ['goodscode', 'goodsCode', 'goods_code', 'goodscd', 'goodsCd']:
            if key in params:
                value = params[key]
                if value:
                    return str(value)
        
        return None
    
    def get_logs_by_goodscode(self, goodscode: str, request_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 로그 필터링
        
        Args:
            goodscode: 상품 번호
            request_type: 필터링할 타입 ('PV', 'Exposure', 'Click', 'Unknown'). None이면 모든 타입
        
        Returns:
            해당 goodscode와 일치하는 로그 리스트
        """
        filtered_logs = []
        
        for log in self.logs:
            # 타입 필터링
            if request_type and log.get('type') != request_type:
                continue
            
            # goodscode 추출 및 비교
            log_goodscode = self._extract_goodscode_from_log(log)
            if log_goodscode and log_goodscode == goodscode:
                filtered_logs.append(log)
        
        return filtered_logs
    
    def get_pv_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 PV 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 PV 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'PV')
    
    def get_exposure_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Exposure 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Exposure 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Exposure')
    
    def get_click_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Click 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Click 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Click')
    
    def get_module_exposure_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Module Exposure 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Module Exposure 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Module Exposure')
    
    def get_product_exposure_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Product Exposure 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Product Exposure 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Product Exposure')
    
    def get_product_click_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Product Click 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Product Click 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Product Click')
    
    def get_product_a2c_click_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Product A2C Click 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 Product A2C Click 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'Product A2C Click')
    
    def get_decoded_gokey_params(self, log: Dict[str, Any], param_key: Optional[str] = None) -> Dict[str, Any]:
        """
        로그에서 디코딩된 gokey 파라미터 조회
        
        Args:
            log: 로그 딕셔너리
            param_key: 특정 파라미터 키 (예: 'params-clk', 'params-exp'). None이면 전체 파라미터 반환
        
        Returns:
            디코딩된 파라미터 딕셔너리
        """
        payload = log.get('payload')
        
        if not isinstance(payload, dict):
            return {}
        
        decoded_gokey = payload.get('decoded_gokey', {})
        params = decoded_gokey.get('params', {})
        
        if param_key:
            return params.get(param_key, {})
        
        return params
    
    def validate_payload(self, log: Dict[str, Any], expected_data: Dict[str, Any]) -> bool:
        """
        로그의 payload 정합성 검증 (디코딩된 값 사용, 개선된 버전)
        
        Args:
            log: 검증할 로그 딕셔너리
            expected_data: 기대하는 데이터 (키-값 쌍)
                          - 경로 방식: 'gokey.params.params-exp.parsed._p_prod' (기존 방식 지원)
                          - 재귀 탐색: '_p_prod' (자동으로 찾음, 간단한 키 이름만 제공)
                          - 일반 키: 'pageId' (payload 최상위 키)
        
        Returns:
            검증 성공 시 True, 실패 시 AssertionError 발생
        
        Raises:
            AssertionError: 검증 실패 시
        """
        def find_value_by_path(obj: Dict[str, Any], path: str) -> Optional[Any]:
            """경로를 따라 값을 찾기"""
            keys = path.split('.')
            current = obj
            for key in keys:
                if current is None or not isinstance(current, dict):
                    return None
                current = current.get(key)
            return current
        
        def find_value_recursive(obj: Any, target_key: str, visited: Optional[set] = None) -> Optional[Any]:
            """재귀적으로 키를 찾아서 값 반환"""
            if visited is None:
                visited = set()
            
            if isinstance(obj, (dict, list)):
                obj_id = id(obj)
                if obj_id in visited:
                    return None
                visited.add(obj_id)
            
            if isinstance(obj, dict):
                if target_key in obj:
                    return obj[target_key]
                
                if 'parsed' in obj and isinstance(obj['parsed'], (dict, list)):
                    result = find_value_recursive(obj['parsed'], target_key, visited)
                    if result is not None:
                        return result
                
                for value in obj.values():
                    result = find_value_recursive(value, target_key, visited)
                    if result is not None:
                        return result
            
            elif isinstance(obj, list):
                for item in obj:
                    result = find_value_recursive(item, target_key, visited)
                    if result is not None:
                        return result
            
            if isinstance(obj, (dict, list)):
                visited.discard(id(obj))
            
            return None
        
        payload = log.get('payload')
        
        if payload is None:
            raise AssertionError(f"로그에 payload가 없습니다. URL: {log.get('url')}")
        
        # payload가 문자열인 경우 (JSON 파싱 실패한 경우)
        if isinstance(payload, str):
            raise AssertionError(
                f"payload가 JSON 형식이 아닙니다. "
                f"URL: {log.get('url')}, Payload: {payload[:100]}..."
            )
        
        # payload가 딕셔너리가 아닌 경우
        if not isinstance(payload, dict):
            raise AssertionError(
                f"payload가 딕셔너리 형식이 아닙니다. "
                f"URL: {log.get('url')}, Payload 타입: {type(payload)}"
            )
        
        # 기대 데이터 검증
        errors = []
        for key, expected_value in expected_data.items():
            actual_value = None
            
            # gokey 내부 파라미터 접근 (경로 방식)
            if key.startswith('gokey.params.'):
                param_path = key.replace('gokey.params.', '')
                actual_value = find_value_by_path(
                    payload.get('decoded_gokey', {}).get('params', {}),
                    param_path
                )
            
            # 재귀 탐색 방식 (간단한 키 이름만 제공)
            elif '.' not in key and key not in payload:
                # payload 전체에서 재귀적으로 찾기
                actual_value = find_value_recursive(payload, key)
            
            # 일반 payload 키 검증
            else:
                actual_value = payload.get(key)
            
            # 값 검증
            if actual_value is None:
                errors.append(f"키 '{key}'에 해당하는 값이 없습니다.")
            elif actual_value != expected_value:
                errors.append(
                    f"키 '{key}'의 값이 일치하지 않습니다. "
                    f"기대값: {expected_value}, 실제값: {actual_value}"
                )
        
        if errors:
            error_msg = "\n".join(errors)
            # 디코딩된 payload 정보 포함
            decoded_info = payload.get('decoded_gokey', {})
            raise AssertionError(
                f"Payload 검증 실패:\n{error_msg}\n"
                f"디코딩된 gokey 파라미터: {json.dumps(decoded_info.get('params', {}), ensure_ascii=False, indent=2)}"
            )
        
        return True
    
    def clear_logs(self):
        """
        수집된 모든 로그 초기화
        """
        self.logs.clear()
        logger.info('로그 초기화 완료')
    
    def __enter__(self):
        """
        Context manager 진입 시 자동으로 트래킹 시작
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager 종료 시 자동으로 트래킹 중지
        """
        self.stop()

