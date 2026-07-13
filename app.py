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

# 버튼이 눌리면 검색을 수행하고 결과를 세션에 저장
if submit_button:
    if not destination:
        st.error("여행지를 입력해주세요!")
    else:
        with st.spinner('일정을 계산 중입니다...'):
            places_found = []
            for interest in interests:
                results = gmaps.places(query=f"{interest} in {destination}")
                for place in results.get('results', [])[:2]:
                    places_found.append({"name": place['name']})
            
            valid_coords = []
            for p in places_found:
                try:
                    p_data = gmaps.find_place(p['name'], 'textquery', fields=['geometry'])
                    if p_data.get('candidates'):
                        loc = p_data['candidates'][0]['geometry']['location']
                        valid_coords.append({'name': p['name'], 'lat': loc['lat'], 'lng': loc['lng']})
                except:
                    continue
            
            # 검색 결과를 세션에 저장 (이 데이터가 유지됨)
            st.session_state.valid_coords = valid_coords

# 결과가 세션에 있으면 항상 화면에 출력
if st.session_state.valid_coords:
    st.subheader(f"📍 {destination} 추천 경로")
    
    data = st.session_state.valid_coords
    m = folium.Map(location=[data[0]['lat'], data[0]['lng']], zoom_start=13)
    
    route_coords = []
    for item in data:
        folium.Marker([item['lat'], item['lng']], popup=item['name']).add_to(m)
        route_coords.append([item['lat'], item['lng']])
    
    folium.PolyLine(route_coords, color="blue", weight=2.5).add_to(m)
    st_folium(m, width=700, height=500)
    
    # 리스트도 표시
    st.table(data)
