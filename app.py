import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 페이지 설정
st.set_page_config(page_title="홍보팀 기사 매칭 툴", layout="wide")

st.title("📂 보도자료 커버리지 자동 체크")
st.write("모니터링 업체에서 온 기사 리스트를 드래그해서 그대로 붙여넣으세요!")

# 좌우 화면 분할
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 배포한 보도자료")
    origin_text = st.text_area("보도자료 본문을 넣어주세요.", height=400)
    threshold = st.slider("유사도 기준 (%)", 0, 100, 60, help="보통 60% 이상이면 보도자료 기반 기사입니다.")

with col2:
    st.subheader("2. 모니터링 기사 리스트")
    raw_input = st.text_area("기사 제목과 URL이 섞인 텍스트를 통째로 붙여넣으세요.", height=400)

if st.button("✨ 분석 시작 (기사 읽어오기)"):
    # 텍스트에서 URL만 뽑아내기
    urls = re.findall(r'(https?://[^\s\n]+)', raw_input)
    
    if not origin_text:
        st.warning("원본 보도자료를 먼저 입력해주세요.")
    elif not urls:
        st.warning("분석할 기사 URL을 찾지 못했습니다.")
    else:
        results = []
        bar = st.progress(0)
        
        for idx, url in enumerate(urls):
            try:
                # 기사 본문 가져오기 (간단 버전)
                res = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                # 보통 언론사 본문은 article이나 특정 id 안에 있습니다.
                content = soup.find('article') or soup.find('div', id='dic_area') or soup.body
                text = content.get_text(strip=True) if content else ""
                
                if text:
                    # 유사도 계산
                    docs = [origin_text, text]
                    vec = TfidfVectorizer().fit_transform(docs)
                    sim = cosine_similarity(vec[0:1], vec[1:]).flatten()[0]
                    score = round(sim * 100, 1)
                    
                    results.append({
                        "기사 URL": url,
                        "일치율(%)": score,
                        "판별": "✅ 매칭" if score >= threshold else "❓ 일반/타사"
                    })
                else:
                    results.append({"기사 URL": url, "일치율(%)": 0, "판별": "접속 불가"})
            except:
                results.append({"기사 URL": url, "일치율(%)": 0, "판입": "오류"})
            
            bar.progress((idx + 1) / len(urls))

        # 결과 보여주기
        df = pd.DataFrame(results)
        st.subheader("📝 분석 리포트")
        st.dataframe(df, use_container_width=True)
        
        # 엑셀 다운로드
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("결과를 엑셀로 저장하기", csv, "report.csv", "text/csv")
