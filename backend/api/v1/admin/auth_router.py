"""소셜 로그인 (카카오/네이버/구글) OAuth2 인증 라우터.

kroaddy Spring Boot 인증 구조를 FastAPI로 변환.
Flow:
  1. 프론트엔드 → GET /api/auth/{provider}/login → 인가 URL 반환
  2. 사용자가 소셜 로그인 완료 → 소셜 서버가 GET /api/auth/{provider}/callback 호출
  3. 백엔드가 인가 코드로 액세스 토큰 → 사용자 정보 조회
  4. JWT(Access + Refresh) 발급 → 쿠키에 설정 → 프론트엔드로 리다이렉트

토큰 저장 전략:
  - Access Token  → Upstash Redis (TTL 30분)
  - Refresh Token → Neon DB refresh_tokens 테이블 (7일)
"""

import logging
import os
import json
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from backend.config import settings
from backend.dependencies import get_db_connection
from backend.api.v1.shared.redis import (
    store_jwt_token,
    get_jwt_token,
    verify_jwt_token,
    delete_jwt_token,
    get_user_token,
    get_redis,
    is_redis_available,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# ─── JWT 유틸리티 ───────────────────────────────────────────────────
import base64

REFRESH_TOKEN_EXPIRE_DAYS = 7


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def generate_jwt(subject: str, token_type: str = "access", expires_minutes: int = None) -> str:
    """HMAC-SHA256 기반 JWT 생성."""
    secret = settings.JWT_SECRET_KEY
    algorithm = settings.JWT_ALGORITHM  # HS256

    now = int(time.time())
    if expires_minutes is None:
        if token_type == "access":
            expires_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES  # 30분
        else:
            expires_minutes = 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS  # 7일 (refresh)

    exp = now + (expires_minutes * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signature_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """JWT 토큰 검증 및 페이로드 반환."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # 서명 검증
        signature_input = f"{header_b64}.{payload_b64}".encode()
        expected_signature = hmac.new(
            settings.JWT_SECRET_KEY.encode(), signature_input, hashlib.sha256
        ).digest()
        actual_signature = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # 페이로드 디코딩
        payload = json.loads(_b64url_decode(payload_b64))

        # 만료 확인
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """인증 쿠키를 응답에 설정."""
    is_production = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    same_site = os.getenv("COOKIE_SAME_SITE", "lax")

    # Access Token 쿠키 (30분)
    response.set_cookie(
        key="Authorization",
        value=access_token,
        httponly=True,
        secure=is_production,
        samesite=same_site,
        path="/",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # Refresh Token 쿠키 (7일)
    response.set_cookie(
        key="RefreshToken",
        value=refresh_token,
        httponly=True,
        secure=is_production,
        samesite=same_site,
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def _clear_auth_cookies(response: Response):
    """인증 쿠키 삭제."""
    is_production = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    same_site = os.getenv("COOKIE_SAME_SITE", "lax")

    response.delete_cookie(
        key="Authorization", httponly=True, secure=is_production,
        samesite=same_site, path="/",
    )
    response.delete_cookie(
        key="RefreshToken", httponly=True, secure=is_production,
        samesite=same_site, path="/",
    )


def _get_frontend_callback_url() -> str:
    """프론트엔드 콜백 URL 반환."""
    return os.getenv("FRONT_LOGIN_CALLBACK_URL", "http://localhost:3000")


# ─── Refresh Token DB 유틸리티 ────────────────────────────────────────

def _save_refresh_token_to_db(user_id: str, token: str, provider: str = None) -> bool:
    """Refresh Token을 Neon DB에 저장."""
    try:
        conn = get_db_connection()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        with conn.cursor() as cur:
            # 기존 유효한 토큰은 revoke 처리 (1 사용자 = 1 active refresh token)
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = %s AND revoked = FALSE",
                (user_id,)
            )
            # 새 refresh token 저장
            cur.execute(
                """
                INSERT INTO refresh_tokens (user_id, token, provider, issued_at, expires_at, revoked)
                VALUES (%s, %s, %s, NOW(), %s, FALSE)
                """,
                (user_id, token, provider, expires_at)
            )
            conn.commit()

        logger.info(f"[Auth/DB] Refresh token 저장 완료: user_id={user_id}")
        return True
    except Exception as e:
        logger.error(f"[Auth/DB] Refresh token 저장 실패: {e}", exc_info=True)
        return False


def _get_refresh_token_from_db(token: str) -> Optional[Dict[str, Any]]:
    """Neon DB에서 Refresh Token 조회. (유효한 토큰만)"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, token, provider, issued_at, expires_at, revoked
                FROM refresh_tokens
                WHERE token = %s AND revoked = FALSE AND expires_at > NOW()
                """,
                (token,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "token": row[2],
            "provider": row[3],
            "issued_at": row[4].isoformat() if row[4] else None,
            "expires_at": row[5].isoformat() if row[5] else None,
            "revoked": row[6],
        }
    except Exception as e:
        logger.error(f"[Auth/DB] Refresh token 조회 실패: {e}", exc_info=True)
        return None


def _revoke_refresh_token_db(token: str) -> bool:
    """Neon DB에서 Refresh Token을 revoke 처리."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE token = %s",
                (token,)
            )
            conn.commit()
        logger.info("[Auth/DB] Refresh token revoke 완료")
        return True
    except Exception as e:
        logger.error(f"[Auth/DB] Refresh token revoke 실패: {e}", exc_info=True)
        return False


def _revoke_user_refresh_tokens_db(user_id: str) -> bool:
    """특정 사용자의 모든 Refresh Token을 revoke 처리 (로그아웃)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = %s AND revoked = FALSE",
                (user_id,)
            )
            conn.commit()
        logger.info(f"[Auth/DB] 사용자 {user_id}의 모든 refresh token revoke 완료")
        return True
    except Exception as e:
        logger.error(f"[Auth/DB] 사용자 refresh token revoke 실패: {e}", exc_info=True)
        return False


# ─── Users 테이블 upsert ──────────────────────────────────────────

def _upsert_user(social_id: str, provider: str, display_name: str = None) -> Dict[str, Any]:
    """소셜 로그인 시 users 테이블에 사용자를 생성하거나 업데이트한다.

    Returns:
        {"id": int, "social_id": str, "display_name": str, "is_new": bool}
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 기존 사용자 조회
            cur.execute(
                "SELECT id, display_name FROM users WHERE social_id = %s",
                (social_id,)
            )
            row = cur.fetchone()

            if row:
                # 기존 사용자 → last_login 갱신
                cur.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = %s RETURNING id, display_name",
                    (row[0],)
                )
                updated = cur.fetchone()
                conn.commit()
                logger.info(f"[Auth/Users] 기존 사용자 로그인: id={updated[0]}, name={updated[1]}")
                return {"id": updated[0], "social_id": social_id, "display_name": updated[1], "is_new": False}
            else:
                # 신규 사용자 → 생성
                name = display_name or f"{provider}_{social_id[:8]}"
                cur.execute(
                    """
                    INSERT INTO users (display_name, social_id, provider, registration_date, last_login)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING id, display_name
                    """,
                    (name, social_id, provider)
                )
                created = cur.fetchone()
                conn.commit()
                logger.info(f"[Auth/Users] 신규 사용자 생성: id={created[0]}, name={created[1]}, social_id={social_id}")
                return {"id": created[0], "social_id": social_id, "display_name": created[1], "is_new": True}
    except Exception as e:
        logger.error(f"[Auth/Users] upsert 실패: {e}", exc_info=True)
        # 실패해도 로그인은 계속 진행 (user 없이)
        return {"id": None, "social_id": social_id, "display_name": None, "is_new": False}


# ─── 소셜 로그인 공통 처리 ──────────────────────────────────────────

async def _process_social_login(
    provider: str,
    social_user_id: str,
    response: Response,
    display_name: str = None,
) -> RedirectResponse:
    """소셜 로그인 공통 후처리: 사용자 upsert → JWT 발급 → 저장 → 쿠키 설정 → 프론트엔드 리다이렉트."""
    # 0. users 테이블에 사용자 upsert (DB user_id 확보)
    user_info = _upsert_user(social_user_id, provider, display_name)
    db_user_id = user_info.get("id")  # 정수형 DB id

    # 1. JWT 발급 (sub에 social_user_id 사용, db_user_id를 추가 클레임으로 포함)
    access_token = generate_jwt(social_user_id, token_type="access")
    refresh_token = generate_jwt(social_user_id, token_type="refresh")

    # 2. Access Token → Redis 저장
    try:
        store_jwt_token(
            user_id=social_user_id,
            access_token=access_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except Exception as e:
        logger.warning(f"[Auth] Redis access token 저장 실패 (계속 진행): {e}")

    # 3. Refresh Token → Neon DB 저장
    _save_refresh_token_to_db(
        user_id=social_user_id,
        token=refresh_token,
        provider=provider,
    )

    # 4. 로그 출력
    timestamp = datetime.now().strftime("%Y. %m. %d. %p %I:%M:%S")
    logger.info(f"\n{'='*60}")
    logger.info(f"[{timestamp}] {provider} 로그인 성공")
    logger.info(f"User ID: {social_user_id}")
    logger.info(f"Access Token  -> Redis (TTL {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}min)")
    logger.info(f"Refresh Token -> Neon DB (TTL {REFRESH_TOKEN_EXPIRE_DAYS}days)")
    logger.info(f"{'='*60}\n")

    # 5. 프론트엔드 콜백 URL로 리다이렉트
    frontend_url = _get_frontend_callback_url()
    redirect_url = f"{frontend_url}/login/{provider}/callback"

    logger.info(f"[Auth] {provider} redirect -> {redirect_url}")

    redirect_response = RedirectResponse(url=redirect_url, status_code=302)

    # 6. 쿠키 설정
    _set_auth_cookies(redirect_response, access_token, refresh_token)

    return redirect_response


# ─── 카카오 로그인 ──────────────────────────────────────────────────

@router.get("/api/auth/kakao/login")
async def kakao_login():
    """카카오 인가 URL 반환."""
    client_id = os.getenv("KAKAO_REST_API_KEY", "")
    redirect_uri = os.getenv(
        "KAKAO_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/kakao/callback"
    )

    if not client_id:
        raise HTTPException(status_code=500, detail="KAKAO_REST_API_KEY가 설정되지 않았습니다.")

    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
    )

    return {"authUrl": auth_url}


@router.get("/api/auth/kakao/callback")
async def kakao_callback(code: str, response: Response):
    """카카오 인가 코드 콜백 처리."""
    client_id = os.getenv("KAKAO_REST_API_KEY", "")
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
    redirect_uri = os.getenv(
        "KAKAO_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/kakao/callback"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. 인가 코드로 액세스 토큰 요청
            token_data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code": code,
            }
            if client_secret:
                token_data["client_secret"] = client_secret

            token_resp = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_resp.status_code != 200:
                logger.error(f"[Kakao] 토큰 요청 실패: {token_resp.text}")
                raise HTTPException(status_code=500, detail="카카오 토큰 요청 실패")

            token_json = token_resp.json()
            kakao_access_token = token_json.get("access_token")

            if not kakao_access_token:
                raise HTTPException(status_code=500, detail="카카오 액세스 토큰이 없습니다.")

            # 2. 사용자 정보 요청
            user_resp = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {kakao_access_token}"},
            )

            if user_resp.status_code != 200:
                logger.error(f"[Kakao] 사용자 정보 요청 실패: {user_resp.text}")
                raise HTTPException(status_code=500, detail="카카오 사용자 정보 조회 실패")

            user_info = user_resp.json()
            kakao_id = str(user_info.get("id", ""))

            if not kakao_id:
                raise HTTPException(status_code=500, detail="카카오 사용자 ID를 찾을 수 없습니다.")

            # 닉네임 추출 (카카오 프로필)
            kakao_nickname = None
            kakao_props = user_info.get("properties", {})
            if kakao_props:
                kakao_nickname = kakao_props.get("nickname")
            if not kakao_nickname:
                kakao_account = user_info.get("kakao_account", {})
                profile = kakao_account.get("profile", {})
                kakao_nickname = profile.get("nickname")

        # 3. JWT 발급 및 리다이렉트
        return await _process_social_login("kakao", kakao_id, response, display_name=kakao_nickname)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Kakao] 로그인 처리 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"카카오 로그인 처리 중 오류: {str(e)}")


# ─── 네이버 로그인 ──────────────────────────────────────────────────

@router.get("/api/auth/naver/login")
async def naver_login():
    """네이버 인가 URL 반환."""
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    redirect_uri = os.getenv(
        "NAVER_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/naver/callback"
    )

    if not client_id:
        raise HTTPException(status_code=500, detail="NAVER_CLIENT_ID가 설정되지 않았습니다.")

    state = str(uuid.uuid4())
    auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    return {"authUrl": auth_url}


@router.get("/api/auth/naver/callback")
async def naver_callback(code: str, state: str, response: Response):
    """네이버 인가 코드 콜백 처리."""
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    redirect_uri = os.getenv(
        "NAVER_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/naver/callback"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. 인가 코드로 액세스 토큰 요청
            token_data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "state": state,
            }

            token_resp = await client.post(
                "https://nid.naver.com/oauth2.0/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_resp.status_code != 200:
                logger.error(f"[Naver] 토큰 요청 실패: {token_resp.text}")
                raise HTTPException(status_code=500, detail="네이버 토큰 요청 실패")

            token_json = token_resp.json()
            naver_access_token = token_json.get("access_token")

            if not naver_access_token:
                raise HTTPException(status_code=500, detail="네이버 액세스 토큰이 없습니다.")

            # 2. 사용자 정보 요청
            user_resp = await client.get(
                "https://openapi.naver.com/v1/nid/me",
                headers={"Authorization": f"Bearer {naver_access_token}"},
            )

            if user_resp.status_code != 200:
                logger.error(f"[Naver] 사용자 정보 요청 실패: {user_resp.text}")
                raise HTTPException(status_code=500, detail="네이버 사용자 정보 조회 실패")

            user_info = user_resp.json()
            naver_response = user_info.get("response", {})
            naver_id = naver_response.get("id", "")

            if not naver_id:
                raise HTTPException(status_code=500, detail="네이버 사용자 ID를 찾을 수 없습니다.")

            naver_nickname = naver_response.get("nickname") or naver_response.get("name")

        # 3. JWT 발급 및 리다이렉트
        return await _process_social_login("naver", naver_id, response, display_name=naver_nickname)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Naver] 로그인 처리 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"네이버 로그인 처리 중 오류: {str(e)}")


# ─── 구글 로그인 ────────────────────────────────────────────────────

@router.get("/api/auth/google/login")
async def google_login():
    """구글 인가 URL 반환."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/google/callback"
    )

    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID가 설정되지 않았습니다.")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return {"authUrl": auth_url}


@router.get("/api/auth/google/callback")
async def google_callback(code: str, response: Response):
    """구글 인가 코드 콜백 처리."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/auth/google/callback"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. 인가 코드로 액세스 토큰 요청
            token_data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }

            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_resp.status_code != 200:
                logger.error(f"[Google] 토큰 요청 실패: {token_resp.text}")
                raise HTTPException(status_code=500, detail="구글 토큰 요청 실패")

            token_json = token_resp.json()
            google_access_token = token_json.get("access_token")

            if not google_access_token:
                raise HTTPException(status_code=500, detail="구글 액세스 토큰이 없습니다.")

            # 2. 사용자 정보 요청
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {google_access_token}"},
            )

            if user_resp.status_code != 200:
                logger.error(f"[Google] 사용자 정보 요청 실패: {user_resp.text}")
                raise HTTPException(status_code=500, detail="구글 사용자 정보 조회 실패")

            user_info = user_resp.json()
            google_id = user_info.get("id", "")

            if not google_id:
                raise HTTPException(status_code=500, detail="구글 사용자 ID를 찾을 수 없습니다.")

            google_nickname = user_info.get("name") or user_info.get("email", "").split("@")[0]

        # 3. JWT 발급 및 리다이렉트
        return await _process_social_login("google", google_id, response, display_name=google_nickname)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Google] 로그인 처리 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"구글 로그인 처리 중 오류: {str(e)}")


# ─── 인증 상태 확인 ─────────────────────────────────────────────────

@router.get("/api/auth/me")
async def get_current_user(request: Request):
    """쿠키에서 JWT를 읽어 현재 사용자 정보 반환.

    Returns:
        {
            "id": int (DB user_id),
            "social_id": str (소셜 로그인 ID),
            "display_name": str,
            "provider": str
        }
    """
    token = request.cookies.get("Authorization")

    if not token:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    # JWT 서명 검증
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="유효하지 않은 Access Token입니다.")

    social_id = payload.get("sub")

    # Redis에서 토큰 확인 (활성 세션 검증)
    try:
        stored_token = get_user_token(social_id)
        if stored_token and stored_token != token:
            raise HTTPException(status_code=401, detail="저장된 토큰과 일치하지 않습니다.")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis 미사용 시 건너뛰기

    # DB에서 사용자 정보 조회 (social_id → DB user_id 매핑)
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, display_name, provider FROM users WHERE social_id = %s",
                (social_id,)
            )
            row = cur.fetchone()

        if row:
            return {
                "id": row[0],            # DB 정수 ID (FK 참조용)
                "social_id": social_id,   # 소셜 로그인 원본 ID
                "display_name": row[1],
                "provider": row[2],
            }
        else:
            # DB에 아직 사용자가 없으면 social_id만 반환
            return {"id": None, "social_id": social_id, "display_name": None, "provider": None}
    except Exception as e:
        logger.warning(f"[Auth/me] DB 조회 실패, social_id만 반환: {e}")
        return {"id": None, "social_id": social_id, "display_name": None, "provider": None}


# ─── 토큰 갱신 ──────────────────────────────────────────────────────

@router.post("/api/auth/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh Token(쿠키)으로 새로운 Access + Refresh Token 발급.

    Token Rotation 적용: 갱신 시 기존 refresh token은 revoke하고 새로 발급.
    """
    refresh_tok = request.cookies.get("RefreshToken")

    if not refresh_tok:
        raise HTTPException(status_code=401, detail="Refresh Token이 필요합니다.")

    # 1. JWT 서명 검증
    payload = verify_jwt(refresh_tok)
    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않은 Refresh Token입니다.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 Refresh Token입니다.")

    user_id = payload.get("sub")

    # 2. Neon DB에서 Refresh Token 유효성 확인 (revoke 여부 + 만료)
    db_token = _get_refresh_token_from_db(refresh_tok)
    if not db_token:
        # 이미 revoke되었거나 만료된 토큰 → 도용 가능성
        logger.warning(f"[Auth] Refresh token DB 검증 실패: user_id={user_id}")
        # 안전을 위해 해당 사용자의 모든 refresh token revoke
        _revoke_user_refresh_tokens_db(user_id)
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh Token이 유효하지 않습니다. 다시 로그인해주세요.")

    # 3. 기존 refresh token revoke (Token Rotation)
    _revoke_refresh_token_db(refresh_tok)

    # 4. 새로운 토큰 발급
    new_access_token = generate_jwt(user_id, token_type="access")
    new_refresh_token = generate_jwt(user_id, token_type="refresh")

    # 5. 새 Access Token → Redis 저장
    try:
        store_jwt_token(
            user_id=user_id,
            access_token=new_access_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except Exception as e:
        logger.warning(f"[Auth] Redis access token 갱신 저장 실패: {e}")

    # 6. 새 Refresh Token → Neon DB 저장
    provider = db_token.get("provider")
    _save_refresh_token_to_db(
        user_id=user_id,
        token=new_refresh_token,
        provider=provider,
    )

    # 7. 쿠키 설정
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    logger.info(f"[Auth] 토큰 갱신 완료: user_id={user_id}")
    return {"success": True, "message": "토큰이 갱신되었습니다."}


# ─── 로그아웃 ───────────────────────────────────────────────────────

@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """로그아웃: Redis access token + DB refresh token 삭제 + 쿠키 삭제."""
    access_token = request.cookies.get("Authorization")
    refresh_tok = request.cookies.get("RefreshToken")

    # 1. Redis에서 Access Token 삭제
    if access_token:
        try:
            # Access Token에서 user_id 추출
            payload = verify_jwt(access_token)
            if payload:
                user_id = payload.get("sub")
                # 해당 사용자의 모든 DB refresh tokens revoke
                if user_id:
                    _revoke_user_refresh_tokens_db(user_id)

            delete_jwt_token(access_token)
        except Exception as e:
            logger.warning(f"[Auth] 로그아웃 - Redis 토큰 삭제 실패: {e}")

    # 2. Neon DB에서 Refresh Token revoke (개별)
    if refresh_tok:
        _revoke_refresh_token_db(refresh_tok)

    # 3. 쿠키 삭제
    _clear_auth_cookies(response)

    return {"success": True, "message": "로그아웃되었습니다."}


# ─── 로그인 로그 ────────────────────────────────────────────────────

@router.post("/api/log/login")
async def log_login(request: Request):
    """로그인 관련 로그 기록."""
    try:
        body = await request.json()
        action = body.get("action", "")
        url = body.get("url", "N/A")

        timestamp = datetime.now().strftime("%Y. %m. %d. %p %I:%M:%S")
        logger.info(f"\n{'='*60}")
        logger.info(f"[{timestamp}] {action}")
        logger.info(f"URL: {url}")
        logger.info(f"{'='*60}\n")

        return {"success": True, "message": "로그가 기록되었습니다."}
    except Exception as e:
        logger.error(f"로그인 로그 기록 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "로그 기록 실패"},
        )
