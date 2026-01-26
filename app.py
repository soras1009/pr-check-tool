import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 게재 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 매체 고정형 게재 현황판 업데이트")

# 1. 보도자료 정보 입력
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="예: 시무식 / EV 대표이사 등")
with col2:
    raw_html = st.text_area("모니터링 HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판에 체크 표시 추가"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        # [데이터 읽기] 헤더를 포함하지 않고 원본 그대로 읽어옴
        df = conn.read(worksheet=SHEET_NAME, header=None)
        
        # [매체명 추출] 이미지상 B열(인덱스 1)에 매체명이 위치함
        # 5행(인덱스 4) 정도부터 실제 매체 리스트가 시작된다고 가정 (필요시 조정 가능)
        start_row = 4 
        media_list = df.iloc[start_row:, 1].tolist()

        # [HTML 분석] 게재된 매체명 찾기
        soup = BeautifulSoup(raw_html, 'html.parser')
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        found_media_set = set()
        for r in rows:
            media_info = r.find('span')
            if media_info:
                m_text = media_info.get_text(strip=True)
                match = re.search(r'\((.*?) \d{4}', m_text)
                if match:
                    found_media_set.add(match.group(1).strip())

        # [새 데이터 열 생성]
        # 날짜와 제목을 상단에 배치 (이미지 양식 반영)
        new_column = [None] * len(df)
        new_column[2] = doc_date.strftime('%m/%d') # 3행에 날짜
        new_column[3] = doc_title                   # 4행에 제목
        
        # 실제 매체별 매칭 결과 (O 표시)
        for i, m_name in enumerate(media_list):
            m_name_str = str(m_name).strip()
            # 매체명에 불필요한 (배포X) 등 제거 후 비교
            clean_name = re.sub(r'\(.*?\)', '', m_name_str).strip()
            
            is_matched = any(clean_name in f_media or f_media in clean_name for f_media in found_media_set)
            new_column[start_row + i] = "○" if is_matched else ""

        # [시트 업데이트] 맨 오른쪽 새로운 열 추가
        df[df.shape[1]] = new_column
        
        # 데이터가 꼬이지 않도록 전체 프레임을 그대로 업데이트
        conn.update(worksheet=SHEET_NAME, data=df)
        st.success(f"✅ '{doc_title}' 결과가 기록되었습니다. 구글 시트를 확인하세요!")

st.divider()
st.subheader("📋 현재 시트 상태 확인")
df_view = conn.read(worksheet=SHEET_NAME)
st.dataframe(df_view)
