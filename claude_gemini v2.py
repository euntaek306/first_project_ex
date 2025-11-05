"""
마라톤 사진 검색 플랫폼 - GPX 통합 버전 (최종 통합 버전)
주요 기능: 와이드 레이아웃, 지도 마커 썸네일/툴팁, 목록 숨김/상세 보기 전환, 선택적 다운로드
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
import zipfile 
from datetime import datetime, timedelta
import random
import base64

# ==========================================
# ⚙️ Streamlit 초기 설정 (와이드 레이아웃 적용)
# ==========================================
st.set_page_config(layout="wide")

# ==========================================
# CLIP 모델 로드 및 캐싱 (모듈 레벨 함수)
# ==========================================
@st.cache_resource
def load_clip_model():
    """모델 로드 및 캐싱 (모듈 레벨 함수)"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.to(device)
    return model, processor

# ==========================================
# ImageSimilarityFinder 클래스
# ==========================================
class ImageSimilarityFinder:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def get_image_embedding(self, image):
        """이미지의 임베딩 벡터 생성"""
        if self.model is None or self.processor is None:
            self.model, self.processor = load_clip_model()
        
        if isinstance(image, str):
            image = Image.open(image).convert('RGB')
        else:
            image = image.convert('RGB')
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            embedding = self.model.get_image_features(**inputs)
        
        return embedding.cpu().numpy()

# ==========================================
# 🖼️ 이미지 표시 및 ZIP 생성 도우미 함수
# ==========================================
def image_bytes_to_st_image(image_bytes, **kwargs):
    """
    이미지 바이트 데이터를 st.image에 안전하게 표시합니다.
    """
    st.image(io.BytesIO(image_bytes), **kwargs)


def create_zip_of_selected_photos(photo_markers):
    """선택된 이미지들을 zip 파일로 만들어 바이트 데이터를 반환합니다."""
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for selected_id in st.session_state.selected_for_download:
            photo = next((p for p in photo_markers if p['id'] == selected_id), None)
            
            if photo:
                file_name = f"Photo_Sim_{photo.get('similarity', 0):.1f}_{photo.get('name', 'image.jpg')}"
                zipf.writestr(file_name, photo['image_bytes'])
            
    buffer.seek(0)
    return buffer.getvalue()


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
    """사진에 GPX 코스 기반 위치와 시간 자동 할당"""
    if not coordinates or len(coordinates) == 0:
        return []
    
    total_points = len(coordinates)
    photo_locations = []
    
    for i in range(num_photos):
        idx = int((i / num_photos) * total_points)
        if idx >= total_points:
            idx = total_points - 1
        
        lat, lon = coordinates[idx]
        km = (idx / total_points) * 42.195
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
    GPX 코스 지도 + 사진 마커 생성 (Full Screen 기능 제거)
    """
    if not coordinates:
        return None
    
    center_lat = sum([c[0] for c in coordinates]) / len(coordinates)
    center_lon = sum([c[1] for c in coordinates]) / len(coordinates)
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='CartoDB positron'
    )
    
    folium.PolyLine(coordinates, color='#FF4444', weight=5, opacity=0.8, popup='마라톤 코스').add_to(m)
    folium.Marker(coordinates[0], popup='🏁 출발', icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(coordinates[-1], popup='🎯 도착', icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)
    total_points = len(coordinates)
    for km in [10, 20, 21.0975, 30, 40]:
        idx = int((km / 42.195) * total_points)
        if idx < total_points:
            folium.CircleMarker(location=coordinates[idx], radius=8, popup=f'{km}km 지점', color='blue', fill=True, fillColor='lightblue', fillOpacity=0.7).add_to(m)

    if photo_markers:
        for photo in photo_markers:
            img_base64 = photo.get('thumbnail_base64', '') 
            similarity_percent = photo['similarity']
            photo_unique_id = photo['id']

            if similarity_percent >= 90:
                border_style = '4px solid #FF0000'
                marker_color = 'red'
            elif similarity_percent >= 80:
                border_style = '2px solid #FFA500'
                marker_color = 'orange'
            else:
                border_style = '1px solid #4a90e2'
                marker_color = 'blue'
            
            icon_html = f"""
            <div style="
                width: 30px; height: 30px; 
                border-radius: 50%; 
                overflow: hidden; 
                border: {border_style};
                box-shadow: 0 0 5px rgba(0,0,0,0.4);
                background-image: url('data:image/png;base64,{img_base64}');
                background-size: cover;
                background-position: center;
                cursor: pointer;
            "></div>
            """
            
            custom_icon = folium.DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=icon_html 
            )

            # ツールチップ HTML (Full Screen 기능 제거)
            tooltip_image_html = f"""
            <div style='width: 150px; font-family: Arial; text-align: center; user-select: none;'>
                <img src='data:image/png;base64,{img_base64}' 
                     style='width: 100%; border-radius: 8px; border: {border_style}; cursor: pointer; margin-bottom: 5px;'>
                <div style='font-size: 12px; color: #333;'>
                    <b>{photo['name']}</b><br>
                    {photo['km']}km | <span style='color: {marker_color}; font-weight: bold;'>{similarity_percent:.1f}%</span>
                </div>
            </div>
            """
            
            # 팝업 HTML (Full Screen 기능 제거 및 상세 보기 버튼 유지)
            popup_html = f"""
            <div style='width: 250px; font-family: Arial;'>
                <img src='data:image/png;base64,{img_base64}'  
                      style='width: 100%; border-radius: 8px; margin-bottom: 10px; border: {border_style};'>
                <div style='background: #f0f7ff; padding: 10px; border-radius: 8px;'>
                    <b style='color: #2c3e50; font-size: 16px;'>📸 {photo['name']}</b><br>
                    <hr style='margin: 8px 0; border: none; border-top: 1px solid #ddd;'>
                    <small style='color: #666;'>
                        📍 <b>위치:</b> {photo['km']}km 지점<br>
                        📅 <b>시간:</b> {photo['time']}<br>
                        🎯 <b>유사도:</b> <span style='color: {marker_color}; font-weight: bold;'>{similarity_percent:.1f}%</span><br>
                        👤 <b>촬영자:</b> {photo.get('photographer', '작가')}
                    </small>
                    <button id='detail_btn_{photo_unique_id}' 
                            onclick="window.parent.postMessage({{
                                type: 'streamlit:setSessionState', 
                                key: 'detailed_photo_id', 
                                value: '{photo_unique_id}'
                            }}, '*'); window.parent.postMessage({{type: 'streamlit:rerun'}}, '*')"
                            style='background-color: #4a90e2; color: white; border: none; padding: 10px; border-radius: 5px; width: 100%; cursor: pointer; margin-top: 10px;'>
                            🔍 상세 보기 및 구매
                    </button>
                </div>
            </div>
            """

            folium.Marker(
                [photo['lat'], photo['lon']],
                popup=folium.Popup(popup_html, max_width=270),
                icon=custom_icon,
                tooltip=folium.Tooltip(tooltip_image_html, max_width=200) 
            ).add_to(m)
            
    return m

# ==========================================
# 세션 스테이트 초기화 함수
# ==========================================
def initialize_session_state():
    """Streamlit 세션 상태를 초기화합니다."""
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
    if 'detailed_photo_id' not in st.session_state:
        st.session_state.detailed_photo_id = None
    if 'selected_similar_photo_id' not in st.session_state:
        st.session_state.selected_similar_photo_id = None
    if 'show_detail_view' not in st.session_state:
        st.session_state.show_detail_view = False
    
    if 'selected_for_download' not in st.session_state:
        st.session_state.selected_for_download = set()


# ==========================================
# 세션 스테이트 초기화
# ==========================================
initialize_session_state()

# ==========================================
# CSS 스타일
# ==========================================
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); }
    /* 버튼 스타일 유지 */
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
    /* 구매 버튼 스타일 */
    .purchase-btn-style {
        background-color: #e35050; 
        color: white; 
        border: none; 
        padding: 10px; 
        border-radius: 5px; 
        width: 100%; 
        font-weight: bold; 
        cursor: pointer; 
        height: 50px;
        text-align: center;
        display: block;
        line-height: 30px; /* 버튼 텍스트 중앙 정렬 */
        text-decoration: none;
    }
    /* st.image 기본 풀스크린 버튼 숨기기 */
    div.stImage > button {
        display: none !important;
    }
    /* Full Screen 팝업 지원 CSS */
    @media all and (display-mode: fullscreen) {
        .leaflet-popup-content img {
            max-width: 100%;
            max-height: 100vh;
        }
    }
</style>
""", unsafe_allow_html=True)
# ==========================================
# 대회 데이터 (생략)
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
# 사이드바: 모드 선택 (생략)
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
    st.markdown("---")
    
    selected_tournament = st.selectbox(
        "대회 선택",
        options=list(tournaments.keys())
    )
    
    uploaded_files = st.file_uploader(
        "사진을 선택하세요",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        key="photographer_upload"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}장의 사진이 업로드되었습니다! (AI 처리 대기 중)") 
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 DB에 저장하기", type="primary"):
                coordinates = load_marathon_course(selected_tournament)
                
                if not coordinates:
                    st.error("❌ GPX 파일을 로드할 수 없습니다.")
                else:
                    start_datetime = datetime.strptime(
                        f"{tournaments[selected_tournament]['date']} {tournaments[selected_tournament]['start_time']}",
                        "%Y년 %m월 %d일 %H:%M:%S"
                    )
                    
                    photo_locations = assign_photo_locations(
                        len(uploaded_files[:8]),
                        coordinates,
                        start_datetime
                    )
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, (file, location) in enumerate(zip(uploaded_files[:8], photo_locations)):
                        status_text.text(f"🤖 AI 처리 중... ({idx+1}/{len(uploaded_files[:8])})")
                        
                        try:
                            image = Image.open(file)
                            embedding = st.session_state.image_finder.get_image_embedding(image)
                            
                            # 원본 이미지 저장 (큰 용량)
                            img_byte_arr_full = io.BytesIO()
                            image.save(img_byte_arr_full, format='JPEG', quality=90) # JPEG로 변경하여 용량 절감
                            image_bytes = img_byte_arr_full.getvalue()

                            # 작은 썸네일 생성 (마커 및 리스트용 - 용량 대폭 감소)
                            thumbnail = image.copy()
                            thumbnail.thumbnail((200, 200))
                            thumb_byte_arr = io.BytesIO()
                            thumbnail.save(thumb_byte_arr, format='JPEG', quality=70)
                            thumb_base64 = base64.b64encode(thumb_byte_arr.getvalue()).decode()
                            
                            st.session_state.saved_photos.append({
                                'name': file.name,
                                'image_bytes': image_bytes,
                                'thumbnail_base64': thumb_base64,
                                'embedding': embedding,
                                'lat': location['lat'],
                                'lon': location['lon'],
                                'km': location['km'],
                                'time': location['time'],
                                'tournament': selected_tournament,
                                'photographer': '작가'
                            })
                            
                        except Exception as e:
                            st.error(f"❌ {file.name} 처리 중 오류: {str(e)}")
                        
                        progress_bar.progress((idx + 1) / len(uploaded_files[:8]))
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success(f"🎉 {len(uploaded_files[:8])}장의 사진이 저장되었습니다!")
                    st.balloons()

# ==========================================
# 이용자 모드
# ==========================================
else:
    if not st.session_state.show_results:
        # 페이지 1: 대회 선택 + 사진 업로드 (생략)
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
                        st.session_state.detailed_photo_id = None
                        st.session_state.show_detail_view = False 
                        st.session_state.selected_for_download = set()
                        st.rerun()
                else:
                    st.info("👆 대회 선택 후, 검색할 사진을 올려주세요")
            else:
                st.info("👆 위에서 대회를 먼저 선택해주세요")
        
    else:
        # 페이지 2: 결과 페이지 (상세 보기 모드 vs. 지도 검색 모드)
        
        tournament_name = st.session_state.selected_tournament
        tournament_info = tournaments[tournament_name]
        
        # 헤더
        header_col1, header_col2 = st.columns([1, 9])
        with header_col1:
            if st.session_state.show_detail_view:
                # 📌 뒤로가기 버튼
                if st.button("⬅️ 유사 사진 목록으로", type="secondary", key="back_to_list"):
                    st.session_state.show_detail_view = False
                    st.session_state.selected_similar_photo_id = None
                    st.rerun()
            else:
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
        
        map_col, content_col = st.columns([5, 5])
        
        # ----------------------------------------------------
        # 1. 지도 영역 (Map Column) - 유사도 검색 및 지도 생성
        # ----------------------------------------------------
        with map_col:
            st.markdown("### 🗺️ 마라톤 코스 및 발견된 사진 위치")
            
            coordinates = load_marathon_course(tournament_name)
            photo_markers = []
            
            if coordinates and st.session_state.uploaded_image:
                with st.spinner("🤖 유사한 사진을 검색하고 있습니다..."):
                    try:
                        query_embedding = st.session_state.image_finder.get_image_embedding(
                            st.session_state.uploaded_image
                        )
                        
                        for saved_photo in st.session_state.saved_photos:
                            if saved_photo['tournament'] != tournament_name:
                                continue
                            
                            similarity = cosine_similarity(
                                query_embedding,
                                saved_photo['embedding']
                            )[0][0]
                            similarity_percent = float(similarity * 100)
                            
                            saved_photo['similarity'] = similarity_percent 
                            saved_photo['id'] = f"{saved_photo['tournament']}_{saved_photo['name']}"
                            
                            if similarity_percent >= 70:
                                photo_markers.append(saved_photo)
                            
                        photo_markers.sort(key=lambda x: x['similarity'], reverse=True)

                        m = create_course_map_with_photos(coordinates, photo_markers)
                        
                        if m:
                            st.success(f"✅ {len(photo_markers)}개의 유사한 사진을 찾았습니다! (마커/리스트 클릭 시 상세 보기)")
                            folium_static(m, width=950, height=500)
                        
                    except Exception as e:
                        st.error(f"❌ 오류: {str(e)}")
                        
            elif not coordinates:
                st.error("❌ GPX 파일을 로드할 수 없습니다.")

        # ----------------------------------------------------
        # 2. 콘텐츠 영역 (List/Detail Column)
        # ----------------------------------------------------
        with content_col:
            selected_photo_id = st.session_state.selected_similar_photo_id
            
            # 지도 마커 클릭 시 상세 보기 상태로 전환
            if st.session_state.detailed_photo_id: 
                selected_photo_id = st.session_state.detailed_photo_id
                st.session_state.detailed_photo_id = None 
                st.session_state.show_detail_view = True 

            selected_photo = next((p for p in photo_markers if p['id'] == selected_photo_id), None)
            
            # --- 상세 보기 화면 (선택된 이미지) ---
            if st.session_state.show_detail_view and selected_photo:
                
                st.markdown("#### ✨ 선택된 이미지 상세")
                
                # 뒤로가기 버튼은 상단에 있으므로 생략
                st.markdown("---")
                
                # 이미지 표시 (오류 해결 반영)
                image_bytes_to_st_image(selected_photo['image_bytes'], use_container_width=True)
                
                st.markdown("---")
                
                # 📌 [수정] 위치 및 시간 정보 추가
                
                st.markdown(f"**📍 위치:** {selected_photo['km']}km 지점")
                st.markdown(f"**📅 시간:** {selected_photo['time']}")
                
                # 작가 정보
                # st.markdown("##### 👤 촬영자 정보")
                
                col_prof1, col_prof2 = st.columns([1, 3])
                with col_prof1:
                    st.markdown("", unsafe_allow_html=True) 
                with col_prof2:
                    st.markdown(f"**{selected_photo.get('photographer', '작가')}**")
                    st.caption("마라톤 전문 포토그래퍼")

                st.markdown("---")
                
                # 구매 버튼 구현 (생략)
                st.metric("가격", "5,000원", "고해상도 다운로드")
                purchase_url = "https://share.streamlit.io/simple-purchase-page" 
                st.markdown(f'<a href="{purchase_url}" target="_blank">'
                            f'<button class="purchase-btn-style">'
                            f'🛒 구매하기 (새 창 열림)'
                            f'</button></a>', unsafe_allow_html=True)


            # --- 유사 사진 목록 화면 ---
            else:
                st.markdown("#### 🖼️ 검색한 사진")
                if st.session_state.uploaded_image:
                    st.image(st.session_state.uploaded_image, width=200) 
                
                st.markdown("---")
                st.markdown("#### 🎯 유사한 사진 목록")

                # ----------------------------------------------------------------------------------
                # 📌 다운로드 새 창 연동 버튼
                # ----------------------------------------------------------------------------------
                if st.session_state.selected_for_download:
                    st.info(f"선택된 사진 {len(st.session_state.selected_for_download)}장에 대해 다운로드 페이지를 열 수 있습니다.")
                    download_url = "https://share.streamlit.io/download-selection"
                    
                    st.markdown(f'<a href="{download_url}" target="_blank">'
                                f'<button class="purchase-btn-style" style="background-color: #50e3c2;">'
                                f'⬇️ 선택된 사진 다운로드 페이지 열기 (새 창)'
                                f'</button></a>', unsafe_allow_html=True)
                else:
                    st.info("다운로드/구매를 위해 사진을 선택해주세요. (각 사진 아래 체크박스 사용)")
                
                st.markdown("---")
                
                if photo_markers:
                    
                    # 3열 바둑판식 레이아웃 생성
                    cols = st.columns(3)
                    
                    for i, photo in enumerate(photo_markers):
                        with cols[i % 3]: 
                            
                            def set_selected_photo_and_show_detail(photo_id):
                                st.session_state.selected_similar_photo_id = photo_id
                                st.session_state.show_detail_view = True 
                            
                            # 📌 체크박스 상태 업데이트 함수 (깜빡임 제거)
                            def update_download_selection(photo_id):
                                if st.session_state[f"select_list_{photo_id}"]:
                                    st.session_state.selected_for_download.add(photo_id)
                                else:
                                    st.session_state.selected_for_download.discard(photo_id)

                            # 이미지 표시 (바둑판식)
                            image_bytes_to_st_image(photo['image_bytes'], use_container_width=True) 

                            st.caption(f"📍 {photo['km']}km | 유사도: **<span style='color:red;'>{photo['similarity']:.1f}%</span>**", unsafe_allow_html=True)

                            col_view, col_select = st.columns([1, 4])

                            with col_view:
                                # '보기' 버튼 (상세 보기 전환)
                                if st.button("보기", key=f"list_btn_{photo['id']}", help="클릭 시 상세 화면으로 이동", type="secondary", use_container_width=True):
                                    set_selected_photo_and_show_detail(photo['id'])
                                    st.rerun()

                            with col_select:
                                # 체크박스 (선택 기능)
                                st.checkbox(
                                    "저장 목록에 추가",
                                    value=photo['id'] in st.session_state.selected_for_download,
                                    key=f"select_list_{photo['id']}",
                                    on_change=update_download_selection,
                                    args=(photo['id'],)
                                )

                else:
                    st.info("검색 결과를 찾을 수 없습니다.")