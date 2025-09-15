from bs4 import BeautifulSoup
import os

CACHE_FILE_NAME = 'report_cache.html'

if not os.path.exists(CACHE_FILE_NAME):
    print(f"캐시 파일({CACHE_FILE_NAME})이 없습니다. 먼저 기본 스크립트를 실행하여 캐시를 생성해주세요.")
else:
    with open(CACHE_FILE_NAME, 'r', encoding='utf-8') as f:
        report_html = f.read()
    
    soup = BeautifulSoup(report_html, 'html.parser')
    
    print("--- 디버깅 시작: '사업의 내용'을 포함하는 <p> 태그 분석 ---")
    
    found = False
    for tag in soup.find_all('p'):
        try:
            text = tag.get_text()
            if '사업의 내용' in text:
                found = True
                print("\n=======================================================")
                print("찾은 태그:", tag)
                print("get_text() 결과:", repr(text)) # repr()로 숨겨진 문자까지 표시
                
                stripped_text = tag.get_text(strip=True)
                print("get_text(strip=True) 결과:", repr(stripped_text))
                
                # 기존 로직으로 테스트
                test_text = stripped_text.replace(' ', '')
                is_found_by_logic = 'II' in stripped_text and '사업의내용' in test_text
                print("기존 로직으로 발견 여부:", is_found_by_logic)
                print("=======================================================")

        except Exception as e:
            print(f"태그 분석 중 오류: {e}")
            
    if not found:
        print("분석 완료: '사업의 내용'을 포함하는 <p> 태그를 찾지 못했습니다.")
