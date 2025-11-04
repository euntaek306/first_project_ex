"""
마라톤 사진 검색 플랫폼 - GPX 통합 버전
작가: GPX 코스 기반 자동 위치/시간 할당
이용자: 지도 위 마커로 유사 사진 표시
"""

import streamlit as st
from PIL import Image
import gpxpy
import folium
from streamlit_folium import folium_static
import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import io
from datetime import datetime, timedelta
import random
import base64

# ==========================================
# ImageSimilarityFinder 클래스
# ==========================================
class ImageSimilarityFinder:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    @st.cache_resource
    def load_model(_self):
        """모델 로드 (캐싱)"""
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model.to(_self.device)
        return model, processor
    
    def get_image_embedding(self, image):
        """이미지의 임베딩 벡터 생성"""
        if self.model is None or self.processor is None:
            self.model, self.processor = self.load_model()
        
        if isinstance(image, str):
            image = Image.open(image).convert('RGB')
        else:
            image = image.convert('RGB')
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            embedding = self.model.get_image_features(**inputs)
        
        return embedding.cpu().numpy()

# ==========================================
# GPX 관련 함수
# ==========================================
def load_marathon_course(tournament_name):
    """대회 이름에 따라 GPX 파일 로드"""
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
            st.error(f"❌ GPX 파일을 찾을 수 없습니다: {gpx_files[tournament_name]}")
            return None
    return None

def assign_photo_locations(num_photos, coordinates, start_time):
    """
    사진에 GPX 코스 기반 위치와 시간 자동 할당
    
    Args:
        num_photos: 사진 개수
        coordinates: GPX 좌표 리스트
        start_time: 대회 시작 시간
    
    Returns:
        list: [{lat, lon, km, time}, ...]
    """
    if not coordinates or len(coordinates) == 0:
        return []
    
    total_points = len(coordinates)
    photo_locations = []
    
    # 코스를 8등분하여 사진 위치 할당
    for i in range(num_photos):
        # 코스 상의 인덱스 계산 (균등 분배)
        idx = int((i / num_photos) * total_points)
        if idx >= total_points:
            idx = total_points - 1
        
        # 좌표
        lat, lon = coordinates[idx]
        
        # km 거리 계산 (비례 계산)
        km = (idx / total_points) * 42.195
        
        # 시간 계산 (평균 페이스 6분/km 가정)
        minutes_elapsed = int(km * 6)
        photo_time = start_time + timedelta(minutes=minutes_elapsed)
        
        photo_locations.append({
            'lat': lat,
            'lon': lon,
            'km': round(km, 2),
            'time': photo_time.strftime("%Y-%m-%d %H:%M:%S"),
            'idx': idx
        })
    
    return photo_locations

def create_course_map_with_photos(coordinates, photo_markers=None):
    """
    GPX 코스 지도 + 사진 마커 생성
    
    Args:
        coordinates: GPX 좌표
        photo_markers: 사진 마커 정보 리스트
    """
    if not coordinates:
        return None
    
    # 지도 중심 계산
    center_lat = sum([c[0] for c in coordinates]) / len(coordinates)
    center_lon = sum([c[1] for c in coordinates]) / len(coordinates)
    
    # 지도 생성
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='CartoDB positron'
    )
    
    # 코스 라인 그리기
    folium.PolyLine(
        coordinates,
        color='#FF4444',
        weight=5,
        opacity=0.8,
        popup='마라톤 코스'
    ).add_to(m)
    
    # 출발/도착 마커
    folium.Marker(
        coordinates[0],
        popup='🏁 출발',
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        coordinates[-1],
        popup='🎯 도착',
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)
    
    # km 지점 마커
    total_points = len(coordinates)
    for km in [10, 20, 21.0975, 30, 40]:
        idx = int((km / 42.195) * total_points)
        if idx < total_points:
            folium.CircleMarker(
                location=coordinates[idx],
                radius=8,
                popup=f'{km}km 지점',
                color='blue',
                fill=True,
                fillColor='lightblue',
                fillOpacity=0.7
            ).add_to(m)
    
    # 사진 마커 추가
    if photo_markers:
        for photo in photo_markers:
            # 이미지를 base64로 인코딩
            img_base64 = photo.get('image_base64', '')
            
            # 팝업 HTML
            popup_html = f"""
            <div style='width: 250px; font-family: Arial;'>
                <img src='data:image/png;base64,{img_base64}' 
                     style='width: 100%; border-radius: 8px; margin-bottom: 10px;'>
                <div style='background: #f0f7ff; padding: 10px; border-radius: 8px;'>
                    <b style='color: #2c3e50; font-size: 16px;'>📸 {photo['name']}</b><br>
                    <hr style='margin: 8px 0; border: none; border-top: 1px solid #ddd;'>
                    <small style='color: #666;'>
                        📍 <b>위치:</b> {photo['km']}km 지점<br>
                        📅 <b>시간:</b> {photo['time']}<br>
                        🎯 <b>유사도:</b> <span style='color: #4a90e2; font-weight: bold;'>{photo['similarity']:.1f}%</span><br>
                        👤 <b>촬영자:</b> {photo.get('photographer', '작가')}
                    </small>
                </div>
            </div>
            """
            
            # 유사도에 따른 마커 색상
            if photo['similarity'] >= 90:
                marker_color = 'red'
            elif photo['similarity'] >= 80:
                marker_color = 'orange'
            else:
                marker_color = 'blue'
            
            folium.Marker(
                [photo['lat'], photo['lon']],
                popup=folium.Popup(popup_html, max_width=270),
                icon=folium.Icon(color=marker_color, icon='camera', prefix='fa'),
                tooltip=f"📸 {photo['km']}km | 유사도: {photo['similarity']:.1f}%"
            ).add_to(m)
    
    return m

# ==========================================
# 세션 스테이트 초기화
# ==========================================
if 'saved_photos' not in st.session_state:
    st.session_state.saved_photos = []
if 'image_finder' not in st.session_state:
    st.session_state.image_finder = ImageSimilarityFinder()
if 'selected_tournament' not in st.session_state:
    st.session_state.selected_tournament = None
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'show_results' not in st.session_state:
    st.session_state.show_results = False

# ==========================================
# CSS 스타일
# ==========================================
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); }
    .stButton>button {
        background: linear-gradient(90deg, #4a90e2 0%, #50e3c2 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px 30px;
        border-radius: 12px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(74, 144, 226, 0.4);
    }
    .info-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #4a90e2;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 대회 데이터
# ==========================================
tournaments = {
    "JTBC 마라톤": {
        "date": "2025년 11월 2일",
        "start_time": "09:00:00",
        "distance": "42.195km",
        "icon": "🏃‍♂️"
    },
    "춘천 마라톤": {
        "date": "2025년 10월 26일",
        "start_time": "09:00:00",
        "distance": "42.195km",
        "icon": "🏔️"
    }
}

# ==========================================
# 사이드바: 모드 선택
# ==========================================
mode = st.sidebar.radio(
    "모드 선택",
    ["📸 작가 모드", "🔍 이용자 모드"],
    label_visibility="collapsed"
)

# ==========================================
# 작가 모드
# ==========================================
if mode == "📸 작가 모드":
    st.title("📸 작가 모드")
    st.caption("사진을 업로드하면 GPX 코스에 따라 자동으로 위치와 시간이 할당됩니다")
    st.markdown("---")
    
    # 대회 선택
    selected_tournament = st.selectbox(
        "대회 선택",
        options=list(tournaments.keys())
    )
    
    # 파일 업로드 (8장 권장)
    st.info("💡 8장의 사진을 업로드하면 코스 전체에 균등하게 배치됩니다")
    uploaded_files = st.file_uploader(
        "사진을 선택하세요 (최대 8장 권장)",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        key="photographer_upload"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}장의 사진이 업로드되었습니다!")
        
        # 미리보기
        cols = st.columns(4)
        for idx, file in enumerate(uploaded_files[:8]):  # 최대 8장만
            col = cols[idx % 4]
            with col:
                image = Image.open(file)
                st.image(image, use_container_width=True, caption=f"사진 {idx+1}")
        
        st.markdown("---")
        
        # 저장 버튼
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 DB에 저장하기", type="primary"):
                # GPX 코스 로드
                coordinates = load_marathon_course(selected_tournament)
                
                if not coordinates:
                    st.error("❌ GPX 파일을 로드할 수 없습니다.")
                else:
                    # 대회 시작 시간
                    start_datetime = datetime.strptime(
                        f"{tournaments[selected_tournament]['date']} {tournaments[selected_tournament]['start_time']}",
                        "%Y년 %m월 %d일 %H:%M:%S"
                    )
                    
                    # 위치/시간 자동 할당
                    photo_locations = assign_photo_locations(
                        len(uploaded_files[:8]),
                        coordinates,
                        start_datetime
                    )
                    
                    # 진행 바
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, (file, location) in enumerate(zip(uploaded_files[:8], photo_locations)):
                        status_text.text(f"🤖 AI 처리 중... ({idx+1}/{len(uploaded_files[:8])})")
                        
                        try:
                            # 이미지 로드
                            image = Image.open(file)
                            
                            # 임베딩 생성
                            embedding = st.session_state.image_finder.get_image_embedding(image)
                            
                            # 이미지를 바이트로 변환
                            img_byte_arr = io.BytesIO()
                            image.save(img_byte_arr, format='PNG')
                            image_bytes = img_byte_arr.getvalue()
                            
                            # base64 인코딩 (지도 마커용)
                            img_base64 = base64.b64encode(image_bytes).decode()
                            
                            # 데이터 저장
                            st.session_state.saved_photos.append({
                                'name': file.name,
                                'image_bytes': image_bytes,
                                'image_base64': img_base64,
                                'embedding': embedding,
                                'lat': location['lat'],
                                'lon': location['lon'],
                                'km': location['km'],
                                'time': location['time'],
                                'tournament': selected_tournament,
                                'photographer': '작가'  # 실제로는 사용자 정보
                            })
                            
                        except Exception as e:
                            st.error(f"❌ {file.name} 처리 중 오류: {str(e)}")
                        
                        progress_bar.progress((idx + 1) / len(uploaded_files[:8]))
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success(f"🎉 {len(uploaded_files[:8])}장의 사진이 저장되었습니다!")
                    st.balloons()
                    
                    # 저장된 위치 정보 표시
                    st.markdown("### 📍 자동 할당된 위치 정보")
                    for idx, loc in enumerate(photo_locations):
                        st.text(f"사진 {idx+1}: {loc['km']}km 지점 | {loc['time']}")

# ==========================================
# 이용자 모드
# ==========================================
else:
    if not st.session_state.show_results:
        # 페이지 1: 대회 선택 + 사진 업로드
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
                    key="photo_uploader"
                )
                
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    st.session_state.uploaded_image = image
                    
                    if st.button("🔍 코스 및 추천 사진 보기", type="primary"):
                        st.session_state.show_results = True
                        st.rerun()
            else:
                st.info("👆 위에서 대회를 먼저 선택해주세요")
    
    else:
        # 페이지 2: 지도 + 유사 사진
        tournament_name = st.session_state.selected_tournament
        tournament_info = tournaments[tournament_name]
        
        # 헤더
        header_col1, header_col2 = st.columns([1, 9])
        with header_col1:
            if st.button("◀️ 처음으로", type="secondary"):
                st.session_state.show_results = False
                st.session_state.selected_tournament = None
                st.session_state.uploaded_image = None
                st.rerun()
        
        with header_col2:
            st.markdown(f"""
            <h1 style='text-align: center; color: #2c3e50;'>
                {tournament_info['icon']} {tournament_name}
            </h1>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 좌우 분할
        left_col, right_col = st.columns([7, 3])
        
        with left_col:
            st.markdown("### 🗺️ 마라톤 코스")
            
            # GPX 코스 로드
            coordinates = load_marathon_course(tournament_name)
            
            if coordinates:
                # 유사도 검색
                if st.session_state.uploaded_image:
                    with st.spinner("🤖 유사한 사진을 검색하고 있습니다..."):
                        try:
                            # 쿼리 이미지 임베딩
                            query_embedding = st.session_state.image_finder.get_image_embedding(
                                st.session_state.uploaded_image
                            )
                            
                            # 유사도 계산
                            photo_markers = []
                            for saved_photo in st.session_state.saved_photos:
                                if saved_photo['tournament'] != tournament_name:
                                    continue
                                
                                similarity = cosine_similarity(
                                    query_embedding,
                                    saved_photo['embedding']
                                )[0][0]
                                similarity_percent = float(similarity * 100)
                                
                                if similarity_percent >= 70:  # 임계값
                                    photo_markers.append({
                                        'lat': saved_photo['lat'],
                                        'lon': saved_photo['lon'],
                                        'km': saved_photo['km'],
                                        'time': saved_photo['time'],
                                        'similarity': similarity_percent,
                                        'name': saved_photo['name'],
                                        'photographer': saved_photo['photographer'],
                                        'image_base64': saved_photo['image_base64']
                                    })
                            
                            # 지도 생성
                            m = create_course_map_with_photos(coordinates, photo_markers)
                            
                            if m:
                                st.success(f"✅ {len(photo_markers)}개의 유사한 사진을 찾았습니다!")
                                folium_static(m, width=1300, height=600)
                            
                        except Exception as e:
                            st.error(f"❌ 오류: {str(e)}")
            else:
                st.error("❌ GPX 파일을 로드할 수 없습니다.")
        
        with right_col:
            if st.session_state.uploaded_image:
                st.markdown("#### 🖼️ 검색한 사진")
                st.image(st.session_state.uploaded_image, use_container_width=True)
                
                st.markdown("---")
                st.info("👈 지도에서 📸 마커를 클릭하면 상세 정보를 볼 수 있습니다")

st.caption("💡 Tip: 작가 모드에서 사진을 먼저 업로드해야 검색이 가능합니다")