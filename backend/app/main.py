from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  (모델 등록을 위해 import)
from app.routers import users, trips, policies, incidents

Base.metadata.create_all(bind=engine)

app = FastAPI(title="여행자보험 전 생애주기 AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(trips.router)
app.include_router(policies.router)
app.include_router(incidents.router)


@app.get("/health")
def health():
    return {"status": "ok"}
