import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="삼천리 보도자료 게재 현황", layout="wide")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "2026년"

st.title("📰 보도자료 게재 현황 추적 시스템")

# 사이드바: 데이터 입력
with st.sidebar:
    st.header("📝 새 보도자료 등록")
    
    # 날짜 입력
    doc_date = st.date_input("배포 날짜", datetime.now())
    date_str = doc_date.strftime("%m/%d")  # 예: "01/23"
    
    # 제목 입력
    doc_title = st.text_input("보도자료 제목", placeholder="예: 이태호 사장 서울부동산포럼 회장 취임")
    
    # HTML 입력
    raw_html = st.text_area("HTML 소스 붙여넣기", height=300, 
                            placeholder="모니스에서 받은 HTML 전체를 붙여넣으세요")
    
    # 제출 버튼
    submit = st.button("🚀 등록하기", type="primary")

# 데이터 처리
if submit:
    if not doc_title or not raw_html:
        st.error("⚠️ 제목과 HTML 소스를 모두 입력해주세요.")
    else:
        try:
            with st.spinner("HTML 분석 중..."):
                # HTML 파싱
                soup = BeautifulSoup(raw_html, 'html.parser')
                found_media = set()
                
                # 패턴: (매체명 YYYY/MM/DD)
                for tag in soup.find_all(['span', 'td']):
                    text = tag.get_text()
                    # 예: (가스신문 2026/01/23)
                    matches = re.findall(r'\(([^)]+)\s+\d{4}/\d{2}/\d{2}\)', text)
                    for match in matches:
                        media_name = match.strip()
                        if media_name:
                            found_media.add(media_name)
                
                if not found_media:
                    st.warning("⚠️ HTML에서 매체 정보를 찾지 못했습니다. HTML 형식을 확인해주세요.")
                else:
                    st.success(f"✅ {len(found_media)}개 매체 발견!")
                    
                    # 기존 시트 데이터 읽기
                    try:
                        df = conn.read(worksheet=SHEET_NAME)
                        if df.empty or len(df.columns) < 2:
                            # 빈 시트인 경우 초기 구조 생성
                            df = pd.DataFrame(columns=["구분", "매체명"])
                    except Exception as e:
                        st.warning(f"시트를 처음 만듭니다: {e}")
                        df = pd.DataFrame(columns=["구분", "매체명"])
                    
                    # 날짜 컬럼이 없으면 추가
                    if date_str not in df.columns:
                        df[date_str] = ""
                    
                    # 각 매체에 대해 O 표시
                    for media in found_media:
                        # 매체가 시트에 없으면 추가
                        if media not in df["매체명"].values:
                            new_row = pd.DataFrame([{"구분": "", "매체명": media}])
                            df = pd.concat([df, new_row], ignore_index=True)
                        
                        # 해당 매체의 날짜 컬럼에 O 표시
                        mask = df["매체명"] == media
                        df.loc[mask, date_str] = "O"
                    
                    # 제목 행 추가/업데이트 (첫 번째 행)
                    # 첫 행에 제목 정보 저장
                    if len(df) > 0:
                        # 제목 행이 있는지 확인
                        title_row_exists = False
                        if df.iloc[0]["구분"] == "제목":
                            df.loc[0, date_str] = doc_title
                            title_row_exists = True
                        
                        if not title_row_exists:
                            # 제목 행 추가
                            title_row = pd.DataFrame([{"구분": "제목", "매체명": ""}])
                            for col in df.columns:
                                if col not in ["구분", "매체명"]:
                                    title_row[col] = ""
                            title_row[date_str] = doc_title
                            df = pd.concat([title_row, df], ignore_index=True)
                    
                    # 구글 시트에 업데이트
                    conn.update(worksheet=SHEET_NAME, data=df)
                    
                    st.success(f"✅ 등록 완료! {len(found_media)}개 매체가 {date_str} 컬럼에 표시되었습니다.")
                    st.balloons()
                    
                    # 발견된 매체 목록 표시
                    with st.expander("📋 등록된 매체 목록"):
                        for media in sorted(found_media):
                            st.write(f"- {media}")
                    
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {e}")
            import traceback
            st.code(traceback.format_exc())

# 메인 화면: 현황 표시
st.divider()
st.subheader("📊 2026년 보도자료 게재 현황")

try:
    # 구글 시트에서 데이터 읽기
    df = conn.read(worksheet=SHEET_NAME)
    
    if not df.empty and len(df.columns) >= 2:
        # 데이터 표시
        st.dataframe(
            df,
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        # 통계 정보
        date_columns = [col for col in df.columns if col not in ["구분", "매체명"]]
        if date_columns:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("총 보도자료 수", len(date_columns))
            
            with col2:
                total_media = len(df[df["매체명"].notna() & (df["매체명"] != "")])
                st.metric("등록된 매체 수", total_media)
            
            with col3:
                # 총 게재 건수 (O의 개수)
                total_coverage = 0
                for col in date_columns:
                    if col in df.columns:
                        total_coverage += (df[col] == "O").sum()
                st.metric("총 게재 건수", total_coverage)
        
        # 매체별 게재율
        st.divider()
        st.subheader("📈 매체별 게재 성과")
        
        if date_columns:
            # 매체별 게재 횟수 계산
            media_stats = []
            for idx, row in df.iterrows():
                if row["매체명"] and row["구분"] != "제목":
                    media_name = row["매체명"]
                    coverage_count = sum([1 for col in date_columns if col in row and row[col] == "O"])
                    coverage_rate = (coverage_count / len(date_columns) * 100) if len(date_columns) > 0 else 0
                    media_stats.append({
                        "매체명": media_name,
                        "게재 건수": coverage_count,
                        "게재율": f"{coverage_rate:.1f}%"
                    })
            
            if media_stats:
                stats_df = pd.DataFrame(media_stats)
                stats_df = stats_df.sort_values("게재 건수", ascending=False).reset_index(drop=True)
                
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.dataframe(stats_df, hide_index=True, height=400)
                
                with col2:
                    # 상위 10개 매체 차트
                    if len(stats_df) > 0:
                        import plotly.express as px
                        top_10 = stats_df.head(10)
                        fig = px.bar(
                            top_10,
                            x="게재 건수",
                            y="매체명",
                            orientation='h',
                            title="상위 10개 매체 게재 현황",
                            color="게재 건수",
                            color_continuous_scale="Blues"
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📝 아직 등록된 데이터가 없습니다. 왼쪽 사이드바에서 첫 보도자료를 등록해보세요!")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("구글 시트 권한을 확인해주세요.")

# 사용 안내
with st.expander("ℹ️ 사용 방법"):
    st.markdown("""
    ### 📖 사용 가이드
    
    1. **구글 시트 권한 설정** (최초 1회)
       - 시트에 `pr-sheet-access@pr-dashboard-485514.iam.gserviceaccount.com` 이메일 추가
       - 권한: 편집자
    
    2. **보도자료 등록**
       - 왼쪽 사이드바에서 날짜, 제목 입력
       - 모니스에서 받은 HTML 전체를 복사하여 붙여넣기
       - "등록하기" 버튼 클릭
    
    3. **현황 확인**
       - 메인 화면에서 매체별 게재 현황 확인
       - 날짜별로 O 표시된 매체 확인
       - 매체별 게재율 통계 확인
    
    ### 💡 팁
    - HTML은 전체를 복사해서 붙여넣으세요
    - 매체명은 자동으로 추출됩니다
    - 날짜 컬럼은 자동으로 추가됩니다
    """)
