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

# 연결 상태 확인
with st.expander("🔧 연결 상태 확인", expanded=False):
    try:
        test_df = conn.read(worksheet=SHEET_NAME, usecols=list(range(50)), header=None, ttl=0)
        st.success(f"✅ 구글 시트 읽기 성공! (행: {len(test_df)}, 열: {test_df.shape[1]})")
        
        # 쓰기 권한 테스트
        st.write("---")
        st.write("**쓰기 권한 테스트:**")
        if st.button("🧪 쓰기 테스트 (A1셀에 테스트 문구 쓰기)"):
            try:
                test_write_df = test_df.copy()
                original_value = test_write_df.iloc[0, 0]
                test_write_df.iloc[0, 0] = f"테스트_{datetime.now().strftime('%H:%M:%S')}"
                
                conn.update(worksheet=SHEET_NAME, data=test_write_df)
                st.success("✅ 쓰기 성공! 구글 시트를 확인해보세요!")
                st.info(f"원래 값: {original_value} → 테스트 값으로 변경됨")
            except Exception as write_error:
                st.error(f"❌ 쓰기 실패: {write_error}")
                st.write("**해결 방법:** Service Account에 편집 권한을 부여하세요")
        
        st.write("---")
        st.write("첫 5행 미리보기:")
        st.dataframe(test_df.head())
    except Exception as e:
        st.error(f"❌ 구글 시트 연결 실패: {e}")
        st.info("""
        **해결 방법:**
        1. Streamlit Cloud → Settings → Secrets 확인
        2. Service Account에 편집 권한 부여
        3. 스프레드시트 URL 확인
        """)

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
            # 1. 시트 읽기 - 범위 지정 (50개 열까지)
            df = conn.read(worksheet=SHEET_NAME, usecols=list(range(50)), header=None).fillna("")
            
            # 최소 200행 확보 (매체 150개 + 여유)
            if len(df) < 200:
                padding = pd.DataFrame([[""] * df.shape[1]] * (200 - len(df)))
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
            
            # 3. 새로운 구조에 맞춰 처리
            # - 0행(1행): 날짜들
            # - 1행(2행): 제목들
            # - 2행(3행)부터: 매체명 & 게재 여부
            
            # C열(index 2)부터 빈 열 찾기
            if df.shape[1] < 3:
                while df.shape[1] < 3:
                    df[df.shape[1]] = ""
            
            # C열부터 빈 열 찾기 - 0행(날짜)이 비어있는 열 찾기
            target_col_idx = 2  # C열부터 시작
            while target_col_idx < df.shape[1]:
                date_val = str(df.iloc[0, target_col_idx]).strip()
                if date_val == "":
                    break
                target_col_idx += 1
            
            # 4. 새 열이 필요하면 추가
            if target_col_idx >= df.shape[1]:
                df[target_col_idx] = ""
            
            # 5. B1에 "매체명" 헤더가 없으면 추가
            if str(df.iloc[0, 1]).strip() == "":
                df.iloc[0, 1] = "매체명"
            
            # 6. 데이터 입력
            df.iloc[0, target_col_idx] = doc_date.strftime('%m/%d')  # 0행: 날짜
            df.iloc[1, target_col_idx] = doc_title  # 1행: 제목
            
            # 7. 2행(index 2)부터 매체 매칭
            match_count = 0
            for i in range(2, len(df)):
                m_name = str(df.iloc[i, 1]).strip()  # B열 매체명
                
                if not m_name or m_name in ["매체명", "구분", ""]:
                    df.iloc[i, target_col_idx] = ""
                    continue
                
                # 괄호 제거
                pure_name = re.sub(r'\(.*?\)', '', m_name).strip()
                
                # 매칭 체크
                is_matched = False
                for fm in found_media:
                    if pure_name in fm or fm in pure_name:
                        is_matched = True
                        break
                
                if is_matched:
                    df.iloc[i, target_col_idx] = "v"  # v 표시
                    match_count += 1
                else:
                    df.iloc[i, target_col_idx] = ""  # 빈칸
            
            # 8. 시트 업데이트
            st.info("⏳ 구글 시트에 데이터를 쓰는 중...")
            
            # 업데이트 전 데이터 확인
            st.write("업데이트할 데이터 샘플:")
            st.write(f"- 대상 열: {chr(65 + target_col_idx)}열 (index {target_col_idx})")
            st.write(f"- 날짜: {df.iloc[0, target_col_idx]}")
            st.write(f"- 제목: {df.iloc[1, target_col_idx]}")
            
            try:
                # 업데이트
                result = conn.update(worksheet=SHEET_NAME, data=df)
                
                col_letter = chr(65 + target_col_idx)
                st.success(f"✅ {col_letter}열에 업데이트 완료! (매칭: {match_count}개)")
                st.info("💡 구글 시트를 새로고침(Ctrl+Shift+R)해서 확인해보세요!")
                
                # 업데이트 결과 확인
                if result is not None:
                    st.write("업데이트 결과:", result)
                    
            except Exception as update_error:
                st.error(f"❌ 시트 업데이트 실패: {update_error}")
                st.write("에러 상세:")
                st.exception(update_error)
            
            # 결과 미리보기
            with st.expander("📊 업데이트 결과 미리보기"):
                preview_data = []
                for i in range(2, min(200, len(df))):
                    media = str(df.iloc[i, 1]).strip()
                    result = str(df.iloc[i, target_col_idx]).strip()
                    if result == "v" and media:
                        preview_data.append({"매체명": media, "결과": "✓"})
                
                if preview_data:
                    st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
                else:
                    st.info("매칭된 매체가 없습니다.")
            
        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
            st.exception(e)
