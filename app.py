import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 성과 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("📊 보도자료 게재 성과 대시보드")

# 2. 상단 입력부
with st.container():
    col1, col2 = st.columns([1, 2])
    with col1:
        doc_date = st.date_input("📅 배포 날짜", datetime.now())
        doc_title = st.text_input("📝 보도자료 제목", placeholder="예: 삼천리 이태호 사장 취임")
    with col2:
        raw_html = st.text_area("🔗 HTML 소스 붙여넣기", height=150, placeholder="스크랩 HTML 소스를 여기에 붙여넣으세요.")

# 3. 데이터 기록 로직
if st.button("🚀 게재 내역 업데이트 및 분석"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        try:
            with st.spinner("데이터를 분석하고 성적표를 갱신 중입니다..."):
                # HTML에서 매체명 추출
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = set()
                for td in soup.find_all('td'):
                    m = re.search(r'\((.*?) \d{4}', td.get_text())
                    if m: found_media.add(m.group(1).strip())

                if not found_media:
                    st.error("HTML에서 매체 정보를 찾을 수 없습니다.")
                else:
                    # 새로운 데이터 생성
                    new_entries = pd.DataFrame({
                        "배포일": [doc_date.strftime('%Y-%m-%d')] * len(found_media),
                        "보도자료 제목": [doc_title] * len(found_media),
                        "매체명": list(found_media)
                    })

                    # 기존 데이터 읽기
                    try:
                        existing_df = conn.read(worksheet=SHEET_NAME).fillna("")
                    except:
                        existing_df = pd.DataFrame(columns=["배포일", "보도자료 제목", "매체명"])

                    # 데이터 합치기 (중복 방지 로직 포함 - 동일 날짜/제목/매체는 제외)
                    updated_df = pd.concat([existing_df, new_entries]).drop_duplicates().reset_index(drop=True)
                    
                    # 시트 업데이트
                    conn.update(worksheet=SHEET_NAME, data=updated_df)
                    st.success(f"✅ {len(found_media)}개 매체의 게재 내역이 안전하게 기록되었습니다!")

        except Exception as e:
            st.error(f"오류 발생: {e}")

st.divider()

# 4. 실시간 성적표(Dashboard) 영역
st.subheader("📈 2026년 매체별 게재 성적표 (실시간)")

try:
    # 전체 데이터 다시 읽기
    df = conn.read(worksheet=SHEET_NAME).fillna("")
    
    if not df.empty:
        # 분석 1: 총 배포 건수 (고유한 제목의 개수)
        total_pr_count = df["보도자료 제목"].nunique()
        
        # 분석 2: 매체별 게재 횟수 계산
        scorecard = df.groupby("매체명").size().reset_index(name="게재 횟수")
        scorecard["게재율 (%)"] = scorecard["게재 횟수"].apply(lambda x: f"{(x / total_pr_count * 100):.1f}%")
        scorecard = scorecard.sort_values(by="게재 횟수", ascending=False).reset_index(drop=True)

        # 화면 표시
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric("올해 총 배포 건수", f"{total_pr_count}건")
        with c2:
            st.dataframe(scorecard, use_container_width=True)
            
        st.caption("※ 게재율 = (해당 매체 게재 횟수 / 전체 보도자료 배포 건수) * 100")
    else:
        st.info("기록된 데이터가 없습니다. 보도자료 정보를 입력해 주세요.")
except:
    st.info("시트를 읽어오는 중입니다...")
