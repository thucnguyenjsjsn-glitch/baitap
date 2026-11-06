from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import Settings,get_settings
from app.database import Base,make_session_factory
from app.expense_models import Expense
from app.routers import expenses
STATIC_DIR=Path(__file__).resolve().parent/'static'
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=app.state.engine)
    yield
    app.state.engine.dispose()
def create_app(settings:Settings|None=None):
    settings=settings or get_settings()
    app=FastAPI(title='Bài 03 - Rà soát hóa đơn gửi trùng',lifespan=lifespan)
    engine,factory=make_session_factory(settings.database_url)
    app.state.engine=engine;app.state.session_factory=factory;app.state.settings=settings
    app.include_router(expenses.router)
    app.mount('/static',StaticFiles(directory=STATIC_DIR),name='static')
    @app.get('/',include_in_schema=False)
    def home():return FileResponse(STATIC_DIR/'expense.html')
    return app
app=create_app()
