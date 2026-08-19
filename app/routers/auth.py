"""Вход и выход."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.auth import authenticate, get_current_user, login_user, logout_user
from app.database import get_session
from app.models import User, UserRole
from app.web import flash, render

router = APIRouter()

_ROLE_HOME = {
    UserRole.RESIDENT: "/dzivoklis",
    UserRole.MANAGER: "/parvalde",
    UserRole.SUPERADMIN: "/admin",
}


@router.get("/login")
def login_form(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(_ROLE_HOME.get(current_user.role, "/"), 303)
    return render(request, "login.html", current_user=None)


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = authenticate(session, email, password)
    if not user:
        flash(request, "Nepareizs e-pasts vai parole.", "error")
        return RedirectResponse("/login", 303)
    login_user(request, user)
    flash(request, f"Sveiki, {user.full_name}!", "success")
    return RedirectResponse(_ROLE_HOME.get(user.role, "/"), 303)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", 303)
