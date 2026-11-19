"""
個人檔案控制器 (Controller)
對應 Unity SilverHealth 模組的 IDataService。使用者一律用路徑上的 user_id，
之後要防 IDOR 的話可以改走跟 /api/assistant/chat 一樣的 session token 驗證。

API 設計：
    GET  /api/profile/{user_id}                       基本資料 + 唯讀等級經驗
    PUT  /api/profile/{user_id}                        存基本資料
    POST /api/profile/{user_id}/avatar                 上傳頭像（存檔慣例同 upload_controller）
    GET  /api/profile/health-conditions/catalog        健康狀況清單（全使用者共用）
    GET  /api/profile/{user_id}/health-conditions      使用者目前勾選的健康狀況
    PUT  /api/profile/{user_id}/health-conditions       覆蓋寫入
    GET  /api/profile/allergens/catalog                 食物過敏原類別（固定 9 項，給下拉選單/勾選用）
    GET  /api/profile/{user_id}/allergies               使用者目前登記的食物過敏原
    PUT  /api/profile/{user_id}/allergies               覆蓋寫入（只接受 catalog 裡的類別）
    GET  /api/profile/{user_id}/outfits                 換裝清單（解鎖狀態）；穿上走 PUT /{user_id} 整包存（同 Unity OutfitPanel 的作法）
    GET  /api/profile/{user_id}/achievements            成就清單
    PUT  /api/profile/{user_id}/achievements/displayed  設定要展示的成就
    GET  /api/profile/{user_id}/settings                個人設定
    PUT  /api/profile/{user_id}/settings                存個人設定
    GET  /api/profile/{user_id}/exercise-sessions       運動紀錄（數據分析頁用，重用 exercise_logs）
"""
import logging
import os
import shutil
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

from models import profile_model
from services.exercise_rules import RuleError

router = APIRouter(prefix="/api/profile", tags=["Profile"])

UPLOAD_DIR = "image"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (RuleError, ValueError) as e:
        raise HTTPException(409, detail=str(e)) from e
    except Exception as e:
        logging.getLogger(__name__).exception("Profile operation failed")
        raise HTTPException(503, detail="暫時無法處理個人檔案，請稍後再試") from e


# ───────────── 基本資料 ─────────────

@router.get("/{user_id}")
def get_profile(user_id: int):
    return dict(success=True, data=_call(profile_model.get_profile, user_id))


class ProfileSaveRequest(BaseModel):
    game_name: str = Field(max_length=50)
    real_name: Optional[str] = Field(default=None, max_length=100)
    gender: Optional[str] = Field(default=None, max_length=10)
    height_cm: Optional[int] = Field(default=None, ge=100, le=220)
    weight_kg: Optional[int] = Field(default=None, ge=25, le=200)
    birthdate: Optional[str] = None
    equipped_outfit_id: Optional[int] = None
    # 阿明用的欄位；不送（None）就保留原值，舊版 Unity 不用改也不會壞。
    is_on_medication: Optional[bool] = None
    diet_type: Optional[Literal["None", "Vegan"]] = None
    is_mobility_limited: Optional[bool] = None


@router.put("/{user_id}")
def save_profile(user_id: int, req: ProfileSaveRequest):
    # Unity 端換裝（OutfitPanel）也是整包 Profile 存這裡，不是走單獨的換裝端點，
    # 所以 equipped_outfit_id 的解鎖驗證放在 profile_model.save_profile 裡面。
    return dict(success=True, data=_call(
        profile_model.save_profile, user_id, req.game_name, req.real_name,
        req.gender, req.height_cm, req.weight_kg, req.birthdate, req.equipped_outfit_id,
        req.is_on_medication, req.diet_type, req.is_mobility_limited))


@router.post("/{user_id}/avatar")
async def upload_avatar(user_id: int, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只允許上傳圖片檔案")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支援的圖片格式: {ext}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_filename)
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    avatar_url = f"/image/{safe_filename}"
    return dict(success=True, data=_call(profile_model.save_avatar_url, user_id, avatar_url))


# ───────────── 健康狀況 ─────────────

@router.get("/health-conditions/catalog")
def health_condition_catalog():
    return dict(success=True, items=_call(profile_model.get_health_condition_catalog))


@router.get("/{user_id}/health-conditions")
def user_health_conditions(user_id: int):
    return dict(success=True, items=_call(profile_model.get_user_health_conditions, user_id))


class HealthConditionItem(BaseModel):
    condition_id: int
    has_condition: bool


class HealthConditionSaveRequest(BaseModel):
    items: List[HealthConditionItem]


@router.put("/{user_id}/health-conditions")
def save_user_health_conditions(user_id: int, req: HealthConditionSaveRequest):
    items = [i.model_dump() for i in req.items]
    return dict(success=True, items=_call(profile_model.save_user_health_conditions, user_id, items))


# ───────────── 食物過敏原 ─────────────

@router.get("/allergens/catalog")
def allergen_catalog():
    return dict(success=True, items=profile_model.get_allergen_catalog())


@router.get("/{user_id}/allergies")
def user_allergies(user_id: int):
    return dict(success=True, items=_call(profile_model.get_user_allergies, user_id))


class AllergySaveRequest(BaseModel):
    names: List[str] = Field(default_factory=list, max_length=9)


@router.put("/{user_id}/allergies")
def save_user_allergies(user_id: int, req: AllergySaveRequest):
    # 不在 9 個類別內 → ValueError → _call 轉成 409，訊息會列出可選的類別。
    return dict(success=True, items=_call(profile_model.save_user_allergies, user_id, req.names))


# ───────────── 換裝 ─────────────

@router.get("/{user_id}/outfits")
def outfits(user_id: int):
    return dict(success=True, items=_call(profile_model.get_outfits, user_id))


# ───────────── 成就 ─────────────

@router.get("/{user_id}/achievements")
def achievements(user_id: int):
    return dict(success=True, items=_call(profile_model.get_achievements, user_id))


class DisplayedAchievementsRequest(BaseModel):
    achievement_ids: List[int]


@router.put("/{user_id}/achievements/displayed")
def save_displayed_achievements(user_id: int, req: DisplayedAchievementsRequest):
    return dict(success=True, items=_call(
        profile_model.save_displayed_achievements, user_id, req.achievement_ids))


# ───────────── 個人設定 ─────────────

@router.get("/{user_id}/settings")
def get_settings(user_id: int):
    return dict(success=True, data=_call(profile_model.get_settings, user_id))


class SettingsSaveRequest(BaseModel):
    font_size: int = Field(default=80, ge=40, le=160)
    master_volume: float = Field(default=0.8, ge=0, le=1)
    sfx_volume: float = Field(default=0.8, ge=0, le=1)
    music_volume: float = Field(default=0.6, ge=0, le=1)
    tts_enabled: bool = False


@router.put("/{user_id}/settings")
def save_settings(user_id: int, req: SettingsSaveRequest):
    return dict(success=True, data=_call(
        profile_model.save_settings, user_id, req.font_size, req.master_volume,
        req.sfx_volume, req.music_volume, req.tts_enabled))


# ───────────── 運動紀錄 ─────────────

@router.get("/{user_id}/exercise-sessions")
def exercise_sessions(user_id: int, date_from: str = Query(...), date_to: str = Query(...)):
    return dict(success=True, items=_call(
        profile_model.get_exercise_sessions, user_id, date_from, date_to))


# ───────────── 飲食週報（取代每日營養攝取，見 PhotoManager.GetWeeklyObservation） ─────────────

class DietReviewSaveRequest(BaseModel):
    week_monday: str
    vegetable_score: int = Field(ge=0, le=5)
    fried_score: int = Field(ge=0, le=5)
    variety_score: int = Field(ge=0, le=5)
    ai_observation: str = ""


@router.put("/{user_id}/diet-review")
def save_diet_review(user_id: int, req: DietReviewSaveRequest):
    return dict(success=True, data=_call(
        profile_model.save_weekly_diet_review, user_id, req.week_monday,
        req.vegetable_score, req.fried_score, req.variety_score, req.ai_observation))


@router.get("/{user_id}/diet-review/latest")
def latest_diet_review(user_id: int):
    data = _call(profile_model.get_latest_weekly_diet_review, user_id)
    if data is None:
        raise HTTPException(404, detail="這個使用者還沒有任何一週的飲食週報")
    return dict(success=True, data=data)
