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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from controllers import recipe_controller, user_controller, upload_controller

# 建立 FastAPI 應用
app = FastAPI(title="銀髮族食譜 App", version="1.0.0")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態資源
app.mount("/image", StaticFiles(directory="image"), name="image")
app.mount("/static", StaticFiles(directory="views"), name="static")

# 掛載各 Controller 路由
app.include_router(recipe_controller.router)
app.include_router(user_controller.router)
app.include_router(upload_controller.router)


# 首頁 (View)
@app.get("/")
def serve_index():
    return FileResponse("views/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("views/login.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
