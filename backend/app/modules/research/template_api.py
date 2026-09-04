"""极简测试 API"""

from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["test"])


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
