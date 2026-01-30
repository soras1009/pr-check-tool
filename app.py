import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 보도자료 게재 현황 누적 관리")

# 2. 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="기사 제목을 입력하세요")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200, placeholder="뉴스 스크랩 HTML 소스를 붙여넣으세요")

if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 및 시트 업데이트 중..."):
                # header=None으로 설정하여 A1부터 순수 데이터로 읽어옵니다.
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석: 매체명과 URL 추출
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = {}
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        span_text = span.get_text()
                        # (매체명 2026/01/23) 패턴에서 매체명만 추출
                        m = re.search(r'\((.*?) \d{4}', span_text)
                        if m:
                            found_media[m.group(1).strip()] = url

                # 3. 새로운 결과 열 생성 (시트 전체 길이에 맞춤)
                new_col = [""] * len(df)
                
                # [좌표 고정] 1행: ID, 2행: 날짜, 3행: 제목
                if len(new_col) >= 3:
                    new_col[0] = f"Log_{datetime.now().strftime('%H%M%S')}" # 1행 (A1 옆)
                    new_col[1] = doc_date.strftime('%m/%d')                # 2행 (A2 옆)
                    new_col[2] = doc_title                                 # 3행 (A3 옆)

                match_count = 0
                # [매칭 시작] 4행(index 3)부터 A열의 매체명을 읽습니다.
                for i in range(len(df)):
                    if i < 3: continue # 1~3행은 헤더 영역이므로 건너뜁니다.
                    
                    sheet_media = str(df.iloc[i, 0]).strip()
                    if not sheet_media or sheet_media == "0": continue
                    
                    # 매체명 가공 (괄호 제거 등)
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
                    # HTML 데이터와 매칭
                    found_url = None
                    for m_name, url in found_media.items():
                        if pure_name in m_name or m_name in pure_name:
                            found_url = url
                            break
                    
                    if found_url:
                        # 매체명과 같은 행(i)에 하이퍼링크 체크 표시
                        new_col[i] = f'=HYPERLINK("{found_url}", "✅")'
                        match_count += 1
                    else:
                        new_col[i] = "-"

                # 4. 시트 업데이트 (기존 데이터 오른쪽에 새 열 추가)
                col_name = f"Col_{datetime.now().strftime('%H%M%S')}"
                df[col_name] = new_col
                
                conn.update(worksheet=SHEET_NAME, data=df)
                
                st.success(f"✅ 업데이트 성공! (매칭된 기사: {match_count}건)")
                st.balloons()

        except Exception as e:
            st.error(f"실행 중 오류 발생: {e}")

st.divider()
st.info("💡 **시트 세팅 확인**: 매체명 리스트를 **A4 셀**부터 입력해 두셨는지 확인해 주세요.")
