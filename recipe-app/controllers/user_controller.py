"""
使用者控制器 (Controller)
處理註冊、登入請求。
"""
from fastapi import APIRouter, HTTPException, Form
from models import user_model, player_model
from services.exercise_rules import RuleError
import logging


def _player(user_id):
    try:
        return player_model.get_player(user_id)
    except RuleError as e:
        raise HTTPException(404, detail=str(e)) from e
    except Exception as e:
        logging.getLogger(__name__).exception("Player lookup failed")
        raise HTTPException(503, detail="暫時無法取得玩家資料") from e


router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    """
    玩家登入 API。
    """
    print("\n" + "="*50)
    print(f"[收到 Unity 登入請求] 帳號: {username}")
    print("="*50)

    user = user_model.verify_user(username, password)
    if not user:
        print(f"[登入失敗] 帳號或密碼錯誤: {username}")
        print("="*50 + "\n")
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    uid = user['user_id']
    player_data = _player(uid)

    print(f"[登入驗證成功] 玩家 UID: {uid}，資料庫數據已打包回傳 Unity")
    print("="*50 + "\n")

    return {
        "success": True,
        "user_id": uid,
        "message": "登入成功",
        "player": player_data
    }


@router.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    """
    玩家註冊 API。
    """
    print("\n" + "="*50)
    print(f"[收到 Unity 註冊請求] 正在嘗試將玩家寫入資料庫...")
    print(f"   註冊帳號: {username}")
    print("="*50)

    new_user = user_model.create_user_with_stats(username, password)
    if not new_user:
        print(f"[資料庫寫入失敗] 帳號 '{username}' 已存在於 users 資料表中")
        print("="*50 + "\n")
        raise HTTPException(status_code=400, detail="此帳號已存在，請換一個名稱")

    print(f"[資料庫寫入成功] 玩家帳號已建立，並同步在 user_stats 與 user_scenes 中初始化完成")
    print("="*50 + "\n")

    return {
        "success": True,
        "user_id": new_user["user_id"],
        "message": "註冊成功，初始遊戲資料已建立！"
    }


@router.get("/profile/{user_id}")
def get_user_profile(user_id: int):
    return {"success": True, "data": _player(user_id)}
