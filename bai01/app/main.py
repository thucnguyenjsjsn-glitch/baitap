from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import Settings, get_settings
from app.database import Base, make_session_factory
from app.models import Ticket  # Import registers the table in Base.metadata.
from app.routers import tickets

STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=app.state.engine)
    yield
    app.state.engine.dispose()

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Bài 01 - Ticket Priority", lifespan=lifespan)
    engine, session_factory = make_session_factory(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.settings = settings
    app.include_router(tickets.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC_DIR / "index.html")
    return app

app = create_app()
