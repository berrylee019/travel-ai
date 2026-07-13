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
        continue
    
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
            for p in places_found:
                try:
                    # 장소의 상세 정보를 가져올 때 'name'과 'formatted_address'를 모두 요청
                    p_data = gmaps.find_place(
                        p['name'], 
                        'textquery', 
                        fields=['name', 'geometry', 'formatted_address']
                    )
                    
                    if p_data.get('candidates'):
                        cand = p_data['candidates'][0]
                        loc = cand['geometry']['location']
                        
                        # 텍스트 정리: 영어 이름과 한글 이름이 섞인 경우 처리
                        # 구글은 보통 '이름(주소)' 형태로 줄 때가 많습니다.
                        clean_name = cand['name']
                        # 필요 시 여기서 추가적인 정제 로직(한글/영어 분리)을 넣을 수 있습니다.
                        
                        valid_coords.append({
                            '장소': clean_name,  # 'name'에서 '장소'로 변경
                            'lat': loc['lat'], 
                            'lng': loc['lng']
                        })
                except:
                    continue
            
            if valid_coords:
                # [지도 생성 로직은 동일합니다]
                m = folium.Map(location=[dest_lat, dest_lng], zoom_start=11)
                route_coords = []
                for item in valid_coords:
                    # 팝업에 '장소' 이름을 표시
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
