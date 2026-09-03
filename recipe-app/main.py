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

from controllers import (
    recipe_controller,
    user_controller,
    upload_controller,
    tts,
    game_controller,
    npc_controller,
    quiz_controller,
    shop_controller,
)
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# ============================================================
# 1. 最先載入 .env
# ============================================================
# 必須放在 controllers / models 被 import 之前，
# 避免 database.py 或其他模組讀不到環境變數。
load_dotenv()


# ============================================================
# 2. 載入正式 Controllers
# ============================================================


# ============================================================
# 3. 建立 FastAPI App
# ============================================================
app = FastAPI(
    title="銀髮族食譜 App",
    version="1.0.0"
)


# ============================================================
# 4. CORS
# ============================================================
# 現在是開發階段，所以先允許所有來源。
# 正式部署 Production 時之後會再縮限。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 5. 靜態資源
# ============================================================
# /image  → image 資料夾
# /static → views 資料夾內 CSS / JS
app.mount(
    "/image",
    StaticFiles(directory="image"),
    name="image"
)

app.mount(
    "/static",
    StaticFiles(directory="views"),
    name="static"
)


# ============================================================
# 6. 正式 API Controllers
# ============================================================
app.include_router(recipe_controller.router)
app.include_router(user_controller.router)
app.include_router(upload_controller.router)
app.include_router(game_controller.router)
app.include_router(npc_controller.router)
app.include_router(quiz_controller.router)
app.include_router(shop_controller.router)


# TTS
app.include_router(
    tts.router,
    prefix="/api",
    tags=["語音功能"]
)


# ============================================================
# 7. Development Admin API
# ============================================================
# 只有：
#
# APP_ENV != production
# 且
# ENABLE_DEV_ADMIN=true
#
# 才會載入 /api/admin/dev/*
#
# 正式 Server 即使程式碼存在，也不會啟用。
# ============================================================

APP_ENV = os.getenv(
    "APP_ENV",
    "production"
).strip().lower()

ENABLE_DEV_ADMIN = (
    os.getenv(
        "ENABLE_DEV_ADMIN",
        "false"
    ).strip().lower() == "true"
)


if APP_ENV != "production" and ENABLE_DEV_ADMIN:

    from controllers import (
        admin_test_controller,
        admin_controller,
    )

    # 開發測試 API
    app.include_router(
        admin_test_controller.router
    )

    # 網頁版管理後台
    app.include_router(
        admin_controller.router
    )

    print(
        f"[DEV] Admin test API + Admin Web enabled "
        f"(APP_ENV={APP_ENV})"
    )

else:

    print(
        f"[INFO] Admin tools disabled "
        f"(APP_ENV={APP_ENV})"
    )


# ============================================================
# 8. View
# ============================================================

@app.get("/")
def serve_index():
    return FileResponse("views/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("views/login.html")


@app.get("/quiz")
def serve_quiz():
    return FileResponse("views/quiz.html")


@app.get("/shop")
def serve_shop():
    return FileResponse("views/shop.html")


# ============================================================
# 9. Local 開發啟動
# ============================================================


if __name__ == "__main__":
    import uvicorn
    # 這裡的 host 設為 0.0.0.0 方便區域網路內測試
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
