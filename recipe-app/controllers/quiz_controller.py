"""
問答遊戲控制器 (Controller)
處理問答相關 HTTP 請求,呼叫 Model 取得資料。

API 設計:
    GET  /api/quiz/questions?count=5&mode=random  取得題目(出題)
    POST /api/quiz/answer                          提交答案,後端驗證
    GET  /api/quiz/total                           查題庫總數
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import quiz_model

router = APIRouter(prefix="/api/quiz", tags=["Quiz"])


class AnswerRequest(BaseModel):
    """提交答案的請求格式"""
    question_id: int = Field(..., gt=0)
    user_answer: str = Field(..., pattern="^[ABab]$")  # 只接受 A/B/a/b


@router.get("/questions")
def get_questions(count: int = 5, mode: str = "random"):
    """
    取得題目。
    參數:
        count - 要幾題(預設 5)。題庫不足會自動少給。
        mode  - random(預設,隨機) / sequential(順序)
    """
    if count < 1 or count > 100:
        raise HTTPException(status_code=400, detail="count 必須介於 1 到 100 之間")

    if mode == "random":
        questions = quiz_model.fetch_random_questions(count)
    elif mode == "sequential":
        questions = quiz_model.fetch_sequential_questions(count)
    else:
        raise HTTPException(status_code=400, detail="mode 只能是 random 或 sequential")

    if not questions:
        raise HTTPException(status_code=404, detail="題庫目前沒有題目")
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
def get_total():
    """回傳題庫總題數,可用於前端顯示。"""
    return {"total": quiz_model.count_total_questions()}
