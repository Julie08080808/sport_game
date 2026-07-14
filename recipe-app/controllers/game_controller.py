from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import game_model

router = APIRouter(prefix="/api/game", tags=["Game Mechanics"])


class ExpUpdateReq(BaseModel):
    user_id: int
    building_type: int  # 0:農場, 1:池塘, 2:森林, 3:中心
    base_exp: int


@router.post("/complete_task")
def complete_task(req: ExpUpdateReq):
    result = game_model.process_task_completion(
        req.user_id, req.building_type, req.base_exp)

    if not result:
        raise HTTPException(status_code=500, detail="經驗值同步失敗，請檢查資料庫連線")

    return {
        "status": "success",
        "player": {
            "level": result["user"][0],
            "exp": result["user"][1],
            "money": result["user"][2]
        },
        "building": {
            "level": result["building"][0],
            "exp": result["building"][1]
        }
    }


class SyncExpReq(BaseModel):
    user_id: int
    building_type: int
    exp_amount: int


@router.post("/sync_exp")
def sync_exp(req: SyncExpReq):
    res = user_model.update_game_exp(
        req.user_id, req.building_type, req.exp_amount)
    if not res:
        raise HTTPException(status_code=400, detail="同步失敗")
    return {"success": True, "data": res}
