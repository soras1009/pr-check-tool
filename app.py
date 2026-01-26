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

st.title("🏢 행 밀림 방지형 현황판 업데이트")

col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 정확한 위치에 ✅ 기록하기"):
    if not doc_title or not raw_html:
        st.warning("제목과 소스를 입력하세요.")
    else:
        # 1. 시트 전체 데이터 읽기 (원본 구조 유지)
        df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
        
        # 2. HTML에서 게재된 매체명 리스트 추출
        soup = BeautifulSoup(raw_html, 'html.parser')
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        found_media = set()
        for r in rows:
            span = r.find('span')
            if span:
                m = re.search(r'\((.*?) \d{4}', span.get_text())
                if m: found_media.add(m.group(1).strip())

        # 3. 새로운 열 데이터 생성 (기본값은 빈칸 혹은 '-')
        new_col_index = df.shape[1]
        new_data = [""] * len(df)
        
        # 날짜와 제목 위치 고정 (이미지상 2행, 3행)
        new_data[1] = doc_date.strftime('%m/%d')
        new_data[2] = doc_title

        # 4. [핵심] 매체명을 직접 찾아서 해당 행에 체크 표시
        # B열(인덱스 1)을 한 줄씩 검사합니다.
        for i in range(len(df)):
            cell_value = str(df.iloc[i, 1]).strip() # B열의 값
            if not cell_value or cell_value == "매체": continue
            
            # (배포X) 등 괄호 제거 후 순수 매체명 추출
            pure_name = re.sub(r'\(.*?\)', '', cell_value).strip()
            
            # HTML에서 찾은 매체명과 시트의 매체명이 매칭되는지 확인
            if any(pure_name in fm or fm in pure_name for fm in found_media):
                new_data[i] = "✅"
            else:
                # 기사 체크가 시작되는 행(2행 이후)부터만 '-' 표시
                if i > 2 and pure_name:
                    new_data[i] = "-"

        # 5. 시트 업데이트
        df[new_col_index] = new_data
        conn.update(worksheet=SHEET_NAME, data=df)
        st.success(f"✅ '{doc_title}' 결과가 매체별 행 위치에 맞춰 정확히 기록되었습니다!")

st.divider()
st.dataframe(conn.read(worksheet=SHEET_NAME))
