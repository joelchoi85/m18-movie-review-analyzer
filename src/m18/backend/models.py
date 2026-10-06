import uuid
from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel


class MovieBase(SQLModel):
    title: str = Field(index=True)
    director: str | None = Field(default=None)
    genre: str | None = Field(default=None)
    year: int | None = Field(default=None)
    poster: str | None = Field(default=None)
    vote_count: int | None = Field(default=None)
    rating: int | None = Field(default=None)


class MovieCreate(MovieBase):
    pass


class Movie(MovieBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviews: list["Review"] = Relationship(back_populates="movie", cascade_delete=True)


class MovieResponse(MovieBase):
    id: int
    created_at: datetime

    reviews: list["ReviewResponse"] = []


class MoviePatch(MovieBase):
    pass


class ReviewBase(SQLModel):
    content: str
    author: str
    rating: int = Field(ge=1, le=5)
    movie_id: int = Field(foreign_key="movie.id")


class ReviewCreate(ReviewBase):
    pass


class ReviewPatch(ReviewBase):
    content: str | None = None
    author: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


class Review(ReviewBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sentiment: str | None = Field(default=None)
    sentiment_score: float | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    movie: Movie | None = Relationship(back_populates="reviews")


class ReviewResponse(ReviewBase):
    id: uuid.UUID
    sentiment: str | None
    sentiment_score: float | None
    created_at: datetime
