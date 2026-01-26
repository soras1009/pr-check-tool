import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 통합 대시보드", layout="wide")

# 구글 시트 연결 설정 (Secrets에 설정된 정보 활용)
conn = st.connection("gsheets", type=GSheetsConnection)

# 설정한 시트 이름 변수
SHEET_NAME = "2026년"

st.title("🏢 삼천리 홍보팀 게재 현황 누적 대시보드")

tab1, tab2 = st.tabs(["📥 데이터 분석 및 저장", "📊 누적 결과 대시보드"])

with tab1:
    st.subheader("새 보도자료 분석")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        doc_title = st.text_input("보도자료 제목", placeholder="예: 삼천리 이태호 사장 취임")
        media_input = st.text_area("체크할 매체 리스트 (한 줄에 하나씩)", height=200, value="가스신문\n조선일보\n매일경제\n에너지신문")
        target_media_list = [m.strip() for m in media_input.split('\n') if m.strip()]

    with col2:
        raw_html = st.text_area("모니터링 메일 HTML 소스 붙여넣기", height=250)
        
    if st.button("🚀 분석 및 구글 시트 저장"):
        if not doc_title or not raw_html:
            st.warning("제목과 HTML 소스 코드를 모두 입력해주세요.")
        else:
            # 1. HTML 소스 파싱 및 기사 추출
            soup = BeautifulSoup(raw_html, 'html.parser')
            rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
            
            found_articles = {}
            for row in rows:
                link_tag = row.find('a', href=True)
                media_info = row.find('span')
                if link_tag and media_info:
                    title = link_tag.get_text(strip=True)
                    media_text = media_info.get_text(strip=True)
                    # 매체명 추출 (괄호 안 텍스트)
                    match = re.search(r'\((.*?) \d{4}', media_text)
                    if match:
                        extracted_media = match.group(1).strip()
                        found_articles[extracted_media] = title

            # 2. 새로운 데이터 행(Row) 생성
            new_rows = []
            today = datetime.now().strftime("%Y-%m-%d")
            for media in target_media_list:
                status = "✅ 게재" if media in found_articles else "❌ 미게재"
                article_title = found_articles.get(media, "-")
                new_rows.append({
                    "날짜": today,
                    "보도자료제목": doc_title,
                    "매체명": media,
                    "게재여부": status,
                    "기사제목": article_title
                })
            
            new_df = pd.DataFrame(new_rows)

            # 3. 구글 시트 업데이트 (기존 데이터 유지하며 추가)
            try:
                # 기존 데이터 읽기
                existing_data = conn.read(worksheet=SHEET_NAME)
                # 데이터 합치기
                updated_df = pd.concat([existing_data, new_df], ignore_index=True)
                # 시트에 다시 쓰기
                conn.update(worksheet=SHEET_NAME, data=updated_df)
                st.success(f"✅ '{doc_title}' 관련 데이터 {len(new_rows)}건이 '{SHEET_NAME}' 시트에 저장되었습니다!")
            except Exception as e:
                st.error(f"시트 업데이트 중 오류가 발생했습니다: {e}")

with tab2:
    st.subheader(f"📈 {SHEET_NAME} 게재 기록 리포트")
    
    try:
        # 실시간으로 시트 데이터 읽어오기
        df_logs = conn.read(worksheet=SHEET_NAME)
        
        if not df_logs.empty:
            # 대시보드 요약 지표
            total_count = len(df_logs)
            success_count = len(df_logs[df_logs["게재여부"] == "✅ 게재"])
            
            m1, m2, m3 = st.columns(3)
            m1.metric("누적 데이터 수", f"{total_count}건")
            m2.metric("누적 게재 성공", f"{success_count}건")
            m3.metric("평균 게재율", f"{round(success_count/total_count*100, 1)}%" if total_count > 0 else "0%")
            
            st.divider()

            # 필터 선택 (보도자료 제목별)
            titles = ["전체 보기"] + sorted(list(df_logs["보도자료제목"].unique()), reverse=True)
            selected = st.selectbox("기록 필터 (보도자료별)", titles)
            
            if selected != "전체 보기":
                filtered_df = df_logs[df_logs["보도자료제목"] == selected]
            else:
                filtered_df = df_logs
            
            # 테이블 출력 (최신순 정렬)
            st.dataframe(filtered_df.sort_values(by="날짜", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("현재 시트에 저장된 데이터가 없습니다. 먼저 분석을 진행해 주세요.")
    except Exception as e:
        st.error(f"데이터를 불러올 수 없습니다. 시트의 탭 이름이 '{SHEET_NAME}' 인지 확인해 주세요. (에러: {e})")
