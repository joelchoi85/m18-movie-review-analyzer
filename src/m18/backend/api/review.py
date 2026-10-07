import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session, asc, select

from m18.backend.database import get_session
from m18.backend.models import Movie, Review, ReviewCreate, ReviewPatch, ReviewResponse

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/movies/{m_id}/reviews/",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    m_id: int, review_in: ReviewCreate, request: Request, session: SessionDep
):
    movie = session.get(Movie, m_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="그런 영화 없음"
        )

    analyzer = getattr(request.app.state, "analyzer", None)

    sentiment_label = None
    sentiment_score = None

    if analyzer is not None:
        analysis_result = analyzer.analyze(review_in.content)
        sentiment_label = analysis_result["label"]
        sentiment_score = analysis_result["score"]
    else:
        print(
            "⚠️ [Warning] SentimentAnalyzer가 전역 상태(app.state)에 등록되어 있지 않습니다."
        )

    db_review = Review.model_validate(
        review_in,
        update={
            "movie_id": m_id,
            "sentiment": sentiment_label,
            "sentiment_score": sentiment_score,
        },
    )
    try:
        session.add(db_review)
        session.commit()
        session.refresh(db_review)

        return db_review
    except Exception as e:
        session.rollback()
        print(f"[DB Error] 리뷰 저장 중 예외 : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 저장 중 DB 에러",
        )


@router.get("/movies/{m_id}/reviews/")
def read_reviews(
    m_id: int,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    movie = session.get(Movie, m_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="그런 영화 없음"
        )

    # 페이지네이션 오프셋 계산
    offset = (page - 1) * limit
    statement = (
        select(Review)
        .where(Review.movie_id == m_id)
        .order_by(asc(Review.id))
        .offset(offset)
        .limit(limit)
    )
    reviews = session.exec(statement).all()
    return reviews


@router.delete("/reviews/{r_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(r_id: uuid.UUID, session: SessionDep):
    db_review = session.get(Review, r_id)

    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="그런 리뷰 없음"
        )
    try:
        session.delete(db_review)
        session.commit()

        return
    except Exception as e:
        session.rollback()
        print(f"[DB Error] 리뷰 삭제 중 예외가 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰를 삭제하는 동안 서버 내부 데이터베이스 오류.",
        )


@router.patch("/reviews/{r_id}", response_model=ReviewResponse)
def update_review(
    r_id: uuid.UUID, review_patch: ReviewPatch, request: Request, session: SessionDep
):
    db_review = session.get(Review, r_id)
    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID가 {r_id}인 리뷰를 찾을 수 없음",
        )

    patch_data = review_patch.model_dump(exclude_unset=True)

    if "content" in patch_data and patch_data["content"].strip():
        new_content = patch_data["content"]

        analyzer = getattr(request.app.state, "analyzer", None)
        if analyzer is not None:
            analysis_result = analyzer.analyze(new_content)

            patch_data["sentiment"] = analysis_result["label"]
            patch_data["sentiment_score"] = analysis_result["score"]
        else:
            print(
                "[Warning] SentimentAnalyzer를 전역 상태에서 찾을 수 없어 감정 재분석을 건너뜀"
            )

    db_review.sqlmodel_update(patch_data)

    try:
        session.add(db_review)
        session.commit()
        session.refresh(db_review)
        return db_review
    except Exception as e:
        session.rollback()
        print(f"[DB Error] 리뷰 수정 중 예외가 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰를 수정하는 동안 서버 내부 데이터베이스 오류",
        )
