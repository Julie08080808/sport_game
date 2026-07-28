"""
銀髮族食譜 App - 應用程式進入點
=========================================
架構: MVC
- Model      : models/        (資料存取)
- View       : views/         (HTML/CSS/JS)
- Controller : controllers/   (API 路由)

啟動方式:
    uvicorn main:app --reload
"""
from controllers import recipe_controller, user_controller, upload_controller, tts, game_controller, npc_controller
import os
from dotenv import load_dotenv  # 引入載入工具
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 1. 在最一開始就載入環境變數 (確保 GOOGLE_APPLICATION_CREDENTIALS 被讀取)
load_dotenv()

# 2. 引入你建立的 controllers

# 建立 FastAPI 應用
app = FastAPI(title="銀髮族食譜 App", version="1.0.0")

# CORS 設定 (開發階段允許所有來源)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態資源
# /image 存取實體 image 資料夾裡的圖片
# /static 存取實體 views 資料夾裡的 CSS/JS
app.mount("/image", StaticFiles(directory="image"), name="image")
app.mount("/static", StaticFiles(directory="views"), name="static")

# 掛載各 Controller 路由
app.include_router(recipe_controller.router)
app.include_router(user_controller.router)
app.include_router(upload_controller.router)
app.include_router(game_controller.router)
app.include_router(npc_controller.router)

# 3. 掛載語音功能路由
# 這裡加上 prefix="/api" 後，前端 fetch 的網址就會是 /api/tts
app.include_router(tts.router, prefix="/api", tags=["語音功能"])

# 首頁 (View)


@app.get("/")
def serve_index():
    return FileResponse("views/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("views/login.html")


if __name__ == "__main__":
    import uvicorn
    # 這裡的 host 設為 0.0.0.0 方便區域網路內測試
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
