from devtools import pformat
from fastapi import APIRouter, Request

from app.auth import AuthContext
from app.client import ExtensionClient, InstallationClient
from app.config import settings
from app.schema import Event, EventResponse

router = APIRouter(prefix="/api/v1")


@router.post("/events/orders")
async def process_order(
    extension_client: ExtensionClient,
    installation_client: InstallationClient,
    event: Event,
):
    print(f"received event: {pformat(event, highlight=True)}")
    task = await extension_client.start_task(event.task.id)
    if task and task["parameters"]["accountId"] != settings.my_account_id:
        await extension_client.update_task(
            event.task.id,
            {
                "description": (
                    f"{task["description"]}<br/>"
                    "The task has been skipped by the extension"
                ),
            }
        )
        await extension_client.complete_task(event.task.id)
        return EventResponse.ok()
    order = await installation_client.get_order(event.object.id)

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



@router.post("/cron/dojob")
async def cron_job(ctx: AuthContext):
    print(ctx)
    return EventResponse.ok()
