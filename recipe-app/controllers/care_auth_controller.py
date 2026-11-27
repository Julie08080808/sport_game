"""照護中心後台登入 / 登出頁面（這兩條路由本身不需要登入）。"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models import care_model
from services import care_auth

router = APIRouter(prefix="/care", tags=["Care Portal Login"])
templates = Jinja2Templates(directory="views")


def _render_login(request: Request, next_path: str, error: str = "", username: str = "", status_code: int = 200):
    response = templates.TemplateResponse(
        request=request,
        name="care/login.html",
        context={"next": next_path, "error": error, "username": username},
        status_code=status_code,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/login")
def login_page(request: Request, next: str = "/care", logged_out: int = 0):
    next_path = care_auth.safe_next(next)
    if care_auth.read_session_cookie(request.cookies.get(care_auth.COOKIE_NAME)):
        return RedirectResponse(url=next_path, status_code=303)
    return _render_login(request, next_path, error="已登出" if logged_out else "")


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    next: str = Form("/care"),
):
    next_path = care_auth.safe_next(next)
    key = care_auth.client_key(request)

    wait = care_auth.seconds_locked(key)
    if wait:
        minutes = (wait + 59) // 60
        return _render_login(
            request, next_path,
            error=f"密碼錯誤次數太多，請 {minutes} 分鐘後再試",
            username=username, status_code=429,
        )

    caregiver = care_model.authenticate_caregiver(username, password)
    if not caregiver:
        care_auth.record_failure(key)
        return _render_login(
            request, next_path, error="帳號或密碼錯誤",
            username=username, status_code=401,
        )

    # 簽章需要目前的密碼雜湊；authenticate_caregiver 沒有回傳，這裡再查一次完整資料。
    full = care_model.get_caregiver_for_session(caregiver["caregiver_id"])

    care_auth.clear_failures(key)
    response = RedirectResponse(url=next_path, status_code=303)
    response.set_cookie(
        key=care_auth.COOKIE_NAME,
        value=care_auth.create_session_cookie(full),
        max_age=care_auth.session_hours() * 3600,
        path=care_auth.COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=care_auth.cookie_secure(),
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/care/login?logged_out=1", status_code=303)
    response.delete_cookie(
        key=care_auth.COOKIE_NAME,
        path=care_auth.COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=care_auth.cookie_secure(),
    )
    return response
