"""/admin 這邊新增「照護中心」管理：建中心、建照護者帳號、把老人指派到中心。

跟照護者實際看數據的 /care 入口完全分開（那邊是獨立的多帳號登入）。
這裡沿用 /admin 現有的單一系統管理員登入（require_admin）。
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models import care_model
from services.admin_auth import require_admin

router = APIRouter(
    prefix="/admin/care-centers",
    tags=["Admin Web - Care Centers"],
    dependencies=[Depends(require_admin)],
)
templates = Jinja2Templates(directory="views")


@router.get("")
def list_centers(request: Request, saved: int = 0):
    centers = care_model.list_care_centers()
    return templates.TemplateResponse(
        request=request,
        name="admin/care_centers.html",
        context={"page": "care-centers", "centers": centers, "saved": bool(saved)},
    )


@router.post("/new")
def create_center(center_name: str = Form(...), center_code: str = Form(...)):
    care_model.create_care_center(center_name, center_code)
    return RedirectResponse(url="/admin/care-centers?saved=1", status_code=303)


@router.get("/{care_center_id}")
def center_detail(request: Request, care_center_id: int, saved: int = 0):
    center = care_model.get_care_center(care_center_id)
    if not center:
        raise HTTPException(status_code=404, detail="Care center not found")

    caregivers = care_model.list_caregivers(care_center_id)
    all_users = care_model.list_users_with_center()
    return templates.TemplateResponse(
        request=request,
        name="admin/care_center_detail.html",
        context={
            "page": "care-centers",
            "center": center,
            "caregivers": caregivers,
            "all_users": all_users,
            "saved": bool(saved),
        },
    )


@router.post("/{care_center_id}/caregivers/new")
def create_caregiver(
    care_center_id: int,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
):
    care_model.create_caregiver(care_center_id, username, password, display_name)
    return RedirectResponse(url=f"/admin/care-centers/{care_center_id}?saved=1", status_code=303)


@router.post("/{care_center_id}/caregivers/{caregiver_id}/toggle")
def toggle_caregiver(care_center_id: int, caregiver_id: int, is_active: str = Form("")):
    care_model.set_caregiver_active(caregiver_id, is_active == "1")
    return RedirectResponse(url=f"/admin/care-centers/{care_center_id}", status_code=303)


@router.post("/{care_center_id}/assign")
def assign_user(care_center_id: int, user_id: int = Form(...)):
    care_model.assign_user_to_center(user_id, care_center_id)
    return RedirectResponse(url=f"/admin/care-centers/{care_center_id}?saved=1", status_code=303)


@router.post("/{care_center_id}/unassign")
def unassign_user(care_center_id: int, user_id: int = Form(...)):
    care_model.assign_user_to_center(user_id, None)
    return RedirectResponse(url=f"/admin/care-centers/{care_center_id}?saved=1", status_code=303)
