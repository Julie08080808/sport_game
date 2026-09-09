from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from models import game_model, user_model

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


@router.post("/sync_exp")
def sync_exp(user_id: int = Form(...), building_type: int = Form(...), exp_amount: int = Form(...)):
    res = user_model.update_game_exp(user_id, building_type, exp_amount)
    if not res:
        raise HTTPException(status_code=400, detail="同步失敗")
    return res


@router.get("/scenes/{user_id}")
def get_scenes(user_id: int):
    """
    Unity 進 MainMap 時呼叫，一次拿回 5 個場景目前的等級/完成次數/外觀顯示覆寫，
    用來同步每棟建築(Farm/Pond/Forest/Center/Store)該顯示哪一階外觀。
    """
    return {"success": True, "scenes": game_model.get_all_scene_status(user_id)}


@router.post("/scene/display_level")
def set_scene_display_level(
    user_id: int = Form(...),
    scene_id: int = Form(...),
    display_level: int = Form(...),
):
    """
    玩家手動把某個場景的建築外觀調到指定等級(不能超過該場景目前的 scene_level)。
    display_level 傳 -1 代表清除覆寫，改回自動顯示最新已解鎖階段。
    """
    result = game_model.set_scene_display_level(user_id, scene_id, display_level)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "設定失敗"))
    return result
