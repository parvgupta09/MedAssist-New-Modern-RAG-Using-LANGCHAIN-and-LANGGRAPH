from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.connection import engine, Base
from src.api import auth, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title = "AI Medical Triage Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"status" : "Triage API running successfully."}