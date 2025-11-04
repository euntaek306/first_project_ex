"""
마라톤 사진 검색 플랫폼 - 최종 완성 버전
지도 위 사진 배치 + 구매 기능 + 개선된 UI
"""

import streamlit as st
from PIL import Image
import streamlit.components.v1 as components

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
# CSS 스타일
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
    
    /* 작은 버튼 (뒤로가기용) */
    div[data-testid="column"] > div > div > button[kind="secondary"] {
        font-size: 14px !important;
        padding: 8px 16px !important;
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
    
    h1 {
        color: #2c3e50;
        text-align: center;
        font-size: 48px;
        margin-bottom: 30px;
    }
    
    h2, h3 {
        color: #4a90e2;
    }
    
    /* 지도 위 사진 썸네일 */
    .photo-thumbnail {
        position: absolute;
        width: 80px;
        height: 80px;
        border: 3px solid #4a90e2;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        overflow: hidden;
        background: white;
    }
    
    .photo-thumbnail:hover {
        transform: scale(1.2);
        border-color: #50e3c2;
        box-shadow: 0 4px 16px rgba(74, 144, 226, 0.6);
        z-index: 100;
    }
    
    .photo-thumbnail img {
        width: 100%;
        height: 100%;
        object-fit: cover;
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
    "서울 국제 마라톤": {
        "date": "2024년 3월 17일",
        "distance": "42.195km",
        "participants": "30,000명",
        "course": "잠실종합운동장 → 광화문 → 남산 → 한강 → 잠실",
        "icon": "🏃‍♂️",
        "color": "#FF6B6B"
    },
    "춘천 마라톤": {
        "date": "2024년 10월 20일",
        "distance": "42.195km",
        "participants": "15,000명",
        "course": "의암호 → 소양강 → 춘천시가지 → 의암호",
        "icon": "🏔️",
        "color": "#4ECDC4"
    },
    "제주 국제 마라톤": {
        "date": "2024년 11월 5일",
        "distance": "42.195km",
        "participants": "12,000명",
        "course": "제주시 → 애월 → 한림 → 제주시",
        "icon": "🌊",
        "color": "#45B7D1"
    },
    "부산 국제 마라톤": {
        "date": "2024년 4월 14일",
        "distance": "42.195km",
        "participants": "25,000명",
        "course": "광안리 → 해운대 → 마린시티 → 광안리",
        "icon": "🌉",
        "color": "#FFA07A"
    }
}

# ==========================================
# 추천 사진 데이터
# ==========================================
recommended_photos = [
    {
        "id": 1,
        "km": 5.2,
        "similarity": 95,
        "position": {"left": "15%", "top": "20%"},
        "time": "2024-10-20 09:15:32",
        "photographer": "김러너",
        "photographer_id": "runner_kim",
        "price": 5000,
    },
    {
        "id": 2,
        "km": 12.8,
        "similarity": 92,
        "position": {"left": "30%", "top": "35%"},
        "time": "2024-10-20 09:42:18",
        "photographer": "박마라톤",
        "photographer_id": "marathon_park",
        "price": 5000,
    },
    {
        "id": 3,
        "km": 18.5,
        "similarity": 89,
        "position": {"left": "50%", "top": "25%"},
        "time": "2024-10-20 10:08:45",
        "photographer": "이달리기",
        "photographer_id": "runner_lee",
        "price": 5000,
    },
    {
        "id": 4,
        "km": 25.3,
        "similarity": 87,
        "position": {"left": "65%", "top": "40%"},
        "time": "2024-10-20 10:35:22",
        "photographer": "최완주",
        "photographer_id": "finisher_choi",
        "price": 5000,
    },
    {
        "id": 5,
        "km": 35.7,
        "similarity": 84,
        "position": {"left": "80%", "top": "30%"},
        "time": "2024-10-20 11:12:08",
        "photographer": "정스프린터",
        "photographer_id": "sprint_jung",
        "price": 5000,
    },
    {
        "id": 6,
        "km": 8.9,
        "similarity": 91,
        "position": {"left": "22%", "top": "50%"},
        "time": "2024-10-20 09:28:15",
        "photographer": "홍체력",
        "photographer_id": "stamina_hong",
        "price": 5000,
    }
]

# ==========================================
# 헬퍼 함수
# ==========================================
def select_photo(photo_id):
    """사진 선택 처리"""
    for photo in recommended_photos:
        if photo['id'] == photo_id:
            st.session_state.selected_photo = photo
            break

def purchase_photo(photo_id):
    """사진 구매 처리"""
    if photo_id not in st.session_state.purchased_photos:
        st.session_state.purchased_photos.append(photo_id)
        return True
    return False

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
    
    # 헤더 (뒤로가기 버튼 포함)
    header_col1, header_col2, header_col3 = st.columns([1, 8, 1])
    
    with header_col1:
        if st.button("◀️ 처음으로", key="back_button", type="secondary"):
            st.session_state.show_results = False
            st.session_state.selected_tournament = None
            st.session_state.uploaded_image = None
            st.session_state.selected_photo = None
            st.rerun()
    
    with header_col2:
        st.markdown(f"""
        <div style='text-align: center; padding: 10px;'>
            <h1 style='margin: 0; font-size: 36px;'>{tournament_info['icon']} {tournament_name}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 좌우 분할
    left_col, right_col = st.columns([6.5, 3.5])
    
    # ==========================================
    # 왼쪽: 코스 지도 (사진 배치)
    # ==========================================
    with left_col:
        st.markdown("### 🗺️ 마라톤 코스")
        
        # 대회 정보
        st.markdown(f"""
        <div class="info-card">
            <p style='margin: 0; line-height: 1.4;'>
                📅 <b>일시:</b> {tournament_info['date']}<br>
                📏 <b>거리:</b> {tournament_info['distance']}<br>
                📍 <b>코스:</b> {tournament_info['course']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 지도 + 작은 사진들 배치 (HTML/JS 사용)
        photo_thumbnails_html = ""
        for photo in recommended_photos:
            photo_thumbnails_html += f"""
            <div class="photo-thumbnail" 
                 style="left: {photo['position']['left']}; top: {photo['position']['top']};"
                 onclick="selectPhoto({photo['id']})">
                <div style='width: 100%; height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; font-size: 32px;'>
                    🏃
                </div>
                <div style='position: absolute; bottom: 2px; right: 2px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;'>
                    {photo['similarity']}%
                </div>
            </div>
            """
        
        # JavaScript로 사진 선택 처리
        js_code = """
        <script>
        function selectPhoto(photoId) {
            // Streamlit과 통신하기 위해 쿼리 파라미터 사용
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: photoId
            }, '*');
        }
        </script>
        """
        
        # 지도 렌더링
        components.html(f"""
        <div style='position: relative; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                    border-radius: 12px; height: 500px; border: 2px solid #e0e7ff; overflow: hidden;'>
            
            <!-- 코스 라인 -->
            <svg style='position: absolute; width: 100%; height: 100%; z-index: 1;'>
                <path d='M 50 250 Q 200 100, 400 200 T 800 250' 
                      stroke='#4a90e2' 
                      stroke-width='4' 
                      fill='none' 
                      opacity='0.6'/>
            </svg>
            
            <!-- 출발점 -->
            <div style='position: absolute; left: 3%; top: 47%; width: 50px; height: 50px; 
                        background: #4CAF50; border-radius: 50%; border: 3px solid white;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 24px; z-index: 5; box-shadow: 0 2px 8px rgba(0,0,0,0.3);'>
                🏁
            </div>
            
            <!-- 도착점 -->
            <div style='position: absolute; left: 92%; top: 47%; width: 50px; height: 50px; 
                        background: #FF5252; border-radius: 50%; border: 3px solid white;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 24px; z-index: 5; box-shadow: 0 2px 8px rgba(0,0,0,0.3);'>
                🎯
            </div>
            
            <!-- 추천 사진 썸네일들 -->
            {photo_thumbnails_html}
            
            <!-- 안내 문구 -->
            <div style='position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                        background: rgba(255,255,255,0.9); padding: 10px 20px; border-radius: 20px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2); z-index: 10;'>
                
                </p>
            </div>
        </div>
        {js_code}
        """, height=550)
        
        # 스트림릿 버튼으로도 선택 가능 (대체 방법)
        st.markdown("---")
        st.markdown("#### 📸 추천 사진 목록 (클릭하여 선택)")
        cols = st.columns(3)
        for idx, photo in enumerate(recommended_photos):
            col = cols[idx % 3]
            with col:
                if st.button(
                    f"📍 {photo['km']}km\n유사도: {photo['similarity']}%",
                    key=f"photo_btn_{photo['id']}",
                    use_container_width=True
                ):
                    select_photo(photo['id'])
                    st.rerun()
    
    # ==========================================
    # 오른쪽: 선택된 사진 상세
    # ==========================================
    with right_col:
      
        # 선택된 사진 표시
        if st.session_state.selected_photo:
            photo = st.session_state.selected_photo
            
            st.markdown("#### 📍 선택한 사진")
            
            # 사진 (플레이스홀더)
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        height: 300px; 
                        border-radius: 12px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        margin-bottom: 15px;
                        position: relative;'>
                <span style='font-size: 80px;'>🏃</span>
                <div style='position: absolute; top: 10px; right: 10px; 
                            background: rgba(74, 144, 226, 0.9); 
                            color: white; padding: 5px 12px; border-radius: 20px;
                            font-weight: bold; font-size: 14px;'>
                    유사도: {photo['similarity']}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 정보 카드
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
            
            # 구매 버튼 (인스타 스타일)
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
            st.info("👈 지도 위의 사진을 클릭해보세요!")
            st.markdown("""
            <div style='text-align: center; padding: 40px 20px; color: #999;'>
                <div style='font-size: 64px; margin-bottom: 15px;'>📸</div>
                <p>지도에서 사진을 선택하면<br>상세 정보를 확인할 수 있습니다</p>
            </div>
            """, unsafe_allow_html=True)

# 푸터
st.caption("💡 Tip: 정확한 검색을 위해 선명한 사진을 업로드해주세요")