import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 페이지 설정
st.set_page_config(page_title="홍보팀 기사 매칭 분석 툴", layout="wide")

st.title("📰 보도자료 커버리지 자동 분석기")
st.write("모니터링 메일의 소스 코드를 그대로 붙여넣으시면 언론사별 매칭율을 계산합니다.")

# 좌우 화면 분할
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 원본 보도자료")
    origin_text = st.text_area("배포한 보도자료 본문을 넣어주세요.", height=400)
    threshold = st.slider("매칭 인정 기준 (%)", 0, 100, 60)

with col2:
    st.subheader("2. 모니터링 HTML 소스")
    raw_html = st.text_area("메일 소스(HTML)를 통째로 붙여넣으세요.", height=400, placeholder="<tr>...<a href=...>...</tr>...")

if st.button("🚀 분석 시작"):
    if not origin_text:
        st.warning("보도자료 원본을 입력해주세요.")
    elif not raw_html:
        st.warning("분석할 소스 코드를 입력해주세요.")
    else:
        # HTML 파싱 시작
        soup = BeautifulSoup(raw_html, 'html.parser')
        rows = soup.find_all('td', style=lambda x: x and 'padding-left:20px' in x)
        
        # 기사 정보 추출
        extracted_data = []
        for row in rows:
            link_tag = row.find('a', href=True)
            if link_tag:
                url = link_tag['href']
                title = link_tag.get_text(strip=True)
                
                # 매체명 추출 (괄호 안의 텍스트 찾기: 예 - 가스신문)
                media_info = row.find('span')
                media_name = "알 수 없음"
                if media_info:
                    media_text = media_info.get_text(strip=True)
                    match = re.search(r'\((.*?) \d{4}', media_text) # (매체명 날짜) 형식 추출
                    if match:
                        media_name = match.group(1)
                    else:
                        media_name = media_text.replace('(','').split(' ')[0]

                extracted_data.append({
                    "media": media_name,
                    "title": title,
                    "url": url
                })

        if not extracted_data:
            st.error("입력한 소스에서 기사 정보를 찾을 수 없습니다. 형식을 확인해주세요.")
        else:
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, data in enumerate(extracted_data):
                status_text.text(f"분석 중 ({i+1}/{len(extracted_data)}): {data['media']} - {data['title'][:20]}...")
                
                try:
                    # 1. 기사 본문 수집
                    res = requests.get(data['url'], headers={'User-Agent':'Mozilla/5.0'}, timeout=5)
                    res.encoding = res.apparent_encoding # 한글 깨짐 방지
                    article_soup = BeautifulSoup(res.text, 'html.parser')
                    
                    # 뉴스 본문이 주로 위치하는 태그들 추출
                    content_tag = article_soup.find('article') or article_soup.find('div', id='dic_area') or article_soup.find('div', id='articleBody') or article_soup.body
                    content_text = content_tag.get_text(strip=True) if content_tag else ""
                    
                    # 2. 유사도 계산
                    if len(content_text) > 50: # 본문이 너무 짧으면 제외
                        docs = [origin_text, content_text]
                        vec = TfidfVectorizer().fit_transform(docs)
                        sim = cosine_similarity(vec[0:1], vec[1:]).flatten()[0]
                        score = round(sim * 100, 1)
                        result_status = "✅ 매칭" if score >= threshold else "❓ 일반"
                    else:
                        score = 0
                        result_status = "⚠️ 본문부족"
                except:
                    score = 0
                    result_status = "❌ 오류"
                
                results.append({
                    "매체명": data['media'],
                    "기사 제목": data['title'],
                    "일치율(%)": score,
                    "판별": result_status,
                    "링크": data['url']
                })
                progress_bar.progress((i + 1) / len(extracted_data))
            
            status_text.text("✅ 분석 완료!")
            
            # 결과 테이블
            df = pd.DataFrame(results)
            st.subheader("📊 분석 결과 요약")
            st.dataframe(df, use_container_width=True)
            
            # 엑셀 다운로드
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("결과 엑셀로 저장", csv, "pr_report.csv", "text/csv")
