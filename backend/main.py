from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db.session import engine, Base
from app.api.endpoints.channels import router as channels_router
# app.models を読み込ませることで、Base にモデルスキーマをバインドし、テーブルを自動生成する
import app.models

# 環境変数の読み込み
load_dotenv()

# アプリケーション起動時にDBテーブルを自動作成 (SQLite用)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="YouTube Research Toolkit API",
    description="YouTube競合分析およびポジショニング分析用APIサービス",
    version="1.0.0"
)

# CORS設定
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(channels_router, prefix="/api/channels", tags=["channels"])

@app.get("/")
def read_root():
    return {"message": "Welcome to YouTube Research Toolkit API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
