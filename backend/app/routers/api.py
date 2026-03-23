from fastapi import APIRouter

from app.dependencies import AuthContext, ExtensionContext


router = APIRouter(prefix="/api/v1")


@router.get("/me")
async def who_am_i(
    auth_ctx: AuthContext,
    ext_ctx: ExtensionContext,
):
    return {
        "auth": auth_ctx.model_dump(),
        "ext": ext_ctx.model_dump(),
    }
