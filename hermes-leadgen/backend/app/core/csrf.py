"""Double-submit-cookie CSRF protection for the cookie-based session.

The auth cookie is httpOnly, so a cross-site request can't read it to forge
a matching header — login/refresh sets a second, JS-readable csrf_token
cookie, and every state-changing request must echo it back in the
X-CSRF-Token header.
"""
import secrets

from fastapi import Header, HTTPException, Request, status

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request, x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")) -> None:
    if request.method in SAFE_METHODS:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token or not x_csrf_token or not secrets.compare_digest(cookie_token, x_csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid")
