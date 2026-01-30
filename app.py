import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# ... (상단 설정 동일)

if st.button("🚀 현황판 업데이트"):
    if not doc_title or not raw_html:
        st.warning("제목과 HTML 소스를 입력해주세요.")
    else:
        try:
            # 1. 시트 읽기
            df = conn.read(worksheet=SHEET_NAME, header=None).fillna("")
            
            # 2. HTML 분석 (주신 소스 전용 로직)
            soup = BeautifulSoup(raw_html, 'html.parser')
            media_map = {} # { "매체명": "URL" }
            
            # 모든 <a> 태그를 찾아서 분석
            for a_tag in soup.find_all('a', href=True):
                url = a_tag['href']
                # <a> 태그 바로 뒤에 있는 <span> 태그에서 매체명 추출
                span = a_tag.find_next_sibling('span')
                if span:
                    span_text = span.get_text()
                    # (매체명 2026/01/23) 패턴에서 매체명만 추출
                    m = re.search(r'\((.*?) \d{4}', span_text)
                    if m:
                        media_name = m.group(1).strip()
                        media_map[media_name] = url

            if not media_map:
                st.warning("매체명과 URL을 추출하지 못했습니다. HTML 형식을 확인해주세요.")
                st.stop()

            # 3. 새로운 열 데이터 생성
            new_col = [""] * len(df)
            if len(new_col) > 2:
                new_col[1] = doc_date.strftime('%m/%d')
                new_col[2] = doc_title

            # 4. 시트의 B열(매체명)과 매칭
            match_count = 0
            for i in range(len(df)):
                if i < 3 or df.shape[1] < 2: continue
                
                # 시트 상의 매체명 (예: 조선일보)
                sheet_media_name = str(df.iloc[i, 1]).strip()
                # 괄호 등 제거하고 순수 이름만 추출
                pure_name = re.sub(r'\(.*?\)', '', sheet_media_name).strip()
                
                # 추출된 media_map에서 유사한 이름 찾기
                found_url = None
                for m_name, url in media_map.items():
                    if pure_name in m_name or m_name in pure_name:
                        found_url = url
                        break
                
                if found_url:
                    # 시트에 하이퍼링크로 입력
                    new_col[i] = f'=HYPERLINK("{found_url}", "보기(✅)")'
                    match_count += 1
                else:
                    new_col[i] = "-"

            # 5. 열 추가 및 업데이트
            # 컬럼명 중복 방지를 위해 날짜_시간 활용
            col_id = datetime.now().strftime('%m%d_%H%M%S')
            df[f"결과_{col_id}"] = new_col
            
            conn.update(worksheet=SHEET_NAME, data=df)
            
            st.success(f"✅ 업데이트 성공! (매칭된 기사: {match_count}건)")
            st.info(f"추출된 매체: {', '.join(media_map.keys())}")
            st.balloons()
            
        except Exception as e:
            st.error(f"오류 발생: {e}")
