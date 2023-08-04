from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slack import api
import firebase_admin

app = FastAPI(
    title="Slack app",
    description="Slack app",
    version="0.0.1",
    docs_url="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api)
firebase_admin.initialize_app()
