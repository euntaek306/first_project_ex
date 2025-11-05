"""
마라톤 사진 검색 플랫폼 - 지도 마커 클릭 시 같은 위치 사진을 유사도 순으로 전부 표시
"""

import streamlit as st
from PIL import Image, ExifTags
import gpxpy
import folium
from streamlit_folium import st_folium
import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import io
from datetime import datetime
import base64
import uuid
from collections import defaultdict
import math

# ==================================================
# Streamlit 설정
# ==================================================
st.set_page_config(layout="wide")
st.markdown("""
<style>
    div.stImage > button { display: none !important; }
    .purchase-btn-style {
        background-color: #e35050; color: white; border: none; 
        padding: 10px; border-radius: 5px; width: 100%; 
        font-weight: bold; cursor: pointer; height: 50px;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# EXIF 파싱
# ==================================================
def extract_exif_data(image):
    try:
        exif_data = {}
        raw_exif = image._getexif()
        if raw_exif:
            for tag, value in raw_exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                exif_data[decoded] = value
        return exif_data
    except:
        return {}

def safe_parse_time(exif_data):
    try:
        time_str = exif_data.get("DateTime", None)
        if time_str:
            return datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")
    except:
        pass
    return datetime.now()

# ==================================================
# GPX 로드
# ==================================================
def load_gpx_coords(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        coords = []
        for track in gpx.tracks:
            for seg in track.segments:
                for point in seg.points:
                    coords.append((point.latitude, point.longitude))
        return coords
    except:
        return None

# ==================================================
# CLIP 모델
# ==================================================
@st.cache_resource
def load_clip_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.to(device)
    return model, processor, device

def get_image_embedding(image, model, processor, device):
    inputs = processor(images=image.convert("RGB"), return_tensors="pt").to(device)
    with torch.no_grad():
        emb = model.get_image_features(**inputs)
    return emb.cpu().numpy()

# ==================================================
# 지도 생성 (개별 마커)
# ==================================================
def create_course_map_with_individual_photos(coords, photos):
    if not coords:
        return None
    
    center = [sum(c[0] for c in coords) / len(coords), 
              sum(c[1] for c in coords) / len(coords)]
    
    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")
    folium.PolyLine(coords, color="#FF4444", weight=4).add_to(m)
    
    location_counter = defaultdict(int)
    
    for photo in photos:
        lat, lon = photo['lat'], photo['lon']
        similarity = photo['similarity']
        
        location_key = (round(lat, 5), round(lon, 5))  # 정밀도 5자리로 조정
        offset_index = location_counter[location_key]
        location_counter[location_key] += 1
        
        angle = (360 / 6) * offset_index
        radius = 0.00022
        lat_offset = radius * math.cos(math.radians(angle))
        lon_offset = radius * math.sin(math.radians(angle))
        
        display_lat = lat + lat_offset
        display_lon = lon + lon_offset
        
        # 유사도별 마커 스타일
        if similarity >= 90:
            size = 65; border = '#FF0000'; color = 'red'
        elif similarity >= 80:
            size = 55; border = '#FF6B00'; color = 'orange'
        else:
            size = 45; border = '#4a90e2'; color = 'blue'
        
        # 마커 클릭 시 Streamlit 세션 상태 업데이트
        icon_html = f"""
        <div style="
            width: {size}px; height: {size}px;
            border-radius: 10px;
            border: 4px solid {border};
            background-image: url('data:image/jpeg;base64,{photo['thumb']}');
            background-size: cover;
            background-position: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            cursor: pointer;
        " onclick="window.parent.postMessage({{
            type: 'streamlit:setSessionState',
            key: 'clicked_photo_id',
            value: '{photo['id']}'
        }}, '*'); window.parent.postMessage({{type: 'streamlit:rerun'}}, '*')">
        </div>
        """
        
        tooltip_html = f"""
        <div style='text-align:center; font-family: sans-serif;'>
            <b>사진: {photo['name']}</b><br>
            <span style='color:{color}; font-weight:bold;'>
                유사도: {similarity:.1f}%
            </span><br>
            <small><b>클릭 → 같은 위치 사진 전부 보기</b></small>
        </div>
        """
        
        custom_icon = folium.DivIcon(
            icon_size=(size, size),
            icon_anchor=(size//2, size//2),
            html=icon_html
        )
        
        folium.Marker(
            [display_lat, display_lon],
            icon=custom_icon,
            tooltip=folium.Tooltip(tooltip_html, sticky=True)
        ).add_to(m)
    
    return m

# ==================================================
# 세션 초기화
# ==================================================
def init_session():
    defaults = {
        "photos": [], "show_results": False, "show_detail_view": False,
        "selected_photo_id": None, "uploaded_image": None,
        "selected_tournament": None, "clicked_photo_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ==================================================
# 대회 정보
# ==================================================
tournaments = {
    "JTBC 마라톤": "data/2025_JTBC.gpx",
    "춘천 마라톤": "data/chuncheon_marathon.gpx",
}

# ==================================================
# 메인
# ==================================================
mode = st.sidebar.radio("모드 선택", ["작가 모드", "이용자 모드"], 
                        label_visibility="collapsed")
model, processor, device = load_clip_model()

# ==================================================
# 작가 모드 (변경 없음)
# ==================================================
if mode == "작가 모드":
    st.title("작가 모드: 사진 등록")
    col_info, col_map = st.columns([1, 1])
    
    with col_info:
        tournament = st.selectbox("1️⃣ 대회 선택", list(tournaments.keys()))
        st.markdown("---")
        st.markdown("2️⃣ **위치 지정:** 지도에서 사진 촬영 지점을 클릭하세요.")
        
        latlon = None
        if st.session_state.get("last_clicked_lat"):
            latlon = (
                st.session_state["last_clicked_lat"],
                st.session_state["last_clicked_lng"]
            )
            st.info(f"✅ 위도 {latlon[0]:.5f}, 경도 {latlon[1]:.5f}")
        else:
            st.warning("⚠️ 지도에서 위치를 클릭해주세요.")
    
    with col_map:
        coords = load_gpx_coords(tournaments[tournament])
        if not coords:
            st.error("❌ GPX 파일을 불러올 수 없습니다.")
            st.stop()
        
        m = folium.Map(location=coords[0], zoom_start=13)
        folium.PolyLine(coords, color="blue", weight=3).add_to(m)
        
        if latlon:
            folium.Marker(latlon, icon=folium.Icon(color='red', icon='camera', 
                                                   prefix='fa')).add_to(m)
        
        map_data = st_folium(m, width=700, height=500, key="photographer_map")
        
        if map_data.get("last_clicked"):
            st.session_state["last_clicked_lat"] = map_data["last_clicked"]["lat"]
            st.session_state["last_clicked_lng"] = map_data["last_clicked"]["lng"]
            st.rerun()
    
    st.markdown("---")
    
    uploaded = st.file_uploader("3️⃣ 사진 업로드", type=["jpg", "jpeg", "png"], 
                                accept_multiple_files=True)
    
    if uploaded and latlon:
        if st.button(f"💾 {len(uploaded)}장 DB에 저장하기", type="primary"):
            progress_bar = st.progress(0, text="AI 처리 중...")
            
            for idx, f in enumerate(uploaded):
                img = Image.open(f).convert("RGB")
                exif = extract_exif_data(img)
                photo_time = safe_parse_time(exif)
                
                emb = get_image_embedding(img, model, processor, device)
                
                thumb = img.copy()
                thumb.thumbnail((150, 150))
                buf_thumb = io.BytesIO()
                thumb.save(buf_thumb, format="JPEG", quality=70)
                thumb_b64 = base64.b64encode(buf_thumb.getvalue()).decode()
                
                buf_full = io.BytesIO()
                img.save(buf_full, format="JPEG", quality=90)
                full_bytes = buf_full.getvalue()
                
                st.session_state["photos"].append({
                    "id": uuid.uuid4().hex,
                    "name": f.name,
                    "lat": latlon[0],
                    "lon": latlon[1],
                    "tournament": tournament,
                    "time": photo_time,
                    "embedding": emb,
                    "thumb": thumb_b64,
                    "bytes": full_bytes,
                })
                progress_bar.progress((idx + 1) / len(uploaded))
            
            st.success(f"🎉 {len(uploaded)}장 업로드 완료!")
            progress_bar.empty()
            st.balloons()
            st.session_state["last_clicked_lat"] = None
            st.session_state["last_clicked_lng"] = None
            st.rerun()

# ==================================================
# 이용자 모드 - 핵심 수정
# ==================================================
else:
    if not st.session_state["show_results"]:
        st.title("High 러너스")
        st.caption("AI가 당신의 마라톤 사진을 찾아드립니다")
        st.markdown("---")
        
        selected = st.selectbox("1️⃣ 대회 선택", ["대회를 선택해주세요"] + list(tournaments.keys()))
        
        if selected != "대회를 선택해주세요":
            st.session_state["selected_tournament"] = selected
            uploaded_file = st.file_uploader("2️⃣ 본인 사진 업로드", type=["png", "jpg", "jpeg"])
            
            if uploaded_file and st.button("유사 사진 찾기", type="primary"):
                st.session_state["uploaded_image"] = Image.open(uploaded_file).convert("RGB")
                st.session_state["show_results"] = True
                st.session_state["clicked_photo_id"] = None
                st.rerun()
            elif uploaded_file:
                st.image(uploaded_file, width=220)

    else:
        tournament_name = st.session_state["selected_tournament"]
        coords = load_gpx_coords(tournaments[tournament_name])
        
        # 헤더
        col1, col2 = st.columns([1, 9])
        with col1:
            if st.session_state["clicked_photo_id"]:
                if st.button("지도로", type="secondary"):
                    st.session_state["clicked_photo_id"] = None
                    st.rerun()
            else:
                if st.button("처음으로", type="secondary"):
                    st.session_state["show_results"] = False
                    st.session_state["uploaded_image"] = None
                    st.session_state["selected_tournament"] = None
                    st.rerun()
        with col2:
            st.markdown(f"<h2 style='text-align:center'>🏁 {tournament_name}</h2>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 유사도 계산
        query_emb = get_image_embedding(st.session_state["uploaded_image"], model, processor, device)
        similar_photos = []
        for p in st.session_state["photos"]:
            if p["tournament"] != tournament_name:
                continue
            sim = cosine_similarity(query_emb, p["embedding"])[0][0] * 100
            if sim >= 70:
                p["similarity"] = sim
                similar_photos.append(p)
        
        similar_photos.sort(key=lambda x: x["similarity"], reverse=True)
        
        map_col, content_col = st.columns([5, 5])
        
        # === 지도 ===
        with map_col:
            st.markdown("### 마라톤 코스")
            if not similar_photos:
                st.warning("유사한 사진을 찾지 못했습니다.")
            else:
                st.success(f"총 {len(similar_photos)}장 발견! (📸 클릭하여 같은 위치 사진 보기)")
                # 동적 키로 캐싱 문제 방지
                map_key = f"user_map_{uuid.uuid4().hex}"
                m = create_course_map_with_individual_photos(coords, similar_photos)
                map_data = st_folium(m, width=900, height=580, key=map_key)
                
                # 디버깅: 클릭 이벤트 확인
                st.write(f"현재 clicked_photo_id: {st.session_state['clicked_photo_id']}")
        
        # === 오른쪽 콘텐츠 ===
        with content_col:
            st.markdown("#### 검색한 사진")
            st.image(st.session_state["uploaded_image"], width=230)
            st.markdown("---")
            
            # 아직 클릭 안 했을 때
            if not st.session_state["clicked_photo_id"]:
                st.info("""
                왼쪽 지도에서 **사진 마커**를 클릭하세요!  
                → **같은 위치에 있는 사진 전부**가  
                **유사도 높은 순**으로 여기 나타납니다!
                """)
            # 클릭했을 때
            else:
                clicked_photo = next((p for p in similar_photos 
                                     if p['id'] == st.session_state["clicked_photo_id"]), None)
                
                if clicked_photo:
                    # 같은 위치 사진들 추출 (정밀도 5자리로 통일)
                    same_loc = [
                        p for p in similar_photos
                        if round(p['lat'], 5) == round(clicked_photo['lat'], 5) and
                           round(p['lon'], 5) == round(clicked_photo['lon'], 5)
                    ]
                    
                    # 디버깅: 필터링된 사진 정보
                    st.write(f"디버깅: 클릭한 사진 위치 - 위도 {clicked_photo['lat']:.5f}, 경도 {clicked_photo['lon']:.5f}")
                    st.write(f"디버깅: 같은 위치 사진 {len(same_loc)}장 발견")
                    
                    # 유사도 높은 순 정렬
                    same_loc.sort(key=lambda x: x["similarity"], reverse=True)
                    
                    if not same_loc:
                        st.warning("이 위치에 사진이 없습니다. 다른 마커를 클릭해 보세요.")
                    else:
                        st.markdown(f"""
                        #### 같은 위치 사진 **{len(same_loc)}장**  
                        <small>위도 {clicked_photo['lat']:.5f} | 경도 {clicked_photo['lon']:.5f}</small>
                        """, unsafe_allow_html=True)
                        st.markdown("---")
                        
                        # 3열로 표시
                        cols = st.columns(3)
                        for idx, photo in enumerate(same_loc):
                            with cols[idx % 3]:
                                st.image(io.BytesIO(photo["bytes"]), use_container_width=True)
                                st.caption(f"**{photo['similarity']:.1f}%** | {photo['name']}")
                                
                                if st.button("원본 보기", key=f"view_{photo['id']}"):
                                    st.session_state["selected_photo_id"] = photo["id"]
                                    st.session_state["show_detail_view"] = True
                                    st.rerun()
                else:
                    st.error(f"클릭한 사진(ID: {st.session_state['clicked_photo_id']})을 찾을 수 없습니다.")