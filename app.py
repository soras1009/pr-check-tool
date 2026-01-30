import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 보도자료 게재 현황 누적 관리")

# 3. 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 및 시트 업데이트 중..."):
                # 최신 시트 데이터 읽기 (머리글 없이 전체 데이터 보존)
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석: 매체명과 URL 매칭
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = {}
                
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        span_text = span.get_text()
                        m = re.search(r'\((.*?) \d{4}', span_text)
                        if m:
                            media_name = m.group(1).strip()
                            found_media[media_name] = url

                # 4. 새로운 결과 열 생성 (정확한 행 매칭)
                new_col = [""] * len(df)
                
                # [고정] 1행(index 0)에 날짜, 2행(index 1)에 제목 입력
                if len(new_col) >= 2:
                    new_col[0] = doc_date.strftime('%m/%d')
                    new_col[1] = doc_title

                match_count = 0
                # [고정] 3행(index 2)부터 매체명 비교 시작
                for i in range(len(df)):
                    if i < 2: continue
                    
                    # A열(index 0)에 적힌 매체명 가져오기
                    sheet_media = str(df.iloc[i, 0]).strip()
                    if not sheet_media or sheet_media == "0": continue
                    
                    # 매체명 가공 (괄호 제거)
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
                    # HTML 데이터와 매칭
                    found_url = None
                    for m_name, url in found_media.items():
                        if pure_name in m_name or m_name in pure_name:
                            found_url = url
                            break
                    
                    if found_url:
                        new_col[i] = f'=HYPERLINK("{found_url}", "✅")'
                        match_count += 1
                    else:
                        new_col[i] = "-"

                # 5. 시트 업데이트 (기존 데이터 유지 + 새 열 추가)
                # 고유한 컬럼 ID 생성
                col_id = f"Result_{datetime.now().strftime('%H%M%S')}"
                df[col_id] = new_col
                
                conn.update(worksheet=SHEET_NAME, data=df)
                
                st.success(f"✅ 업데이트 성공! (매칭: {match_count}건)")
                st.balloons()

        except Exception as e:
            st.error(f"오류 발생: {e}")
