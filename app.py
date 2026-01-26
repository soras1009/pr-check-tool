import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 게재 현황판 (양식 최적화)")

col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트"):
    try:
        # 1. 데이터 읽기 (B1이 '매체'이므로 header=0으로 설정)
        df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
        
        # 2. HTML 매체명 추출
        soup = BeautifulSoup(raw_html, 'html.parser')
        found_media = set()
        for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
            span = r.find('span')
            if span:
                m = re.search(r'\((.*?) \d{4}', span.get_text())
                if m: found_media.add(m.group(1).strip())

        # 3. 새로운 열 데이터 생성
        new_col_index = df.shape[1]
        new_data = [""] * len(df)
        
        # 날짜와 제목 입력 (1행, 2행 사용)
        new_data[0] = doc_date.strftime('%m/%d')
        new_data[1] = doc_title

        # 4. 매체명 매칭 (B열: 인덱스 1)
        # B1('매체') 다음인 B2(인덱스 1)부터 검사 시작
        for i in range(len(df)):
            cell_value = str(df.iloc[i, 1]).strip()
            
            # 제목 행이거나 빈칸이면 건너뜀
            if not cell_value or cell_value in ["매체", "Unnamed: 1", "0", "1"]:
                continue
            
            # 매체명 비교 (괄호 제거 로직)
            pure_name = re.sub(r'\(.*?\)', '', cell_value).strip()
            
            if any(pure_name in fm or fm in pure_name for fm in found_media):
                new_data[i] = "✅"
            else:
                # 매체 이름이 있는 행에만 '-' 표시
                if i >= 1: 
                    new_data[i] = "-"

        # 5. 업데이트
        df[new_col_index] = new_data
        conn.update(worksheet=SHEET_NAME, data=df)
        st.success("✅ 업데이트 완료!")
        st.rerun()

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.subheader("📋 시트 미리보기")
st.dataframe(conn.read(worksheet=SHEET_NAME, header=None).fillna(""))
