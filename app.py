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
            # 1. 장소 검색
            places_found = []
            for interest in interests:
                query = f"{interest} in {destination}"
                results = gmaps.places(query=query)
                for place in results.get('results', [])[:2]:
                    places_found.append({"name": place['name']})
            
            # 2. 좌표 수집 (에러 방지 추가)
            valid_coords = []
            for p in places_found:
                try:
                    p_data = gmaps.find_place(p['name'], 'textquery', fields=['geometry'])
                    if p_data.get('candidates'):
                        loc = p_data['candidates'][0]['geometry']['location']
                        valid_coords.append({'name': p['name'], 'lat': loc['lat'], 'lng': loc['lng']})
                except Exception as e:
                    continue # 정보 못 찾으면 다음 장소로
            
            # 3. 지도 및 시각화
            if valid_coords:
                # 지도 중심점: 첫 번째 장소의 좌표
                m = folium.Map(location=[valid_coords[0]['lat'], valid_coords[0]['lng']], zoom_start=13)
                
                route_coords = []
                for item in valid_coords:
                    folium.Marker([item['lat'], item['lng']], popup=item['name']).add_to(m)
                    route_coords.append([item['lat'], item['lng']])
                
                folium.PolyLine(route_coords, color="blue", weight=2.5).add_to(m)
                st_folium(m, width=700, height=500)
            else:
                st.error("좌표를 찾을 수 없습니다. 검색어를 바꿔보세요.")
