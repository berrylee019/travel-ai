import streamlit as st
import pandas as pd
import requests
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 1. API 및 구글 권한 설정
try:
    SERP_API_KEY = st.secrets["serp_api_key"]
except:
    st.error("Secrets에 'serp_api_key'가 설정되지 않았습니다.")
    SERP_API_KEY = None
    
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_google_calendar():
    """구글 캘린더 API 인증을 수행합니다."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def add_to_calendar(service, summary, departure_date, airline):
    """확정된 항공편 정보를 구글 캘린더에 등록합니다."""
    # 간단한 예시로 출발일 오전 9시로 일정 설정
    start_time = f"{departure_date}T09:00:00Z"
    end_time = f"{departure_date}T12:00:00Z"

    event = {
        'summary': f'✈️ {summary} 여행 출발 ({airline})',
        'description': f'AI 비서가 예약한 {airline} 항공편 일정입니다.',
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
    }
    
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('htmlLink')
    except Exception as e:
        st.error(f"캘린더 등록 중 오류 발생: {e}")
        return None

def fetch_flights(departure_id, arrival_id, outbound_date):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "return_date": ret_date,
        "currency": "KRW",
        "hl": "ko",
        "type": "2",
        "type": "1",
        "api_key": SERP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        res_data = response.json()
        
        # 1. API 응답 자체에 에러가 있는지 확인
        if "error" in res_data:
            st.error(f"⚠️ SerpApi 에러 발생: {res_data['error']}")
            return None
            
        # 2. 검색 결과가 아예 없는 경우
        if "best_flights" not in res_data:
            st.warning("🧐 검색 결과는 성공했으나, 해당 날짜에 추천 항공권(Best Flights)이 없습니다.")
            # 데이터 구조를 확인해보고 싶다면 아래 주석을 해제하세요
            # st.write(res_data) 
            return None
            
        return res_data
        
    except Exception as e:
        st.error(f"🚨 네트워크 또는 코드 오류: {e}")
        return None

# --- UI 부분 ---
st.set_page_config(page_title="제로 클릭 여행 비서", layout="wide")
st.title("🛫 제로 클릭 여행 비서: 항공권 & 일정 자동화")

with st.sidebar:
    st.header("👤 내 여행 프로필")
    st.info("형님은 현재 '국적기'와 '창가 좌석'을 선호하도록 설정되어 있습니다.")
    if st.button("구글 계정 연결하기"):
        authenticate_google_calendar()
        st.success("캘린더 권한이 활성화되었습니다.")

col1, col2, col3 = st.columns(3)
with col1:
    dep = st.text_input("출발지 (공항코드)", value="ICN")
with col2:
    arr = st.text_input("도착지 (공항코드)", value="KIX")
with col3:
    date = st.date_input("출발 일자")
    date = st.date_input("오는 날자")

if st.button("최적의 항공권 찾기"):
    with st.spinner("AI가 실시간 최저가와 동선을 분석 중입니다..."):
        data = fetch_flights(dep, arr, str(date))
        
        if data and "best_flights" in data:
            st.subheader(f"✨ 형님을 위한 추천 항공편")
            
            for i, flight in enumerate(data["best_flights"][:3]):
                with st.container(border=True):
                    airline = flight["flights"][0]["airline"]
                    price = flight["price"]
                    duration = flight["total_duration"]
                    
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.markdown(f"**{airline}** | ⏱️ {duration}분 소요")
                    c2.markdown(f"**{price:,}원**")
                    
                    with c3:
                        st.link_button("예약하기", "http://google.com/travel/flights")
                    
                    with c4:
                        # 캘린더 등록 버튼 (고유 키 부여)
                        if st.button(f"캘린더 등록", key=f"cal_{i}"):
                            service = authenticate_google_calendar()
                            link = add_to_calendar(service, f"{dep} ➔ {arr}", str(date), airline)
                            if link:
                                st.toast("구글 캘린더에 일정이 추가되었습니다!", icon="✅")
                                st.markdown(f"[📅 일정 보기]({link})")
        else:
            st.warning("항공권 정보를 불러올 수 없습니다. API 설정을 확인하세요.")
