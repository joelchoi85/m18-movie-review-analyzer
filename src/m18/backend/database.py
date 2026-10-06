from sqlmodel import Session, SQLModel, create_engine

from .config import settings

connect_args = {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)


def init_db():

    from . import models

    _ = models.SQLModel.metadata
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
