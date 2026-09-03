from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models import admin_model, admin_test_model

router = APIRouter(prefix="/admin", tags=["Admin Web"])
templates = Jinja2Templates(directory="views")


def _none_if_blank(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value != "" else None


def _int_or_none(value):
    value = _none_if_blank(value)
    return int(value) if value is not None else None


def _task_form_data(
    task_key, task_name, task_description,
    task_category, task_type, task_mode,
    scene_id, npc_id, exercise_type,
    goal_type, target_count, target_seconds,
    input_requirement, required_ball_count,
    recurrence_type, reward_player_exp,
    reward_scene_exp, reward_money,
    required_player_level, expire_policy,
    expire_after_seconds, allow_pause,
    allow_resume, is_initial_unlock, is_active,
):
    return {
        "task_key": task_key.strip(),
        "task_name": task_name.strip(),
        "task_description": _none_if_blank(task_description),
        "task_category": task_category,
        "task_type": task_type,
        "task_mode": task_mode,
        "scene_id": int(scene_id),
        "npc_id": _int_or_none(npc_id),
        "exercise_type": _none_if_blank(exercise_type),
        "goal_type": goal_type,
        "target_count": _int_or_none(target_count),
        "target_seconds": _int_or_none(target_seconds),
        "input_requirement": input_requirement,
        "required_ball_count": int(required_ball_count or 0),
        "recurrence_type": recurrence_type,
        "reward_player_exp": int(reward_player_exp or 0),
        "reward_scene_exp": int(reward_scene_exp or 0),
        "reward_money": int(reward_money or 0),
        "required_player_level": int(required_player_level or 1),
        "expire_policy": expire_policy,
        "expire_after_seconds": _int_or_none(expire_after_seconds),
        "allow_pause": bool(allow_pause),
        "allow_resume": bool(allow_resume),
        "is_initial_unlock": bool(is_initial_unlock),
        "is_active": bool(is_active),
    }


@router.get("")
def dashboard(request: Request):
    data = admin_model.get_dashboard_stats()
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={"page": "dashboard", **data},
    )


@router.get("/tasks")
def tasks(request: Request, q: str = ""):
    rows = admin_model.list_tasks(q)
    return templates.TemplateResponse(
        request=request,
        name="admin/tasks.html",
        context={"page": "tasks", "tasks": rows, "q": q},
    )


@router.get("/tasks/new")
def new_task(request: Request):
    options = admin_model.get_task_form_options()
    return templates.TemplateResponse(
        request=request,
        name="admin/task_form.html",
        context={"page": "tasks", "mode": "new", "task": {}, **options},
    )


@router.post("/tasks/new")
def create_task(
    task_key: str = Form(...),
    task_name: str = Form(...),
    task_description: str = Form(""),
    task_category: str = Form(...),
    task_type: str = Form(...),
    task_mode: str = Form(...),
    scene_id: int = Form(...),
    npc_id: str = Form(""),
    exercise_type: str = Form(""),
    goal_type: str = Form(...),
    target_count: str = Form(""),
    target_seconds: str = Form(""),
    input_requirement: str = Form(...),
    required_ball_count: int = Form(0),
    recurrence_type: str = Form(...),
    reward_player_exp: int = Form(0),
    reward_scene_exp: int = Form(0),
    reward_money: int = Form(0),
    required_player_level: int = Form(1),
    expire_policy: str = Form("none"),
    expire_after_seconds: str = Form(""),
    allow_pause: str | None = Form(None),
    allow_resume: str | None = Form(None),
    is_initial_unlock: str | None = Form(None),
    is_active: str | None = Form(None),
):
    data = _task_form_data(
        task_key, task_name, task_description,
        task_category, task_type, task_mode,
        scene_id, npc_id, exercise_type,
        goal_type, target_count, target_seconds,
        input_requirement, required_ball_count,
        recurrence_type, reward_player_exp,
        reward_scene_exp, reward_money,
        required_player_level, expire_policy,
        expire_after_seconds, allow_pause,
        allow_resume, is_initial_unlock, is_active,
    )
    task_id = admin_model.create_task(data)
    return RedirectResponse(url=f"/admin/tasks/{task_id}/edit?saved=1", status_code=303)


@router.get("/tasks/{task_id}/edit")
def edit_task(request: Request, task_id: int, saved: int = 0):
    task = admin_model.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    options = admin_model.get_task_form_options()
    return templates.TemplateResponse(
        request=request,
        name="admin/task_form.html",
        context={
            "page": "tasks",
            "mode": "edit",
            "task": task,
            "saved": bool(saved),
            **options,
        },
    )


@router.post("/tasks/{task_id}/edit")
def update_task(
    task_id: int,
    task_key: str = Form(...),
    task_name: str = Form(...),
    task_description: str = Form(""),
    task_category: str = Form(...),
    task_type: str = Form(...),
    task_mode: str = Form(...),
    scene_id: int = Form(...),
    npc_id: str = Form(""),
    exercise_type: str = Form(""),
    goal_type: str = Form(...),
    target_count: str = Form(""),
    target_seconds: str = Form(""),
    input_requirement: str = Form(...),
    required_ball_count: int = Form(0),
    recurrence_type: str = Form(...),
    reward_player_exp: int = Form(0),
    reward_scene_exp: int = Form(0),
    reward_money: int = Form(0),
    required_player_level: int = Form(1),
    expire_policy: str = Form("none"),
    expire_after_seconds: str = Form(""),
    allow_pause: str | None = Form(None),
    allow_resume: str | None = Form(None),
    is_initial_unlock: str | None = Form(None),
    is_active: str | None = Form(None),
):
    data = _task_form_data(
        task_key, task_name, task_description,
        task_category, task_type, task_mode,
        scene_id, npc_id, exercise_type,
        goal_type, target_count, target_seconds,
        input_requirement, required_ball_count,
        recurrence_type, reward_player_exp,
        reward_scene_exp, reward_money,
        required_player_level, expire_policy,
        expire_after_seconds, allow_pause,
        allow_resume, is_initial_unlock, is_active,
    )
    admin_model.update_task(task_id, data)
    return RedirectResponse(url=f"/admin/tasks/{task_id}/edit?saved=1", status_code=303)


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int):
    admin_model.toggle_task(task_id)
    return RedirectResponse(url="/admin/tasks", status_code=303)


@router.get("/users")
def users(request: Request, q: str = ""):
    rows = admin_model.list_users(q)
    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={"page": "users", "users": rows, "q": q},
    )


@router.get("/users/{user_id}")
def user_detail(request: Request, user_id: int, replay: int = 0):
    data = admin_model.get_user_detail(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/user_detail.html",
        context={"page": "users", "replay": bool(replay), **data},
    )


@router.post("/users/{user_id}/tasks/{task_id}/replay")
def replay_task(user_id: int, task_id: int):
    result = admin_test_model.restart_task_for_testing(
        user_id=user_id,
        task_id=task_id,
        reason="Admin Web replay",
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Replay failed"))

    return RedirectResponse(url=f"/admin/users/{user_id}?replay=1", status_code=303)
