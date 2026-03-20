import json
import logging
import logging.config
from pathlib import Path
from typing import Annotated

import httpx
import typer
from mrok.agent import ziticorn

from app.config import settings
from app.logging import get_logging_config
from app.utils import get_instance_external_id, get_meta

logger = logging.getLogger(__name__)


app = typer.Typer(help="Marketplace extension bootstrap and runner.")


@app.command()
def main(
    ziti_load_timeout_ms: Annotated[
        int,
        typer.Option(
            "--ziti-load-timeout-ms",
            help="Timeout (ms) waiting for Ziti to load.",
            show_default=True,
        ),
    ] = 5000,
    server_workers: Annotated[
        int,
        typer.Option(
            "--server-workers",
            "-w",
            help="Number of workers.",
            show_default=True,
        ),
    ] = 4,
    server_backlog: Annotated[
        int,
        typer.Option(
            "--server-backlog",
            help="TCP socket listen backlog.",
            show_default=True,
        ),
    ] = 2048,
    server_timeout_keep_alive: Annotated[
        int,
        typer.Option(
            "--server-timeout-keep-alive",
            help="Seconds to keep idle HTTP connections open.",
            show_default=True,
        ),
    ] = 5,
    server_limit_concurrency: Annotated[
        int | None,
        typer.Option(
            "--server-limit-concurrency",
            help="Maximum number of concurrent requests per worker.",
            show_default=True,
        ),
    ] = None,
    server_limit_max_requests: Annotated[
        int | None,
        typer.Option(
            "--server-limit-max-requests",
            help="Restart a worker after handling this many requests.",
            show_default=True,
        ),
    ] = None,
    server_reload: Annotated[
        bool,
        typer.Option(
            "--server-reload",
            "-r",
            help="Enable server auto-reload. Default: False",
            show_default=True,
        ),
    ] = False,
    events_publishers_port: Annotated[
        int,
        typer.Option(
            "--events-publishers-port",
            help=(
                "TCP port where the mrok agent "
                "should connect to publish to request/response messages."
            ),
            show_default=True,
        ),
    ] = 50000,
    events_subscribers_port: Annotated[
        int,
        typer.Option(
            "--events-subscribers-port",
            help=(
                "TCP port where the mrok agent should listen for incoming subscribers "
                "connections for request/response messages."
            ),
            show_default=True,
        ),
    ] = 50001,
    events_metrics_collect_interval: Annotated[
        float,
        typer.Option(
            "--events-metrics-collect-interval",
            help="Interval in seconds between events metrics collect.",
            show_default=True,
        ),
    ] = 5.0,
):
    logging_config = get_logging_config()
    logging.config.dictConfig(logging_config)

    if not settings.get("extension_id"):
        raise Exception("No Extension ID has been provided.")
    if not settings.get("base_url"):
        raise Exception("No Marketplace API Url has been provided.")
    if not settings.get("api_key"):
        raise Exception("No Marketplace Vendor API Key has been provided.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.api_key}",
    }

    external_id = get_instance_external_id()

    identity_file = Path(__file__).parent.parent.parent.resolve() / f"{external_id}_identity.json"

    logger.info(
        f"Boostrap instance for extension {settings.extension_id}: externalId={external_id}",
    )



    data = {"externalId": external_id, "meta": get_meta()}
    for evtinfo in data["meta"]["events"]:
        msg = (
            f"Register event subscription to {evtinfo['event']} "
            f"(task={evtinfo['task']}, filter={evtinfo.get('condition', '-')}) "
            f"-> {evtinfo['path']}"
        )
        logger.info(msg)

    if not identity_file.exists():
        logger.info(
            f"Request new identity for {settings.extension_id}: externalId={external_id}",
        )
        data["channel"] = {}
    else:
        identity = json.load(open(identity_file))
        identity_extension = identity.get("mrok", {}).get("extension", "")
        if identity_extension.lower() != settings.extension_id.lower():
            logger.warning(
                f"The existing identity belongs to the extension {identity_extension}. "
                f"Request new identity for {settings.extension_id}: externalId={external_id}",
            )
            data["channel"] = {}

    response = httpx.post(
        f"{settings.base_url}/integration/extensions/{settings.extension_id}/instances",
        headers=headers,
        json=data,
        timeout=httpx.Timeout(connect=1.0, pool=1.0, read=180.0, write=30.0),
    )
    response.raise_for_status()
    response_data = response.json()
    identity = response_data.get("channel", {}).get("identity")
    if identity:
        logger.info(f"Save instance identity to {identity_file}")
        with open(identity_file, "w") as writer:
            json.dump(identity, writer)
    logger.info(
        f"Instance bootstrap for extension {settings.extension_id} completed: "
        f"{response_data['id']}"
    )
    ziticorn.run(
        "app.extension:app",
        str(identity_file),
        ziti_load_timeout_ms=ziti_load_timeout_ms,
        server_workers=server_workers,
        server_reload=server_reload,
        server_backlog=server_backlog,
        server_timeout_keep_alive=server_timeout_keep_alive,
        server_limit_concurrency=server_limit_concurrency,
        server_limit_max_requests=server_limit_max_requests,
        events_metrics_collect_interval=events_metrics_collect_interval,
        events_publishers_port=events_publishers_port,
        events_subscribers_port=events_subscribers_port,
        logging_config=logging_config,
    )


if __name__ == "__main__":
    app()
