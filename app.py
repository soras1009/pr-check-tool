import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="삼천리 홍보팀 게재 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 보도자료 게재 현황판")

col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="제목을 입력하세요")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트 시작"):
    if not doc_title or not raw_html:
        st.warning("내용을 입력해주세요.")
    else:
        try:
            # 1. 시트 읽기 (B열 매체명 리스트 보호)
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # 2. HTML 매체명 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    m = re.search(r'\((.*?) \d{4}', span.get_text())
                    if m: found_media.add(m.group(1).strip())

            # 3. 신규 열 데이터 생성
            new_col = [""] * len(df)
            new_col[1] = doc_date.strftime('%m/%d') # 2행 날짜
            new_col[2] = doc_title                   # 3행 제목

            # 4. B열(index 1) 기준 4행(index 3)부터 매칭
            for i in range(len(df)):
                m_name = str(df.iloc[i, 1]).strip()
                if i < 3 or not m_name or m_name in ["매체", "구분"]: continue
                
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                if any(pure_name in fm or fm in pure_name for fm in found_media):
                    new_col[i] = "✅"
                else:
                    new_col[i] = "-"

            # 5. 오른쪽 끝에 열 추가 후 업데이트
            df[f"Col_{df.shape[1]}"] = new_col
            conn.update(worksheet=SHEET_NAME, data=df)
            st.success("✅ 업데이트 성공!")
            st.rerun()

        except Exception as e:
            st.error(f"오류 발생: {e}")
