from fastapi import APIRouter

from cadis.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": get_settings().health_name}
