import streamlit as st
import googlemaps

# 1. API 키 설정 (Streamlit Secrets에서 가져오기)
# Streamlit Cloud 배포 시 Secrets 설정 필수: 
# [secrets.toml]
# google_maps_api_key = "AIza..."
@st.cache_resource
def get_gmaps_client():
    return googlemaps.Client(key=st.secrets["google_maps_api_key"])

gmaps = get_gmaps_client()

# 2. UI 구성
st.title("✈️ 여행 비서 AI: 제로 클릭 일정 생성")

with st.form("travel_form"):
    destination = st.text_input("여행지 (예: 서울, 도쿄)")
    days = st.number_input("여행 기간 (일)", min_value=1, max_value=10, value=3)
    interests = st.multiselect("관심사", ["맛집", "자연", "역사", "쇼핑", "예술"])
    submit_button = st.form_submit_button("일정 생성 시작!")

# 3. 데이터 연동 로직
if submit_button:
    if not destination:
        st.error("여행지를 입력해주세요!")
    else:
        st.write(f"🔍 {destination} 여행을 위한 {days}일치 일정을 계획 중입니다...")
        
        # Google Places API를 통한 장소 검색 (관심사 활용)
        places_found = []
        for interest in interests:
            query = f"{interest} in {destination}"
            results = gmaps.places(query=query)
            
            # 검색 결과에서 상위 2개만 추출
            for place in results.get('results', [])[:2]:
                places_found.append({
                    "name": place['name'],
                    "address": place['formatted_address'],
                    "rating": place.get('rating', 0)
                })
        
        st.subheader("추천 장소 목록")
        st.table(places_found)
        st.success("이제 이 장소들을 기반으로 동선을 최적화하겠습니다.")