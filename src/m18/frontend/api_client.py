import math
import uuid
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"


def create_movie(
    title: str,
    director: str | None,
    genre: str | None,
    year: int | None,
    poster: str | None,
    vote_count: int | None,
    rating: int | None,
):
    payload = {
        "title": title,
        "director": director,
        "genre": genre,
        "year": year,
        "poster": poster,
        "vote_count": vote_count,
        "rating": rating,
    }

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post("/movies/", json=payload)
        response.raise_for_status()
        return response.json()


def fetch_movies(page: int, limit: int) -> list[dict[str, Any]]:
    params = {"page": page, "limit": limit}
    try:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
            response = client.get("/movies/", params=params)
            response.raise_for_status()
            return response.json()
    except Exception:
        return []


def get_total_pages(items_per_page: int) -> int:
    try:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
            response = client.get("/movies/meta")
            response.raise_for_status()
            total_count = response.json().get("total_count", 1)

            if total_count == 0:
                return 1
            return math.ceil(total_count / items_per_page)
    except Exception:
        return 1


def delete_movie(m_id: int):
    try:
        with httpx.Client(base_url=BASE_URL, timeout=2.0) as client:
            response = client.delete(f"/movies/{m_id}")
            response.raise_for_status()
            return response.json()
    except Exception:
        return 0


def modify_movie(
    id: int,
    title: str,
    director: str | None,
    genre: str | None,
    year: int | None,
    poster: str | None,
):
    payload = {
        "title": title,
        "director": director,
        "genre": genre,
        "year": year,
        "poster": poster,
    }

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.patch(f"/movies/{id}", json=payload)
        response.raise_for_status()
        return response.json()


def fetch_recent_reviews(m_id: int) -> list[dict[str, Any]]:
    try:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
            response = client.get(f"/movies/{m_id}/reviews/recent")
            response.raise_for_status()
            return response.json()
    except Exception:
        return []


def write_review(m_id: int, author: str, content: str, rating: int):
    payload = {
        "movie_id": m_id,
        "author": author,
        "content": content,
        "rating": rating,
    }

    try:
        with httpx.Client(base_url=BASE_URL, timeout=3.0) as client:
            response = client.post(f"/movies/{m_id}/reviews/", json=payload)
            response.raise_for_status()
            return response.json()
    except Exception:
        return []


def delete_review(r_id: uuid.UUID):
    try:
        with httpx.Client(base_url=BASE_URL, timeout=3.0) as client:
            response = client.delete(f"/reviews/{r_id}")
            response.raise_for_status()
            return response.json()
    except Exception:
        return []
