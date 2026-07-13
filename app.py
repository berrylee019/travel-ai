import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium

# 세션 상태 초기화
if 'valid_coords' not in st.session_state:
    st.session_state.valid_coords = None

@st.cache_resource
def get_gmaps_client():
    return googlemaps.Client(key=st.secrets["google_maps_api_key"])

gmaps = get_gmaps_client()

st.title("✈️ 여행 비서 AI: 제로 클릭 일정 생성")

with st.form("travel_form"):
    destination = st.text_input("여행지")
    days = st.number_input("여행 기간 (일)", 1, 10, 3)
    interests = st.multiselect("관심사", ["맛집", "자연", "역사", "쇼핑", "예술"])
    submit_button = st.form_submit_button("일정 생성 시작!")

# 1. 버튼이 눌리면 검색 수행
if submit_button:
    # 이름에 숫자가 3개 이상 들어가거나(코드성), 특정 키워드가 포함되면 제외
    if any(char.isdigit() for char in clean_name) and len(clean_name) < 10:
    
    if not destination:
        st.error("여행지를 입력해주세요!")
    else:
        with st.spinner('일정을 계산 중입니다...'):
            # (A) 여행지의 중심 좌표 찾기
            try:
                geo_result = gmaps.geocode(destination)
                if not geo_result:
                    st.error("해당 여행지를 찾을 수 없습니다.")
                    st.stop()
                dest_loc = geo_result[0]['geometry']['location']
                dest_lat, dest_lng = dest_loc['lat'], dest_loc['lng']
            except:
                st.error("위치 검색 오류")
                st.stop()

            # (B) 지역 편향(Location Bias)을 적용한 장소 검색
            places_found = []
            for interest in interests:
                results = gmaps.places(
                    query=f"{interest} in {destination}",
                    location=(dest_lat, dest_lng),
                    radius=50000 # 50km 이내로 제한
                )
                for place in results.get('results', [])[:2]:
                    places_found.append({"name": place['name']})
            
            # (C) 좌표 수집 및 지도 생성
            valid_coords = []
            
            # 여기서부터 for 루프가 시작되어야 합니다.
            for p in places_found:
                try:
                    p_data = gmaps.find_place(
                        p['name'], 
                        'textquery', 
                        fields=['name', 'geometry', 'formatted_address']
                    )
                    
                    if p_data.get('candidates'):
                        cand = p_data['candidates'][0]
                        loc = cand['geometry']['location']
                        
                        # 장소 이름이 너무 짧거나(이상한 코드 방지) 체크
                        clean_name = cand['name']
                        
                        valid_coords.append({
                            '장소': clean_name, 
                            'lat': loc['lat'], 
                            'lng': loc['lng']
                        })
                except Exception:
                    continue  # 이 continue는 반드시 for 루프 안쪽에 있어야 합니다.
            
            # for 루프가 끝난 뒤 아래 로직 실행
            if valid_coords:
                m = folium.Map(location=[dest_lat, dest_lng], zoom_start=11)
                route_coords = []
                for item in valid_coords:
                    folium.Marker([item['lat'], item['lng']], popup=item['장소']).add_to(m)
                    route_coords.append([item['lat'], item['lng']])
                
                folium.PolyLine(route_coords, color="blue", weight=2.5).add_to(m)
                
                st.session_state.valid_coords = valid_coords
                st.session_state.map_data = m
            else:
                st.error("해당 지역 주변에서 장소를 찾을 수 없습니다.")
                st.session_state.valid_coords = None

# 2. 결과 출력부
if st.session_state.valid_coords and 'map_data' in st.session_state:
    st.subheader(f"📍 {destination} 추천 경로")
    st_folium(st.session_state.map_data, width=700, height=500)
    st.table(st.session_state.valid_coords)
