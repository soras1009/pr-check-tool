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

st.title("🏢 보도자료 게재 현황 누적 관리")

# 3. 입력부 (배포 정보 및 HTML 소스)
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="기사 제목을 입력하세요")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200, placeholder="뉴스 스크랩 HTML 소스를 붙여넣으세요")

# 4. 실행 버튼 및 누적 업데이트 로직
if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 및 시트 업데이트 중..."):
                # 최신 시트 데이터 읽기 (전체 행/열 유지)
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석: 매체명과 URL 매칭
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = {} # { "매체명": "URL" }
                
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        span_text = span.get_text()
                        # (매체명 2026/01/23) 패턴에서 매체명만 추출
                        m = re.search(r'\((.*?) \d{4}', span_text)
                        if m:
                            media_name = m.group(1).strip()
                            found_media[media_name] = url

                if not found_media:
                    st.error("HTML에서 매체 정보를 찾을 수 없습니다. 소스 형식을 확인해주세요.")
                    st.stop()

                # 새로운 결과 열 생성 (A열 길이에 맞춤)
                new_col = [""] * len(df)
                
                # 헤더 구성 (이미지 구조에 맞게 1행: 날짜, 2행: 제목)
                if len(new_col) > 1:
                    new_col[0] = doc_date.strftime('%m/%d')
                    new_col[1] = doc_title

                # A열(index 0)의 매체명 리스트와 비교하여 체크
                match_count = 0
                for i in range(len(df)):
                    # 3행(index 2)부터 매체명 비교 시작
                    if i < 2: continue
                    
                    # A열에 적힌 매체명 가져오기
                    sheet_media = str(df.iloc[i, 0]).strip()
                    if not sheet_media: continue
                    
                    # 가공된 이름으로 매칭 (괄호 제거 등)
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
                    # HTML 데이터와 매칭
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

                # 기존 데이터프레임의 가장 오른쪽 열로 추가
                new_col_name = f"Result_{datetime.now().strftime('%H%M%S')}"
                df[new_col_name] = new_col
                
                # 구글 시트에 최종 데이터 쓰기
                conn.update(worksheet=SHEET_NAME, data=df)
                
                st.success(f"✅ 업데이트 성공! (매칭된 기사: {match_count}건)")
                st.balloons()
                
                with st.expander("추출된 매체 리스트"):
                    st.write(", ".join(found_media.keys()))

        except Exception as e:
            st.error(f"실행 중 오류 발생: {e}")

st.divider()
st.info("💡 사용법: 구글 시트의 **A열 3행**부터 관리하실 매체명 리스트를 미리 입력해 두세요.")
