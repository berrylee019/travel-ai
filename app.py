import streamlit as st
import pandas as pd
import requests

# 1. API 설정 (SerpApi에서 발급받은 키를 입력하세요)
SERP_API_KEY = "YOUR_SERP_API_KEY"

def fetch_flights(departure_id, arrival_id, outbound_date):
    """Google Flights 데이터를 SerpApi를 통해 가져옵니다."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": departure_id, # 예: ICN
        "arrival_id": arrival_id,     # 예: KIX (오사카)
        "outbound_date": outbound_date,
        "currency": "KRW",
        "hl": "ko",
        "api_key": SERP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        st.error(f"데이터를 가져오는데 실패했습니다: {e}")
        return None

# --- UI 부분 ---
st.title("🛫 제로 클릭 여행 비서: 실시간 항공권")

# 사이드바에서 사용자 취향(기사 내용 반영) 설정 가능
with st.sidebar:
    st.header("👤 내 여행 프로필")
    st.info("형님은 현재 '국적기'와 '창가 좌석'을 선호하도록 설정되어 있습니다.")

# 입력 폼
col1, col2, col3 = st.columns(3)
with col1:
    dep = st.text_input("출발지 (공항코드)", value="ICN")
with col2:
    arr = st.text_input("도착지 (공항코드)", value="KIX")
with col3:
    date = st.date_input("출발 일자")

if st.button("최적의 항공권 찾기"):
    with st.spinner("AI가 실시간 최저가와 동선을 분석 중입니다..."):
        data = fetch_flights(dep, arr, str(date))
        
        if data and "best_flights" in data:
            st.subheader(f"✨ 형님을 위한 추천 항공편")
            
            # 검색 결과 중 '가장 좋은 항공편' 위주로 노출
            for flight in data["best_flights"][:3]: # 상위 3개만
                with st.container(border=True):
                    airline = flight["flights"][0]["airline"]
                    price = flight["price"]
                    duration = flight["total_duration"]
                    
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**{airline}** | ⏱️ {duration}분 소요")
                    c2.markdown(f"**{price:,}원**")
                    
                    # 기사에서 언급된 '예약 직행' 버튼
                    # 실제 서비스에선 구글 플라이츠 상세 페이지나 예약 대행사 링크 연결
                    with c3:
                        st.link_button("예약하기", "https://www.google.com/travel/flights")
        else:
            st.warning("일치하는 항공권 정보가 없습니다. API 키를 확인해 보세요.")
