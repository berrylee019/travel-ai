import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# Google Sheets 연결 함수
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client.open("내여행앱로그").sheet1 # 시트 이름 변경 필수

# 1. 사용 로그 기록 (검색 시 호출)
def log_search(destination, days, interests):
    sheet = get_sheet()
    sheet.append_row([str(datetime.datetime.now()), destination, days, str(interests)])

# 2. 피드백 수집 (화면 하단)
def save_feedback(rating, comment):
    sheet = client.open("내여행앱로그").worksheet("피드백") # 별도 탭
    sheet.append_row([str(datetime.datetime.now()), rating, comment])
    

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
                    p_data = gmaps.find_place(p['name'], 'textquery', fields=['name', 'geometry', 'formatted_address', 'place_id'])
                    if p_data.get('candidates'):
                        cand = p_data['candidates'][0]
                        clean_name = cand['name']
                        
                        # [필터링 로직 위치] 이름에 숫자가 3개 이상 들어간 코드성 이름이면 패스
                        if any(char.isdigit() for char in clean_name) and len(clean_name) < 10:
                            continue
                        
                        loc = cand['geometry']['location']
                        valid_coords.append({
                            '장소': clean_name,
                            '주소': cand.get('formatted_address', '주소 정보 없음'),
                            'place_id': cand.get('place_id', ''),
                            'lat': loc['lat'], 
                            'lng': loc['lng']
                        })
                except Exception:
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
    num_days = int(st.session_state.get('days', 1)) 
    daily_groups = np.array_split(data, num_days)
    
    # 탭으로 일자별 구성
    tabs = st.tabs([f"{i+1}일차" for i in range(num_days)])
    
    for i, tab in enumerate(tabs):
        with tab:
            if i < len(daily_groups) and len(daily_groups[i]) > 0:
                for item in daily_groups[i]:
                    st.write(f"✅ **{item['장소']}**")
                    st.caption(f"📍 {item['주소']}")
                    # 구글 맵으로 이동하는 버튼
                    map_url = f"https://www.google.com/maps/place/?q=place_id:{item['place_id']}"
                    st.link_button("구글 맵에서 보기", map_url)
            else:
                st.write("해당 날짜에 추천할 장소가 없습니다.")

# [출력부 하단 추가]
if st.session_state.valid_coords and 'map_data' in st.session_state:
    st.subheader(f"📍 {destination} 추천 경로 및 일정")
    
    # 1. 레이아웃 분할 (좌: 지도, 우: 일정 탭)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # st_folium에 key를 추가하여 중복을 방지합니다.
        st_folium(st.session_state.map_data, width=400, height=400, key="travel_map")
    
    with col2:
        # 일자별 일정 탭
        num_days = int(st.session_state.get('days', 1))
        tabs = st.tabs([f"{i+1}일차" for i in range(num_days)])
        
        for i, tab in enumerate(tabs):
            with tab:
                if i < len(daily_groups) and len(daily_groups[i]) > 0:
                    for item in daily_groups[i]:
                        st.write(f"✅ **{item['장소']}**")
                        st.caption(f"📍 {item.get('주소', '주소 정보 없음')}")
                        st.link_button("구글 맵에서 보기", f"https://www.google.com/maps/place/?q=place_id:{item['place_id']}")
                else:
                    st.write("해당 날짜에 추천할 장소가 없습니다.")

    # 2. 일정 공유하기 (세션 상태의 데이터를 활용)
    st.divider()
    summary = f"✨ {destination} 추천 여행 일정:\n\n"
    for i, group in enumerate(daily_groups):
        summary += f"[{i+1}일차]\n"
        for item in group:
            summary += f"- {item['장소']}\n"
    st.text_area("📋 일정 공유하기 (복사해서 친구에게 보내세요!)", value=summary, height=150)

    # 3. 피드백 섹션
    st.divider()
    st.write("### 💬 이 일정이 도움이 되었나요?")
    f_col1, f_col2 = st.columns(2)
    
    # 세션 상태에 피드백 여부를 기록하여 중복 제출 방지
    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = False

    with f_col1:
        if st.button("👍 좋았어요") and not st.session_state.feedback_submitted:
            save_feedback("Good", "사용자 긍정 평가")
            st.session_state.feedback_submitted = True
            st.success("소중한 의견 감사합니다!")
    with f_col2:
        if st.button("👎 아쉬워요") and not st.session_state.feedback_submitted:
            save_feedback("Bad", "사용자 부정 평가")
            st.session_state.feedback_submitted = True
            st.warning("더 개선하도록 하겠습니다.")
    
    feedback_text = st.text_area("기타 자유 의견을 남겨주세요!")
    if st.button("의견 보내기"):
        if feedback_text:
            save_feedback("Text", feedback_text)
            st.info("의견이 전송되었습니다.")
        else:
            st.warning("의견을 입력해주세요.")
