import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 보도자료 게재 현황 누적 관리")

# 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("내용을 모두 입력해주세요.")
    else:
        try:
            with st.spinner("업데이트 중..."):
                # A1부터 데이터를 순수하게 읽어옴
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

                # 새 열 생성
                new_col = [""] * len(df)
                
                # [좌표 고정] 1행: 날짜, 2행: 제목
                if len(new_col) >= 2:
                    new_col[0] = doc_date.strftime('%m/%d')
                    new_col[1] = doc_title

                # 4행(index 3)부터 매체명 비교
                match_count = 0
                for i in range(len(df)):
                    if i < 3: continue 
                    
                    sheet_media = str(df.iloc[i, 0]).strip()
                    if not sheet_media or sheet_media in ["0", "1"]: continue
                    
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
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

                # 열 추가 및 업데이트
                df[f"Col_{datetime.now().strftime('%H%M%S')}"] = new_col
                conn.update(worksheet=SHEET_NAME, data=df)
                st.success(f"✅ 업데이트 완료! (매칭: {match_count}건)")
                st.balloons()
        except Exception as e:
            st.error(f"오류: {e}")
