from fastapi import APIRouter, Request

from app.auth import AuthContext
from app.client import InstallationClient
from app.schema import Event, EventResponse

router = APIRouter(prefix="/api/v1")


@router.post("/events/orders")
async def process_order(event: Event, client: InstallationClient):
    order = await client.get_order(event.object.id)
    print(event.model_dump_json())
    print(order)
    return EventResponse.cancel()


@router.post("/validation/orders")
async def validate_order():
    pass


@router.get("/tasks/synchronize")
async def synchronize(request: Request):
    print(request.headers)


@router.get("/management/whoami")
async def whoami(ctx: AuthContext, client: InstallationClient):
    account = await client.get_account(ctx.account_id)
    user = None if not ctx.user_id else await client.get_user(ctx.user_id)
    token = None if not ctx.token_id else await client.get_token(ctx.token_id)

    return {
        "account": account,
        "token": token,
        "user": user,
    }
