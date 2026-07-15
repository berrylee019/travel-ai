import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- 설정 및 함수 정의 (상단 유지) ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

def save_feedback(rating, comment):
#    client = get_client()
#    sheet = client.open_by_key("1xryDZgNxkMvZChlUk9u9QXyWg7nO7bm9gx3GUAomo6w")
#    sheet.append_row([str(datetime.datetime.now()), rating, comment])
    
# 피드백 저장 함수 (들여쓰기 정리 완료)

    try:
        client = get_client()
        # 시트 이름이 아닌, 시트 파일 URL에서 긴 ID 값을 가져와서 넣는 것을 추천합니다.
        # 예: sheet = client.open_by_key("여기에_긴_ID_입력").worksheet("피드백")
        sheet = client.open("내여행앱로그").worksheet("피드백")
        sheet.append_row([str(datetime.datetime.now()), rating, comment])
    except Exception as e:
        # 에러가 나면 화면에 친절하게 띄워줍니다.
        st.error(f"의견 전송 중 문제가 발생했습니다: {e}")

@st.cache_resource
def get_gmaps_client():
    return googlemaps.Client(key=st.secrets["google_maps_api_key"])

gmaps = get_gmaps_client()

# --- 앱 실행부 ---
st.title("✈️ 여행 비서 AI: 제로 클릭 일정 생성")

with st.form("travel_form"):
    destination = st.text_input("여행지")
    days = st.number_input("여행 기간 (일)", 1, 10, 3)
    interests = st.multiselect("관심사", ["맛집", "자연", "역사", "쇼핑", "예술"])
    submit_button = st.form_submit_button("일정 생성 시작!")

if submit_button:
    st.session_state.show_result = True
    if not destination:
        st.error("여행지를 입력해주세요!")
    else:
        # 1. 여기서 미리 빈 리스트를 만들어둡니다.
        valid_coords = [] 
        
        with st.spinner('일정을 계산 중입니다...'):
            # (중략: A, B 로직 수행)
            places_found = [] 
            valid_coords = [] 
            
            # (B) 지역 편향 검색
            for interest in interests:
                results = gmaps.places(
                    query=f"{interest} in {destination}",
                    location=(dest_lat, dest_lng),
                    radius=50000
                )
                if results and 'results' in results:
                    for place in results['results'][:2]:
                        places_found.append({"name": place['name']})
                        
                for place in results.get('results', [])[:2]:
                    places_found.append({"name": place['name']})
                    
            # (C) 좌표 수집 및 '이름 필터링' 적용
            for p in places_found:
                try:
                    # [여기] 이 내용들이 try보다 4칸 더 들어가 있어야 합니다!
                    p_data = gmaps.find_place(p['name'], 'textquery', fields=['name', 'geometry', 'formatted_address', 'place_id'])
                    if p_data.get('candidates'):
                        cand = p_data['candidates'][0]
                        clean_name = cand['name']
                        
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
                    # [여기] except도 try와 세로 줄을 맞춰야 합니다.
                    continue
                
                st.session_state.valid_coords = valid_coords
                st.session_state.map_data = m
                st.session_state.days = days
                st.session_state.show_result = True
                st.session_state.destination = destination # destination도 저장 필요

# --- [중요] 출력부는 오직 아래 블록 하나만 남기세요! ---
if st.session_state.get("show_result") and st.session_state.valid_coords:
    dest = st.session_state.get("destination", "여행지")
    st.subheader(f"📍 {dest} 추천 경로 및 일정")
    
    # 1. 레이아웃
    col1, col2 = st.columns([1, 1])
    
    # 2. 지도 출력
    with col1:
        st_folium(st.session_state.map_data, width=400, height=400, key="map_unique")
    
    # 3. 일정 탭 출력
    with col2:
        num_days = int(st.session_state.get('days', 1))
        daily_groups = np.array_split(st.session_state.valid_coords, num_days)
        tabs = st.tabs([f"{i+1}일차" for i in range(num_days)])
        
        for i, tab in enumerate(tabs):
            with tab:
                if i < len(daily_groups) and len(daily_groups[i]) > 0:
                    for item in daily_groups[i]:
                        st.write(f"✅ **{item['장소']}**")
                        st.caption(f"📍 {item.get('주소', '주소 정보 없음')}")
                        st.link_button("구글 맵에서 보기", f"https://www.google.com/maps/place/?q=place_id:{item['place_id']}")
                else:
                    st.write("일정이 없습니다.")

    # 4. 공유 및 피드백 (로직 통합)
    st.divider()
    # ... (요약 생성 및 text_area, 피드백 버튼 로직)

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
