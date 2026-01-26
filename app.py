import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 게재 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 매체 고정형 게재 현황판 (✅ 체크 버전)")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("1. 보도자료 정보")
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="예: 시무식 / 이태호 사장 취임 등")
with col2:
    st.subheader("2. 모니터링 소스")
    raw_html = st.text_area("HTML 소스를 붙여넣으세요.", height=200)

if st.button("🚀 현황판에 ✅ 표시 기록하기"):
    if not doc_title or not raw_html:
        st.warning("제목과 소스를 입력하세요.")
    else:
        # 1. 시트 원본 읽기 (헤더 없이 전체 구조 유지)
        df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
        
        # 2. 매체명 리스트 (B열: 인덱스 1, 5행: 인덱스 4부터 시작)
        start_row = 4 
        media_names = df.iloc[start_row:, 1].tolist()

        # 3. HTML에서 게재된 매체명 추출
        soup = BeautifulSoup(raw_html, 'html.parser')
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        found_media = set()
        for r in rows:
            span = r.find('span')
            if span:
                m = re.search(r'\((.*?) \d{4}', span.get_text())
                if m: found_media.add(m.group(1).strip())

        # 4. 새로운 열(Column) 데이터 생성
        new_col_index = df.shape[1]
        new_data = [""] * len(df)
        
        # 상단 행 위치 지정 (이미지 양식 기준)
        new_data[1] = doc_date.strftime('%m/%d') # 2행에 날짜
        new_data[2] = doc_title                   # 3행에 제목

        # 매체별 매칭 및 '✅' 표시
        for i, name in enumerate(media_names):
            name_str = str(name).strip()
            if not name_str: continue
            
            # (배포X) 등 괄호 내용 제거 후 비교
            pure_name = re.sub(r'\(.*?\)', '', name_str).strip()
            
            # 매체명이 포함되어 있다면 초록색 체크박스 표시
            if any(pure_name in fm or fm in pure_name for fm in found_media):
                new_data[start_row + i] = "✅"
            else:
                new_data[start_row + i] = "-"

        # 5. 데이터프레임 업데이트 및 저장
        df[new_col_index] = new_data
        conn.update(worksheet=SHEET_NAME, data=df)
        st.success(f"✅ '{doc_title}' 결과가 시트 맨 오른쪽에 기록되었습니다!")

st.divider()
st.subheader("📋 실시간 시트 미리보기")
st.dataframe(conn.read(worksheet=SHEET_NAME))
