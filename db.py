from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, create_engine, Session

# Using a local SQLite file: chat.db in your project folder
DATABASE_URL = "sqlite:///./chat.db"

engine = create_engine(DATABASE_URL, echo=False)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # later you can use real user/session IDs – for now, keep it simple
    session_id: str = Field(index=True)

    role: str  # "user" or "assistant"
    content: str

    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db() -> None:
    """Create tables if they don't exist yet."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that gives a DB session to each request."""
    with Session(engine) as session:
        yield session
