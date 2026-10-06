import os

import httpx
from dotenv import load_dotenv

import m18.frontend.api_client as api

load_dotenv()

TOKEN = os.environ["TMDB_TOKEN"]
BASE = "https://api.themoviedb.org/3"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "accept": "application/json"}


def search_movie(client: httpx.Client, title: str):
    r = client.get(
        f"{BASE}/search/movie",
        params={"query": title, "include_adult": "false", "language": "ko-KR"},
        headers=HEADERS,
        timeout=10.0,
    )
    r.raise_for_status()
    results = r.json()["results"]
    return results[0] if results else None


def movie_details(client: httpx.Client, movie_id: int):
    r = client.get(
        f"{BASE}/movie/{movie_id}",
        # credits를 함께 가져와서 감독 정보를 추출합니다.
        params={"append_to_response": "credits", "language": "ko-KR"},
        headers=HEADERS,
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()


def parse_movie_info(data: dict):
    # 1. Title
    title = data.get("title")

    # 2. Year (개봉 연도)
    release_date = data.get("release_date", "")
    year = release_date.split("-")[0] if release_date else "N/A"

    # 3. Genres (장르 목록을 쉼표로 연결)
    genres = [g["name"] for g in data.get("genres", [])]
    genre_str = ", ".join(genres) if genres else "N/A"

    # 4. Poster URL
    poster_path = data.get("poster_path")
    poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "N/A"

    # 5. Director (크루 중 Directing 직책 검색)
    crew = data.get("credits", {}).get("crew", [])
    directors = [member["name"] for member in crew if member.get("job") == "Director"]
    director_str = ", ".join(directors) if directors else "N/A"

    # 6. Rating (TMDB 평점 및 투표 수 추가)
    rating = data.get("vote_average", 0.0)
    vote_count = data.get("vote_count", 0)

    return {
        "title": title,
        "year": year,
        "genre": genre_str,
        "poster": poster,
        "director": director_str,
        "rating": rating,
        "vote_count": vote_count,
    }


movies = []

search_list = [
    "사운드 오브 뮤직",
    "오만과 편견",
    "기억의 저편에서",
    "타임머신",
    "파더",
    "도그빌",
    "이터널 선샤인",
    "에반 올마이티",
    "스폰지밥",
    "늑대개",
    "내겐 너무 가벼운 그녀",
    "쇼생크 탈출",
    "나는 내일 어제의 너와 만난다",
]

# 실행
with httpx.Client() as client:
    for keyword in search_list:
        hit = search_movie(client, keyword)
        if hit:
            movie = movie_details(client, hit["id"])
            info = parse_movie_info(movie)

            movies.append({
                "title": info["title"],
                "year": info["year"],
                "genre": info["genre"],
                "director": info["director"],
                "poster": info["poster"],
                "rating": round(info["rating"] % 5, 0),
                "vote_count": info["vote_count"],
            })

            print(
                f"{info['title']} | {info['year']} | {info['genre']} | {info['director']} | {info['poster']}"
            )


for m in movies:
    api.create_movie(**m)
