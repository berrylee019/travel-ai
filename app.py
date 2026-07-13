import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium
import numpy as np

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

            # (B) 지역 편향 검색
            places_found = []
            for interest in interests:
                results = gmaps.places(
                    query=f"{interest} in {destination}",
                    location=(dest_lat, dest_lng),
                    radius=50000
                )
                for place in results.get('results', [])[:2]:
                    places_found.append({"name": place['name']})
            
            # (C) 좌표 수집 및 '이름 필터링' 적용
            valid_coords = []
            for p in places_found:
                try:
                    p_data = gmaps.find_place(p['name'], 'textquery', fields=['name', 'geometry'])
                    if p_data.get('candidates'):
                        cand = p_data['candidates'][0]
                        clean_name = cand['name']
                        
                        # [필터링 로직 위치] 이름에 숫자가 3개 이상 들어간 코드성 이름이면 패스
                        if any(char.isdigit() for char in clean_name) and len(clean_name) < 10:
                            continue
                        
                        loc = cand['geometry']['location']
                        valid_coords.append({'장소': clean_name, 'lat': loc['lat'], 'lng': loc['lng']})
                except:
                    continue
            
            # (D) 지도 시각화
            if valid_coords:
                m = folium.Map(location=[dest_lat, dest_lng], zoom_start=11)
                for item in valid_coords:
                    folium.Marker([item['lat'], item['lng']], popup=item['장소']).add_to(m)
                
                # 경로 표시 (좌표 리스트 추출)
                route_coords = [[item['lat'], item['lng']] for item in valid_coords]
                folium.PolyLine(route_coords, color="blue", weight=2.5).add_to(m)
                
                st.session_state.valid_coords = valid_coords
                st.session_state.map_data = m
                st.session_state.days = days
            else:
                st.error("해당 지역 주변에서 장소를 찾을 수 없습니다.")
                st.session_state.valid_coords = None

# 2. 결과 출력부
if st.session_state.valid_coords and 'map_data' in st.session_state:
    st.subheader(f"📍 {destination} 추천 경로 및 일정")
    st_folium(st.session_state.map_data, width=700, height=500)
    
    # 장소를 일자별로 나누기 (Numpy 사용)
    data = st.session_state.valid_coords
    days = st.session_state.get('days', 1) # 폼에서 입력받은 days
    
    # 장소들을 days 수만큼 나눔
    daily_groups = np.array_split(data, num_days)
    
    # 탭으로 일자별 구성
    tabs = st.tabs([f"{i+1}일차" for i in range(num_days)])
    
    for i, tab in enumerate(tabs):
        with tab:
            if i < len(daily_groups) and len(daily_groups[i]) > 0:
                for item in daily_group[i]:
                    st.write(f"✅ {item['장소']}")
            else:
                st.write("해당 날짜에 추천할 장소가 없습니다.")
