import uvicorn
from fastapi import FastAPI

from config import config
from database import init_db
from api.participants import router as participants_router
from api.sessions import router as sessions_router
from api.results import router as results_router
from api.otp import router as otp_router
from api.tournament import router as tournament_router

app = FastAPI(title="SimAuth Server", version="1.0.0")

app.include_router(participants_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(results_router, prefix="/api")
app.include_router(otp_router, prefix="/api")
app.include_router(tournament_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=config.host, port=config.port, reload=True)
