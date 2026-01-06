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
    
    def _classify_request_type(self, url: str) -> str:
        """
        URL 패턴에 따라 요청 타입을 분류
        
        Args:
            url: 요청 URL
            
        Returns:
            'PV', 'Exposure', 'Click', 또는 'Unknown'
        """
        url_lower = url.lower()
        
        if 'gif' in url_lower:
            return 'PV'
        elif 'exposure' in url_lower:
            return 'Exposure'
        elif 'click' in url_lower:
            return 'Click'
        else:
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
            
            # 요청 타입 분류
            request_type = self._classify_request_type(url)
            
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
        payload = log.get('payload')
        log_type = log.get('type')
        
        if not isinstance(payload, dict):
            return None
        
        # 1. payload 최상위에서 x_object_id 확인
        if 'x_object_id' in payload:
            value = payload['x_object_id']
            if value:
                return str(value)
        
        # decoded_gokey의 params에서 찾기
        decoded_gokey = payload.get('decoded_gokey', {})
        params = decoded_gokey.get('params', {})
        
        # 2. 로그 타입에 따라 특정 파라미터 확인
        if log_type == 'Exposure':
            # Exposure의 경우 expdata 내부의 params-exp 확인
            if 'expdata' in params:
                expdata_info = params['expdata']
                if isinstance(expdata_info, dict) and 'parsed' in expdata_info:
                    expdata_list = expdata_info['parsed']
                    if isinstance(expdata_list, list) and len(expdata_list) > 0:
                        # 첫 번째 아이템의 exargs.params-exp 확인
                        first_item = expdata_list[0]
                        if isinstance(first_item, dict) and 'exargs' in first_item:
                            exargs = first_item['exargs']
                            if isinstance(exargs, dict) and 'params-exp' in exargs:
                                params_exp_info = exargs['params-exp']
                                if isinstance(params_exp_info, dict) and 'parsed' in params_exp_info:
                                    parsed_params = params_exp_info['parsed']
                                    # _p_prod 확인 (우선순위 1)
                                    if '_p_prod' in parsed_params:
                                        value = parsed_params['_p_prod']
                                        if value:
                                            return str(value)
                                    # utLogMap 내부의 x_object_id 확인 (우선순위 2)
                                    if 'utLogMap' in parsed_params:
                                        utlogmap_info = parsed_params['utLogMap']
                                        if isinstance(utlogmap_info, dict) and 'parsed' in utlogmap_info:
                                            utlogmap = utlogmap_info['parsed']
                                            if isinstance(utlogmap, dict) and 'x_object_id' in utlogmap:
                                                value = utlogmap['x_object_id']
                                                if value:
                                                    return str(value)
            
            # 직접 params-exp도 확인 (gokey의 직접 파라미터인 경우)
            if 'params-exp' in params:
                param_data = params['params-exp']
                if isinstance(param_data, dict) and 'parsed' in param_data:
                    parsed = param_data['parsed']
                    # _p_prod 확인
                    if '_p_prod' in parsed:
                        value = parsed['_p_prod']
                        if value:
                            return str(value)
                    # utLogMap 내부의 x_object_id 확인
                    if 'utLogMap' in parsed:
                        utlogmap_info = parsed['utLogMap']
                        if isinstance(utlogmap_info, dict) and 'parsed' in utlogmap_info:
                            utlogmap = utlogmap_info['parsed']
                            if isinstance(utlogmap, dict) and 'x_object_id' in utlogmap:
                                value = utlogmap['x_object_id']
                                if value:
                                    return str(value)
                            
        elif log_type == 'Click':
            # Click의 경우 params-clk의 _p_prod 또는 utLogMap.x_object_id 확인
            if 'params-clk' in params:
                param_data = params['params-clk']
                if isinstance(param_data, dict) and 'parsed' in param_data:
                    parsed = param_data['parsed']
                    # _p_prod 확인 (우선순위 1)
                    if '_p_prod' in parsed:
                        value = parsed['_p_prod']
                        if value:
                            return str(value)
                    # utLogMap 내부의 x_object_id 확인 (우선순위 2)
                    if 'utLogMap' in parsed:
                        utlogmap_info = parsed['utLogMap']
                        if isinstance(utlogmap_info, dict) and 'parsed' in utlogmap_info:
                            utlogmap = utlogmap_info['parsed']
                            if isinstance(utlogmap, dict) and 'x_object_id' in utlogmap:
                                value = utlogmap['x_object_id']
                                if value:
                                    return str(value)
        
        # 3. params-exp, params-clk 모두 확인 (타입이 Unknown인 경우 대비)
        for param_key in ['params-exp', 'params-clk']:
            if param_key in params:
                param_data = params[param_key]
                if isinstance(param_data, dict) and 'parsed' in param_data:
                    parsed = param_data['parsed']
                    # _p_prod 확인 (우선순위 1)
                    if '_p_prod' in parsed:
                        value = parsed['_p_prod']
                        if value:
                            return str(value)
                    # utLogMap 내부의 x_object_id 확인 (우선순위 2)
                    if 'utLogMap' in parsed:
                        utlogmap_info = parsed['utLogMap']
                        if isinstance(utlogmap_info, dict) and 'parsed' in utlogmap_info:
                            utlogmap = utlogmap_info['parsed']
                            if isinstance(utlogmap, dict) and 'x_object_id' in utlogmap:
                                value = utlogmap['x_object_id']
                                if value:
                                    return str(value)
        
        # 4. expdata 내부 확인 (타입이 Unknown인 경우)
        if 'expdata' in params:
            expdata_info = params['expdata']
            if isinstance(expdata_info, dict) and 'parsed' in expdata_info:
                expdata_list = expdata_info['parsed']
                if isinstance(expdata_list, list):
                    for item in expdata_list:
                        if isinstance(item, dict) and 'exargs' in item:
                            exargs = item['exargs']
                            if isinstance(exargs, dict) and 'params-exp' in exargs:
                                params_exp_info = exargs['params-exp']
                                if isinstance(params_exp_info, dict) and 'parsed' in params_exp_info:
                                    parsed_params = params_exp_info['parsed']
                                    # _p_prod 확인
                                    if '_p_prod' in parsed_params:
                                        value = parsed_params['_p_prod']
                                        if value:
                                            return str(value)
                                    # utLogMap 내부의 x_object_id 확인
                                    if 'utLogMap' in parsed_params:
                                        utlogmap_info = parsed_params['utLogMap']
                                        if isinstance(utlogmap_info, dict) and 'parsed' in utlogmap_info:
                                            utlogmap = utlogmap_info['parsed']
                                            if isinstance(utlogmap, dict) and 'x_object_id' in utlogmap:
                                                value = utlogmap['x_object_id']
                                                if value:
                                                    return str(value)
        
        # 5. payload에서 직접 확인 (다양한 키 이름 시도)
        for key in ['goodscode', 'goodsCode', 'goods_code', 'goodscd', 'goodsCd', 'x_object_id']:
            if key in payload:
                value = payload[key]
                if value:
                    return str(value)
        
        # 6. decoded_gokey의 params에서 직접 확인
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
        로그의 payload 정합성 검증 (디코딩된 값 사용)
        
        Args:
            log: 검증할 로그 딕셔너리
            expected_data: 기대하는 데이터 (키-값 쌍)
                          예: {'pageId': '123', 'gokey.params.keyword': 'test'}
                          gokey 내부 파라미터는 'gokey.params.키' 형식으로 접근
                          params-clk, params-exp 내부는 'gokey.params.params-clk.parsed.키' 형식
        
        Returns:
            검증 성공 시 True, 실패 시 AssertionError 발생
        
        Raises:
            AssertionError: 검증 실패 시
        """
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
            # gokey 내부 파라미터 접근 (예: 'gokey.params.keyword' 또는 'gokey.params.params-clk.parsed.utLogMap')
            if key.startswith('gokey.params.'):
                param_path = key.replace('gokey.params.', '').split('.')
                actual_value = payload.get('decoded_gokey', {}).get('params', {})
                
                # 중첩된 키 경로 탐색
                for path_key in param_path:
                    if actual_value is None:
                        break
                    elif isinstance(actual_value, dict):
                        # 'parsed' 키가 있으면 parsed 내부를 확인 (params-clk, params-exp 같은 경우)
                        if path_key == 'parsed' and 'parsed' in actual_value:
                            actual_value = actual_value['parsed']
                        else:
                            actual_value = actual_value.get(path_key)
                    else:
                        actual_value = None
                        break
                
                if actual_value is None:
                    errors.append(f"키 경로 '{key}'에 해당하는 값이 없습니다.")
                elif actual_value != expected_value:
                    errors.append(
                        f"키 경로 '{key}'의 값이 일치하지 않습니다. "
                        f"기대값: {expected_value}, 실제값: {actual_value}"
                    )
            else:
                # 일반 payload 키 검증
                if key not in payload:
                    errors.append(f"키 '{key}'가 payload에 없습니다.")
                elif payload[key] != expected_value:
                    errors.append(
                        f"키 '{key}'의 값이 일치하지 않습니다. "
                        f"기대값: {expected_value}, 실제값: {payload[key]}"
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

