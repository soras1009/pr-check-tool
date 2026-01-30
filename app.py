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

st.title("🏢 2026년 보도자료 게재 현황판")

# 3. 입력부 (변수를 먼저 정의합니다)
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="기사 제목을 입력하세요")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200, placeholder="뉴스 스크랩 HTML 소스를 붙여넣으세요")

# 4. 실행 버튼 및 로직
if st.button("🚀 현황판 업데이트"):
    # 입력값이 있는지 먼저 체크
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 중..."):
                # 시트 읽기
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석
                soup = BeautifulSoup(raw_html, 'html.parser')
                media_map = {}
                
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        span_text = span.get_text()
                        m = re.search(r'\((.*?) \d{4}', span_text)
                        if m:
                            media_name = m.group(1).strip()
                            media_map[media_name] = url

                if not media_map:
                    st.error("HTML에서 매체 정보를 찾을 수 없습니다.")
                else:
                    # 데이터 매칭 및 열 생성
                    new_col = [""] * len(df)
                    if len(new_col) > 2:
                        new_col[1] = doc_date.strftime('%m/%d')
                        new_col[2] = doc_title

                    match_count = 0
                    for i in range(len(df)):
                        if i < 3 or df.shape[1] < 2: continue
                        sheet_media = str(df.iloc[i, 1]).strip()
                        pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                        
                        found_url = None
                        for m_name, url in media_map.items():
                            if pure_name in m_name or m_name in pure_name:
                                found_url = url
                                break
                        
                        if found_url:
                            new_col[i] = f'=HYPERLINK("{found_url}", "보기(✅)")'
                            match_count += 1
                        else:
                            new_col[i] = "-"

                    # 결과 업데이트
                    col_id = datetime.now().strftime('%H%M%S')
                    df[f"결과_{col_id}"] = new_col
                    conn.update(worksheet=SHEET_NAME, data=df)
                    
                    st.success(f"✅ 업데이트 성공! (매칭: {match_count}건)")
                    st.balloons()

        except Exception as e:
            st.error(f"실행 중 오류 발생: {e}")

st.divider()
st.caption("Samchully PR Team Tool - 2026")
