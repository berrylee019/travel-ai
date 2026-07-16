import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json

# 1. 상단에 빈 리스트로 초기화 (가장 중요!)
#if "path_coordinates" not in st.session_state:
#    st.session_state.path_coordinates = []

# 일반 변수를 호출하려고 하니 파이썬이 찾지 못하는 것
#if path_coordinates: 
#    draw_map(path_coordinates)

st.image("https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEg9zqBbDRhDl9WATjDpLOFMhMosMBDQU07rVsVV80jqjCJ70MxpCx2didYnGQXI7Lg7952zQKC8aZWHFDN06ZN2rSJKwU5Bt2A-TdZo1ZX8PIQSLmRbnSgRWPcfm1aoLM1xkaAw9-mXAKxDymCpTUuebAz8qG2SFLGYUjhRxMYEIdwEMuSvMnpGNTkeolo/s1248/Ah6RG.jpg", use_container_width=True)

# --- 설정 및 함수 정의 (상단 유지) ---
def get_client():
    # 1. 시크릿에서 가져온 데이터를 변수에 담습니다.
    raw_data = st.secrets["gcp"]["service_account"]
    
    # 2. 데이터가 문자열이면 JSON 객체로 변환, 이미 딕셔너리면 그대로 사용
    if isinstance(raw_data, str):
        creds_dict = json.loads(raw_data)
    else:
        creds_dict = raw_data
    #return creds_dict
    
    # 3. 권한 범위 설정
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 4. 인증 및 클라이언트 반환
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def save_feedback(rating, comment):
#    client = get_client()
#    sheet = client.open_by_key("1xryDZgNxkMvZChlUk9u9QXyWg7nO7bm9gx3GUAomo6w")
#    sheet.append_row([str(datetime.datetime.now()), rating, comment])
    
# 피드백 저장 함수 (들여쓰기 정리 완료)

    try:
            client = get_client()
            
            # 1. 파일 이름 대신 '고유 ID'를 사용하는 것이 훨씬 정확합니다.
            # 구글 시트 URL 주소창에 보면 /d/ 뒤부터 /edit 전까지의 긴 문자열이 ID입니다.
            spreadsheet_id = "1xryDZgNxkMvZChlUk9u9QXyWg7nO7bm9gx3GUAomo6w"
            
            # 2. open_by_key로 열기
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.worksheet("시트1")
            
            # 3. 데이터 추가
            sheet.append_row([str(datetime.datetime.now()), rating, comment])
            
            # 4. 성공 메시지 출력 (Response [200] 대신 깔끔하게!)
            st.success("의견이 성공적으로 전송되었습니다! 감사합니다.")
            
    except Exception as e:
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
    if not destination:
        st.error("여행지를 입력해주세요!")
    else:
        with st.spinner('일정을 계산 중입니다...'):
            valid_coords = []
            try:
                # (A) 중심 좌표 찾기
                geo_result = gmaps.geocode(destination)
                if not geo_result:
                    st.error("해당 여행지를 찾을 수 없습니다.")
                    st.stop()
                
                dest_loc = geo_result[0]['geometry']['location']
                dest_lat, dest_lng = dest_loc['lat'], dest_loc['lng']
                
                # (B) 지역 편향 검색
                places_found = []
                for interest in interests:
                    results = gmaps.places(
                        query=f"{interest} in {destination}",
                        location=(dest_lat, dest_lng),
                        radius=50000
                    )
                    if results and 'results' in results:
                        for place in results['results'][:2]:
                            places_found.append({"name": place['name']})
                
                # (C) 좌표 수집 및 필터링
                for p in places_found:
                    try:
                        p_data = gmaps.find_place(p['name'], 'textquery', fields=['name', 'geometry', 'formatted_address', 'place_id'])
                        if p_data.get('candidates'):
                            cand = p_data['candidates'][0]
                            #clean_name = cand['name']
                            #if any(char.isdigit() for char in clean_name) and len(clean_name) < 10:
                            #if destination not in cand.get('formatted_address', ''):
                            addr = cand.get('formatted_address', '')
                            name = cand.get('name', '')
                            
                            # '강화' 또는 'Incheon'이 주소나 이름에 포함되어야 함
                            if not ("강화" in addr or "강화" in name or "Incheon" in addr):
                                continue
                            
                            loc = cand['geometry']['location']
                            valid_coords.append({
                                '장소': clean_name,
                                '주소': cand.get('formatted_address', '주소 정보 없음'),
                                'place_id': cand.get('place_id', ''),
                                'lat': loc['lat'], 
                                'lng': loc['lng']
                            })
                    except Exception as e:
                        continue

            except Exception as e: # <--- 이 부분이 반드시 있어야 합니다!
                st.error(f"오류 발생: {e}")
                
                # 경로를 그리기 전에 좌표 데이터 출력 확인
                #st.write("현재 좌표 데이터:", path_coordinates)

                    # 2. 사용자가 여행 정보를 입력하고 '생성' 버튼을 눌렀을 때
                #if st.button("일정 생성"):
                    #if destination:
                        #new_coords = calculate_route(destination) # 경로 계산 함수 호출
                    
                    # [핵심] 여기에 값을 할당합니다
                        #st.session_state.path_coordinates = new_coords 
                        #st.success("경로가 생성되었습니다!")
                    #else:
                        #st.warning("여행지를 입력해주세요.")

        # (C) 좌표 수집 및 필터링 후, 유효하지 않은 좌표 제거
            clean_coords = []
            for item in valid_coords:
                # 위도나 경도가 0인 경우(검색 실패 데이터)는 제외
                if item['lat'] != 0 and item['lng'] != 0:
                    clean_coords.append(item)
            
            # 이제 clean_coords를 valid_coords로 사용합니다.
            valid_coords = clean_coords
            
        # (D) 지도 시각화 (장소가 있을 때만 m 생성)
            try:
                
                if valid_coords:
                    # 데이터 내용 확인 (이건 무조건 보일 겁니다)
                    st.sidebar.write("### 현재 수집된 좌표 데이터")
                    st.sidebar.write(f"개수: {len(valid_coords)}개")
                    st.sidebar.json(valid_coords) # 데이터 내용을 사이드바에 고정 출력
                    
                    # ... (이하 지도 시각화 로직) ...
                    
                    m = folium.Map(location=[dest_lat, dest_lng], zoom_start=11)
                    
                    # 1. 경로를 담을 리스트를 생성합니다.
                    coords_list = [[item['lat'], item['lng']] for item in valid_coords]
                    
                    # 2. 경로선(PolyLine)을 한 번만 그립니다.
                    folium.PolyLine(coords_list, color="blue", weight=2.5).add_to(m)
                    
                    # 3. 마커를 추가합니다.
                    for item in valid_coords:
                        folium.Marker(
                            [item['lat'], item['lng']], 
                            popup=item['장소']
                        ).add_to(m)
                    
                    # 4. 세션 상태에 저장
                    st.session_state.valid_coords = valid_coords
                    st.session_state.map_data = m
                    st.session_state.days = days
                    st.session_state.destination = destination
                    st.session_state.show_result = True

                    st.rerun()
                else:
                    st.warning("검색 결과가 없습니다.")
                    st.session_state.show_result = False

            except Exception as e:
                st.error(f"오류 발생: {e}")

            # 지도 그리기 직전에 확인용 코드
            st.write(f"현재 수집된 좌표 개수: {len(valid_coords)}")
            st.write(valid_coords)

# --- 1. 출력부 코드 시작 전 ---
# 폼 바깥에서 세션 상태를 직접 확인하여 출력합니다.
if st.session_state.get("valid_coords"):
    st.sidebar.write("### 현재 수집된 좌표 데이터")
    st.sidebar.write(f"개수: {len(st.session_state.valid_coords)}개")
    st.sidebar.json(st.session_state.valid_coords)
    
# --- [중요] 출력부는 오직 아래 블록 하나만 남기세요! ---
if st.session_state.get("show_result") and st.session_state.get("valid_coords"):
    dest = st.session_state.get("destination", "여행지")
    st.subheader(f"📍 {st.session_state.get('destination', '여행지')} 추천 경로 및 일정")
    
    # 1. 레이아웃
    col1, col2 = st.columns([1, 1])
    
    # 2. 지도 출력
    with col1:
        #st_folium(st.session_state.map_data, width=400, height=400, key="map_unique")
        if st.session_state.get("map_data"):
            st_folium(st.session_state.map_data, width=400, height=400, key="map_unique")
        else:
            st.warning("지도를 불러올 수 없습니다.")
    
        # 3. 지도에 그리는 부분
        #if st.session_state.path_coordinates:
            # 데이터가 있을 때만 지도를 그림
            #draw_map(st.session_state.path_coordinates)
        #else:
            #st.info("여행지를 입력하고 일정을 생성해 주세요.")
        
    # 3. 일정 탭 출력 
    
    with col2:
        num_days = int(st.session_state.get('days', 1))
        data = st.session_state.valid_coords
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
    
    # 세션 상태 초기화 (이미 있다면 무시됨)
    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = False
    if "feedback_message" not in st.session_state:
        st.session_state.feedback_message = ""
    
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        # 버튼은 항상 표시
        if st.button("👍 좋았어요"):
            if not st.session_state.feedback_submitted:
                save_feedback("Good", "사용자 긍정 평가")
                st.session_state.feedback_submitted = True
                st.session_state.feedback_message = "소중한 의견 감사합니다!"
            st.success("소중한 의견 감사합니다!")
    
    with f_col2:
        if st.button("👎 아쉬워요"):
            if not st.session_state.feedback_submitted:
                save_feedback("Bad", "사용자 부정 평가")
                st.session_state.feedback_submitted = True
                st.session_state.feedback_message = "더 개선하도록 하겠습니다."
            st.warning("더 개선하도록 하겠습니다.")
    
    # 기타 의견 섹션
    feedback_text = st.text_area("기타 자유 의견을 남겨주세요!")
    if st.button("의견 보내기"):
        if feedback_text:
            save_feedback("Text", feedback_text)
            #st.info("의견이 전송되었습니다.")
        else:
            st.warning("의견을 입력해주세요.")

    # [핵심] 메시지는 여기서 딱 한 번만 출력!
    if st.session_state.get("feedback_msg"):
        st.success(st.session_state.feedback_msg)
        st.session_state.feedback_msg = None
