
import pandas as pd
from bs4 import BeautifulSoup

import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from tabulate import tabulate
import dart_fss as dart
import pandas as pd
from bs4 import BeautifulSoup
import os
import time
import re
import json
from io import StringIO
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- 설정 --- #
CORP_NAME_TO_SEARCH = '일진전기'
HTML_CACHE_FILE = f"{CORP_NAME_TO_SEARCH}_cache.html"
XBRL_CACHE_FILE = f"{CORP_NAME_TO_SEARCH}_cache.xbrl.json"

# --- 함수 정의 --- #
def get_html_report(corp, latest_report):
    if os.path.exists(HTML_CACHE_FILE):
        print(f"INFO: HTML 캐시 파일({HTML_CACHE_FILE})에서 로드합니다.")
        with open(HTML_CACHE_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print("INFO: HTML 캐시가 없어 DART에서 다운로드합니다.")
        if not latest_report.pages:
            raise ValueError("보고서의 개별 페이지를 찾을 수 없습니다.")
        html_list = [page.html for page in latest_report.pages if page.html and time.sleep(1) is None]
        if not html_list:
            raise ValueError("보고서의 모든 페이지에 HTML 내용이 없습니다.")
        report_html = "".join(html_list)
        with open(HTML_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(report_html)
        print(f"INFO: HTML 다운로드 및 캐시 저장 완료.")
        return report_html

def manual_parse_table(table):
    """rowspan이 포함된 복잡한 테이블을 수동으로 파싱하는 함수"""
    print("--- 수동으로 테이블 데이터 추출 시작 ---")
    data_rows = []
    header_rows = table.find_all('tr', limit=2) # 보통 헤더는 첫 1~2줄
    headers = []
    if header_rows:
        for r in header_rows:
            cols = r.find_all(['th', 'td'])
            headers.append([c.get_text(strip=True) for c in cols])

    body_rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')
    
    # 헤더 행 건너뛰기 (이미 읽었으므로)
    start_row = len(header_rows)

    row_idx = start_row
    while row_idx < len(body_rows):
        cells = body_rows[row_idx].find_all('td')
        if not cells:
            row_idx += 1
            continue

        # rowspan 처리
        if cells and cells[0].get('rowspan'):
            row_span_count = int(cells[0]['rowspan'])
            category_data = [cell.get_text(strip=True) for cell in cells]
            
            for i in range(row_span_count):
                if (row_idx + i) >= len(body_rows):
                    break
                current_row_cells = body_rows[row_idx + i].find_all('td')
                if i == 0:
                    row_data = category_data
                else:
                    row_data = category_data[:1] + [td.get_text(strip=True) for td in current_row_cells]
                data_rows.append(row_data)
            row_idx += row_span_count
        else:
            data_rows.append([cell.get_text(strip=True) for cell in cells])
            row_idx += 1
    
    # 최종 데이터프레임 생성 및 출력
    print(data_rows)
    if data_rows:
        df = pd.DataFrame(data_rows)
        print("--- 추출 완료된 데이터 ---")
        print(df)
        print("\n" + "="*50 + "\n")
    else:
        print("WARN: 테이블에서 데이터를 추출하지 못했습니다.")


def parse_html_report_bf(report_html):
    print("STEP 6: HTML 파싱 시작 (html.parser 사용).")
    soup = BeautifulSoup(report_html, 'html.parser')

    print("STEP 7: 'II. 사업의 내용' 섹션 검색...")
    business_section_title = next((tag for tag in soup.find_all(['p', 'h1', 'h2', 'h3']) if 'II' in (text := tag.get_text(strip=True)) and '사업의 내용' in text and len(text) < 30), None)

    if not business_section_title:
        raise ValueError("보고서에서 'II. 사업의 내용' 섹션을 찾지 못했습니다.")

    print(f"STEP 8: 'II. 사업의 내용' 섹션 분리 완료.")
    business_section_content = []
    for sibling in business_section_title.find_next_siblings():
        if sibling.name in ['h1', 'h2', 'h3'] and ('III.' in sibling.get_text() or 'Ⅲ.' in sibling.get_text()):
            break
        business_section_content.append(str(sibling))
    
    business_soup = BeautifulSoup("\n".join(business_section_content), 'html.parser')
    
    print("STEP 9: '4. 매출 및 수주상황' 소제목 검색...")
    order_title_tag = next((tag for tag in business_soup.find_all() if '4. 매출 및 수주상황' in tag.get_text() and len(tag.get_text(strip=True)) < 30), None)

    for tag in business_soup.find_all():
        print(f"DEBUG: 태그 발견 - {tag.name}: {tag.get_text(strip=True)[:30]}...")
        if '4. 매출 및 수주상황' in tag.get_text():
            order_title_tag = tag
            print(order_title_tag)
            break
    
    if not order_title_tag:
        raise ValueError("'II. 사업의 내용'에서 '4. 매출 및 수주상황' 소제목을 찾지 못했습니다.")

    print(f"INFO: '4. 매출 및 수주상황' 소제목을 찾았습니다. 다음 테이블을 추출합니다...")
    table = order_title_tag.find_next('table')

    if not table:
        raise ValueError("'4. 매출 및 수주상황' 소제목 바로 다음에 테이블이 없습니다.")

    manual_parse_table(table)




import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from tabulate import tabulate

def parse_html_report_robust(report_html):
    """
    HTML 보고서에서 '다. 수주상황' 이후의 유효한 테이블을 찾아 DataFrame으로 변환합니다.
    컬럼 이름 문제에 대한 예외 처리를 포함합니다.

    Args:
        report_html: HTML 콘텐츠 문자열.

    Returns:
        추출된 데이터가 담긴 pandas DataFrame.
    """
    soup = BeautifulSoup(report_html, "html.parser")
    
    order_title_tag = soup.find(lambda tag: "다. 수주상황" in tag.get_text(strip=True))
    if not order_title_tag:
        raise ValueError("'다. 수주상황' 소제목을 찾지 못했습니다.")
    
    for tag in order_title_tag:
        print(f"DEBUG: 태그 발견 - {tag.name}: {tag.get_text(strip=True)[:30]}...")
        if '다. 수주상황' in tag.get_text():
            order_title_tag = tag
            print(order_title_tag)
            break
    tables = order_title_tag.find_all_next("table")
    
    if len(tables) < 2:
        raise ValueError("'다. 수주상황' 이후에 유효한 테이블이 없습니다.")

    target_table = tables[1]

    print("DEBUG: 유효한 테이블 태그를 찾았습니다.")

    try:
        df = pd.read_html(StringIO(str(target_table)), header=0)[0]
        
        # 컬럼명에서 띄어쓰기 제거
        df.columns = df.columns.str.replace(' ', '')
        
        print("DEBUG: 컬럼명 정리 후:", df.columns.tolist())

        # '품목' 컬럼의 NaN 값 채우기
        if '품목' in df.columns:
            df['품목'].ffill(inplace=True)
        else:
            raise KeyError("데이터프레임에서 '품목' 컬럼을 찾을 수 없습니다.")

        # 합계 행 제거
        if '구분' in df.columns:
            df = df[~df['구분'].isin(['계'])]

        # 인덱스 초기화 (선택 사항)
        df.reset_index(drop=True, inplace=True)
        
    except Exception as e:
        raise Exception(f"HTML 보고서 처리 중 오류 발생: {e}")

    print("INFO: 테이블 데이터 추출 및 정리 완료.")
    print(tabulate(df, headers="keys", tablefmt="pretty", showindex=False))
    
    return df


# --- 메인 로직 --- #
load_dotenv()
api_key = os.getenv('DART_API_KEY')
dart.set_api_key(api_key=api_key)
print("STEP 1: DART API 키 로드 완료.")

corp_list = dart.get_corp_list()
corp = corp_list.find_by_corp_name(CORP_NAME_TO_SEARCH, exactly=True)[0]
print(f"STEP 2: '{corp.corp_name}' 회사 검색 완료.")

filings = corp.search_filings(bgn_de=(datetime.today() - timedelta(days=365)).strftime('%Y%m%d'), pblntf_ty=['A', 'B', 'C'])
if not filings:
    print(f"INFO: '{corp.corp_name}'의 최근 1년간 보고서가 없습니다.")
else:
    latest_report = filings[0]
    print(f"STEP 3: 최신 보고서 '{latest_report.report_nm}' 분석 시작.")

    # XBRL 우선 시도 (현재는 태그를 몰라 HTML로 넘어감)
    try:
        xbrl = latest_report.xbrl
        if xbrl:
            print("INFO: XBRL 데이터가 존재하나, 수주잔고 태그를 특정할 수 없어 HTML로 전환합니다.")
    except Exception:
        print("INFO: XBRL 데이터가 없거나 오류가 있어 HTML로 전환합니다.")

    # HTML 파싱
    print("\nINFO: HTML 파싱을 시작합니다.")
    try:
        report_html = get_html_report(corp, latest_report)
        if report_html:
            parse_html_report_robust(report_html)
    except Exception as e:
        print(f"ERROR: HTML 보고서 처리 중 오류 발생: {e}")
