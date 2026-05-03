"""
使用者控制器 (Controller)
處理註冊、登入請求。簡易帳密比對,不發 JWT。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import user_model

router = APIRouter(prefix="/api/users", tags=["Users"])


class AuthRequest(BaseModel):
    """登入/註冊請求格式"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


@router.post("/login")
def login(req: AuthRequest):
    """簡易帳密比對。比對成功回傳使用者資料。"""
    user = user_model.verify_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    return {"success": True, "user": user}


@router.post("/register")
def register(req: AuthRequest):
    """註冊新帳號。"""
    new_user = user_model.create_user(req.username, req.password)
    if not new_user:
        raise HTTPException(status_code=400, detail="此帳號已存在,請換一個")
    return {"success": True, "user": new_user}
