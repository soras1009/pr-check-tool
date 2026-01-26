import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 홍보팀 통합 대시보드", layout="wide")

# 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏢 삼천리 홍보팀 게재 현황 누적 대시보드")

tab1, tab2 = st.tabs(["📥 데이터 분석 및 저장", "📊 누적 결과 대시보드"])

with tab1:
    st.subheader("새 보도자료 분석")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        doc_title = st.text_input("보도자료 제목", placeholder="예: 삼천리 이태호 사장 취임")
        media_input = st.text_area("체크할 매체 리스트", height=200, value="가스신문\n조선일보\n매일경제")
        target_media_list = [m.strip() for m in media_input.split('\n') if m.strip()]

    with col2:
        raw_html = st.text_area("모니터링 메일 HTML 소스", height=250)
        
    if st.button("🚀 분석 및 데이터베이스 저장"):
        if not doc_title or not raw_html:
            st.warning("제목과 소스 코드를 모두 입력해주세요.")
        else:
            # HTML 파싱
            soup = BeautifulSoup(raw_html, 'html.parser')
            rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
            
            found_articles = {}
            for row in rows:
                link_tag = row.find('a', href=True)
                media_info = row.find('span')
                if link_tag and media_info:
                    title = link_tag.get_text(strip=True)
                    media_text = media_info.get_text(strip=True)
                    match = re.search(r'\((.*?) \d{4}', media_text)
                    if match:
                        extracted_media = match.group(1).strip()
                        found_articles[extracted_media] = title

            # 새로운 데이터 생성
            new_data_list = []
            today = datetime.now().strftime("%Y-%m-%d")
            for media in target_media_list:
                status = "✅ 게재" if media in found_articles else "❌ 미게재"
                article_title = found_articles.get(media, "-")
                new_data_list.append([today, doc_title, media, status, article_title])
            
            # 구글 시트에 기존 데이터 불러오기 및 추가
            existing_data = conn.read(worksheet="Sheet1")
            new_df = pd.DataFrame(new_data_list, columns=["날짜", "보도자료제목", "매체명", "게재여부", "기사제목"])
            updated_df = pd.concat([existing_data, new_df], ignore_index=True)
            
            # 시트에 다시 쓰기 (누적 저장)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success(f"'{doc_title}' 분석 결과가 구글 시트에 누적 저장되었습니다!")

with tab2:
    st.subheader("📈 전사 보도자료 게재 기록")
    
    # 구글 시트에서 최신 데이터 읽기
    try:
        df_logs = conn.read(worksheet="Sheet1")
        
        if not df_logs.empty:
            # 필터 기능: 특정 보도자료만 골라보기
            all_titles = ["전체 보기"] + list(df_logs["보도자료제목"].unique())
            selected_title = st.selectbox("보도자료별 필터", all_titles)
            
            if selected_title != "전체 보기":
                display_df = df_logs[df_logs["보도자료제목"] == selected_title]
            else:
                display_df = df_logs
            
            # 대시보드 상단 요약
            total_count = len(display_df)
            success_count = len(display_df[display_df["게재여부"] == "✅ 게재"])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("총 전송 건수", f"{total_count}건")
            c2.metric("총 게재 건수", f"{success_count}건")
            c3.metric("평균 게재율", f"{round(success_count/total_count*100, 1)}%" if total_count > 0 else "0%")
            
            st.divider()
            st.table(display_df.sort_values(by="날짜", ascending=False))
        else:
            st.info("시트에 저장된 데이터가 없습니다.")
    except:
        st.error("구글 시트 연결을 확인해주세요. (Secrets 설정 필요)")
