import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 보도자료 게재 현황 누적 관리")

# 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 누적 업데이트"):
    if not doc_title or not raw_html:
        st.warning("내용을 모두 입력해주세요.")
    else:
        try:
            with st.spinner("업데이트 중..."):
                # header=None으로 읽어와서 시트의 1행(index 0)부터 인식함
                df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
                
                # HTML 분석
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = {}
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']
                    span = a_tag.find_next_sibling('span')
                    if span:
                        # (매체명 2026/01/23) 패턴에서 매체명 추출
                        m = re.search(r'\((.*?) \d{4}', span.get_text())
                        if m: found_media[m.group(1).strip()] = url

                # 새 결과 열 생성 (시트 전체 길이에 맞춤)
                new_col = [""] * len(df)
                
                # [좌표 고정] index 0=1행, 1=2행, 2=3행
                if len(new_col) >= 3:
                    new_col[0] = f"Log_{datetime.now().strftime('%H%M%S')}" # 1행
                    new_col[1] = doc_date.strftime('%m/%d')                # 2행
                    new_col[2] = doc_title                                 # 3행

                match_count = 0
                # index 3(4행)부터 매체명 비교 시작
                for i in range(len(df)):
                    if i < 3: continue 
                    
                    sheet_media = str(df.iloc[i, 0]).strip()
                    # 유효한 매체명이 있는 경우만 처리
                    if not sheet_media or sheet_media in ["0", "1", "매체명"]: continue
                    
                    # 괄호 제거 후 순수 이름으로 매칭
                    pure_name = re.sub(r'\(.*?\)', '', sheet_media).strip()
                    
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

                # 기존 데이터프레임의 가장 오른쪽에 새 열 추가
                df[f"Col_{datetime.now().strftime('%H%M%S')}"] = new_col
                
                # 시트 업데이트
                conn.update(worksheet=SHEET_NAME, data=df)
                st.success(f"✅ 업데이트 완료! (매칭: {match_count}건)")
                st.balloons()
                
        except Exception as e:
            st.error(f"오류 발생: {e}")
