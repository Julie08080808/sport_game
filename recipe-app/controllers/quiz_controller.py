"""
問答遊戲控制器 (Controller)
處理問答相關 HTTP 請求,呼叫 Model 取得資料。

API 設計:
    GET  /api/quiz/questions?count=5&mode=random&type=all
         取得題目(出題)
    POST /api/quiz/answer
         提交答案,後端驗證
    GET  /api/quiz/total?type=all
         查題庫總數

【type 參數說明】
    all(預設) — 文字題與圖片題混合隨機,一般使用者走這條
    text      — 只出文字題
    image     — 只出圖片題

前端介面「不會」提供切換按鈕,type 只透過網址參數控制,
用於 demo 或審查時精準展示特定題型。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import quiz_model

router = APIRouter(prefix="/api/quiz", tags=["Quiz"])

# 允許的題型參數
ALLOWED_TYPES = ("all", "text", "image")


class AnswerRequest(BaseModel):
    """提交答案的請求格式"""
    question_id: int = Field(..., gt=0)
    user_answer: str = Field(..., pattern="^[ABab]$")  # 只接受 A/B/a/b


def _normalize_type(q_type: str):
    """
    驗證並正規化 type 參數。
    'all' 會轉成 None,代表不做篩選。
    """
    if q_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"type 只能是 {', '.join(ALLOWED_TYPES)}"
        )
    return None if q_type == "all" else q_type


@router.get("/questions")
def get_questions(count: int = 5, mode: str = "random", type: str = "all"):
    """
    取得題目。
    參數:
        count - 要幾題(預設 5)。題庫不足會自動少給。
        mode  - random(預設,隨機) / sequential(順序)
        type  - all(預設) / text / image
    """
    if count < 1 or count > 100:
        raise HTTPException(status_code=400, detail="count 必須介於 1 到 100 之間")

    q_type = _normalize_type(type)

    if mode == "random":
        questions = quiz_model.fetch_random_questions(count, q_type)
    elif mode == "sequential":
        questions = quiz_model.fetch_sequential_questions(count, 0, q_type)
    else:
        raise HTTPException(status_code=400, detail="mode 只能是 random 或 sequential")

    if not questions:
        raise HTTPException(status_code=404, detail="題庫目前沒有符合條件的題目")
    return questions


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    """
    提交答案,回傳正確與否、正解、解釋。
    答案驗證放在後端,避免前端被改而作弊。
    """
    result = quiz_model.check_answer(req.question_id, req.user_answer)
    if result is None:
        raise HTTPException(status_code=404, detail="題目不存在")
    return result


@router.get("/total")
def get_total(type: str = "all"):
    """
    回傳題庫總題數,可用於前端顯示。
    可依 type 篩選,例如 /api/quiz/total?type=image 查圖片題有幾題。
    """
    q_type = _normalize_type(type)
    return {
        "total": quiz_model.count_total_questions(q_type),
        "type": type,
    }
