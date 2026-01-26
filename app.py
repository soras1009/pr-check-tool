import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="삼천리 홍보팀 게재 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 매체별 게재 현황판 자동 업데이트")

tab1, tab2 = st.tabs(["📥 새 보도자료 분석 및 기록", "📊 현재 현황 확인"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        doc_date = st.date_input("배포 날짜", datetime.now())
        doc_title = st.text_input("보도자료 제목", placeholder="제목을 입력하세요")
        
    with col2:
        raw_html = st.text_area("HTML 소스를 붙여넣으세요.", height=300)

    if st.button("🚀 현황판에 기록하기"):
        if not doc_title or not raw_html:
            st.warning("제목과 소스 코드를 입력해주세요.")
        else:
            # 1. 시트 데이터 가져오기
            df_existing = conn.read(worksheet=SHEET_NAME)
            
            # [수정] 이미지 양식상 매체명은 보통 2번째 열(B열)에 위치함
            # 'Unnamed' 등으로 표시될 수 있어 인덱스로 접근합니다.
            media_list = df_existing.iloc[:, 1].tolist() # 2번째 열 전체 읽기

            # 2. HTML 소스에서 실제 보도자료를 쓴 매체들만 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            # <td> 태그 중 기사 정보가 담긴 부분만 타겟팅
            rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
            
            found_media_set = set()
            for row in rows:
                media_info = row.find('span')
                if media_info:
                    media_text = media_info.get_text(strip=True)
                    # '(매체명 2026/01/23)' 형식에서 매체명만 추출
                    match = re.search(r'\((.*?) \d{4}', media_text)
                    if match:
                        found_media_set.add(match.group(1).strip())

            # 3. 새로운 열 데이터 생성 (유연한 매칭 적용)
            new_col_name = f"{doc_date.strftime('%m/%d')}\n{doc_title}"
            new_status = []
            
            for m_name in media_list:
                m_name_str = str(m_name).strip()
                # 시트의 매체명(예: 가스신문)이 추출된 매체셋에 포함되어 있는지 확인
                # '가스신문(배포X)' 같은 경우도 '가스신문'이 포함되어 있으면 인식하도록 개선
                is_matched = False
                for f_media in found_media_set:
                    if f_media in m_name_str or m_name_str in f_media:
                        is_matched = True
                        break
                
                new_status.append("✅" if is_matched else "-")
            
            # 4. 시트에 새로운 열 추가 및 업데이트
            df_existing[new_col_name] = new_status
            conn.update(worksheet=SHEET_NAME, data=df_existing)
            st.success(f"✅ '{doc_title}' 결과가 기록되었습니다!")

with tab2:
    st.subheader("📋 현재 현황판")
    df_display = conn.read(worksheet=SHEET_NAME)
    st.dataframe(df_display, use_container_width=True)
