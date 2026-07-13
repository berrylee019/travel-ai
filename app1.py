import streamlit as st
import pandas as pd
import requests
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json

# 1. API 및 구글 권한 설정
# SerpApi 키는 Streamlit Cloud의 Settings -> Secrets에 serp_api_key로 저장하세요.
try:
    SERP_API_KEY = st.secrets["serp_api_key"]
except:
    SERP_API_KEY = "YOUR_SERP_API_KEY_LOCAL" # 로컬 테스트용

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_google_calendar():
    creds = None
    # 1. token.json 경로는 그대로 유지 (서버 실행 시 생성됨)
    token_path = os.path.join(os.getcwd(), 'token.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 2. 파일이 없으면 Secrets에서 읽어와서 임시 파일 생성
            if not os.path.exists('credentials.json'):
                try:
                    creds_dict = json.loads(st.secrets["google_credentials"])
                    with open('credentials.json', 'w') as f:
                        json.dump(creds_dict, f)
                except Exception as e:
                    st.error("Secrets에서 구글 인증 정보를 읽지 못했습니다.")
                    return None
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)

def add_to_calendar(service, summary, departure_date, airline, return_date=None):
    """확정된 항공편 정보를 구글 캘린더에 등록합니다."""
    description = f'AI 비서가 예약한 {airline} 항공편 일정입니다.'
    if return_date:
        description += f' (귀국일: {return_date})'

    event = {
        'summary': f'✈️ {summary} 여행 ({airline})',
        'description': description,
        'start': {'date': departure_date, 'timeZone': 'Asia/Seoul'},
        'end': {'date': departure_date, 'timeZone': 'Asia/Seoul'},
    }
    
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('htmlLink')
    except Exception as e:
        st.error(f"캘린더 등록 중 오류 발생: {e}")
        return None

def fetch_flights(departure_id, arrival_id, outbound_date, return_date=None):
    """Google Flights 데이터를 SerpApi를 통해 가져옵니다."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "currency": "KRW",
        "hl": "ko",
        "api_key": SERP_API_KEY
    }

    # 왕복 여부에 따른 파라미터 분기
    if return_date and return_date > datetime.date.fromisoformat(outbound_date):
        params["return_date"] = str(return_date)
        params["type"] = "1"  # 왕복
    else:
        params["type"] = "2"  # 편도

    try:
        response = requests.get(url, params=params)
        res_data = response.json()
        if "error" in res_data:
            st.error(f"⚠️ SerpApi 에러: {res_data['error']}")
            return None
        return res_data
    except Exception as e:
        st.error(f"🚨 연결 오류: {e}")
        return None

# --- UI 부분 ---
st.set_page_config(page_title="제로 클릭 여행 비서", layout="wide")
st.title("🛫 제로 클릭 여행 비서: 왕복 항공권 & 일정 자동화")

with st.sidebar:
    st.header("👤 내 여행 프로필")
    st.info("형님은 현재 '국적기'와 '창가 좌석'을 선호하도록 설정되어 있습니다.")
    if st.button("구글 계정 연결하기"):
        authenticate_google_calendar()
        st.success("캘린더 권한이 활성화되었습니다.")

# 입력 폼
col1, col2, col3, col4 = st.columns(4)
with col1:
    dep = st.text_input("출발지 (공항코드)", value="ICN")
with col2:
    arr = st.text_input("도착지 (공항코드)", value="DFW")
with col3:
    date = st.date_input("출발 일자", value=datetime.date.today() + datetime.timedelta(days=7))
with col4:
    ret_date = st.date_input("오는 날짜 (선택)", value=datetime.date.today() + datetime.timedelta(days=14))

if st.button("최적의 항공권 찾기"):
    with st.spinner("AI가 실시간 최저가와 동선을 분석 중있는 중..."):
        # 수정 포인트: ret_date 변수를 함수에 전달
        data = fetch_flights(dep, arr, str(date), ret_date)
        
        if data and "best_flights" in data:
            st.subheader(f"✨ 형님을 위한 추천 항공편 (왕복/편도)")
            
            for i, flight in enumerate(data["best_flights"][:3]):
                with st.container(border=True):
                    airline = flight["flights"][0]["airline"]
                    price = flight["price"]
                    duration = flight["total_duration"]
                    
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.markdown(f"**{airline}** | ⏱️ {duration}분 소요")
                    c2.markdown(f"**{price:,}원**")
                    
                    with c3:
                        # 실제 예약 페이지 링크 (예시)
                        st.link_button("예약하기", "https://www.google.com/travel/flights")
                    
                    with c4:
                        if st.button(f"캘린더 등록", key=f"cal_{i}"):
                            service = authenticate_google_calendar()
                            if service:
                                link = add_to_calendar(service, f"{dep} ➔ {arr}", str(date), airline, str(ret_date))
                                if link:
                                    st.toast("구글 캘린더에 일정이 추가되었습니다!", icon="✅")
                                    st.markdown(f"[📅 일정 보기]({link})")
        else:
            st.warning("일치하는 항공권 정보가 없습니다. 날짜나 공항 코드를 확인해 보세요.")
