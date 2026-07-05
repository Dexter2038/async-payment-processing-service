from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])
