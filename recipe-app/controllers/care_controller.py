from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from models import care_model
from services.care_auth import require_caregiver

# 每一頁都要先登入（登入頁在 care_auth_controller，不受這個限制）。
router = APIRouter(
    prefix="/care",
    tags=["Care Portal"],
    dependencies=[Depends(require_caregiver)],
)
templates = Jinja2Templates(directory="views")

CATEGORY_LABELS = {"hand": "手部", "leg": "腳部", "ball": "球類", "full_body": "全身"}
RANGE_LABELS = {"week": "最近 7 天", "month": "最近 30 天", "year": "最近 12 個月"}


@router.get("")
def dashboard(request: Request):
    caregiver = request.state.caregiver
    stats = care_model.get_dashboard_stats(caregiver["care_center_id"])
    trend = care_model.get_center_trend(caregiver["care_center_id"], days=7)
    return templates.TemplateResponse(
        request=request,
        name="care/dashboard.html",
        context={"page": "dashboard", "caregiver": caregiver, "trend": trend, **stats},
    )


@router.get("/residents")
def residents(request: Request, cat: list[str] = Query(default=[]), sort: str = "desc", q: str = ""):
    caregiver = request.state.caregiver
    cat = list(dict.fromkeys(c for c in cat if c in CATEGORY_LABELS))
    sort = "asc" if sort == "asc" else "desc"
    q = q.strip()[:100]
    rows = care_model.list_residents(caregiver["care_center_id"], cat, sort)
    if q:
        rows = [r for r in rows if q.casefold() in r["username"].casefold()]
    return templates.TemplateResponse(
        request=request,
        name="care/residents.html",
        context={
            "page": "residents",
            "caregiver": caregiver,
            "residents": rows,
            "q": q,
            "selected_categories": cat,
            "sort": sort,
            "category_labels": CATEGORY_LABELS,
        },
    )


@router.get("/residents/{user_id}")
def resident_detail(request: Request, user_id: int, range: str = "week", back: str = ""):
    caregiver = request.state.caregiver
    if not care_model.resident_belongs_to_center(user_id, caregiver["care_center_id"]):
        raise HTTPException(status_code=404, detail="找不到這位使用者")

    if range not in ("week", "month", "year"):
        range = "week"

    overview = care_model.get_resident_overview(user_id)
    trend = care_model.get_resident_trend(user_id, range)
    breakdown = care_model.get_resident_exercise_breakdown(user_id, range)
    diet = care_model.get_resident_diet_trend(user_id)

    return templates.TemplateResponse(
        request=request,
        name="care/resident_detail.html",
        context={
            "page": "residents",
            "caregiver": caregiver,
            "resident": overview,
            "trend": trend,
            "breakdown": breakdown,
            "diet": diet,
            "range": range,
            "back": back[:1000],
            "range_label": RANGE_LABELS[range],
            "category_labels": CATEGORY_LABELS,
        },
    )
