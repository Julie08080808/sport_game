"""
NPC 任務 Controller - 新版 Task 架構
========================================
POST /api/npc/dialogue
    取得某 NPC 目前可以提供給玩家的一個任務。

POST /api/npc/task/respond
    玩家接受或暫時不接該任務。
"""

from typing import Optional

from fastapi import APIRouter, Form, HTTPException
from models import npc_model

router = APIRouter(prefix="/api/npc", tags=["NPC Tasks"])


@router.post("/dialogue")
def get_dialogue(
    user_id: int = Form(...),
    npc_key: Optional[str] = Form(None),
    # 暫時相容舊 Unity：舊版送的是 npc_id 字串，例如 FARMER_01。
    npc_id: Optional[str] = Form(None),
):
    resolved_npc_key = npc_key or npc_id
    if not resolved_npc_key:
        raise HTTPException(status_code=400, detail="請提供 npc_key")

    result = npc_model.get_npc_task_offer(user_id, resolved_npc_key)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get(
            "message", "NPC 目前沒有可用任務"))

    return result


@router.post("/task/respond")
def respond_task(
    user_id: int = Form(...),
    npc_id: int = Form(...),
    task_id: int = Form(...),
    accepted: bool = Form(...),
    story_variant: str = Form("A"),
):
    result = npc_model.accept_or_decline_task(
        user_id=user_id,
        npc_id=npc_id,
        task_id=task_id,
        accepted=accepted,
        story_variant=story_variant,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("message", "任務處理失敗"))

    return result
