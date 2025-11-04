"""
마라톤 사진 검색 플랫폼
대회 선택 → 사진 업로드 → 새 화면에서 코스 지도 + 유사 사진 표시
"""

import streamlit as st
from PIL import Image
import gpxpy
import folium
from streamlit_folium import st_folium
import datetime

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="마라톤 사진 검색",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 간결한 CSS 스타일
# ==========================================
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    }
    .stSelectbox {
        font-size: 18px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #4a90e2 0%, #50e3c2 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px 30px;
        border-radius: 12px;
        border: none;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(74, 144, 226, 0.4);
    }
    .stFileUploader {
        border: 2px dashed #4a90e2;
        border-radius: 12px;
        padding: 30px;
        background: white;
    }
    .info-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #4a90e2;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .photo-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #e0e7ff;
        text-align: center;
        transition: all 0.3s;
        cursor: pointer;
    }
    .photo-card:hover {
        transform: scale(1.05);
        border-color: #4a90e2;
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        font-size: 48px;
        margin-bottom: 30px;
    }
    h2 {
        color: #34495e;
        font-size: 28px;
    }
    h3 {
        color: #4a90e2;
        font-size: 22px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 세션 스테이트 초기화
# ==========================================
if 'selected_tournament' not in st.session_state:
    st.session_state.selected_tournament = None
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'selected_photo' not in st.session_state:
    st.session_state.selected_photo = None
if 'purchased_photos' not in st.session_state:
    st.session_state.purchased_photos = []

# ==========================================
# 대회 데이터
# ==========================================
tournaments = {
    "JTBC 마라톤": {
        "date": "2025년 11월 2일",
        "distance": "42.195km",
        "participants": "30,000명",
        "course": "잠실종합운동장 → 광화문 → 남산 → 한강 → 잠실",
        "icon": "🏃‍♂️",
        "color": "#FF6B6B"
    },
    "춘천 마라톤": {
        "date": "2025년 10월 26일",
        "distance": "42.195km",
        "participants": "15,000명",
        "course": "의암호 → 소양강 → 춘천시가지 → 의암호",
        "icon": "🏔️",
        "color": "#4ECDC4"
    }
}

# 임시 사진 데이터 (DB 대체)
recommended_photos = [
    {'id': 1, 'lat': 37.5665, 'lon': 126.9780, 'km': 5.0, 'similarity': 95, 'thumbnail': 'https://via.placeholder.com/150', 'time': '2025-11-04 09:30:00', 'photographer': 'John', 'photographer_id': 'john123', 'price': 10000, 'name': 'Photo 1'},
    {'id': 2, 'lat': 37.5670, 'lon': 126.9790, 'km': 10.0, 'similarity': 90, 'thumbnail': 'https://via.placeholder.com/150', 'time': '2025-11-04 10:00:00', 'photographer': 'Jane', 'photographer_id': 'jane456', 'price': 12000, 'name': 'Photo 2'},
    {'id': 3, 'lat': 37.5680, 'lon': 126.9800, 'km': 15.0, 'similarity': 85, 'thumbnail': 'https://via.placeholder.com/150', 'time': '2025-11-04 10:30:00', 'photographer': 'Bob', 'photographer_id': 'bob789', 'price': 15000, 'name': 'Photo 3'},
]

# 사진 선택 함수
def select_photo(photo_id):
    photo = next((p for p in recommended_photos if p['id'] == photo_id), None)
    st.session_state.selected_photo = photo

# 구매 함수
def purchase_photo(photo_id):
    st.session_state.purchased_photos.append(photo_id)
    return True

# ==========================================
# GPX 지도 설정
# ==========================================
def load_marathon_course(tournament_name):
    gpx_files = {
        "JTBC 마라톤": "data/2025_JTBC.gpx",
        "춘천 마라톤": "data/chuncheon_marathon.gpx",
    }
    if tournament_name in gpx_files:
        try:
            with open(gpx_files[tournament_name], 'r') as f:
                gpx = gpxpy.parse(f)
            coordinates = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        coordinates.append([point.latitude, point.longitude])
            return coordinates
        except FileNotFoundError:
            # 테스트용 좌표
            return [[37.5665, 126.9780], [37.5670, 126.9790], [37.5680, 126.9800]]
    return None

def create_course_map(coordinates, photo_locations=None):
    if not coordinates:
        return None
    center_lat = sum([c[0] for c in coordinates]) / len(coordinates)
    center_lon = sum([c[1] for c in coordinates]) / len(coordinates)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='CartoDB positron')
    folium.PolyLine(coordinates, color='#FF4444', weight=5, opacity=0.8, popup='마라톤 코스').add_to(m)
    folium.Marker(coordinates[0], popup='🏁 출발', icon=folium.Icon(color='green', icon='play')).add_to(m)
    folium.Marker(coordinates[-1], popup='🎯 도착', icon=folium.Icon(color='red', icon='stop')).add_to(m)
    
    total_points = len(coordinates)
    for km in [10, 20, 21.0975, 30, 40]:
        idx = int((km / 42.195) * total_points)
        if idx < total_points:
            folium.CircleMarker(
                location=coordinates[idx], radius=8, popup=f'{km}km 지점',
                color='blue', fill=True, fillColor='lightblue', fillOpacity=0.7
            ).add_to(m)
    
    if photo_locations:
        for photo in photo_locations:
            folium.Marker(
                [photo['lat'], photo['lon']],
                popup=folium.Popup(
                    f"""
                    <div style='width: 200px;'>
                        <img src='{photo['thumbnail']}' style='width: 100%; border-radius: 8px;'>
                        <b>{photo['name']}</b><br>
                        <small>{photo['km']:.1f}km 지점 | 유사도: {photo['similarity']}%</small><br>
                        <small>촬영 시간: {photo['time']}</small>
                    </div>
                    """,
                    max_width=220
                ),
                icon=folium.Icon(color='orange', icon='camera'),
                # 마커에 photo_id 속성 추가
                tooltip=f"Photo ID: {photo['id']}"
            ).add_child(folium.Popup(max_width=220)).add_to(m)
    
    return m

# ==========================================
# 페이지 1: 대회 선택 및 사진 업로드
# ==========================================
if not st.session_state.show_results:
    st.title("🏃 High 러너스 🏃")
    st.caption("AI가 마라톤 코스에서 당신의 사진을 찾아드립니다")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 80, 1])
    with col2:
        st.markdown("### 1️⃣ 대회 선택")
        selected = st.selectbox(
            "참가한 마라톤 대회를 선택하세요",
            options=["대회를 선택해주세요"] + list(tournaments.keys()),
            key="tournament_selectbox"
        )
        
        if selected != "대회를 선택해주세요":
            st.session_state.selected_tournament = selected
            st.markdown("### 2️⃣ 사진 업로드")
            uploaded_file = st.file_uploader(
                "Drag and drop file here",
                type=['png', 'jpg', 'jpeg'],
                key="photo_uploader",
                help="마라톤 사진을 업로드하세요 (최대 200MB)"
            )
            
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.session_state.uploaded_image = image
                if st.button("🔍 코스 및 추천 사진 보기", type="primary"):
                    st.session_state.show_results = True
                    st.rerun()
        else:
            st.info("👆 위에서 대회를 먼저 선택해주세요")

# ==========================================
# 페이지 2: 코스 지도 + 유사 사진
# ==========================================
else:
    tournament_name = st.session_state.selected_tournament
    tournament_info = tournaments[tournament_name]
    
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: white; border-radius: 12px; margin-bottom: 30px;'>
        <h1 style='margin: 0; font-size: 36px;'>{tournament_info['icon']} {tournament_name}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    header_col1, header_col2, header_col3 = st.columns([1, 5, 1])
    with header_col1:
        if st.button("◀️ 처음으로", key="back_button", type="secondary"):
            st.session_state.show_results = False
            st.session_state.selected_tournament = None
            st.session_state.uploaded_image = None
            st.session_state.selected_photo = None
            st.rerun()
    
    left_col, right_col = st.columns([6, 4])
    
    # 왼쪽: 지도 및 시간 슬라이더
    with left_col:
        st.markdown("### 🗺️ 마라톤 코스")
        st.markdown(f"""
        <div class="info-card">
            <p style='margin: 0; line-height: 1.8;'>
                📅 <b>일시:</b> {tournament_info['date']}<br>
                📏 <b>거리:</b> {tournament_info['distance']}<br>
                📍 <b>코스:</b> {tournament_info['course']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 시간 슬라이더
        st.markdown("#### ⏰ 시간대 선택")
        start_time = datetime.datetime.strptime("2025-11-04 08:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.strptime("2025-11-04 14:00:00", "%Y-%m-%d %H:%M:%S")
        time_range = st.slider(
            "촬영 시간대 선택",
            min_value=start_time,
            max_value=end_time,
            value=(start_time, end_time),
            format="HH:mm",
            step=datetime.timedelta(minutes=30)
        )
        
        # 시간 필터링된 사진
        filtered_photos = [
            photo for photo in recommended_photos
            if time_range[0] <= datetime.datetime.strptime(photo['time'], "%Y-%m-%d %H:%M:%S") <= time_range[1]
        ]
        
        coordinates = load_marathon_course(tournament_name)
        if coordinates:
            m = create_course_map(coordinates, filtered_photos)
            if m:
                # st_folium으로 마커 클릭 이벤트 처리
                map_data = st_folium(m, width=1050, height=800, key="course_map")
                # 마커 클릭 시 photo_id 추출
                if map_data.get('last_clicked') and map_data['last_clicked'].get('tooltip'):
                    photo_id = int(map_data['last_clicked']['tooltip'].replace("Photo ID: ", ""))
                    select_photo(photo_id)
                    st.rerun()
        else:
            st.error("❌ 코스 데이터를 찾을 수 없습니다.")
    
    # 오른쪽: 업로드 사진 및 추천 사진 상세
    with right_col:
        if st.session_state.uploaded_image:
            st.markdown("#### 🖼️ 검색한 사진")
            st.image(st.session_state.uploaded_image, use_container_width=True)
        
        st.markdown("#### 📍 선택한 사진")
        if st.session_state.selected_photo:
            photo = st.session_state.selected_photo
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        height: 300px; 
                        border-radius: 12px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        margin-bottom: 15px;
                        position: relative;'>
                <img src='{photo['thumbnail']}' style='max-width: 100%; max-height: 100%; border-radius: 8px;'>
                <div style='position: absolute; top: 10px; right: 10px; 
                            background: rgba(74, 144, 226, 0.9); 
                            color: white; padding: 5px 12px; border-radius: 20px;
                            font-weight: bold; font-size: 14px;'>
                    유사도: {photo['similarity']}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="info-card">
                <p style='margin: 0; line-height: 1.8; font-size: 14px;'>
                    📍 <b>위치:</b> {photo['km']}km 지점<br>
                    📅 <b>촬영 시간:</b> {photo['time']}<br>
                    👤 <b>촬영자:</b> {photo['photographer']}<br>
                    🆔 <b>ID:</b> @{photo['photographer_id']}<br>
                    💰 <b>가격:</b> <span style='color: #4a90e2; font-size: 18px; font-weight: bold;'>{photo['price']:,}원</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if photo['id'] in st.session_state.purchased_photos:
                st.success("✅ 구매 완료!")
                st.info("📧 구매한 사진이 이메일로 전송되었습니다.")
            else:
                if st.button("🛒 구매하기", type="primary", use_container_width=True, key="purchase_btn"):
                    if purchase_photo(photo['id']):
                        st.success("🎉 구매가 완료되었습니다!")
                        st.balloons()
                        st.info(f"""
                        **구매 정보:**
                        - 사진 ID: {photo['id']}
                        - 촬영자: {photo['photographer']}
                        - 금액: {photo['price']:,}원
                        - 구매 일시: 방금 전
                        
                        📧 고해상도 사진이 등록하신 이메일로 전송됩니다.
                        """)
                        st.rerun()
        else:
            st.info("👈 지도 위의 사진 마커를 클릭해보세요!")
            st.markdown("""
            <div style='text-align: center; padding: 40px 20px; color: #999;'>
                <div style='font-size: 64px; margin-bottom: 15px;'>📸</div>
                <p>지도에f서 사진을 선택하면<br>상세 정보를 확인할 수 있습니다</p>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 하단 푸터
# ==========================================
st.caption("💡 Tip: 정확한 검색을 위해 선명한 사진을 업로드해주세요")