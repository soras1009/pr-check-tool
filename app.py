import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")

# 캐싱을 활용해 연결 속도 향상
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 보도자료 게재 현황판")

# 상단 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="예: 2026년 상반기 경영실적 발표")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200, placeholder="스크랩 서비스의 HTML 소스를 복사해 넣어주세요.")

if st.button("🚀 현황판 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해주세요.")
    else:
        with st.spinner("데이터를 분석하고 시트를 업데이트 중입니다..."):
            try:
                # 1. 최신 데이터 읽기 (전체 데이터를 가져오되, 빈 행 제거 고려)
                df = conn.read(worksheet=SHEET_NAME).fillna("")
                
                # 2. HTML 매체명 추출 로직 개선
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = set()
                
                # 기존 스타일 기반 + 텍스트 패턴 기반 병행
                tds = soup.find_all('td')
                for td in tds:
                    text = td.get_text().strip()
                    # 괄호 안의 매체명 추출 (예: (조선일보 2026-01-30))
                    m = re.search(r'\((.*?) \d{4}', text)
                    if m:
                        found_media.add(m.group(1).strip())

                if not found_media:
                    st.error("HTML에서 매체명을 찾을 수 없습니다. 소스 형식을 확인해주세요.")
                    st.stop()

                # 3. 새로운 결과 열 생성
                # 시트 구조에 따라 인덱스를 조정하세요 (현재 B열에 매체명이 있다고 가정)
                new_results = []
                
                # 헤더 구성 (1행: 날짜, 2행: 제목, 3행부터 결과)
                # 시트의 행 수에 맞춰 리스트 생성
                status_col = []
                for i, row in df.iterrows():
                    # 0번 인덱스가 엑셀의 2행(날짜), 1번이 3행(제목)인 경우 예시
                    if i == 0: 
                        status_col.append(doc_date.strftime('%m/%d'))
                    elif i == 1: 
                        status_col.append(doc_title)
                    else:
                        # 매체명 매칭 (B열 기준)
                        m_name = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                        
                        if pure_name and any(pure_name in fm or fm in pure_name for fm in found_media):
                            status_col.append("✅")
                        else:
                            status_col.append("-")

                # 4. 데이터프레임 합치기
                new_col_name = f"배포_{datetime.now().strftime('%m%d_%H%M')}"
                df[new_col_name] = status_col

                # 5. 업데이트
                conn.update(worksheet=SHEET_NAME, data=df)
                
                st.success(f"✅ 업데이트 완료! 총 {len(found_media)}개 매체 매칭됨.")
                st.balloons()
                
                # 결과 미리보기
                with st.expander("추출된 매체 리스트 확인"):
                    st.write(", ".join(list(found_media)))

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("Samchully PR Dashboard v1.1 | 2026")
