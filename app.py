import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium

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

    if places_found:
            # 중심점 계산을 위한 첫 장소의 좌표 가져오기 (상세 검색)
            first_place = gmaps.find_place(places_found[0]['name'], 'textquery', fields=['geometry'])
            location = first_place['candidates'][0]['geometry']['location']
            
            # 지도 생성
            m = folium.Map(location=[location['lat'], location['lng']], zoom_start=13)
            
            # 장소별 마커 및 경로 데이터 수집
            route_coords = []
            for p in places_found:
                # 장소 좌표 검색
                p_data = gmaps.find_place(p['name'], 'textquery', fields=['geometry'])
                lat = p_data['candidates'][0]['geometry']['location']['lat']
                lng = p_data['candidates'][0]['geometry']['location']['lng']
                route_coords.append([lat, lng])
                
                # 지도에 마커 표시
                folium.Marker([lat, lng], popup=p['name'], tooltip=p['name']).add_to(m)
            
            # 동선(경로) 선 그리기
            folium.PolyLine(route_coords, color="blue", weight=2.5, opacity=1).add_to(m)
            
            # Streamlit에 지도 렌더링
            st.subheader("📍 여행 동선 지도")
            st_folium(m, width=700, height=500)
        else:
            st.warning("추천할 장소를 찾지 못했습니다.")
