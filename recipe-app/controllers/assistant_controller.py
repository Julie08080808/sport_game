"""
阿明（長輩陪伴 AI 助手）後端代理。

App 只跟這支 API 講話，不知道 Cloudflare Worker 的存在：
    App → 這支 API（查資料庫、組 JSON）→ Worker（阿明）→ 原樣轉回 App

對應規格：AI助手後端說明.pdf（2026/11/07，規則版本 1104-k）。
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from models import assistant_model
from services import auth_service

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])
log = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    userMessage: str = ""
    # 規格沒有明講 topic 從哪裡來，但範例 payload 在不同情境下值不同
    # （閒聊 / 食譜推薦...），所以當成 App 自己決定、後端照轉的欄位。
    topic: str = "閒聊"
    lastUserMessage: str = ""
    lastReply: str = ""
    history: list = Field(default_factory=list)
    toldFacts: str = ""
    lastFactId: str = ""
    wantFact: bool = False


def require_user_id(authorization: Optional[str] = Header(None)) -> int:
    """
    user_id 一律從登入 session 取，不從請求參數拿——這是規格的硬性要求（防 IDOR）。
    Authorization 可以是 "<token>" 或 "Bearer <token>"。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登入")

    token = authorization[7:] if authorization.lower().startswith("bearer ") else authorization
    user_id = auth_service.get_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登入已過期，請重新登入")

    return user_id


@router.post("/chat")
def chat(req: ChatRequest, user_id: int = Depends(require_user_id)):
    try:
        return assistant_model.build_chat_reply(user_id, req.model_dump())
    except Exception:
        log.exception("組裝阿明請求失敗 user_id=%s", user_id)
        # 第 5 步：查詢或組裝本身出問題，也不讓長輩看到錯誤訊息或 500。
        return {"reply": assistant_model.FALLBACK_REPLY, "factId": "", "safetyLevel": "none"}
