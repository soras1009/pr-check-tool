import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 게재 관리", layout="wide")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 매체별 게재 현황판 자동 업데이트")

# 탭 구성
tab1, tab2 = st.tabs(["📥 새 보도자료 분석 및 기록", "📊 현재 현황 확인"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. 보도자료 정보")
        doc_date = st.date_input("배포 날짜", datetime.now())
        doc_title = st.text_input("보도자료 제목", placeholder="예: 삼천리 미래사업 이태호 사장 취임")
        
    with col2:
        st.subheader("2. 모니터링 HTML 소스")
        raw_html = st.text_area("HTML 소스를 붙여넣으세요.", height=300)

    if st.button("🚀 현황판에 기록하기"):
        if not doc_title or not raw_html:
            st.warning("제목과 소스 코드를 입력해주세요.")
        else:
            # 1. 시트에서 현재 고정된 매체 리스트 읽어오기
            # (이미지처럼 B열이나 특정 열에 매체명이 있다고 가정)
            df_existing = conn.read(worksheet=SHEET_NAME)
            
            # 매체명이 들어있는 열 찾기 (이미지상 '전문지', '지방지' 옆 열)
            # 여기서는 '매체명'이라는 컬럼이 있다고 가정하거나 첫 번째 열을 사용합니다.
            media_column = df_existing.columns[1] # 보통 2번째 열에 매체명이 있음
            media_list = df_existing[media_column].tolist()

            # 2. HTML 소스 분석 (기사 추출)
            soup = BeautifulSoup(raw_html, 'html.parser')
            rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
            
            found_media = []
            for row in rows:
                media_info = row.find('span')
                if media_info:
                    media_text = media_info.get_text(strip=True)
                    match = re.search(r'\((.*?) \d{4}', media_text)
                    if match:
                        found_media.append(match.group(1).strip())

            # 3. 새로운 열 데이터 생성
            new_col_name = f"{doc_date.strftime('%m/%d')}\n{doc_title}"
            new_status = []
            for media in media_list:
                # 매체명이 포함되어 있는지 체크
                if any(m in str(media) for m in found_media):
                    new_status.append("✅")
                else:
                    new_status.append("-")
            
            # 4. 시트에 새로운 열 추가
            df_existing[new_col_name] = new_status
            
            # 구글 시트 업데이트
            conn.update(worksheet=SHEET_NAME, data=df_existing)
            st.success(f"✅ '{doc_title}' 결과가 새로운 열에 기록되었습니다!")

with tab2:
    st.subheader("📋 현재 현황판 (구글 시트 동기화)")
    df_display = conn.read(worksheet=SHEET_NAME)
    st.dataframe(df_display, use_container_width=True)
