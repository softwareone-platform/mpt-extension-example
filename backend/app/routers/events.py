import logging

from fastapi import APIRouter

from app.auth import AuthContext
from app.dependencies import ExtensionClient, ExtensionContext, InstallationClient
from app.schema import Event, EventResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events")


@router.post("/commerce/orders")
async def process_order(
    event: Event,
    ctx: AuthContext,
    ext_ctx: ExtensionContext,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> EventResponse:
    """Provision service quickly (completes within timeout)."""
    order_id = event.object.id
    task_id = event.task.id
    # 1. Start task
    task = await ext_client.start_task(task_id, ext_ctx.instance_id)

    try:
        # 2. Fetch order
        order = await client.get_order(order_id)

        # 3. Check status — skip if not processing
        if order["status"] != "Processing":
            await ext_client.complete_task(task_id)
            return EventResponse.ok()

        # 4. Provision service in external system
        # service_id = await provision_service(
        #     order,
        #     api_key=settings.external_api_key,
        # )

        # 5. Create subscription in platform
        # await client.create_subscription(
        #     order_id,
        #     external_id=service_id,
        # )

        # 6. Complete order
        # await client.complete_order(order_id)

        # 7. Complete task
        await ext_client.complete_task(task_id)

        return EventResponse.ok()

    except Exception as exc:
        await ext_client.update_task(task_id, {
            "description": f"{task["description"]} - {exc}"
        })

        await ext_client.reschedule_task(task_id)
        return EventResponse.reschedule(seconds=300)
