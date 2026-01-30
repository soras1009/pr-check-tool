import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 보도자료 게재 현황 누적 관리")

# 2. 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 중..."):
                # header=None으로 설정하여 A1부터 순수 데이터로 읽어옵니다.
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = {}
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        m = re.search(r'\((.*?) \d{4}', span.get_text())
                        if m: found_media[m.group(1).strip()] = url

                # 3. 새로운 결과 열 생성 (df의 전체 행 개수 유지)
                new_col = [""] * len(df)
                
                # [좌표 고정] 이미지에 보이는 엑셀 행 번호와 정확히 맞춤
                # 1행(index 0) -> 결과 ID (Result_...)
                # 2행(index 1) -> 날짜 (01/23)
                # 3행(index 2) -> 제목 (이태호 사장...)
                if len(new_col) >= 3:
                    new_col[0] = doc_date.strftime('%m/%d') # 1행 옆에 날짜
                    new_col[1] = doc_title                  # 2행 옆에 제목
                    # 3행부터는 데이터 영역입니다.

                match_count = 0
                # [매칭 시작] 엑셀 2행(index 1)에 있는 '가스신문'부터 읽습니다.
                for i in range(len(df)):
                    # 1행(index 0)은 숫자 '1'이 있으므로 매체명 비교에서 제외
                    if i < 1: continue
                    
                    # A열(index 0) 매체명 확인
                    sheet_media = str(df.iloc[i, 0]).strip()
                    if not sheet_media or sheet_media == "1": continue
                    
                    # 매체명 가공
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
                    # HTML 매칭
                    found_url = None
                    for m_name, url in found_media.items():
                        if pure_name in m_name or m_name in pure_name:
                            found_url = url
                            break
                    
                    if found_url:
                        # ✅ 매체명과 동일한 행(i)에 정확히 체크 표시를 합니다.
                        new_col[i] = f'=HYPERLINK("{found_url}", "✅")'
                        match_count += 1
                    else:
                        # 매체명이 존재하지만 기사가 없는 경우
                        if i >= 2: # 제목 행 아래부터만 '-' 표시
                            new_col[i] = "-"

                # 4. 시트 업데이트
                col_name = f"Result_{datetime.now().strftime('%H%M%S')}"
                df[col_name] = new_col
                
                conn.update(worksheet=SHEET_NAME, data=df)
                
                st.success(f"✅ 업데이트 성공! (매칭: {match_count}건)")
                st.balloons()

        except Exception as e:
            st.error(f"오류 발생: {e}")
