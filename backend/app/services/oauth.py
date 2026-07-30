"""카카오·구글 OAuth 인가 코드(Authorization Code)를 사용자 정보로 교환한다.
클라이언트 시크릿은 절대 프론트엔드로 내려가지 않고, 이 서버 코드에서만 사용한다."""
import httpx
from fastapi import HTTPException

from app import config


async def exchange_kakao_code(code: str) -> dict:
    """카카오 인가 코드 → {provider_id, email, nickname}"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": config.KAKAO_REST_API_KEY,
                "client_secret": config.KAKAO_CLIENT_SECRET,
                "redirect_uri": config.KAKAO_REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"카카오 토큰 발급 실패: {token_res.text}")
        access_token = token_res.json()["access_token"]

        user_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"카카오 사용자 정보 조회 실패: {user_res.text}")
        user = user_res.json()

    account = user.get("kakao_account") or {}
    profile = account.get("profile") or {}
    return {
        "provider_id": str(user["id"]),
        "email": account.get("email"),  # 이메일 동의항목 미설정 시 None일 수 있음
        "nickname": profile.get("nickname") or "카카오 사용자",
    }


async def exchange_google_code(code: str) -> dict:
    """구글 인가 코드 → {provider_id, email, nickname}"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": config.GOOGLE_REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"구글 토큰 발급 실패: {token_res.text}")
        access_token = token_res.json()["access_token"]

        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"구글 사용자 정보 조회 실패: {user_res.text}")
        user = user_res.json()

    return {
        "provider_id": user["sub"],
        "email": user.get("email"),
        "nickname": user.get("name") or "구글 사용자",
    }
