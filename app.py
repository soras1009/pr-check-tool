import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 게재 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("🏢 행 밀림 방지 및 오류 추적 시스템")

col1, col2 = st.columns([1, 2])
with col1:
    doc_date = st.date_input("배포 날짜", datetime.now())
    doc_title = st.text_input("보도자료 제목")
with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 분석 및 ✅ 기록 (오류 추적 포함)"):
    if not doc_title or not raw_html:
        st.warning("제목과 소스를 입력하세요.")
    else:
        # 1. 시트 전체 데이터 읽기
        df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
        
        # 2. HTML에서 게재된 매체명 리스트 추출
        soup = BeautifulSoup(raw_html, 'html.parser')
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        found_media = set()
        for r in rows:
            span = r.find('span')
            if span:
                m = re.search(r'\((.*?) \d{4}', span.get_text())
                if m: found_media.add(m.group(1).strip())

        # 3. 새로운 열 데이터 생성
        new_col_index = df.shape[1]
        new_data = [""] * len(df)
        new_data[1] = doc_date.strftime('%m/%d')
        new_data[2] = doc_title

        # 매칭된 매체를 추적하기 위한 집합
        matched_found_media = set()

        # 4. 매체명 직접 찾아서 매칭
        for i in range(len(df)):
            cell_value = str(df.iloc[i, 1]).strip() # B열
            if not cell_value or cell_value in ["매체", "Unnamed: 1"]: continue
            
            pure_name = re.sub(r'\(.*?\)', '', cell_value).strip()
            
            is_matched = False
            for fm in found_media:
                if pure_name in fm or fm in pure_name:
                    is_matched = True
                    matched_found_media.add(fm) # 매칭 성공한 매체 기록
                    break
            
            if is_matched:
                new_data[i] = "✅"
            elif i > 3: # 제목/날짜 행 제외하고 미게재 표시
                new_data[i] = "-"

        # 5. 시트 업데이트
        df[new_col_index] = new_data
        conn.update(worksheet=SHEET_NAME, data=df)
        
        # --- [오류 추적 로그 출력 부분] ---
        st.success(f"✅ '{doc_title}' 결과가 기록되었습니다!")
        
        st.divider()
        st.subheader("⚠️ 매칭 오류 분석 (디버깅)")
        
        # HTML에는 있는데 시트 리스트에서 못 찾은 매체 계산
        missed_media = found_media - matched_found_media
        
        col_log1, col_log2 = st.columns(2)
        with col_log1:
            st.info(f"💡 HTML에서 찾은 총 기사 수: {len(found_media)}개")
            st.write("※ 중복 기사(한 매체가 여러 번 씀)는 1개로 계산됨")
            
        with col_log2:
            if missed_media:
                st.error(f"❌ 시트 리스트에 없어서 누락된 매체 ({len(missed_media)}개)")
                for m in sorted(list(missed_media)):
                    st.write(f"- {m}")
            else:
                st.success("🎉 모든 매체가 시트 리스트와 완벽히 매칭되었습니다!")

st.divider()
st.dataframe(conn.read(worksheet=SHEET_NAME))
