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


from services import reward_worker
from controllers import exercise_controller, task_controller
from controllers import (
    recipe_controller,
    user_controller,
    upload_controller,
    tts,
    game_controller,
    npc_controller,
    quiz_controller,
    shop_controller,
    assistant_controller,
    profile_controller,
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
load_dotenv(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), ".env"), override=False)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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

# /games → 認知遊戲靜態網頁(腦力健康站，4款小遊戲)，從 GitHub Mind_games 分支合併進來。
# Unity 這邊目前還沒有買支援跳轉 WebView 的套件，先把後端這條路接通，
# 等套件買好以後，直接讓 Unity 開啟 {serverUrl}/games/index.html 即可。
app.mount(
    "/games",
    StaticFiles(directory=os.path.join(BASE_DIR, "mind_games"), html=True),
    name="mind_games"
)


# ============================================================
# 6. 正式 API Controllers
# ============================================================
app.include_router(recipe_controller.router)
app.include_router(user_controller.router)
app.include_router(upload_controller.router)
app.include_router(game_controller.router)
app.include_router(npc_controller.router)
app.include_router(exercise_controller.router)
app.include_router(task_controller.router)
reward_worker.install(app)
app.include_router(quiz_controller.router)
app.include_router(shop_controller.router)
app.include_router(assistant_controller.router)
app.include_router(profile_controller.router)


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


DEV_ADMIN_MODE = APP_ENV != "production" and ENABLE_DEV_ADMIN

if DEV_ADMIN_MODE:

    from controllers import admin_test_controller

    # 開發測試 API（沒有登入保護，所以只在開發環境載入）
    app.include_router(
        admin_test_controller.router
    )

    print(
        f"[DEV] Admin test API enabled "
        f"(APP_ENV={APP_ENV})"
    )

else:

    print(
        f"[INFO] Admin test API disabled "
        f"(APP_ENV={APP_ENV})"
    )


# ============================================================
# 7-1. 網頁版管理後台 /admin（需要登入）
# ============================================================
# 開發環境（上面的 DEV_ADMIN_MODE）預設開啟；
# 正式 Server 要另外設 ENABLE_ADMIN_WEB=true 才會開。
# 兩種情況都必須在 .env 設好 ADMIN_USERNAME / ADMIN_PASSWORD_HASH /
# ADMIN_SESSION_SECRET（跑 scripts/set_admin_password.py），否則不載入。
# ============================================================

ENABLE_ADMIN_WEB = (
    os.getenv(
        "ENABLE_ADMIN_WEB",
        "false"
    ).strip().lower() == "true"
)

if DEV_ADMIN_MODE or ENABLE_ADMIN_WEB:

    from services import admin_auth

    missing_admin_settings = admin_auth.missing_settings()

    if missing_admin_settings:
        print(
            "[WARN] Admin Web disabled: .env 缺少 "
            + ", ".join(missing_admin_settings)
            + "（執行 python scripts/set_admin_password.py 設定）"
        )
    else:
        from controllers import admin_auth_controller, admin_controller

        app.include_router(admin_auth_controller.router)
        app.include_router(admin_controller.router)

        print("[INFO] Admin Web enabled at /admin (login required)")

else:

    print("[INFO] Admin Web disabled")


# ============================================================
# 8. View
# ============================================================

@app.get("/")
def serve_index():
    return FileResponse("views/index.html")


# Unity 料理鼠「食譜」用 WebView 開這個路徑(內容同首頁)
@app.get("/recipe")
def serve_recipe():
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
