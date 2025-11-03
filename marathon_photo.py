"""
마라톤 사진 검색 플랫폼 - UI/UX 프로토타입
이용자가 대회를 선택하고 사진을 업로드하면 코스 위에 유사한 사진을 추천
"""

import streamlit as st
from PIL import Image

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="마라톤 사진 검색",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS 스타일
# ==========================================
st.markdown("""
<style>
    /* 전체 배경 */
    .main {
        background-color: #f8f9fa;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 2px solid #e9ecef;
    }
    
    /* 대회 선택 버튼 스타일 */
    .tournament-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #e9ecef;
        margin-bottom: 15px;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .tournament-card:hover {
        border-color: #4CAF50;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
        transform: translateY(-2px);
    }
    
    .tournament-card.active {
        border-color: #4CAF50;
        background: #f1f8f4;
    }
    
    /* 코스 지도 영역 */
    .course-map {
        background: white;
        border-radius: 12px;
        padding: 20px;
        min-height: 600px;
        border: 2px solid #e9ecef;
    }
    
    /* 업로드 영역 */
    .upload-area {
        background: white;
        border-radius: 12px;
        padding: 30px;
        border: 3px dashed #dee2e6;
        text-align: center;
        min-height: 300px;
        transition: all 0.3s;
    }
    
    .upload-area:hover {
        border-color: #4CAF50;
        background: #f8fff9;
    }
    
    /* 사진 핀 스타일 */
    .photo-pin {
        background: white;
        border: 3px solid #4CAF50;
        border-radius: 12px;
        padding: 10px;
        margin: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .photo-pin:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    
    /* 헤더 */
    h1 {
        color: #2c3e50;
        font-weight: 700;
    }
    
    h2, h3 {
        color: #34495e;
    }
    
    /* 버튼 */
    .stButton>button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 세션 스테이트 초기화
# ==========================================
if 'selected_tournament' not in st.session_state:
    st.session_state.selected_tournament = None

if 'uploaded_photo' not in st.session_state:
    st.session_state.uploaded_photo = None

if 'show_recommendations' not in st.session_state:
    st.session_state.show_recommendations = False

# ==========================================
# 대회 데이터 (예시)
# ==========================================
tournaments = {
    "서울 국제 마라톤": {
        "date": "2024년 3월 17일",
        "distance": "42.195km",
        "participants": "30,000명",
        "course": "잠실종합운동장 → 광화문 → 남산 → 한강 → 잠실",
        "icon": "🏃‍♂️"
    },
    "춘천 마라톤": {
        "date": "2024년 10월 20일",
        "distance": "42.195km",
        "participants": "15,000명",
        "course": "의암호 → 소양강 → 춘천시가지 → 의암호",
        "icon": "🏔️"
    },
    "제주 국제 마라톤": {
        "date": "2024년 11월 5일",
        "distance": "42.195km",
        "participants": "12,000명",
        "course": "제주시 → 애월 → 한림 → 제주시",
        "icon": "🌊"
    },
    "부산 국제 마라톤": {
        "date": "2024년 4월 14일",
        "distance": "42.195km",
        "participants": "25,000명",
        "course": "광안리 → 해운대 → 마린시티 → 광안리",
        "icon": "🌉"
    }
}

# ==========================================
# 사이드바: 대회 선택
# ==========================================
with st.sidebar:
    st.title("🏃‍♂️ 대회 선택")
    st.markdown("참가한 마라톤 대회를 선택하세요")
    st.markdown("---")
    
    for tournament_name, info in tournaments.items():
        # 대회 카드 생성
        is_selected = st.session_state.selected_tournament == tournament_name
        
        if st.button(
            f"{info['icon']} {tournament_name}",
            key=tournament_name,
            use_container_width=True,
            type="primary" if is_selected else "secondary"
        ):
            st.session_state.selected_tournament = tournament_name
            st.session_state.show_recommendations = False
            st.rerun()
        
        if is_selected:
            st.markdown(f"""
            <div style='background: #f1f8f4; padding: 10px; border-radius: 8px; margin-bottom: 15px;'>
                <small>
                📅 <b>일시:</b> {info['date']}<br>
                📏 <b>거리:</b> {info['distance']}<br>
                👥 <b>참가자:</b> {info['participants']}
                </small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("💡 대회를 선택하면 코스 지도가 표시됩니다")

# ==========================================
# 메인 화면: 좌우 분할
# ==========================================

# 헤더
st.title("🏃‍♂️ 마라톤 사진 검색 플랫폼")
st.caption("AI가 당신의 마라톤 사진을 코스 위에서 찾아드립니다")
st.markdown("---")

# 좌우 분할 (6:4 비율)
left_col, right_col = st.columns([6, 4])

# ==========================================
# 왼쪽: 코스 지도 + 추천 사진
# ==========================================
with left_col:
    st.markdown("### 🗺️ 마라톤 코스")
    
    if st.session_state.selected_tournament:
        selected_info = tournaments[st.session_state.selected_tournament]
        
        # 대회 정보 헤더
        st.info(f"""
        **{selected_info['icon']} {st.session_state.selected_tournament}**  
        📍 코스: {selected_info['course']}
        """)
        
        # 코스 지도 영역 (실제로는 지도 API 사용)
        st.markdown("""
        <div class="course-map">
            <div style='text-align: center; padding: 50px 0;'>
                <h2 style='color: #95a5a6; margin-bottom: 20px;'>🗺️</h2>
                <h3 style='color: #95a5a6;'>코스 지도 영역</h3>
                <p style='color: #bdc3c7;'>(실제 구현시 Google Maps API 또는 Folium 사용)</p>
                <br><br>
                <div style='display: flex; justify-content: space-around; margin-top: 40px;'>
                    <div style='text-align: center;'>
                        <div style='width: 60px; height: 60px; background: #e8f5e9; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px;'>
                            🏁
                        </div>
                        <p style='margin-top: 10px; color: #666;'>출발점</p>
                    </div>
                    <div style='text-align: center;'>
                        <div style='width: 60px; height: 60px; background: #fff3e0; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px;'>
                            📸
                        </div>
                        <p style='margin-top: 10px; color: #666;'>중간 지점</p>
                    </div>
                    <div style='text-align: center;'>
                        <div style='width: 60px; height: 60px; background: #fce4ec; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px;'>
                            🎯
                        </div>
                        <p style='margin-top: 10px; color: #666;'>도착점</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 추천 사진이 있을 때
        if st.session_state.show_recommendations:
            st.markdown("---")
            st.markdown("#### 📍 코스 상 유사한 사진들")
            st.success("✨ AI가 찾은 유사한 사진 5장")
            
            # 추천 사진 표시 (3개씩)
            rec_cols = st.columns(3)
            
            for i in range(5):
                col = rec_cols[i % 3]
                with col:
                    st.markdown(f"""
                    <div class="photo-pin">
                        <div style='background: #f0f0f0; height: 150px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px;'>
                            <span style='font-size: 48px;'>🖼️</span>
                        </div>
                        <p style='margin: 0; font-size: 14px; color: #666;'>
                            <b>📍 {i*8 + 5}km 지점</b><br>
                            유사도: {95 - i*3}%
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        # 대회 미선택 시
        st.info("👈 왼쪽 사이드바에서 대회를 선택하세요")
        st.markdown("""
        <div style='text-align: center; padding: 100px 50px; color: #95a5a6;'>
            <h1 style='font-size: 80px; margin-bottom: 20px;'>🏃‍♂️</h1>
            <h2>마라톤 대회를 선택해주세요</h2>
            <p>대회를 선택하면 코스 지도가 표시됩니다</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 오른쪽: 사진 업로드
# ==========================================
with right_col:
    st.markdown("### 📤 내 사진 업로드")
    
    if st.session_state.selected_tournament:
        st.info("📸 마라톤 사진을 업로드하면 AI가 비슷한 사진을 찾아드립니다")
        
        # 파일 업로드
        uploaded_file = st.file_uploader(
            "사진을 선택하세요",
            type=['png', 'jpg', 'jpeg'],
            key="user_photo_upload",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            # 업로드된 사진 미리보기
            st.markdown("#### 🖼️ 업로드한 사진")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True, caption=uploaded_file.name)
            
            st.markdown("---")
            
            # 검색 옵션
            st.markdown("#### ⚙️ 검색 옵션")
            
            # 코스 구간 선택
            course_section = st.selectbox(
                "📍 코스 구간 (선택사항)",
                ["전체 코스", "0-10km", "10-20km", "20-30km", "30-42km"]
            )
            
            # 유사도 임계값
            similarity = st.slider(
                "🎯 최소 유사도",
                min_value=70,
                max_value=100,
                value=85,
                help="높을수록 더 비슷한 사진만 표시됩니다"
            )
            
            st.markdown("---")
            
            # 검색 버튼
            if st.button("🔍 유사 사진 검색", type="primary", use_container_width=True):
                with st.spinner("🤖 AI가 코스 위에서 유사한 사진을 찾고 있습니다..."):
                    import time
                    time.sleep(2)  # 시뮬레이션
                    st.session_state.uploaded_photo = image
                    st.session_state.show_recommendations = True
                    st.success("✅ 5장의 유사한 사진을 찾았습니다!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
        else:
            # 업로드 전 안내
            st.markdown("""
            <div class="upload-area">
                <div style='padding: 50px 20px;'>
                    <div style='font-size: 64px; margin-bottom: 20px;'>📤</div>
                    <h3 style='color: #666; margin-bottom: 10px;'>사진을 업로드하세요</h3>
                    <p style='color: #999;'>JPG, PNG 형식 지원</p>
                    <br>
                    <small style='color: #bbb;'>위 버튼을 클릭하여 파일을 선택하세요</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        # 대회 미선택 시
        st.warning("⚠️ 먼저 대회를 선택해주세요")
        st.markdown("""
        <div style='text-align: center; padding: 50px 20px; color: #95a5a6;'>
            <div style='font-size: 48px; margin-bottom: 20px;'>🏃‍♂️</div>
            <p>대회를 먼저 선택하면<br>사진을 업로드할 수 있습니다</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 하단 안내
# ==========================================
st.markdown("---")
st.markdown("""
<div style='background: white; padding: 20px; border-radius: 12px; text-align: center;'>
    <h4 style='color: #2c3e50; margin-bottom: 15px;'>💡 사용 방법</h4>
    <div style='display: flex; justify-content: space-around; text-align: center;'>
        <div style='flex: 1;'>
            <div style='font-size: 36px; margin-bottom: 10px;'>1️⃣</div>
            <p style='color: #666;'><b>대회 선택</b><br>사이드바에서 참가한 대회 클릭</p>
        </div>
        <div style='flex: 1;'>
            <div style='font-size: 36px; margin-bottom: 10px;'>2️⃣</div>
            <p style='color: #666;'><b>사진 업로드</b><br>오른쪽에서 마라톤 사진 업로드</p>
        </div>
        <div style='flex: 1;'>
            <div style='font-size: 36px; margin-bottom: 10px;'>3️⃣</div>
            <p style='color: #666;'><b>검색 실행</b><br>AI가 코스 위에서 유사한 사진 찾기</p>
        </div>
        <div style='flex: 1;'>
            <div style='font-size: 36px; margin-bottom: 10px;'>4️⃣</div>
            <p style='color: #666;'><b>결과 확인</b><br>왼쪽 지도에서 추천 사진 보기</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)