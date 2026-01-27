import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. 초기 설정
st.set_page_config(page_title="삼천리 홍보팀 현황판", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 보도자료 게재 현황판 (최종 보정본)")

# 2. 입력 인터페이스
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="예: 삼천리 신년 하례식")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 소스를 입력해주세요.")
    else:
        try:
            # 3. 데이터 로드 및 도화지 작업
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # 행이 부족하면 100행까지 늘려 에러 방지
            if len(df) < 100:
                padding = pd.DataFrame([[""] * df.shape[1]] * (100 - len(df)))
                df = pd.concat([df, padding], ignore_index=True)

            # 4. HTML 매체명 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    m = re.search(r'\((.*?) \d{4}', span.get_text())
                    if m: found_media.add(m.group(1).strip())

            # 5. 새로운 열(Column) 데이터 생성
            new_col_data = [""] * len(df)
            new_col_data[1] = doc_date.strftime('%m/%d') # 2행에 날짜
            new_col_data[2] = doc_title                   # 3행에 제목

            # 6. B열(index 1) 매체 리스트와 비교 (4행/index 3부터 시작)
            for i in range(len(df)):
                m_name = str(df.iloc[i, 1]).strip()
                if i < 3 or not m_name or m_name in ["매체", "구분"]: 
                    continue
                
                # 괄호 내용(배포X 등) 무시하고 비교
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                if any(pure_name in fm or fm in pure_name for fm in found_media):
                    new_col_data[i] = "✅"
                else:
                    new_col_data[i] = "-"

            # 7. 절대 밀리지 않게 '오른쪽 끝'에 열 추가
            new_col_idx = df.shape[1]
            df.insert(new_col_idx, f"Result_{datetime.now().strftime('%H%M%S')}", new_col_data)
            
            # 8. 시트 전체 덮어쓰기 업데이트
            conn.update(worksheet=SHEET_NAME, data=df)
            st.success(f"✅ '{doc_title}' 분석 완료! 시트 오른쪽 끝을 확인하세요.")
            st.rerun()

        except Exception as e:
            st.error(f"오류 발생: {e}")

st.divider()
st.subheader("📋 실시간 시트 미리보기")
st.dataframe(conn.read(worksheet=SHEET_NAME, header=None).fillna(""))
