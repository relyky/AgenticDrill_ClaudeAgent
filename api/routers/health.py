from fastapi import APIRouter
from __init__ import SERVICE_NAME, VERSION

router = APIRouter()

@router.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service_name": SERVICE_NAME,
        "version": VERSION,
    }
