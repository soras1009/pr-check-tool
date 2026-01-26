import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 게재 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 보도자료 게재 현황판")

# 상단 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="보도자료 제목 입력")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        try:
            # 1. 시트 데이터 읽기
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # [행 확보] 최소 100행까지 확보하여 인덱스 에러 방지
            if len(df) < 100:
                padding = pd.DataFrame([[""] * df.shape[1]] * (100 - len(df)))
                df = pd.concat([df, padding], ignore_index=True)

            # 2. HTML에서 게재 매체 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    m = re.search(r'\((.*?) \d{4}', span.get_text())
                    if m: found_media.add(m.group(1).strip())

            # 3. 새로운 열(Column) 데이터 생성
            new_data = [""] * len(df)
            
            # 위치 고정: 2행(index 1) 날짜, 3행(index 2) 제목
            new_data[1] = doc_date.strftime('%m/%d')
            new_data[2] = doc_title

            # 4. B열(index 1) 매체명 매칭 - 4행(index 3)부터 시작
            for i in range(len(df)):
                m_name = str(df.iloc[i, 1]).strip()
                
                # 매체 리스트 시작점(4행) 이전이거나 빈칸 스킵
                if i < 3 or not m_name or m_name in ["매체", "구분", "0", "1"]:
                    continue
                
                # 괄호 제거 후 비교 (예: 전기신문(배포X) -> 전기신문)
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                
                if any(pure_name in fm or fm in pure_name for fm in found_media):
                    new_data[i] = "✅"
                else:
                    new_data[i] = "-"

            # 5. 기존 데이터 옆에 새 열 추가
            df[f"Col_{df.shape[1]}"] = new_data
