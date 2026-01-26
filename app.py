import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re

# 페이지 설정
st.set_page_config(page_title="매체별 보도자료 게재 체크", layout="wide")

st.title("📊 매체별 보도자료 게재 자동 체크 시스템")
st.write("우리 매체 리스트와 모니터링 HTML 소스를 비교하여 게재 여부를 확인합니다.")

# 좌우 화면 분할
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 우리 매체 리스트")
    # 팀원들이 평소 관리하는 매체명을 한 줄에 하나씩 입력
    media_input = st.text_area("체크할 매체명들을 입력하세요. (한 줄에 하나씩)", 
                              height=400,
                              value="가스신문\n시사캐스트\n이투뉴스\n조선일보\n매일경제")
    target_media_list = [m.strip() for m in media_input.split('\n') if m.strip()]

with col2:
    st.subheader("2. 모니터링 HTML 소스")
    raw_html = st.text_area("모니터링 메일의 HTML 소스를 붙여넣으세요.", height=400)

if st.button("🔍 게재 여부 자동 체크 시작"):
    if not target_media_list:
        st.warning("왼쪽에 매체 리스트를 입력해주세요.")
    elif not raw_html:
        st.warning("오른쪽에 분석할 HTML 소스를 입력해주세요.")
    else:
        # 1. HTML 소스에서 기사 정보 추출
        soup = BeautifulSoup(raw_html, 'html.parser')
        # <td style="...padding-left:20px;"> 태그 안에 기사 정보가 있는 구조를 활용
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        
        found_articles = {} # {매체명: 기사제목}
        
        for row in rows:
            link_tag = row.find('a', href=True)
            media_info = row.find('span')
            
            if link_tag and media_info:
                title = link_tag.get_text(strip=True)
                media_text = media_info.get_text(strip=True)
                # 괄호 안의 매체명 추출
                match = re.search(r'\((.*?) \d{4}', media_text)
                if match:
                    extracted_media = match.group(1).strip()
                    found_articles[extracted_media] = title

        # 2. 우리 매체 리스트와 비교하여 결과 테이블 생성
        check_results = []
        for media in target_media_list:
            if media in found_articles:
                check_results.append({
                    "매체명": media,
                    "게재 여부": "✅ 게재 완료",
                    "기사 제목": found_articles[media]
                })
            else:
                check_results.append({
                    "매체명": media,
                    "게재 여부": "❌ 미게재",
                    "기사 제목": "-"
                })

        # 3. 결과 출력
        st.subheader("📝 최종 게재 현황 리포트")
        df_final = pd.DataFrame(check_results)
        
        # 표 형식으로 보여주기
        st.dataframe(df_final, use_container_width=True, hide_index=True)
        
        # 통계 요약
        total = len(target_media_list)
        success = sum(1 for r in check_results if r["게재 여부"] == "✅ 게재 완료")
        st.info(f"총 {total}개 매체 중 {success}개 매체 게재 확인 (게재율: {round(success/total*100, 1)}%)")

        # 엑셀 다운로드 버튼
        csv = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("결과 리포트 저장 (Excel/CSV)", csv, "coverage_check.csv", "text/csv")
