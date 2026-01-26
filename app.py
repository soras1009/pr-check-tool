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
    doc_title = st.text_input("보도자료 제목", placeholder="제목을 입력하세요")

with col2:
    raw_html = st.text_area("HTML 소스 붙여넣기", height=200)

if st.button("🚀 현황판 업데이트 시작"):
    if not doc_title or not raw_html:
        st.warning("내용을 입력해주세요.")
    else:
        try:
            # 1. 시트 읽기
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # 최소 100행 확보
            if len(df) < 100:
                padding = pd.DataFrame([[""] * df.shape[1]] * (100 - len(df)))
                df = pd.concat([df, padding], ignore_index=True)
            
            # 2. HTML 매체명 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            found_media = set()
            
            for r in soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x):
                span = r.find('span')
                if span:
                    # 괄호 안의 매체명 추출
                    m = re.search(r'\((.*?)\s+\d{4}/', span.get_text())
                    if m:
                        media_name = m.group(1).strip()
                        found_media.add(media_name)
            
            st.info(f"🔍 발견된 매체: {len(found_media)}개")
            with st.expander("추출된 매체명 확인"):
                st.write(sorted(found_media))
            
            # 3. C열(index 2)이 비어있는지 확인
            if df.shape[1] < 3:
                # C열이 없으면 생성
                while df.shape[1] < 3:
                    df[df.shape[1]] = ""
            
            # 4. C열부터 빈 열 찾기 (1행 기준으로 확인)
            target_col_idx = 2  # C열부터 시작
            while target_col_idx < df.shape[1]:
                # 해당 열의 1행이 비어있으면 사용
                if df.iloc[0, target_col_idx] == "":
                    break
                target_col_idx += 1
            
            # 5. 새 열이 필요하면 추가
            if target_col_idx >= df.shape[1]:
                df[target_col_idx] = ""
            
            # 6. 새로운 열 데이터 생성 (1행=번호, 2행=날짜, 3행=제목)
            col_number = target_col_idx - 1  # C열=2, D열=3, ...
            df.iloc[0, target_col_idx] = str(col_number)  # 1행: 번호
            df.iloc[1, target_col_idx] = doc_date.strftime('%m/%d')  # 2행: 날짜
            df.iloc[2, target_col_idx] = doc_title  # 3행: 제목
            
            # 7. 4행부터 매칭 (index 3부터)
            match_count = 0
            for i in range(3, len(df)):
                m_name = str(df.iloc[i, 1]).strip()  # B열
                
                if not m_name or m_name in ["매체명", "구분", ""]:
                    df.iloc[i, target_col_idx] = ""
                    continue
                
                # 괄호 제거
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                
                # 매칭 체크
                is_matched = False
                for fm in found_media:
                    # 양방향 포함 체크
                    if pure_name in fm or fm in pure_name:
                        is_matched = True
                        break
                
                if is_matched:
                    df.iloc[i, target_col_idx] = "O"
                    match_count += 1
                else:
                    df.iloc[i, target_col_idx] = ""
            
            # 8. 시트 업데이트
            conn.update(worksheet=SHEET_NAME, data=df)
            
            col_letter = chr(65 + target_col_idx)  # A=65, B=66, C=67...
            st.success(f"✅ {col_letter}열에 업데이트 완료! (매칭: {match_count}개)")
            
            # 결과 미리보기
            with st.expander("📊 업데이트 결과 미리보기"):
                preview_df = df.iloc[:50, [1, target_col_idx]]
                preview_df.columns = ["매체명", "결과"]
                st.dataframe(preview_df[preview_df["결과"] != ""], use_container_width=True)
            
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
            st.exception(e)
