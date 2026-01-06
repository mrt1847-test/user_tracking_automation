import time
from pom.SrpPage import Srp
from pom.Etc import Etc
from utils.db_check import DatabricksSPClient
import json
from utils.TimeLogger import TimeLogger
import pytest
from case_data.search_data import search_testcases1, search_testcases2, search_testcases3, search_testcases4
import io
import contextlib
from datetime import datetime, timedelta

FILE_START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
FILE_START_HOUR = datetime.now().strftime("%H")

@pytest.fixture(scope="module")
def file_start_time():
    # 이 모듈(파일) 내 테스트가 처음 실행될 때 한 번만 호출됨
    return FILE_START_TIME
@pytest.fixture(scope="module")
def file_start_dt():
    # 이 모듈(파일) 내 테스트가 처음 실행될 때 한 번만 호출됨
    return datetime.now().strftime("%Y%m%d")
@pytest.fixture(scope="module")
def file_start_hour():
    # 이 모듈(파일) 내 테스트가 처음 실행될 때 한 번만 호출됨
    return FILE_START_HOUR

#--
@pytest.mark.flaky(reruns=2, reruns_delay=1)
@pytest.mark.parametrize("keyword, case_id", search_testcases1, ids=[c for _, c in search_testcases1])
def test_01_srp_1(page, keyword, case_id, request):
    # TestRail 케이스 ID를 현재 실행 노드에 저장
    request.node._testrail_case_id = case_id
    etc = Etc(page)
    srp_page = Srp(page)
    logger = TimeLogger("json/test_srp.json")
    try:
        # #testrail 결과 기록시 로그 포함 위해 로그 수집
        output_content = io.StringIO()
        with contextlib.redirect_stdout(output_content):

            # g마켓 홈 으로 이동
            etc.goto()
            # 일반회원 로그인
            # etc.login("t4adbuy01", "Gmkt1004!!")
            # keyword 로 검색창에 검색
            srp_page.search_product(keyword)
            # 상품 노출 확인시간 저장
            logger.record_time("case1", keyword,"exposure")
            # 먼저 둘러보세요 모듈로 이동 후 확인
            srp_page.search_module_by_title("먼저 둘러보세요")
            # 먼저 둘러보세요 모듈내 광고 상품 곽인
            goodscode = srp_page.assert_item_in_module("먼저 둘러보세요")
            # 상품 번호 저장
            logger.record_goodscode("case1",keyword, goodscode)
            # 상품 클릭시간 저장
            logger.record_time("case1", keyword,"click")
            # 상품 클릭후 해당 vip 이동 확인
            srp_page.montelena_goods_click(goodscode)
    finally:
        # hook에서 사용하기 위해 item에 저장
        request.node._stdout_capture = output_content.getvalue()

@pytest.mark.flaky(reruns=2, reruns_delay=1)
@pytest.mark.parametrize("keyword, case_id", search_testcases2, ids=[c for _, c in search_testcases2])
def test_02_srp_2(page, keyword, case_id, request):
    # TestRail 케이스 ID를 현재 실행 노드에 저장
    request.node._testrail_case_id = case_id
    etc = Etc(page)
    srp_page = Srp(page)
    logger = TimeLogger("json/test_srp.json")
    try:
        # # testrail 결과 기록시 로그 포함 위해 로그 수집
        output_content = io.StringIO()
        with contextlib.redirect_stdout(output_content):
            # g마켓 홈 으로 이동
            etc.goto()
            # 일반회원 로그인
            # etc.login("t4adbuy01", "Gmkt1004!!")
            # keyword 로 검색창에 검색
            srp_page.search_product(keyword)
            # 상품 노출 확인시간 저장
            logger.record_time("case2", keyword,"exposure")
            # 일반상품 모듈로 이동 후 확인
            parent = srp_page.search_module_by_title("일반상품")
            # 일반상품 모듈내 광고 상품 비율 곽인
            srp_page.hybrid_ratio_check(parent)
            # 광고상품 상품 번호 추출
            goodscode = srp_page.assert_ad_item_in_hybrid(parent)
            # 상품 번호 저장
            logger.record_goodscode("case2",keyword, goodscode)
            # 상품 클릭시간 저장
            logger.record_time("case2", keyword,"click")
            # 상품 클릭후 해당 vip 이동 확인
            srp_page.montelena_goods_click(goodscode)
    finally:
        # hook에서 사용하기 위해 item에 저장
        request.node._stdout_capture = output_content.getvalue()

def test_03_wait_15min():
    # -----------------------------
    # DB에 데이터가 쌓일 때까지 대기
    # 약 15분 30초 (930초) 동안 대기
    # -----------------------------
    print("DB 데이터 반영 대기 시작... 약 15분 30초 대기합니다.")
    time.sleep(920)  # 실제 대기

click_db = None
imp_db = None
vimp_db = None
click_db_ai = None
imp_db_ai = None
vimp_db_ai = None

def test_04_fetch_from_db(file_start_time, file_start_dt, file_start_hour):
    db_check = DatabricksSPClient()  # Databricks 클라이언트 객체 생성
    print(file_start_time, file_start_dt, file_start_hour)

    # 전역 변수로 조회 결과를 저장 (다른 테스트에서 재사용)
    global click_db, imp_db, vimp_db, click_db_ai, imp_db_ai, vimp_db_ai

    with open("json/test_srp.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    product_ids_case1 = []

    for case_group in data:  # 리스트 안의 dict 순회
        case1_items = case_group.get("case1", {})  # case1만 가져오기
        for _, info in case1_items.items():
            product_id = info.get("상품번호")
            if product_id:
                product_ids_case1.append(product_id)

    product_ids_case2 = []

    for case_group in data:  # 리스트 안의 dict 순회
        case2_items = case_group.get("case2", {})  # case2만 가져오기
        for _, info in case2_items.items():
            product_id = info.get("상품번호")
            if product_id:
                product_ids_case2.append(product_id)

    prduct_ids_caxe = product_ids_case1 + product_ids_case2

    # 1. 클릭 로그(click_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ad_cpc_click_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND cguid = '11758850530814005372000000'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    click_db = db_check.query_databricks(sql)
    time.sleep(10)  # 조회 후 10초 대기 (DB 처리 반영 시간 고려)

    # 2. 노출 로그(imp_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ad_cpc_imp_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND cguid = '11758850530814005372000000'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    imp_db = db_check.query_databricks(sql)
    time.sleep(10)  # 조회 후 10초 대기

    # 3. 가상노출 로그(vimp_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ad_cpc_vimp_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND cguid = '11758850530814005372000000'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    vimp_db = db_check.query_databricks(sql)
    time.sleep(10)  # 조회 후 10초 대기

    # 4. AI 매출업 클릭 로그(click_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ra_click_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND cguid = '11758850530814005372000000'
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    click_db_ai = db_check.query_databricks(sql)
    time.sleep(10)  # 조회 후 10초 대기 (DB 처리 반영 시간 고려)

    # 5. AI 매출업 노출 로그(imp_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ra_imp_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND cguid = '11758850530814005372000000'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    imp_db_ai = db_check.query_databricks(sql)
    time.sleep(10)  # 조회 후 10초 대기

    # 6. AI 매출업 가상노출 로그(vimp_db) 조회
    sql = f"""
    SELECT item_no, ins_date
    FROM baikali1xs.ad_ats_silver.ub_ra_vimp_gmkt
    WHERE ins_date >= '{file_start_time}'
      AND cguid = '11758850530814005372000000'
      AND item_no IN ({','.join(f"'{x}'" for x in prduct_ids_caxe)})
      AND dt = '{file_start_dt}'
      AND hour IN ('{file_start_hour}', '{int(file_start_hour) + 1:02d}');
    """
    vimp_db_ai = db_check.query_databricks(sql)
    print(click_db)
    print(imp_db)
    print(vimp_db)
    print(click_db_ai)
    print(imp_db_ai)
    print(vimp_db_ai)


@pytest.mark.parametrize("keyword, case_id", search_testcases3,ids=[c for _, c in search_testcases3])
def test_05_srp_3(keyword, case_id, request):
    # TestRail 케이스 ID를 현재 실행 노드에 저장
    request.node._testrail_case_id = case_id
    db_check = DatabricksSPClient()
    with open("json/test_srp.json", "r", encoding="utf-8") as f:
        test_record = json.load(f)
    try:
        # testrail 결과 기록시 로그 포함 위해 로그 수집
        output_content = io.StringIO()
        with contextlib.redirect_stdout(output_content):
            # JSON에서 테스트에 필요한 값 추출
            goodscode = test_record[0]["case1"][keyword]["상품번호"]   # 상품 번호
            click_time = test_record[0]["case1"][keyword]["click"]     # 클릭 발생 시간
            expose_time = test_record[0]["case1"][keyword]["exposure"] # 노출 발생 시간

            # DB 기록 검증
            try:
                # - click_db : 클릭 로그 DB, 클릭 시간 검증
                db_check.assert_db_record_time(click_db, click_time, goodscode)
                print("click_db 조회시 적재 확인")
            except:
                try:
                    # - click_db : 클릭 로그 DB, 클릭 시간 검증
                    db_check.assert_db_record_time(click_db_ai, click_time, goodscode)
                    print("click_db_ai 조회시 적재 확인")
                except:
                    print("click_db 조회 오류")
                    raise

            try:
                # - imp_db   : 노출 로그 DB, 노출 시간 검증
                db_check.assert_db_record_time(imp_db, expose_time, goodscode)
                print("imp_db 조회시 적재 확인")
            except:
                try:
                    # - imp_db   : 노출 로그 DB, 노출 시간 검증
                    db_check.assert_db_record_time(imp_db_ai, expose_time, goodscode)
                    print("imp_db_ai 조회시 적재 확인")
                except:
                    print("imp_db 조회 오류")
                    raise
            try:
                # - vimp_db  : 가상 노출 로그 DB, 노출 시간 검증
                db_check.assert_db_record_time(vimp_db, expose_time, goodscode)
                print("vimp_db 조회시 적재 확인")
            except:
                try:
                    # - vimp_db  : 가상 노출 로그 DB, 노출 시간 검증
                    db_check.assert_db_record_time(vimp_db_ai, expose_time, goodscode)
                    print("vimp_db_ai 조회시 적재 확인")
                except:
                    print("vimp_db 조회 오류")
                    raise
    finally:
        # hook에서 사용하기 위해 item에 저장
        request.node._stdout_capture = output_content.getvalue()

@pytest.mark.parametrize("keyword, case_id", search_testcases4, ids=[c for _, c in search_testcases3])
def test_06_srp_4(keyword, case_id, request):
    # TestRail 케이스 ID를 현재 실행 노드에 저장
    request.node._testrail_case_id = case_id
    db_check = DatabricksSPClient()
    with open("json/test_srp.json", "r", encoding="utf-8") as f:
        test_record = json.load(f)
    try:
        # # testrail 결과 기록시 로그 포함 위해 로그 수집
        output_content = io.StringIO()
        with contextlib.redirect_stdout(output_content):
            # JSON에서 테스트에 필요한 값 추출
            goodscode = test_record[0]["case2"][keyword]["상품번호"]  # 상품 번호
            click_time = test_record[0]["case2"][keyword]["click"]  # 클릭 발생 시간
            expose_time = test_record[0]["case2"][keyword]["exposure"]  # 노출 발생 시간

            # DB 기록 검증
            try:
                # - click_db : 클릭 로그 DB, 클릭 시간 검증
                db_check.assert_db_record_time(click_db, click_time, goodscode)
                print("click_db 조회시 적재 확인")
            except:
                try:
                    # - click_db : 클릭 로그 DB, 클릭 시간 검증
                    db_check.assert_db_record_time(click_db_ai, click_time, goodscode)
                    print("click_db_ai 조회시 적재 확인")
                except:
                    print("click_db 조회 오류")
                    raise

            try:
                # - imp_db   : 노출 로그 DB, 노출 시간 검증
                db_check.assert_db_record_time(imp_db, expose_time, goodscode)
                print("imp_db 조회시 적재 확인")
            except:
                try:
                    # - imp_db   : 노출 로그 DB, 노출 시간 검증
                    db_check.assert_db_record_time(imp_db_ai, expose_time, goodscode)
                    print("imp_db_ai 조회시 적재 확인")
                except:
                    print("imp_db 조회 오류")
                    raise
            try:
                # - vimp_db  : 가상 노출 로그 DB, 노출 시간 검증
                db_check.assert_db_record_time(vimp_db, expose_time, goodscode)
                print("vimp_db 조회시 적재 확인")
            except:
                try:
                    # - vimp_db  : 가상 노출 로그 DB, 노출 시간 검증
                    db_check.assert_db_record_time(vimp_db_ai, expose_time, goodscode)
                    print("vimp_db_ai 조회시 적재 확인")
                except:
                    print("vimp_db 조회 오류")
                    raise
    finally:
        # hook에서 사용하기 위해 item에 저장
        request.node._stdout_capture = output_content.getvalue()
