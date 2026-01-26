import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 게재 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 2026년 보도자료 게재 현황판")

# 상단 입력부
col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목", placeholder="보도자료 제목을 입력하세요")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기 (모니터링 결과)", height=200)

if st.button("🚀 현황판 업데이트 시작"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 모두 입력해 주세요.")
    else:
        try:
            # 1. 시트 데이터 읽기 (원본 구조 그대로 유지)
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # [행 확보] 인덱스 오류 방지를 위해 최소 100행까지 확보
            current_rows = len(df)
            if current_rows < 100:
                padding = pd.DataFrame([[""] * df.shape[1]] * (100 - current_rows))
                df = pd.concat([df, padding], ignore_index=True)

            # 2. HTML에서 게재된 매체명 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    m = re.search(r'\((.*?) \d{4}', span.get_text())
                    if m: 
                        found_media.add(m.group(1).strip())

            # 3. 새로운 열 데이터 생성 (기존 열의 맨 오른쪽에 추가)
            new_data = [""] * len(df)
            
            # [위치 고정] 2행(index 1) 날짜, 3행(index 2) 제목
            new_data[1] = doc_date.strftime('%m/%d')
            new_data[2] = doc_title

            # 4. 매체명 매칭 (B열: 인덱스 1 기준)
            # 4행(index 3)부터 매체 리스트(가스신문 등) 검사
            for i in range(len(df)):
                # B열(index 1)의 값을 읽어옴
                if df.shape[1] < 2: continue
                
                m_name = str(df.iloc[i, 1]).strip()
                
                # 4행(index 3) 이전이거나 매체명이 없으면 스킵
                if i < 3 or not m_name or m_name in ["매체", "구분", "0", "1"]:
                    continue
                
                # 순수 매체명 추출 (괄호 제거)
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                
                # HTML 추출 명단과 비교
                if any(pure_name in fm or fm in pure_name for fm in found_media):
                    new_data[i] = "✅"
                else:
                    new_data[i] = "-"

            # 5. 기존 DataFrame에 새로운 열 추가 (데이터가 밀리지 않게 열 이름 지정)
            df[f"Result_{datetime.now().strftime('%H%M%S')}"] = new_data
            
            # 6. 구글 시트 업데이트 (전체 덮어쓰기 방식으로 구조 유지)
            conn.update(worksheet=SHEET_NAME, data=df)
            
            st.success(f"✅ '{doc_title}' 업데이트가 완료되었습니다!")
            st.rerun()

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.subheader("📋 실시간 현황판 미리보기")
st.dataframe(conn.read(worksheet=SHEET_NAME, header=None).fillna(""))
