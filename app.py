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

st.title("🏢 2026년 보도자료 게재 현황판")

# 상단 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트"):
    if not doc_title or not raw_html:
        st.warning("내용을 입력해주세요.")
    else:
        try:
            # 1. 시트 읽기 (최대한 가볍게)
            # 데이터가 있는 영역만 읽어오도록 설정
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # 2. HTML 매체명 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    m = re.search(r'\((.*?) \d{4}', span.get_text())
                    if m: found_media.add(m.group(1).strip())

            # 3. 새로운 결과 열 데이터 생성
            new_col = [""] * len(df)
            # 인덱스 범위 확인 후 안전하게 입력 (2행, 3행)
            if len(new_col) > 2:
                new_col[1] = doc_date.strftime('%m/%d')
                new_col[2] = doc_title

            # 4. 매체명 매칭 (B열: index 1) - 4행(index 3)부터
            for i in range(len(df)):
                if i < 3 or df.shape[1] < 2: continue
                m_name = str(df.iloc[i, 1]).strip()
                if not m_name or m_name in ["매체", "구분"]: continue
                
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                if any(pure_name in fm or fm in pure_name for fm in found_media):
                    new_col[i] = "✅"
                else:
                    new_col[i] = "-"

            # 5. 오른쪽 끝에 열 추가
            df[f"R_{datetime.now().strftime('%H%M%S')}"] = new_col
            
            # 6. 업데이트 (성공 메시지 출력)
            conn.update(worksheet=SHEET_NAME, data=df)
            st.success("✅ 업데이트 성공!")
            st.balloons() # 축하 효과
            
        except Exception as e:
            st.error(f"연결 오류: {e}")

st.divider()
st.info("💡 팁: 'Running'이 길어지면 브라우저를 새로고침(F5)한 뒤 다시 시도해 보세요.")
