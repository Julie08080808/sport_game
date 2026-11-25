"""管理後台登入 / 登出頁面（這兩條路由本身不需要登入）。"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from services import admin_auth

router = APIRouter(prefix="/admin", tags=["Admin Web Login"])
templates = Jinja2Templates(directory="views")


def _render_login(request: Request, next_path: str, error: str = "", username: str = "", status_code: int = 200):
    response = templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"next": next_path, "error": error, "username": username},
        status_code=status_code,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/login")
def login_page(request: Request, next: str = "/admin", logged_out: int = 0):
    next_path = admin_auth.safe_next(next)
    if admin_auth.read_session_cookie(request.cookies.get(admin_auth.COOKIE_NAME)):
        return RedirectResponse(url=next_path, status_code=303)
    return _render_login(request, next_path, error="已登出" if logged_out else "")


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    next: str = Form("/admin"),
):
    next_path = admin_auth.safe_next(next)
    key = admin_auth.client_key(request)

    wait = admin_auth.seconds_locked(key)
    if wait:
        minutes = (wait + 59) // 60
        return _render_login(
            request, next_path,
            error=f"密碼錯誤次數太多，請 {minutes} 分鐘後再試",
            username=username, status_code=429,
        )

    if not admin_auth.check_credentials(username, password):
        admin_auth.record_failure(key)
        return _render_login(
            request, next_path, error="帳號或密碼錯誤",
            username=username, status_code=401,
        )

    admin_auth.clear_failures(key)
    response = RedirectResponse(url=next_path, status_code=303)
    response.set_cookie(
        key=admin_auth.COOKIE_NAME,
        value=admin_auth.create_session_cookie(username.strip()),
        max_age=admin_auth.session_hours() * 3600,
        path=admin_auth.COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=admin_auth.cookie_secure(),
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/admin/login?logged_out=1", status_code=303)
    response.delete_cookie(
        key=admin_auth.COOKIE_NAME,
        path=admin_auth.COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=admin_auth.cookie_secure(),
    )
    return response
