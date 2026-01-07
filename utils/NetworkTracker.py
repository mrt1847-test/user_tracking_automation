import re
import json
import time
import logging
from urllib.parse import unquote
from typing import Dict, List, Optional, Any
from playwright.sync_api import Page, Request, BrowserContext

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
        self.context = page.context
        self.tracked_pages: List[Page] = [page]  # 추적 중인 페이지 목록
        self.logs: List[Dict[str, Any]] = []
        self.is_tracking = False
        
        # 타겟 도메인 패턴
        self.domain_pattern = re.compile(r'aplus\.gmarket\.co(\.kr|m)')
    
    def _classify_request_type(self, url: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """
        URL 패턴을 분석하여 이벤트 타입을 분류
        
        Args:
            url: 요청 URL
            payload: 파싱된 payload (goodscode 확인용)
            
        Returns:
            'PV', 'PDP PV', 'Module Exposure', 'Product Exposure', 'Product Click', 'Product A2C Click', 또는 'Unknown'
        """
        url_lower = url.lower()
        
        # PV: gif 요청
        if 'gif' in url_lower:
            # payload에서 PDP PV인지 판단
            if payload and isinstance(payload, dict):
                # 1. _p_ispdp 필드 확인 (1이면 PDP PV)
                if '_p_ispdp' in payload:
                    ispdp = payload.get('_p_ispdp')
                    if str(ispdp) == '1':
                        return 'PDP PV'
                
                # 2. _p_typ 필드 확인 (pdp이면 PDP PV)
                if '_p_typ' in payload:
                    ptyp = payload.get('_p_typ', '').lower()
                    if ptyp == 'pdp':
                        return 'PDP PV'
                
                # 3. decoded_gokey 내부에서 _p_prod 직접 확인
                decoded_gokey = payload.get('decoded_gokey', {})
                if decoded_gokey:
                    params = decoded_gokey.get('params', {})
                    # params에서 _p_prod 직접 확인
                    if '_p_prod' in params and params['_p_prod']:
                        return 'PDP PV'
                    # 또는 decoded_gokey 내부를 재귀적으로 탐색하여 _p_prod 찾기
                    def find_p_prod_recursive(obj: Any, visited: Optional[set] = None) -> bool:
                        """재귀적으로 _p_prod 찾기"""
                        if visited is None:
                            visited = set()
                        if isinstance(obj, (dict, list)):
                            obj_id = id(obj)
                            if obj_id in visited:
                                return False
                            visited.add(obj_id)
                        
                        if isinstance(obj, dict):
                            if '_p_prod' in obj and obj['_p_prod']:
                                return True
                            for value in obj.values():
                                if find_p_prod_recursive(value, visited):
                                    return True
                        elif isinstance(obj, list):
                            for item in obj:
                                if find_p_prod_recursive(item, visited):
                                    return True
                        
                        if isinstance(obj, (dict, list)):
                            visited.discard(id(obj))
                        return False
                    
                    if find_p_prod_recursive(decoded_gokey):
                        return 'PDP PV'
                
                # 4. payload에서 직접 _p_prod 확인 (일부 PV 로그는 payload에 직접 포함)
                if '_p_prod' in payload and payload['_p_prod']:
                    return 'PDP PV'
            return 'PV'
        
        # Product A2C Click: ATC 관련 URL 패턴
        if '/pdp.atc.click' in url_lower or '/product.atc.click' in url_lower:
            return 'Product A2C Click'
        
        # Product Click: Product.Click.Event 패턴
        if '/product.click.event' in url_lower:
            return 'Product Click'
        
        # Module Exposure: Module.Exposure.Event 패턴
        if '/module.exposure.event' in url_lower:
            return 'Module Exposure'
        
        # Product Exposure: Product.Exposure.Event 패턴
        if '/product.exposure.event' in url_lower:
            return 'Product Exposure'
        
        # 기본 Exposure (URL에 exposure 포함하지만 위 패턴에 매칭되지 않음)
        if 'exposure' in url_lower:
            return 'Exposure'
        
        # 기본 Click (URL에 click 포함하지만 위 패턴에 매칭되지 않음)
        if 'click' in url_lower:
            return 'Click'
        
        return 'Unknown'
    
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
    
    def _parse_query_string(self, query_string: str) -> Dict[str, Any]:
        """
        쿼리 문자열을 파싱하고 디코딩
        
        Args:
            query_string: URL 인코딩된 쿼리 문자열
            
        Returns:
            파싱된 딕셔너리
        """
        parsed_params = {}
        
        if not query_string:
            return parsed_params
        
        try:
            # &로 분리하여 각 파라미터 파싱
            for item in query_string.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    decoded_key = unquote(key)
                    decoded_value = unquote(value)
                    
                    # gokey가 있으면 디코딩
                    if decoded_key == 'gokey' and decoded_value:
                        decoded_gokey_info = self._decode_gokey(decoded_value)
                        parsed_params[decoded_key] = decoded_value
                        parsed_params['decoded_gokey'] = decoded_gokey_info
                    else:
                        parsed_params[decoded_key] = decoded_value
        except Exception as e:
            logger.debug(f'쿼리 문자열 파싱 중 오류: {e}')
            parsed_params['_raw'] = query_string
        
        return parsed_params
    
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
            # JSON이 아니면 쿼리 문자열 파싱 시도
            try:
                # 쿼리 문자열 형태인지 확인 (& 또는 = 포함)
                if '&' in post_data or '=' in post_data:
                    return self._parse_query_string(post_data)
            except Exception as e:
                logger.debug(f'쿼리 문자열 파싱 실패: {e}')
            
            # 모든 파싱이 실패하면 raw string 반환
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
            # Playwright Request 객체의 url과 method는 속성일 수도 있고 메서드일 수도 있음
            url = request.url if isinstance(request.url, str) else request.url()
            method = request.method if isinstance(request.method, str) else request.method()
            
            # 도메인 필터링
            if not self.domain_pattern.search(url):
                return
            
            # POST 메소드만 수집
            if method != 'POST':
                return
            
            # POST Body 가져오기
            post_data = request.post_data() if callable(getattr(request, 'post_data', None)) else getattr(request, 'post_data', None)
            parsed_payload = self._parse_payload(post_data)
            
            # 요청 타입 분류 (URL 패턴 및 payload 기반)
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
        Context 레벨에서 추적하여 모든 페이지(기존 + 새 탭)의 네트워크 요청을 감지
        """
        if self.is_tracking:
            logger.warning('이미 트래킹이 시작되어 있습니다.')
            return
        
        self.is_tracking = True
        
        # 기존 페이지에 리스너 추가
        self.page.on('request', self._on_request)
        
        # Context에 새 페이지 이벤트 리스너 추가 (새 탭이 열릴 때마다 추적)
        self.context.on('page', self._on_new_page)
        
        # 이미 열려있는 모든 페이지에도 리스너 추가
        for page in self.context.pages:
            if page not in self.tracked_pages:
                page.on('request', self._on_request)
                self.tracked_pages.append(page)
        
        logger.info(f'네트워크 트래킹 시작 (페이지 수: {len(self.tracked_pages)})')
    
    def _on_new_page(self, page: Page):
        """
        새 페이지(새 탭)가 열릴 때 호출되는 콜백
        
        Args:
            page: 새로 생성된 Page 객체
        """
        if not self.is_tracking:
            return
        
        # 새 페이지에 리스너 추가
        if page not in self.tracked_pages:
            page.on('request', self._on_request)
            self.tracked_pages.append(page)
            logger.info(f'새 페이지 추적 시작: {page.url if page.url else "로딩 중"}')
    
    def stop(self):
        """
        네트워크 트래킹 중지
        """
        if not self.is_tracking:
            logger.warning('트래킹이 시작되지 않았습니다.')
            return
        
        self.is_tracking = False
        
        # 모든 추적 중인 페이지에서 리스너 제거
        for page in self.tracked_pages:
            try:
                if not page.is_closed():
                    page.off('request', self._on_request)
            except Exception as e:
                logger.warning(f'페이지 리스너 제거 중 오류 (무시됨): {e}')
        
        # Context 리스너 제거
        try:
            self.context.off('page', self._on_new_page)
        except Exception as e:
            logger.warning(f'Context 리스너 제거 중 오류 (무시됨): {e}')
        
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
        PV 타입 로그만 반환 (PDP PV 제외)
        
        Returns:
            PV 로그 리스트
        """
        return self.get_logs('PV')
    
    def get_pdp_pv_logs(self) -> List[Dict[str, Any]]:
        """
        PDP PV 타입 로그만 반환 (goodscode가 있는 PV)
        
        Returns:
            PDP PV 로그 리스트
        """
        return self.get_logs('PDP PV')
    
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
    
    def _extract_gmkt_area_code_from_log(self, log: Dict[str, Any]) -> Optional[str]:
        """
        로그에서 gmkt_area_code 추출
        
        Args:
            log: 로그 딕셔너리
        
        Returns:
            추출된 gmkt_area_code 또는 None
        """
        payload = log.get('payload', {})
        decoded_gokey = payload.get('decoded_gokey', {})
        params = decoded_gokey.get('params', {})
        
        # Product Exposure: expdata.parsed 배열의 각 항목에서 확인
        if 'expdata' in params:
            expdata = params['expdata']
            if isinstance(expdata, dict) and 'parsed' in expdata:
                parsed_list = expdata['parsed']
                if isinstance(parsed_list, list) and len(parsed_list) > 0:
                    # 첫 번째 항목의 params-exp.parsed.gmkt_area_code 확인
                    first_item = parsed_list[0]
                    if isinstance(first_item, dict) and 'exargs' in first_item:
                        exargs = first_item['exargs']
                        if isinstance(exargs, dict) and 'params-exp' in exargs:
                            params_exp = exargs['params-exp']
                            if isinstance(params_exp, dict) and 'parsed' in params_exp:
                                parsed = params_exp['parsed']
                                if isinstance(parsed, dict) and 'gmkt_area_code' in parsed:
                                    return str(parsed['gmkt_area_code'])
        
        # Product Click: params-clk.parsed.gmkt_area_code 확인
        if 'params-clk' in params:
            params_clk = params['params-clk']
            if isinstance(params_clk, dict) and 'parsed' in params_clk:
                parsed = params_clk['parsed']
                if isinstance(parsed, dict) and 'gmkt_area_code' in parsed:
                    return str(parsed['gmkt_area_code'])
        
        # Module Exposure: params-exp.parsed.gmkt_area_code 확인
        if 'params-exp' in params:
            params_exp = params['params-exp']
            if isinstance(params_exp, dict) and 'parsed' in params_exp:
                parsed = params_exp['parsed']
                if isinstance(parsed, dict) and 'gmkt_area_code' in parsed:
                    return str(parsed['gmkt_area_code'])
        
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
        goodscode 기준으로 PV 로그만 반환 (PDP PV 포함)
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 PV/PDP PV 로그 리스트
        """
        # PV와 PDP PV 모두에서 goodscode로 필터링
        pv_logs = self.get_logs_by_goodscode(goodscode, 'PV')
        pdp_pv_logs = self.get_logs_by_goodscode(goodscode, 'PDP PV')
        return pv_logs + pdp_pv_logs
    
    def get_pdp_pv_logs_by_goodscode(self, goodscode: str) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 PDP PV 로그만 반환
        
        Args:
            goodscode: 상품 번호
        
        Returns:
            해당 goodscode의 PDP PV 로그 리스트
        """
        return self.get_logs_by_goodscode(goodscode, 'PDP PV')
    
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
    
    def _extract_spm_from_log(self, log: Dict[str, Any]) -> Optional[str]:
        """
        로그에서 spm 값 추출
        
        Args:
            log: 로그 딕셔너리
        
        Returns:
            추출된 spm 값 또는 None
        """
        payload = log.get('payload')
        
        if not isinstance(payload, dict):
            return None
        
        # decoded_gokey.params.spm에서 확인
        decoded_gokey = payload.get('decoded_gokey', {})
        params = decoded_gokey.get('params', {})
        
        # 1. params 최상위에서 spm 확인
        if 'spm' in params and params['spm']:
            return str(params['spm'])
        
        # 2. expdata 내부의 spm 확인 (Module Exposure의 경우)
        expdata = params.get('expdata', {})
        if isinstance(expdata, dict) and 'parsed' in expdata:
            parsed_expdata = expdata['parsed']
            if isinstance(parsed_expdata, list):
                # 리스트의 각 아이템에서 spm 찾기 (첫 번째 것 사용)
                for item in parsed_expdata:
                    if isinstance(item, dict) and 'spm' in item:
                        spm_value = item.get('spm')
                        if spm_value:
                            return str(spm_value)
        
        return None
    
    def get_module_exposure_logs_by_spm(self, spm: str) -> List[Dict[str, Any]]:
        """
        spm 기준으로 Module Exposure 로그만 반환
        
        Args:
            spm: SPM 값 (예: "gmktpc.searchlist.prime.d0_0")
        
        Returns:
            해당 spm의 Module Exposure 로그 리스트
        """
        filtered_logs = []
        
        # Module Exposure 로그만 필터링
        module_exposure_logs = self.get_logs('Module Exposure')
        
        for log in module_exposure_logs:
            log_spm = self._extract_spm_from_log(log)
            # spm이 부분 일치하는지 확인 (예: "gmktpc.searchlist.prime"로 시작하는 경우)
            if log_spm and (log_spm == spm or log_spm.startswith(spm)):
                filtered_logs.append(log)
        
        return filtered_logs
    
    def get_product_exposure_logs_by_goodscode(self, goodscode: str, gmkt_area_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Product Exposure 로그만 반환
        gmkt_area_code가 제공되면 추가로 필터링
        
        Args:
            goodscode: 상품 번호
            gmkt_area_code: 모듈 area code (선택적)
        
        Returns:
            해당 goodscode의 Product Exposure 로그 리스트
        """
        logs = self.get_logs_by_goodscode(goodscode, 'Product Exposure')
        
        # gmkt_area_code로 추가 필터링
        if gmkt_area_code:
            filtered_logs = []
            for log in logs:
                log_gmkt_area_code = self._extract_gmkt_area_code_from_log(log)
                if log_gmkt_area_code == gmkt_area_code:
                    filtered_logs.append(log)
            return filtered_logs
        
        return logs
    
    def get_product_click_logs_by_goodscode(self, goodscode: str, gmkt_area_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        goodscode 기준으로 Product Click 로그만 반환
        gmkt_area_code가 제공되면 추가로 필터링
        
        Args:
            goodscode: 상품 번호
            gmkt_area_code: 모듈 area code (선택적)
        
        Returns:
            해당 goodscode의 Product Click 로그 리스트
        """
        logs = self.get_logs_by_goodscode(goodscode, 'Product Click')
        
        # gmkt_area_code로 추가 필터링
        if gmkt_area_code:
            filtered_logs = []
            for log in logs:
                log_gmkt_area_code = self._extract_gmkt_area_code_from_log(log)
                if log_gmkt_area_code == gmkt_area_code:
                    filtered_logs.append(log)
            return filtered_logs
        
        return logs
    
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
    
    def validate_payload(self, log: Dict[str, Any], expected_data: Dict[str, Any], goodscode: Optional[str] = None, event_type: Optional[str] = None) -> bool:
        """
        로그의 payload 정합성 검증 (디코딩된 값 사용, 개선된 버전)
        
        Args:
            log: 검증할 로그 딕셔너리
            expected_data: 기대하는 데이터 (키-값 쌍)
                          - 경로 방식: 'gokey.params.params-exp.parsed._p_prod' (기존 방식 지원)
                          - 재귀 탐색: '_p_prod' (자동으로 찾음, 간단한 키 이름만 제공)
                          - 일반 키: 'pageId' (payload 최상위 키)
            goodscode: 상품 번호 (Product Exposure의 경우 expdata.parsed 배열에서 필터링용)
            event_type: 이벤트 타입 ('Product Exposure', 'Product Click' 등)
        
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
        
        # Product Exposure의 경우 expdata.parsed 배열에서 goodscode와 일치하는 항목 찾기
        matched_expdata_item = None
        if event_type == 'Product Exposure' and goodscode:
            decoded_gokey = payload.get('decoded_gokey', {})
            params = decoded_gokey.get('params', {})
            expdata = params.get('expdata', {})
            
            if isinstance(expdata, dict) and 'parsed' in expdata:
                parsed_list = expdata.get('parsed', [])
                if isinstance(parsed_list, list):
                    for item in parsed_list:
                        if isinstance(item, dict) and 'exargs' in item:
                            exargs = item['exargs']
                            if isinstance(exargs, dict) and 'params-exp' in exargs:
                                params_exp = exargs['params-exp']
                                if isinstance(params_exp, dict) and 'parsed' in params_exp:
                                    parsed = params_exp['parsed']
                                    # _p_prod 또는 utLogMap.x_object_id로 goodscode 확인
                                    item_goodscode = None
                                    if isinstance(parsed, dict):
                                        item_goodscode = parsed.get('_p_prod')
                                        if not item_goodscode and 'utLogMap' in parsed:
                                            utlogmap = parsed['utLogMap']
                                            if isinstance(utlogmap, dict) and 'parsed' in utlogmap:
                                                utlogmap_parsed = utlogmap['parsed']
                                                if isinstance(utlogmap_parsed, dict):
                                                    item_goodscode = utlogmap_parsed.get('x_object_id')
                                    
                                    if item_goodscode and str(item_goodscode) == str(goodscode):
                                        matched_expdata_item = parsed
                                        break
        
        # 기대 데이터 검증
        errors = []
        for key, expected_value in expected_data.items():
            actual_value = None
            
            # gokey 내부 파라미터 접근 (경로 방식)
            if key.startswith('gokey.params.'):
                param_path = key.replace('gokey.params.', '')
                
                # Product Exposure이고 matched_expdata_item이 있으면 특별 처리
                if event_type == 'Product Exposure' and matched_expdata_item and param_path.startswith('params-exp.parsed.'):
                    # expdata.parsed[*].exargs.params-exp.parsed.* 경로 처리
                    field_name = param_path.replace('params-exp.parsed.', '')
                    if field_name.startswith('utLogMap.parsed.'):
                        # utLogMap.parsed.* 경로
                        utlogmap_path = field_name.replace('utLogMap.parsed.', '')
                        utlogmap = matched_expdata_item.get('utLogMap', {})
                        if isinstance(utlogmap, dict) and 'parsed' in utlogmap:
                            utlogmap_parsed = utlogmap['parsed']
                            if isinstance(utlogmap_parsed, dict):
                                actual_value = utlogmap_parsed.get(utlogmap_path)
                    else:
                        # 일반 필드
                        actual_value = matched_expdata_item.get(field_name) if isinstance(matched_expdata_item, dict) else None
                else:
                    # 일반 경로 처리
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

