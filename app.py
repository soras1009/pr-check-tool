import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 성과 대시보드", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년" # 사용하는 시트 이름 확인

st.title("📊 보도자료 게재 성과 대시보드")

# 1. 입력 영역
with st.container():
    col1, col2 = st.columns([1, 2])
    with col1:
        doc_date = st.date_input("📅 배포 날짜", datetime.now())
        doc_title = st.text_input("📝 보도자료 제목", placeholder="예: 삼천리 신년 전략 발표")
    with col2:
        raw_html = st.text_area("🔗 HTML 소스 붙여넣기", height=150)

# 2. 저장 로직
if st.button("🚀 게재 내역 업데이트 및 성적표 갱신"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        try:
            with st.spinner("데이터 분석 중..."):
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = set()
                # HTML 내 매체명 추출
                for td in soup.find_all('td'):
                    m = re.search(r'\((.*?) \d{4}', td.get_text())
                    if m: found_media.add(m.group(1).strip())

                if not found_media:
                    st.error("HTML에서 매체 정보를 찾을 수 없습니다.")
                else:
                    # 신규 데이터 생성
                    new_entries = pd.DataFrame({
                        "배포일": [doc_date.strftime('%Y-%m-%d')] * len(found_media),
                        "보도자료 제목": [doc_title] * len(found_media),
                        "매체명": list(found_media)
                    })

                    # 기존 데이터 읽기 및 병합
                    try:
                        existing_df = conn.read(worksheet=SHEET_NAME).fillna("")
                    except:
                        existing_df = pd.DataFrame(columns=["배포일", "보도자료 제목", "매체명"])

                    updated_df = pd.concat([existing_df, new_entries]).drop_duplicates().reset_index(drop=True)
                    
                    # 구글 시트 업데이트
                    conn.update(worksheet=SHEET_NAME, data=updated_df)
                    st.success(f"✅ {len(found_media)}개 매체가 기록되었습니다!")
                    st.balloons()
        except Exception as e:
            st.error(f"오류: {e}")

st.divider()

# 3. 실시간 매체별 게재 성적표 (관리자용 화면)
st.subheader("📈 매체별 게재 성적표 (누적)")
try:
    df = conn.read(worksheet=SHEET_NAME).fillna("")
    if not df.empty:
        total_pr = df["보도자료 제목"].nunique() # 총 배포 건수
        scorecard = df.groupby("매체명").size().reset_index(name="게재 횟수")
        scorecard["게재율 (%)"] = scorecard["게재 횟수"].apply(lambda x: f"{(x / total_pr * 100):.1f}%")
        scorecard = scorecard.sort_values(by="게재 횟수", ascending=False).reset_index(drop=True)

        c1, c2 = st.columns([1, 3])
        c1.metric("올해 총 배포 건수", f"{total_pr}건")
        c2.dataframe(scorecard, use_container_width=True)
    else:
        st.info("기록된 데이터가 없습니다.")
except:
    st.write("데이터를 불러오는 중입니다...")
