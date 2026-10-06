from datetime import datetime
from time import sleep
from zoneinfo import ZoneInfo

import api_client as api
import httpx
import streamlit as st

tz_seoul = ZoneInfo("Asia/Seoul")

if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "editing_movie_id" not in st.session_state:
    st.session_state.editing_movie_id = None


st.title("🎞️ AI 영화 리뷰 API")


ITEMS_PER_PAGE = 5


@st.cache_data
def get_year():
    return datetime.now(tz_seoul).year


@st.cache_data(ttl=60)
def get_total_pages():
    return api.get_total_pages(ITEMS_PER_PAGE)


total_pages = get_total_pages()

current_page = st.pagination(
    num_pages=total_pages, default=st.session_state.get("current_page", 1)
)


@st.cache_data(ttl=60)
def fetch_movies(page: int):
    return api.fetch_movies(page=page, limit=ITEMS_PER_PAGE)


page_items = fetch_movies(page=current_page)

if page_items:
    start_idx = (current_page - 1) * ITEMS_PER_PAGE + 1
    end_idx = start_idx + len(page_items) - 1
    st.markdown(
        f"**📄 현재 {current_page} 페이지 ({start_idx}~{end_idx}번째 영화 표시 중)**"
    )

for movie in page_items:
    movie_id = movie.get("id")
    is_editing = st.session_state.editing_movie_id == movie_id

    with st.expander(
        f"{movie.get('title', 'No title')} - {movie.get('year', 'unknown')} - {movie.get('genre', 'not classify')} - {'⭐️' * movie.get('rating', 'not rated')}",
        expanded=is_editing,
    ):
        if is_editing:
            # [수정 모드]
            with st.form(key=f"edit_form_{movie_id}"):
                col_info, col_button = st.columns([3, 1])

                with col_info:
                    new_title = st.text_input("제목", value=movie.get("title"))
                    new_year = st.text_input("개봉 연도", value=movie.get("year"))
                    new_director = st.text_input("감독", value=movie.get("director"))
                    new_genre = st.text_input("장르", value=movie.get("genre"))
                    new_poster = st.text_input("포스터 URL", value=movie.get("poster"))

                with col_button:
                    submit_btn = st.form_submit_button(
                        "💾 저장", use_container_width=True
                    )
                    cancel_btn = st.form_submit_button(
                        "❌ 취소", use_container_width=True
                    )

                    if submit_btn:
                        result = api.modify_movie(
                            id=movie_id,
                            title=new_title,
                            director=new_director,
                            genre=new_genre,
                            year=new_year,
                            poster=new_poster,
                        )
                        st.session_state.editing_movie_id = None
                        st.toast(f"성공적으로 수정되었습니다! {result}")
                        fetch_movies.clear()
                        sleep(0.3)
                        st.rerun()

                    if cancel_btn:
                        st.session_state.editing_movie_id = None
                        st.rerun()
        else:
            # [일반 조회 모드] 폼 없이 일반 컬럼과 일반 버튼으로만 구성합니다.
            col_info, col_button = st.columns([4, 1])

            with col_info:
                col_thumbnail, col_detail = st.columns([1, 2])
                with col_thumbnail:
                    st.image(movie.get("poster", "None"))
                with col_detail:
                    st.subheader(movie.get("title", "제목 없음"))
                    st.write(movie.get("year", "년도 미상"))
                    st.caption(f"감독: {movie.get('director', '-')}")
                    genres = movie.get("genre").split(",")
                    badge_markdown = " ".join([
                        f":blue-badge[{g.strip()}]" for g in genres
                    ])
                    rating = movie.get("rating", None)
                    if rating:
                        st.markdown(badge_markdown)
                        stars = "⭐️" * rating
                        st.markdown(
                            f":orange[{stars}] **({movie.get('vote_count', '~')})**"
                        )

            with col_button:
                st.write("")  # 수직 정렬 여백

                if st.session_state.editing_movie_id is None:
                    if st.button(
                        "✏️ 수정", key=f"edit_btn_{movie_id}", use_container_width=True
                    ):
                        st.session_state.editing_movie_id = movie_id
                        st.rerun()

                    if st.button(
                        "🗑️ 삭제", key=f"delete_btn_{movie_id}", use_container_width=True
                    ):
                        result = api.delete_movie(movie_id)
                        st.write(result)
                        st.toast(f"'{movie.get('title')}' 영화가 삭제되었습니다.")
                        st.rerun()

            # Review Section
            st.write("---")
            st.markdown("#### 💬 관람평")

            # [STEP 1] 현재 영화에 달린 리뷰 목록 가져오기
            # movie 객체 내부에 관계형으로 포함되어 있거나, 없으면 별도 API(api.get_reviews)로 조회
            reviews = movie.get("reviews", [])

            if reviews:
                # 간단한 AI 감정 통계 요약 피드백 생성
                sentiments = [r.get("sentiment") for r in reviews if r.get("sentiment")]
                if sentiments:
                    from collections import Counter

                    most_common_emotion = Counter(sentiments).most_common(1)[0][0]
                    st.caption(
                        f"📊 이 영화의 전체적인 AI 관람평 감정 분위기는 **:{most_common_emotion}** 입니다."
                    )

                # 리뷰 리스트 출력
                for rev in reviews:
                    rev_id = rev.get("id")

                    # 카드 스타일 레이아웃 (본문 4 : 삭제버튼 1)
                    r_col1, r_col2 = st.columns([5, 1])

                    with r_col1:
                        # 별점 생성 (1~5개)
                        stars = "⭐️" * rev.get("rating", 0)

                        # AI 감정 라벨에 따른 시각적 배지 컬러 설정
                        lbl = rev.get("sentiment", "중립")
                        score = rev.get("sentiment_score", 0.0) * 100

                        if lbl in ["행복", "기쁨"]:
                            badge_color = "green-badge"
                        elif lbl in ["분노", "혐오", "공포"]:
                            badge_color = "red-badge"
                        elif lbl in ["슬픔", "당황"]:
                            badge_color = "orange-badge"
                        else:
                            badge_color = "blue-badge"

                        # 리뷰어 이름, 별점, AI 분석 결과 한 줄 배치
                        st.markdown(
                            f"**{rev.get('author', '익명')}** {stars} | "
                            f":{badge_color}[AI 분석: {lbl} ({score:.1f}%)]"
                        )
                        st.write(rev.get("content"))
                        st.caption(f"작성일: {rev.get('created_at', '')[:10]}")

                    with r_col2:
                        st.write("")  # 패딩용
                        # 리뷰 삭제 버튼 (UUID 충돌을 피하기 위해 rev_id 기반 고유 key 부여)
                        if st.button("🗑️", key=f"del_rev_{rev_id}", help="리뷰 삭제"):
                            try:
                                api.delete_review(r_id=rev_id)
                                st.toast("리뷰가 정상적으로 삭제되었습니다.")
                                fetch_movies.clear()  # 캐시 초기화
                                st.rerun()
                            except Exception as e:
                                st.error(f"리뷰 삭제 실패: {e}")
                    st.markdown(
                        "<hr style='margin: 0.5em 0px; border-style: dashed; border-color: lightgray;'/>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("아직 등록된 관람평이 없습니다. 첫 번째 리뷰를 남겨보세요!")

            # [STEP 2] 새로운 리뷰 작성 폼 (영화 id별로 독립된 토글/폼 구성)
            with (
                st.expander("✍️ 관람평 남기기", expanded=False),
                st.form(key=f"review_form_{movie_id}", clear_on_submit=True),
            ):
                r_author = st.text_input(
                    "작성자", placeholder="닉네임", key=f"auth_{movie_id}"
                )

                col_rate, _ = st.columns([1, 2])
                with col_rate:
                    r_rating = st.slider(
                        "평점",
                        min_value=1,
                        max_value=5,
                        value=5,
                        key=f"rate_{movie_id}",
                    )

                r_content = st.text_area(
                    "리뷰 본문",
                    placeholder="영화에 대한 솔직한 평을 적어주세요. AI가 감정을 실시간으로 분석합니다.",
                    key=f"cont_{movie_id}",
                )

                r_submit = st.form_submit_button(
                    "✍️ 리뷰 등록", use_container_width=True
                )

                if r_submit:
                    if not r_author.strip() or not r_content.strip():
                        st.warning("작성자와 리뷰 내용을 모두 입력해 주세요.")
                    else:
                        try:
                            # api_client.py 에 보낼 페이로드 매핑
                            result = api.write_review(
                                m_id=movie_id,
                                author=r_author,
                                rating=r_rating,
                                content=r_content,
                            )
                            st.success(
                                f"리뷰가 등록되었습니다! AI 분석 결과: [{result.get('sentiment')}]"
                            )
                            fetch_movies.clear()  # 영화 목록 새로고침을 위한 캐시 비우기
                            sleep(0.3)
                            st.rerun()
                        except Exception as e:
                            st.error(f"리뷰 등록 오류: {e}")

st.divider()

with (
    st.expander("영화 추가", expanded=False),
    st.form(key="movie_create_form", clear_on_submit=True),
):
    title = st.text_input("제목")
    genre = st.text_input("장르")
    director = st.text_input("감독")
    year = st.number_input("개봉년도", min_value=1900, max_value=get_year())
    poster = st.text_input("포스터 URL")

    submitted = st.form_submit_button("추가")

    if submitted:
        if not title:
            st.warning("제목 필수")
        else:
            try:
                movie_data = api.create_movie(
                    title, director, genre, year, poster, None, None
                )
                fetch_movies.clear()
                st.toast("영화가 추가됐습니다", icon="✅")
                sleep(0.3)
                st.rerun()
            except httpx.HTTPStatusError as exc:
                error_detail = exc.response.json().get(
                    "detail", "Unknown Error Occur....ah..."
                )
                st.error(f"영화 추가 실패 ({exc.response.status_code}): {error_detail}")
            except Exception as e:
                st.error(f"통신 오류: {e!s}")
