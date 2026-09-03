from fastapi import APIRouter, Form, HTTPException, Query
from models import admin_test_model

router = APIRouter(
    prefix="/api/admin/dev",
    tags=["Admin Dev Tools"],
)


@router.post("/task-replay/restart")
def restart_task_for_testing(
    user_id: int = Form(...),
    task_id: int = Form(...),
    reason: str = Form("manual dev replay"),
):
    result = admin_test_model.restart_task_for_testing(
        user_id=user_id,
        task_id=task_id,
        reason=reason,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "重新開放測試任務失敗"),
        )

    return result


@router.get("/task-replay/status")
def get_task_test_status(
    user_id: int = Query(...),
    task_id: int = Query(...),
):
    result = admin_test_model.get_task_test_status(
        user_id=user_id,
        task_id=task_id,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("message", "找不到資料"),
        )

    return result
