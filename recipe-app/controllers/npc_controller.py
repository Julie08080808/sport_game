"""
NPC 對話控制器 (Controller)
處理「點擊 NPC 抽對話/任務」與「玩家接受/放棄任務」的請求。
"""
from fastapi import APIRouter, HTTPException, Form
from models import npc_model

router = APIRouter(prefix="/api/npc", tags=["NPC Dialogue"])


@router.post("/dialogue")
def get_dialogue(user_id: int = Form(...), npc_id: str = Form(...)):
    dialogue = npc_model.get_random_dialogue(user_id, npc_id)
    if not dialogue:
        raise HTTPException(status_code=404, detail="這個 NPC 目前沒有可用的任務")

    return {
        "success": True,
        "dialogue_id": dialogue["dialogue_id"],
        "npc_id": dialogue["npc_id"],
        "npc_name": dialogue["npc_name"],
        "dialogue_text": dialogue["dialogue_text"],
        "task_category": dialogue["task_category"],
        "action_type": dialogue["action_type"],
        "target_scene": dialogue["target_scene"],
        "background_key": dialogue["background_key"],
        "reward_exp": dialogue["reward_exp"],
        "reward_coin": dialogue["reward_coin"],
    }


@router.post("/task/respond")
def respond_task(user_id: int = Form(...), dialogue_id: int = Form(...), accepted: bool = Form(...)):
    status = "accepted" if accepted else "abandoned"
    ok = npc_model.record_task_response(user_id, dialogue_id, status)
    if not ok:
        raise HTTPException(status_code=500, detail="任務狀態寫入失敗")
    return {"success": True, "status": status}
