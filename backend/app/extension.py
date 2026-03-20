from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import api, bypass, deferreds, events, schedules, webhooks

app = FastAPI(
    title="SoftwareOne Marketplace Extension Example",
    description="This is an example of an Extension for the Marketplace Plaform of SoftwareOne",
    swagger_ui_parameters={"showExtensions": False, "showCommonExtensions": False},
    version="5.0.0",
    openapi_url="/bypass/openapi.json",
    docs_url="/bypass/docs",
    redoc_url="/bypass/redoc",
)

app.mount(
    "/static",
    StaticFiles(
        directory=Path(__file__).parent.parent.parent.resolve() / "static",
        html=True,
    ),
    name="static",
)

for router_module in (api, bypass, deferreds, events, schedules, webhooks):
    app.include_router(router_module.router)
