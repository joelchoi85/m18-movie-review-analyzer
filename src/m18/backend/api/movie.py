from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, desc, func, select

from m18.backend.database import get_session
from m18.backend.models import (
    Movie,
    MovieCreate,
    MoviePatch,
    MovieResponse,
)

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


# 1. 영화 등록 API
@router.post("/movies/", response_model=MovieResponse)
def create_movie(movie_in: MovieCreate, session: SessionDep):
    db_movie = Movie.model_validate(movie_in)
    session.add(db_movie)
    session.commit()
    session.refresh(db_movie)
    return db_movie


# 2. 페이징 처리된 영화 목록 조회 API
@router.get("/movies/", response_model=list[MovieResponse])
def read_movies(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    # 페이지네이션 오프셋 계산
    offset = (page - 1) * limit
    statement = select(Movie).order_by(desc(Movie.id)).offset(offset).limit(limit)
    movies = session.exec(statement).all()
    return movies


# 3. Streamlit이 페이지 수를 계산할 때 필요한 메타데이터 API
@router.get("/movies/meta")
def get_movies_meta(session: SessionDep) -> dict[str, int]:
    # 전체 영화 개수 조회
    total_count = session.exec(select(func.count()).select_from(Movie)).one()
    return {"total_count": total_count}


# 3. 영화 삭제 API
@router.delete("/movies/{m_id}")
def remove_movie(m_id: int, session: SessionDep):
    movie = session.get(Movie, m_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="영화 정보가 없음"
        )

    session.delete(movie)
    session.commit()

    return {"ok": True, "message": f"ID {m_id} 영화가 삭제됨"}


@router.patch("/movies/{m_id}")
def modify_movie(m_id: int, patch_movie: MoviePatch, session: SessionDep):
    movie = session.get(Movie, m_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="영화 정보 없음"
        )

    movie.sqlmodel_update(patch_movie.model_dump(exclude_unset=True))

    session.add(movie)
    session.commit()
    session.refresh(movie)

    return movie
