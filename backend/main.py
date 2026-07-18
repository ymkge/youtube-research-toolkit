import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

app = FastAPI(
    title="YouTube Research Toolkit API",
    description="YouTube競合分析およびポジショニング分析用APIサービス",
    version="1.0.0"
)

# CORS設定
origins = [
    "http://localhost:3000",  # フロントエンド開発用サーバー
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to YouTube Research Toolkit API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
