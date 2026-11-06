from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_session_factory(database_url: str):
    if not database_url:
        raise ValueError("Chưa cấu hình DATABASE_URL trong .env")
    if database_url.startswith("postgresql+psycopg://"):
        pass
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    engine = create_engine(database_url, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
