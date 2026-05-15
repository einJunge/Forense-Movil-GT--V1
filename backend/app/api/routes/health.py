from fastapi import APIRouter
router = APIRouter()
@router.get("")
def ok(): return {"status": "ok"}
